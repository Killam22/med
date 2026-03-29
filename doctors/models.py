from django.db import models
from django.conf import settings

class Doctor(models.Model):
    SPECIALTY_CHOICES = (
        ('general', 'Médecine Générale'),
        ('cardiology', 'Cardiologie'),
        ('dermatology', 'Dermatologie'),
        ('gynecology', 'Gynécologie'),
        ('pediatrics', 'Pédiatrie'),
        ('ophthalmology', 'Ophtalmologie'),
        ('ent', 'O.R.L'),
        ('orthopedics', 'Orthopédie'),
        ('neurology', 'Neurologie'),
        ('psychiatry', 'Psychiatrie'),
        ('dentistry', 'Dentisterie'),
        ('urology', 'Urologie'),
        ('oncology', 'Oncologie'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=50, choices=SPECIALTY_CHOICES, default='general')
    license_number = models.CharField(max_length=50, unique=True)
    clinic_name = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    photo = models.ImageField(upload_to='doctors/', null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    languages = models.CharField(max_length=200, blank=True, help_text="Ex: Français, Arabe, Anglais")

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

class Doctor_professionel_info(models.Model):
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE, related_name='professional_info')
    diploma = models.FileField(upload_to='diplomas/', null=True, blank=True)
    order_registration_number = models.CharField(max_length=100, blank=True)
    cv = models.FileField(upload_to='cvs/', null=True, blank=True)
    
    def __str__(self):
        return f"Infos Pro - {self.doctor}"

class Exercice(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='exercises')
    establishment_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_main_location = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.establishment_name} ({self.doctor})"
