# users/utils.py
from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp, purpose):
    """
    Sends a 6-digit OTP to the given email address.
    purpose: 'register' | 'reset'
    """
    if purpose == 'register':
        subject = "Verify your MedSmart account"
        body = (
            f"Welcome to MedSmart!\n\n"
            f"Your verification code is:\n\n"
            f"    {otp}\n\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not create an account, ignore this email."
        )
    else:
        subject = "MedSmart password reset code"
        body = (
            f"You requested a password reset on MedSmart.\n\n"
            f"Your reset code is:\n\n"
            f"    {otp}\n\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not request this, ignore this email."
        )

    send_mail(
        subject=subject,
        message=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@medsmart.com'),
        recipient_list=[email],
        fail_silently=False,
    )


ROLE_LABELS = {
    'doctor': 'Médecin',
    'pharmacist': 'Pharmacien',
    'caretaker': 'Garde-malade',
}


def notify_admins_new_registration(user):
    """
    Crée une Notification pour chaque admin afin de signaler une nouvelle
    inscription professionnelle en attente de validation.
    """
    from django.contrib.auth import get_user_model
    from notifications.models import Notification

    User = get_user_model()
    role_label = ROLE_LABELS.get(user.role, user.role)
    full_name = user.get_full_name() or user.email

    admins = User.objects.filter(role='admin', is_active=True)
    Notification.objects.bulk_create([
        Notification(
            user=admin,
            title="Nouvelle inscription à valider",
            message=f"{role_label} : {full_name} ({user.email}) a soumis une demande d'inscription.",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        for admin in admins
    ])