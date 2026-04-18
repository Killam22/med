"""
notifications/utils.py

Use this helper anywhere in your project to create a Notification.
It automatically checks the user's NotificationPreferences before creating.

Usage example (in your pharmacists app):
    from notifications.utils import send_notification

    send_notification(
        user=order.patient,
        title="Your order is ready",
        message="Your pharmacy order is ready to be picked up.",
        notif_type='pharmacy'
    )
"""

from .models import Notification


def send_notification(user, title: str, message: str, notif_type: str) -> Notification | None:
    """
    Creates a Notification for `user` only if their preferences allow it.

    Args:
        user:       The CustomUser recipient.
        title:      Short title for the notification.
        message:    Full notification body.
        notif_type: One of 'appointment' | 'pharmacy' | 'caretaker' | 'system'

    Returns:
        The created Notification instance, or None if blocked by preferences.
    """
    # Check preferences — if the user has no prefs record yet, default to allow
    try:
        prefs = user.notification_preferences
        if not prefs.is_type_enabled(notif_type):
            return None
    except Exception:
        pass  # No prefs record yet → allow by default

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notif_type,
    )