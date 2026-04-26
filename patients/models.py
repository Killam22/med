from django.db import models
from django.conf import settings
from users.validators import validate_file_type

class Patient(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')

    def __str__(self):
        return f"{self.user.get_full_name()} (Patient)"

    @property
    def age(self):
        from datetime import date
        if self.user.date_of_birth:
            today = date.today()
            return today.year - self.user.date_of_birth.year - (
                (today.month, today.day) < (self.user.date_of_birth.month, self.user.date_of_birth.day)
            )
        return None

class MedicalProfile(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+','A+'), ('A-','A-'), ('B+','B+'), ('B-','B-'),
        ('AB+','AB+'), ('AB-','AB-'), ('O+','O+'), ('O-','O-'),
    ]
    patient = models.OneToOneField(
        Patient, on_delete=models.CASCADE, related_name='medical_profile'
    )
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True
    )
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    @property
    def bmi(self):
        """IMC calculé automatiquement"""
        if self.weight and self.height:
            return round(self.weight / (self.height / 100) ** 2, 1)
        return None

    def __str__(self):
        return f"Profil — {self.patient}"

class Allergy(models.Model):
    SEVERITY = [
        ('mild', 'Légère'),
        ('moderate', 'Modérée'),
        ('severe', 'Sévère'),
    ]
    profile = models.ForeignKey(
        MedicalProfile, on_delete=models.CASCADE, related_name='allergies'
    )
    substance = models.CharField(max_length=200)  # "Pénicilline", "Pollen"
    severity = models.CharField(max_length=10, choices=SEVERITY, default='mild')
    reaction = models.TextField(blank=True)       # "Choc anaphylactique"

    def __str__(self):
        return f"{self.substance} ({self.get_severity_display()})"

class Antecedent(models.Model):
    TYPE_CHOICES = [('personnel', 'Personnel'), ('familial', 'Familial')]
    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('resolved', 'Résolu'),
        ('chronic', 'Chronique'),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='antecedents'
    )
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='active'
    )
    description = models.TextField(blank=True)
    date_diagnosis = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-date_diagnosis']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()} — {self.get_status_display()})"

class Treatment(models.Model):
    FREQUENCY_CHOICES = [
        ('1x_day', '1× par jour'),
        ('2x_day', '2× par jour'),
        ('3x_day', '3× par jour'),
        ('weekly', 'Hebdomadaire'),
        ('as_needed', 'Si besoin'),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='treatments'
    )
    prescribed_by = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prescribed_treatments'
    )
    medication = models.ForeignKey(
        'medications.Medication',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='patient_treatments'
    )
    medication_name = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    @property
    def is_active(self):
        from django.utils import timezone
        if self.is_ongoing:
            return True
        return self.end_date and self.end_date >= timezone.now().date()

    def __str__(self):
        return f"{self.medication_name} {self.dosage} — {self.patient}"

class SymptomAnalysis(models.Model):
    URGENCY_CHOICES = [
        ('low', 'Faible'),
        ('moderate', 'Modérée'),
        ('high', 'Élevée'),
        ('emergency', 'Urgence'),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='symptom_analyses'
    )
    symptoms = models.TextField(help_text="Symptômes décrits par le patient")
    suggested_diagnosis = models.TextField(blank=True)
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='low')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"IA — {self.patient} ({self.created_at:%Y-%m-%d})"


class MedicalDocument(models.Model):
    DOCUMENT_TYPES = [
        ('lab_result', 'Résultat d\'analyse'),
        ('imaging', 'Imagerie (Radio/Scanner)'),
        ('prescription', 'Ordonnance'),
        ('report', 'Compte-rendu'),
        ('other', 'Autre'),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='medical_documents'
    )
    name = models.CharField(max_length=200)
    document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPES, default='other'
    )
    date = models.DateField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    is_visible_to_patient = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.name} ({self.date})"


class DocumentFile(models.Model):
    """Séparé pour permettre plusieurs fichiers par document"""
    document = models.ForeignKey(
        MedicalDocument, on_delete=models.CASCADE, related_name='files'
    )
    file = models.FileField(
        upload_to='medical_documents/%Y/%m/',
        validators=[validate_file_type]
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # en bytes

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
