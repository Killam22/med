import uuid
from django.db import models
from django.conf import settings
from users.validators import validate_file_type

class Caretaker(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='caretaker_profile')
    certification = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    availability_area = models.CharField(max_length=200, blank=True)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True, help_text="Visible dans les recherches des patients")
    criminal_record_scan = models.FileField(upload_to='caretaker_records/', validators=[validate_file_type], null=True, blank=False) 
    tarif_de_base = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"GM. {self.user.last_name} (Garde-Malade)"

class CaretakerService(models.Model):
    caretaker = models.ForeignKey(Caretaker, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=200)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.service_name} ({self.caretaker.user.get_full_name()})"

class CareRequest(models.Model):
    """La demande (ou offre d'emploi) envoyée par le patient au garde-malade"""
    class Status(models.TextChoices):
        PENDING   = 'pending',   'En attente'
        ACCEPTED  = 'accepted',  'Acceptée'
        REJECTED  = 'rejected',  'Refusée'
        COMPLETED = 'completed', 'Terminée'
        CANCELLED = 'cancelled', 'Annulée'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_care_requests')
    caretaker = models.ForeignKey(Caretaker, on_delete=models.CASCADE, related_name='received_requests')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    patient_message = models.TextField(help_text="Détails des tâches et besoins médicaux")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Demande {self.status} : Patient {self.patient.get_full_name()} -> {self.caretaker.user.get_full_name()}"

class CareMessage(models.Model):
    """Messagerie instantanée liée à une demande spécifique"""
    request = models.ForeignKey(CareRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class CaretakerCertificate(models.Model):
    caretaker = models.ForeignKey(Caretaker, on_delete=models.CASCADE, related_name='certificates')
    name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)
    date_obtained = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)
    scan = models.FileField(upload_to='caretaker_certificates/', validators=[validate_file_type])

    def __str__(self):
        return f"{self.name} - {self.caretaker.user.last_name}"