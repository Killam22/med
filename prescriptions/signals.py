from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Prescription, QRToken

@receiver(post_save, sender=Prescription)
def create_prescription_qr_token(sender, instance, created, **kwargs):
    """
    Crée automatiquement un QRToken dès qu'une ordonnance est générée.
    """
    if created:
        # Vérifie si un token n'existe pas déjà (au cas où)
        if not hasattr(instance, 'qr_token'):
            QRToken.objects.create(prescription=instance)
