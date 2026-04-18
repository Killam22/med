from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import NotificationPreferences


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_notification_preferences(sender, instance, created, **kwargs):
    """
    Auto-create a NotificationPreferences record whenever a new user is created.
    This ensures every user always has preferences without needing to create manually.
    """
    if created:
        NotificationPreferences.objects.get_or_create(user=instance)