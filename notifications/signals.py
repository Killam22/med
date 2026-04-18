"""
notifications/signals.py

Auto-fires send_notification() when key business events happen.
No need to touch your views — signals listen to model saves automatically.

Covers:
  - PharmacyOrder  : status changes
  - CareRequest    : status changes
  - CustomUser     : verification_status changes
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .utils import send_notification

User = get_user_model()


# ─────────────────────────────────────────────────────────────
# HELPER — store old value before save so we can detect changes
# ─────────────────────────────────────────────────────────────
@receiver(pre_save, sender='pharmacists.PharmacyOrder')
def cache_old_order_status(sender, instance, **kwargs):
    """Store the previous status before the save so post_save can compare."""
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(pre_save, sender='caretakers.CareRequest')
def cache_old_care_request_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(pre_save, sender=User)
def cache_old_verification_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_verification = sender.objects.get(pk=instance.pk).verification_status
        except sender.DoesNotExist:
            instance._old_verification = None
    else:
        instance._old_verification = None


# ─────────────────────────────────────────────────────────────
# 1. PHARMACY ORDER — notify patient on every status change
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='pharmacists.PharmacyOrder')
def notify_pharmacy_order_status(sender, instance, created, **kwargs):

    # Notify pharmacist when a NEW order arrives
    if created:
        pharmacist_user = instance.pharmacist
        if pharmacist_user:
            send_notification(
                user=pharmacist_user,
                title="Nouvelle commande reçue",
                message=f"Vous avez reçu une nouvelle commande de {instance.patient.get_full_name()}.",
                notif_type='pharmacy'
            )
        return

    # Notify patient when status changes
    old_status = getattr(instance, '_old_status', None)
    if old_status == instance.status:
        return  # No change, skip

    STATUS_MESSAGES = {
        'preparing': (
            "Commande en préparation",
            "Votre commande est en cours de préparation par la pharmacie."
        ),
        'ready': (
            "Commande prête",
            "Votre commande est prête à être récupérée."
        ),
        
        'cancelled': (
            "Commande annulée",
            "Votre commande a été annulée."
        ),
    }

    if instance.status in STATUS_MESSAGES:
        title, message = STATUS_MESSAGES[instance.status]
        send_notification(
            user=instance.patient,
            title=title,
            message=message,
            notif_type='pharmacy'
        )


# ─────────────────────────────────────────────────────────────
# 2. CARE REQUEST — notify both patient and caretaker
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='caretakers.CareRequest')
def notify_care_request_status(sender, instance, created, **kwargs):

    # Notify caretaker when a NEW request arrives
    if created:
        send_notification(
            user=instance.caretaker.user,
            title="Nouvelle demande de soin",
            message=f"{instance.patient.get_full_name()} vous a envoyé une demande de soin.",
            notif_type='caretaker'
        )
        return

    # Notify patient when status changes
    old_status = getattr(instance, '_old_status', None)
    if old_status == instance.status:
        return

    STATUS_MESSAGES = {
        'accepted': (
            "Demande acceptée",
            f"{instance.caretaker.user.get_full_name()} a accepté votre demande de soin.",
            instance.patient,
        ),
        'rejected': (
            "Demande refusée",
            f"{instance.caretaker.user.get_full_name()} a refusé votre demande de soin.",
            instance.patient,
        ),
        'completed': (
            "Soin terminé",
            f"Votre demande de soin avec {instance.caretaker.user.get_full_name()} est terminée.",
            instance.patient,
        ),
        'cancelled': (
            "Demande annulée",
            "Une demande de soin a été annulée.",
            instance.caretaker.user,
        ),
    }

    if instance.status in STATUS_MESSAGES:
        title, message, recipient = STATUS_MESSAGES[instance.status]
        send_notification(
            user=recipient,
            title=title,
            message=message,
            notif_type='caretaker'
        )


# ─────────────────────────────────────────────────────────────
# 3. USER VERIFICATION — notify user when admin verifies/rejects
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender=User)
def notify_verification_status(sender, instance, created, **kwargs):
    if created:
        return  # Skip on registration

    old_verification = getattr(instance, '_old_verification', None)
    if old_verification == instance.verification_status:
        return  # No change, skip

    if instance.verification_status == 'verified':
        send_notification(
            user=instance,
            title="Compte vérifié ✓",
            message="Votre compte a été vérifié avec succès. Vous avez maintenant accès à toutes les fonctionnalités.",
            notif_type='system'
        )

    elif instance.verification_status == 'rejected':
        send_notification(
            user=instance,
            title="Vérification refusée",
            message="Votre demande de vérification a été refusée. Veuillez contacter le support.",
            notif_type='system'
        )