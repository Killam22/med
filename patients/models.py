from django.db import models
from  users.models import CustomUser  
# patients/models.py
class Patient(models.Model):
    user              = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='patient_profile')
    blood_group        = models.CharField(max_length=5, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    access_level      = models.CharField(max_length=30, default='private')

    def __str__(self):
        return f"Patient: {self.user.username}"

class MedicalProfile(models.Model):
    patient      = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='medical_profile')
    allergies    = models.JSONField(default=list, blank=True)   # ["Penicillin","Pollen"]
    vaccinations = models.JSONField(default=list, blank=True)


    def __str__(self):
        return f"Profile: {self.patient.user.username}"


class Antecedent(models.Model):
    STATUS_CHOICES = [('chronic','Chronic'),('resolved','Resolved'),('ongoing','Ongoing')]

    patient        = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='antecedents')
    name           = models.CharField(max_length=200)
    diagnosed_year = models.IntegerField(null=True, blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    icon           = models.CharField(max_length=10, blank=True)  # emoji

    def __str__(self):
        return f"{self.name} — {self.patient}"


class Treatment(models.Model):
    patient      = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    name         = models.CharField(max_length=200)
    dosage       = models.CharField(max_length=100, blank=True)
    frequency    = models.CharField(max_length=100, blank=True)
    start_date   = models.DateField(null=True, blank=True)
    end_date     = models.DateField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.dosage}) — {self.patient}"


class LabResult(models.Model):
    patient        = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_results')
    lab_name       = models.CharField(max_length=200, blank=True)
    analysis_type  = models.CharField(max_length=100)
    date           = models.DateField()
    values         = models.JSONField(default=dict)
    interpretation = models.TextField(blank=True)
    ai_summary     = models.TextField(blank=True)
    is_abnormal    = models.BooleanField(default=False)
    report_file    = models.FileField(upload_to='lab_reports/', null=True, blank=True)

    def __str__(self):
        return f"{self.analysis_type} — {self.patient} ({self.date})"


class SymptomAnalysis(models.Model):
    URGENCY_CHOICES = [('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')]

    patient               = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='symptom_analyses')
    analysis_date         = models.DateTimeField(auto_now_add=True)
    symptoms              = models.JSONField()
    provisional_diagnosis = models.TextField(blank=True)
    urgency_level         = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='low')
    suggestions           = models.TextField(blank=True)

    def __str__(self):
        return f"Analysis #{self.id} — {self.patient} ({self.urgency_level})"