from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')  # ← force admin role
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return super().create_superuser(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('patient',    'Patient'),
        ('doctor',     'Doctor'),
        ('pharmacist', 'Pharmacist'),
        ('caretaker',  'Caretaker'),
        ('admin',      'Admin'),
    )
    VERIFICATION_CHOICES = (
        ('pending',  'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    objects = CustomUserManager()  # ← attach the custom manager

    user_id             = models.AutoField(primary_key=True)
    role                = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    
    SEX_CHOICES = [('male','Male'), ('female','Female')]
    first_name        = models.CharField(max_length=50, blank=True)
    last_name         = models.CharField(max_length=50, blank=True)
    sex               = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    date_of_birth     = models.DateField(null=True, blank=True)
    phone             = models.CharField(max_length=20, blank=True)
    id_card_number    = models.CharField(max_length=50, blank=True)
    id_card_photo     = models.ImageField(upload_to='id_cards/', null=True, blank=True)
    address           = models.CharField(max_length=255, blank=True)
    postal_code       = models.CharField(max_length=10, blank=True)
    city              = models.CharField(max_length=100, blank=True)
    wilaya            = models.CharField(max_length=100, blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default='pending')
    created_at          = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    def is_verified(self):
        return self.verification_status == 'verified'