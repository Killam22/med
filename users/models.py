from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
import random
from django.utils import timezone
from django.conf import settings
 

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

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    role                = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    
    SEX_CHOICES = [('male','Male'), ('female','Female')]
    first_name        = models.CharField(max_length=50, blank=True)
    last_name         = models.CharField(max_length=50, blank=True)
    sex               = models.CharField(max_length=10, choices=SEX_CHOICES, blank=True)
    date_of_birth     = models.DateField(null=True, blank=True)
    phone             = models.CharField(max_length=20, blank=True)
    id_card_number = models.CharField(max_length=50, blank=True)
    id_card_recto = models.ImageField(upload_to='id_cards/', null=True, blank=True)
    id_card_verso = models.ImageField(upload_to='id_cards/', null=True, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    address           = models.CharField(max_length=255, blank=True)
    postal_code       = models.CharField(max_length=10, blank=True)
    city              = models.CharField(max_length=100, blank=True)
    wilaya            = models.CharField(max_length=100, blank=True)
    # Champs hérités de l'ancien modèle (encore présents en DB)
    blood_type        = models.CharField(max_length=5, blank=True, default='')
    emergency_contact = models.CharField(max_length=100, blank=True, default='')
    access_level      = models.IntegerField(blank=True, default=1)
    # ─────────────────────────────────────────────────────────────────
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default='pending')
    created_at          = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"

    def is_verified(self):
        return self.verification_status == 'verified'
    

 
class EmailOTP(models.Model):
    """
    Stores a 6-digit OTP tied to an email address.
    Used for both registration verification and password reset.
    """
    PURPOSE_REGISTER = 'register'
    PURPOSE_RESET    = 'reset'
    PURPOSE_CHOICES  = [
        (PURPOSE_REGISTER, 'Registration'),
        (PURPOSE_RESET,    'Password Reset'),
    ]
 
    email      = models.EmailField()
    otp        = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=16, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used    = models.BooleanField(default=False)
 
    class Meta:
        ordering = ['-created_at']
 
    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)
 
    @classmethod
    def generate(cls, email, purpose):
        # Invalidate any previous unused OTPs for this email+purpose
        cls.objects.filter(email=email, purpose=purpose, is_used=False).delete()
        otp = f"{random.randint(0, 999999):06d}"
        return cls.objects.create(email=email, otp=otp, purpose=purpose)
 
    def __str__(self):
        return f"{self.email} — {self.purpose} — {self.otp}"