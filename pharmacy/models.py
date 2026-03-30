import uuid
from django.db import models
from django.conf import settings
from patients.models import Patient
from prescriptions.models import Prescription

class Pharmacist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacist_profile')
    license_number = models.CharField(max_length=50, unique=True)
    pharmacy_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pharmacy_name} ({self.user.get_full_name()})"

class PharmacyBranch(models.Model):
    pharmacist = models.ForeignKey(Pharmacist, on_delete=models.CASCADE, related_name='branches')
    branch_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_open_24h = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.branch_name} - {self.pharmacist.pharmacy_name}"

class PharmacyOrder(models.Model):
    """Commande envoyée par un patient à une pharmacie depuis son ordonnance."""
    class Status(models.TextChoices):
        PENDING    = 'pending',    'En attente'
        PREPARING  = 'preparing',  'En préparation'
        READY      = 'ready',      'Prête à récupérer'
        DELIVERED  = 'delivered',  'Livrée'
        CANCELLED  = 'cancelled',  'Annulée'

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pharmacy_orders')
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name='pharmacy_orders')
    pharmacist   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_orders')
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    patient_message = models.TextField(blank=True)
    pharmacist_note = models.TextField(blank=True)
    estimated_ready = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Commande {self.id} — {self.patient.get_full_name()}"