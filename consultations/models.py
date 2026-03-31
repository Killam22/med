import uuid
from django.db import models
from django.conf import settings
from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment


class Consultation(models.Model):

    class Status(models.TextChoices):
        SCHEDULED  = 'scheduled',  'Planifiée'
        IN_PROGRESS = 'in_progress', 'En cours' 
        COMPLETED  = 'completed',  'Terminée'
        CANCELLED  = 'cancelled',  'Annulée'

    class ConsultationType(models.TextChoices):
        IN_PERSON        = 'in_person',        'En cabinet'
        TELECONSULTATION = 'teleconsultation', 'Téléconsultation'
        HOME_VISIT       = 'home_visit',       'Visite à domicile'

    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Acteurs — doctor et patient restent directs car
    # consultation peut exister sans appointment (urgence, téléconsult libre)
    doctor  = models.ForeignKey(Doctor,on_delete=models.PROTECT,related_name='consultations_as_doctor')
    patient = models.ForeignKey(Patient,on_delete=models.PROTECT,related_name='consultations_as_patient')

    # Lien optionnel au rendez-vous d'origine
    appointment = models.OneToOneField(Appointment,on_delete=models.SET_NULL,null=True, blank=True,related_name='consultation')

    consultation_type = models.CharField(max_length=30,choices=ConsultationType.choices,default=ConsultationType.IN_PERSON)
    status = models.CharField(max_length=20,choices=Status.choices,default=Status.SCHEDULED)

    # Compte rendu médical
    chief_complaint   = models.TextField()             # Motif de consultation
    history           = models.TextField(blank=True)   # Anamnèse
    examination       = models.TextField(blank=True)   # Examen clinique
    diagnosis         = models.TextField(blank=True)   # Diagnostic retenu
    treatment_plan    = models.TextField(blank=True)   # Plan de traitement
    doctor_notes      = models.TextField(blank=True)   # Notes internes médecin
    follow_up_date    = models.DateField(null=True, blank=True)
    follow_up_notes   = models.TextField(blank=True)

    # Constantes vitales relevées pendant la consultation
    vitals = models.TextField(blank=True)
    # ex: {"bp": "138/88", "hr": 78, "temp": 37.2, "weight": 72, "spo2": 98}

    consulted_at = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-consulted_at']

    def __str__(self):
        return (
            f"Consultation {self.doctor.user.get_full_name()} / "
            f"{self.patient.user.get_full_name()} — {self.consulted_at:%d/%m/%Y}"
        )
