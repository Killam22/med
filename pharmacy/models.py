# pharmacy/models.py
from django.db import models
from users.models import CustomUser


class Pharmacist(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='pharmacist_profile')

    def __str__(self):
        return f"Pharmacist: {self.user.first_name} {self.user.last_name}"

    def get_initials(self):
        fn = self.user.first_name
        ln = self.user.last_name
        return f"{fn[0].upper()}{ln[0].upper()}" if fn and ln else "?"


class Pharmacist_Professional_info(models.Model):
    pharmacist                      = models.OneToOneField(Pharmacist, on_delete=models.CASCADE, related_name='professional_info')
    oharmacist_diplome              = models.ImageField(upload_to='pharmacists/diplome/', null=True, blank=True)
    pharmacy_numero_ordre                    = models.CharField(max_length=100, blank=True)
    pharmacy_autorisation_ouverture          = models.ImageField(upload_to='pharmacists/autorisation/', null=True, blank=True)
    pharmacy_numero_registre_commerce        = models.CharField(max_length=100, blank=True)
    PHARMACY_CNAS_CHOICES                    = [('oui', 'Oui'), ('non', 'Non')]
    pharmacy_convention_cnas                 = models.CharField(max_length=10, choices=PHARMACY_CNAS_CHOICES, default='non')

    def __str__(self):
        return f"Pro info: {self.pharmacist}"


class Pharmacy(models.Model):
    pharmacist              = models.OneToOneField(Pharmacist, on_delete=models.CASCADE, related_name='pharmacy')
    pharmacy_name           = models.CharField(max_length=200)
    pharmacy_address                 = models.TextField(blank=True)
    pharmacy_hours                = models.CharField(max_length=200, blank=True)
    pharmacy_license_number          = models.CharField(max_length=100, blank=True)
    pharmacy_location                = models.CharField(max_length=100, blank=True)
    is_verified             = models.BooleanField(default=False)

    def __str__(self):
        return self.pharmacy_name


