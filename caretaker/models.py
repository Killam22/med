from django.db import models
from django.conf import settings

class Caretaker(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='caretaker_profile')
    certification = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    availability_area = models.CharField(max_length=200, blank=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Soin à domicile - {self.user.get_full_name()}"

class CaretakerService(models.Model):
    caretaker = models.ForeignKey(Caretaker, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=200)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.service_name} ({self.caretaker.user.get_full_name()})"
