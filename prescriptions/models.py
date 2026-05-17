import uuid
import hmac
import hashlib
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from consultations.models import Consultation
from medications.models import Medication

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

    @property
    def external_patient(self):
        return self.consultation.external_patient

    @property
    def patient_name(self):
        if self.consultation.patient_id:
            return self.consultation.patient.user.get_full_name()
        if self.consultation.external_patient_id:
            ep = self.consultation.external_patient
            return f"{ep.first_name} {ep.last_name}"
        return "—"


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
    medication = models.ForeignKey(
        Medication, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescription_items'
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
    token             = models.CharField(max_length=64, unique=True)
    digital_signature = models.CharField(max_length=64, blank=True)
    is_used           = models.BooleanField(default=False)
    expires_at        = models.DateTimeField()
    scanned_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='qr_scans'
    )
    scanned_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def _compute_signature(token: str, prescription_id: str, doctor_id: int) -> str:
        """
        Génère une signature HMAC-SHA256 liant le token à l'ordonnance et au médecin.
        Prouve que le QR a été émis par notre serveur et n'a pas été falsifié.
        """
        secret = getattr(settings, 'SECRET_KEY', 'fallback-secret').encode()
        payload = f"{token}:{prescription_id}:{doctor_id}".encode()
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=90)
        # Génère la signature numérique à la création
        if not self.digital_signature and self.prescription_id:
            try:
                doc_id = self.prescription.doctor.id
                self.digital_signature = self._compute_signature(
                    self.token, str(self.prescription_id), doc_id
                )
            except Exception:
                pass
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def verify_signature(self) -> bool:
        """Vérifie que le QR n'a pas été falsifié depuis son émission."""
        if not self.digital_signature:
            return False
        try:
            doc_id = self.prescription.doctor.id
            expected = self._compute_signature(
                self.token, str(self.prescription_id), doc_id
            )
            return hmac.compare_digest(self.digital_signature, expected)
        except Exception:
            return False


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
'''
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
'''
