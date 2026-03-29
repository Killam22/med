from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('pharmacist', 'Pharmacist'),
        ('caretaker', 'Caretaker'),
        ('admin', 'Admin'),
    )

    SEX_CHOICES = (
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    )

    VERIFICATION_STATUS = (
        ('unverified', 'Non vérifié'),
        ('pending', 'En attente'),
        ('verified', 'Vérifié'),
        ('rejected', 'Rejeté'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Common profile fields
    id_card_number = models.CharField(max_length=50, blank=True)
    id_card_photo = models.ImageField(upload_to='id_cards/', null=True, blank=True)
    address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    wilaya = models.CharField(max_length=100, blank=True)
    
    # Specific fields from original projects
    blood_type = models.CharField(max_length=5, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    access_level = models.IntegerField(default=1) # Original app field
    
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS, 
        default='unverified'
    )

    # Use email as username
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.role})"

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
