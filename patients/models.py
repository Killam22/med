from django.db import models
from django.conf import settings
from users.validators import validate_file_type

class Patient(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')

    photo = models.ImageField(upload_to='patients/', null=True, blank=True)
    blood_group = models.CharField(max_length=5, blank=True) # Redundant but kept for teammate's code compatibility
    
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
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='medical_profile')
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    allergies = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)

    def __str__(self):
        return f"Profil Médical - {self.patient}"

class Antecedent(models.Model):
    TYPES = (('personnel', 'Personnel'), ('familial', 'Familial'))
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='antecedents')
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPES)
    description = models.TextField(blank=True)
    date_diagnosis = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.type})"

class Treatment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.medication_name} - {self.patient}"

class LabResult(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_results')
    test_name = models.CharField(max_length=200)
    date = models.DateField()
    result_value = models.TextField()
    files = models.FileField(upload_to='lab_results/', null=True, blank=True, validators=[validate_file_type])

    def __str__(self):
        return f"{self.test_name} ({self.date})"

class SymptomAnalysis(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='symptom_analyses')
    symptoms = models.TextField()
    possible_diagnosis = models.TextField(blank=True)
    severity_level = models.IntegerField(default=1) # 1-5
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analyse {self.date.date()} - {self.patient}"
