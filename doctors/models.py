
# doctors/models.py
from django.db import models
from users.models import CustomUser
class Doctor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='doctor_profile')
    def __str__(self):  
        return f"Doctor: {self.user.username}"

class Doctor_professionel_info(models.Model):
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE, related_name='doctor_professionel_info')
    
    doctor_professional_phone = models.CharField(max_length=20, blank=True)
    doctor_diplome = models.ImageField(upload_to='diplome_images/', null=True, blank=True)
    doctor_experience_years = models.IntegerField(null=True, blank=True)
    doctor_medical_speciality = models.CharField(max_length=255, blank=True)
    doctor_num_denregistration_au_conseil_de_ordre = models.CharField(max_length=255, blank=True) 
    doctor_license_number = models.CharField(max_length=255, blank=True) # Numéro de licence professionnelle
    doctor_authorisation_exercer =models.ImageField(upload_to='autorisation_exercer_images/', null=True, blank=True)
    DOCTOR_CNAS_CHOICES = [('oui','Oui'), ('non','Non')]
    doctor_convention_cnas = models.CharField(max_length=10, choices=DOCTOR_CNAS_CHOICES, default='non')
   
    
# Create your models here.
class Exercice(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='exercices')
    ETABLISSEMENT_TYPE = [('prive', 'Privé'), ('public', 'Public'),('adomicile', 'Adomicile')]
    type_etablissement = models.CharField(max_length=10, choices=ETABLISSEMENT_TYPE, default='prive')
    nom_etablissement = models.CharField(max_length=255, blank=True)
    adresse_etablissement = models.CharField(max_length=255, blank=True)
    doctor_exercer_hours = models.CharField(max_length=255, blank=True)