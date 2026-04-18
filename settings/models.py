from django.db import models
from django.conf import settings


class NotificationPreferences(models.Model):
    """
    Stores the user's preferences for HOW and WHICH notifications they want.
    The actual Notification objects live in the `notifications` app.
    This model only controls delivery/filtering preferences.

    Type toggles map directly to notifications.Notification.NotificationType choices:
        appointment, pharmacy, caretaker, system
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # ── Type toggles (match NotificationType in notifications app) ──
    notify_appointment = models.BooleanField(default=True, help_text="Appointment notifications")
    notify_pharmacy    = models.BooleanField(default=True, help_text="Pharmacy / order notifications")
    notify_caretaker   = models.BooleanField(default=True, help_text="Caretaker request notifications")
    notify_system      = models.BooleanField(default=True, help_text="System notifications")

    # ── Channel preferences ──────────────────────────────────────────
    email_notifications = models.BooleanField(default=True)
    sms_notifications   = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NotifPrefs — {self.user.email}"

    def is_type_enabled(self, notification_type: str) -> bool:
        """
        Helper used by the notifications app before creating a Notification.
        Example:
            prefs = user.notification_preferences
            if prefs.is_type_enabled('pharmacy'):
                Notification.objects.create(...)
        """
        mapping = {
            'appointment': self.notify_appointment,
            'pharmacy':    self.notify_pharmacy,
            'caretaker':   self.notify_caretaker,
            'system':      self.notify_system,
        }
        return mapping.get(notification_type, True)