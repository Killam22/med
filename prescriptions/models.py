import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from consultations.models import Consultation

class Prescription(models.Model):

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        EXPIRED   = 'expired',   'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        PENDING   = 'pending',   'En attente CNAS'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(Consultation,on_delete=models.CASCADE,related_name='prescriptions')    
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes       = models.TextField(blank=True)
    valid_until = models.DateField()                          # date d'expiration
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"RX-{str(self.id)[:8].upper()} — {self.patient}"

    def is_expired(self):
        return self.valid_until < timezone.now().date()

    def save(self, *args, **kwargs):
        # auto-expire
        if self.is_expired() and self.status == self.Status.ACTIVE:
            self.status = self.Status.EXPIRED
        super().save(*args, **kwargs)
    @property
    def doctor(self):
        return self.consultation.doctor

    @property
    def patient(self):
        return self.consultation.patient    


class PrescriptionItem(models.Model):

    class Frequency(models.TextChoices):
        ONCE_DAILY    = '1x_day',  '1 fois/jour'
        TWICE_DAILY   = '2x_day',  '2 fois/jour'
        THREE_DAILY   = '3x_day',  '3 fois/jour'
        EVERY_8H      = 'every_8h','Toutes les 8h'
        AS_NEEDED     = 'as_needed','Au besoin'

    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name='items'
    )
    drug_name    = models.CharField(max_length=200)       # ex: Metformin
    molecule     = models.CharField(max_length=200, blank=True)  # ex: Metformine HCl
    dosage       = models.CharField(max_length=100)       # ex: 500mg
    frequency    = models.CharField(max_length=20, choices=Frequency.choices)
    duration     = models.CharField(max_length=100)       # ex: 30 jours
    instructions = models.TextField(blank=True)           # ex: prendre avec le repas
    quantity     = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.drug_name} {self.dosage} — {self.get_frequency_display()}"


class QRToken(models.Model):
    prescription = models.OneToOneField(
        Prescription, on_delete=models.CASCADE, related_name='qr_token'
    )
    token      = models.CharField(max_length=64, unique=True)
    is_used    = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='qr_scans'
    )
    scanned_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            # expire dans 3 mois par défaut
            self.expires_at = timezone.now() + timedelta(days=90)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class CNASCoverage(models.Model):

    class CoverageStatus(models.TextChoices):
        PENDING  = 'pending',  'En attente'
        APPROVED = 'approved', 'Approuvé'
        REJECTED = 'rejected', 'Rejeté'

    prescription    = models.OneToOneField(
        Prescription, on_delete=models.CASCADE, related_name='cnas_coverage'
    )
    cnas_number     = models.CharField(max_length=100)
    coverage_rate   = models.DecimalField(max_digits=5, decimal_places=2)  # ex: 80.00
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    covered_amount  = models.DecimalField(max_digits=10, decimal_places=2)
    patient_pays    = models.DecimalField(max_digits=10, decimal_places=2)
    status          = models.CharField(
        max_length=20, choices=CoverageStatus.choices, default=CoverageStatus.PENDING
    )
    verified_at     = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

class Medication(models.Model):
    """Catalogue des médicaments de la plateforme."""

    class Category(models.TextChoices):
        CARDIO      = 'cardio',      'Cardiologie'
        DIABETES    = 'diabetes',    'Diabétologie'
        ANTIBIOTIC  = 'antibiotic',  'Antibiotique'
        ANALGESIC   = 'analgesic',   'Analgésique'
        ANTI_INFLAM = 'anti_inflam', 'Anti-inflammatoire'
        GASTRO      = 'gastro',      'Gastro-entérologie'
        NEURO       = 'neuro',       'Neurologie'
        OTHER       = 'other',       'Autre'

    name         = models.CharField(max_length=200, unique=True)   # Metformin
    molecule     = models.CharField(max_length=200, blank=True)    # Metformine HCl
    category     = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description  = models.TextField(blank=True)
    dosage_forms = models.JSONField(default=list)   # ["500mg", "850mg", "1g"]
    side_effects = models.TextField(blank=True)
    interactions = models.TextField(blank=True)     # interactions médicamenteuses
    contraindications = models.TextField(blank=True)
    price_dzd    = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    cnas_covered = models.BooleanField(default=False)
    requires_prescription = models.BooleanField(default=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.molecule}"
    