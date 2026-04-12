from django.db import models
# settings/models.py
from django.conf import settings


class UserSettings(models.Model):
    """
    One row per user. Created automatically on first access via
    UserSettings.objects.get_or_create(user=request.user).
    Covers: notification prefs, language, theme, privacy, 2FA flag.
    """

    LANGUAGE_CHOICES = [
        ('fr', 'Français'),
        ('ar', 'العربية'),
        ('en', 'English'),
    ]

    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark',  'Dark'),
        ('system', 'System'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings',
    )

    # ── Notifications ────────────────────────────────────────────────────────
    notif_appointments  = models.BooleanField(default=True,  help_text='Appointment reminders')
    notif_prescriptions = models.BooleanField(default=True,  help_text='New prescription alerts')
    notif_pharmacy      = models.BooleanField(default=True,  help_text='Pharmacy order updates')
    notif_caretaker     = models.BooleanField(default=True,  help_text='Care request updates')
    notif_system        = models.BooleanField(default=True,  help_text='System & security alerts')
    notif_email         = models.BooleanField(default=False, help_text='Send notifications by email')
    notif_sms           = models.BooleanField(default=False, help_text='Send notifications by SMS')

    # ── Appearance ───────────────────────────────────────────────────────────
    language = models.CharField(max_length=5,  choices=LANGUAGE_CHOICES, default='fr')
    theme    = models.CharField(max_length=10, choices=THEME_CHOICES,    default='system')

    # ── Privacy ──────────────────────────────────────────────────────────────
    profile_visible_to_doctors     = models.BooleanField(default=True)
    profile_visible_to_caretakers  = models.BooleanField(default=True)
    share_medical_data_with_doctor = models.BooleanField(default=True)

    # ── Security ─────────────────────────────────────────────────────────────
    two_factor_enabled = models.BooleanField(default=False)

    # ── Timestamps ───────────────────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Settings'

    def __str__(self):
        return f'Settings — {self.user.email}'


class AccountDeletionRequest(models.Model):
    """
    User requests account deletion. Admin reviews before deleting.
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('cancelled', 'Cancelled'),
    ]

    user      = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deletion_request',
    )
    reason     = models.TextField(blank=True)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Deletion request — {self.user.email} ({self.status})'