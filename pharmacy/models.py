import uuid
from django.db import models
from django.conf import settings
from patients.models import Patient
from prescriptions.models import Prescription
from medications.models import Medication
from users.validators import validate_file_type

class Pharmacist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacist_profile')
    order_registration_number = models.CharField(max_length=100, unique=True, blank = False, help_text="Numéro d'ordre", default = "")
    is_verified = models.BooleanField(default=False)
    cnas_coverage = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.last_name} (Pharmacien)"


class Pharmacy(models.Model):
    pharmacist = models.OneToOneField(Pharmacist, on_delete=models.CASCADE, related_name='pharmacy')
    name = models.CharField(max_length=200)
    pharm_address = models.TextField()
    pharm_city = models.CharField(max_length=100)
    pharm_phone = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_open_24h = models.BooleanField(default=False)
    agreement_number = models.CharField(max_length=50, unique=True)
    agreement_scan = models.FileField(upload_to='agreement_scans/', null=True, blank=False, validators=[validate_file_type])
    registre_commerce = models.FileField(upload_to='registre_commerce/', null=True, blank=False, validators=[validate_file_type])
    def __str__(self):
        return f"Pharmacie {self.name} - {self.pharm_city}"


class PharmacistQualification(models.Model):
    pharmacist = models.ForeignKey(Pharmacist, on_delete=models.CASCADE, related_name='qualifications')
    title = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    graduation_year = models.PositiveIntegerField()
    degree_type = models.CharField(max_length=100)
    scan = models.FileField(upload_to='pharmacist_qualifications/', validators=[validate_file_type])

    def __str__(self):
        return f"{self.title} - {self.pharmacist.user.last_name}"

class PharmacyStock(models.Model):
    """Inventaire local de chaque pharmacie"""
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='stocks', default = 0)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='pharmacy_stocks')
    quantity = models.PositiveIntegerField(default=0)
    selling_price = models.DecimalField(max_digits=8, decimal_places=2, help_text="Prix de vente DZD en pharmacie")
    expiry_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('pharmacy', 'medication') # Un seul enregistrement par médicament par pharmacie

    def __str__(self):
        return f"{self.medication.name} - {self.pharmacy.branch_name} ({self.quantity} en stock)"

class PharmacyOrder(models.Model):
    """Commande envoyée par un patient à une pharmacie"""
    
    class Status(models.TextChoices): # Vos statuts existants
        PENDING    = 'pending',    'En attente'
        PREPARING  = 'preparing',  'En préparation'
        READY      = 'ready',      'Prête à récupérer'
        DELIVERED  = 'delivered',  'Livrée'
        CANCELLED  = 'cancelled',  'Annulée'

    class OrderType(models.TextChoices):
        PRESCRIPTION = 'prescription', 'Préparation d\'ordonnance'
        DIRECT = 'direct', 'Achat direct'

    class WithdrawalMethod(models.TextChoices):
        PATIENT = 'patient', 'Retrait par le patient'
        CARETAKER = 'caretaker', 'Retrait par le garde-malade'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pharmacy_orders')
    
    # MODIFICATION : Nullable car l'achat direct n'a pas d'ordonnance
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name='pharmacy_orders', null=True, blank=True)
    pharmacist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_orders')
    
    # NOUVEAUX CHAMPS
    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.PRESCRIPTION)
    withdrawal_method = models.CharField(max_length=20, choices=WithdrawalMethod.choices, default=WithdrawalMethod.PATIENT)
    caretaker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_orders', help_text="Garde-malade assigné si applicable")
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    patient_message = models.TextField(blank=True)
    pharmacist_note = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Prix total de la commande")
    estimated_ready = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)        

