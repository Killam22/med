from django.db import models
from django.conf import settings

class Pharmacist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pharmacist_profile')
    license_number = models.CharField(max_length=50, unique=True)
    pharmacy_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.pharmacy_name} ({self.user.get_full_name()})"

class PharmacyBranch(models.Model):
    pharmacist = models.ForeignKey(Pharmacist, on_delete=models.CASCADE, related_name='branches')
    branch_name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_open_24h = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.branch_name} - {self.pharmacist.pharmacy_name}"
