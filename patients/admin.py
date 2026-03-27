from django.contrib import admin
from .models import Patient, MedicalProfile, Antecedent, Treatment, LabResult, SymptomAnalysis

admin.site.register(Patient)
admin.site.register(MedicalProfile)
admin.site.register(Antecedent)
admin.site.register(Treatment)
admin.site.register(LabResult)
admin.site.register(SymptomAnalysis)
