from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

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
    practice_authorization = models.FileField(upload_to='doctor_authorizations/', null=True, blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"

class Doctor_professionel_info(models.Model):
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE, related_name='professional_info')
    diploma = models.ForeignKey('DoctorQualification', on_delete=models.SET_NULL, null=True, blank=True, related_name='professional_infos')
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

class WeeklySchedule(models.Model):
    DAY_CHOICES = [
        (0, 'Lundi'), (1, 'Mardi'),   (2, 'Mercredi'), (3, 'Jeudi'),
        (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche'),
    ]
    DURATION_CHOICES = [(15, '15 min'), (20, '20 min'), (30, '30 min'), (45, '45 min'), (60, '1h')]

    doctor        = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week   = models.IntegerField(choices=DAY_CHOICES)
    start_time    = models.TimeField()
    end_time      = models.TimeField()
    slot_duration = models.IntegerField(choices=DURATION_CHOICES, default=30)
    is_active     = models.BooleanField(default=True)

    class Meta:
        unique_together = ('doctor', 'day_of_week')
        verbose_name = "Planning hebdomadaire"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("L'heure de fin doit être après l'heure de début.")

    def __str__(self):
        return f"Dr.{self.doctor.user.last_name} — {self.get_day_of_week_display()} {self.start_time}–{self.end_time}"


class DayOff(models.Model):
    """A specific date the doctor is unavailable (holiday, leave, etc.)"""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='days_off')
    date   = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('doctor', 'date')
        verbose_name = "Jour de congé"

    def __str__(self):
        return f"Dr.{self.doctor.user.last_name} off — {self.date}"

class DoctorQualification(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='qualifications')
    title = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    graduation_year = models.PositiveIntegerField()
    degree_type = models.CharField(max_length=100)
    scan = models.FileField(upload_to='doctor_qualifications/')

    def __str__(self):
        return f"{self.title} - {self.doctor.user.last_name}"