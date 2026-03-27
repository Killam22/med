from django.db import models
from users.models import CustomUser


class Caretaker(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='caretaker_profile')
    def __str__(self):
        return f"Caretaker: {self.user.first_name} {self.user.last_name}"

    def get_initials(self):
        fn = self.user.first_name
        ln = self.user.last_name
        return f"{fn[0].upper()}{ln[0].upper()}" if fn and ln else "?"


class Caretaker_professional_info(models.Model):
    caretaker               = models.OneToOneField(Caretaker, on_delete=models.CASCADE, related_name='qualification')
    caretaker_diplome                 = models.ImageField(upload_to='caretakers/diplome/', null=True, blank=True)
    caretaker_certificat_formation    = models.ImageField(upload_to='caretakers/certificats/', null=True, blank=True)
    caretaker_experience_years       = models.IntegerField(default=0)
    caretaker_references              = models.TextField(blank=True)
    caretaker_type          = models.CharField(
                                max_length=20,
                                choices=[('assistant', 'Assistant'), ('infirmier', 'Infirmier'), ('aide-soignant', 'Aide_soignant'), ('auxiliare de vie', 'Auxiliare de vie'), ('paramedical', 'Paramedical'), ('family member', 'Family Member')],
                                default='assistant')
    is_available            = models.BooleanField(default=True)
    average_rating          = models.FloatField(default=0.0)

    def __str__(self):
        return f"caretaker_professional_info: {self.caretaker}"

# Create your models here.
