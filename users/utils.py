# users/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@medsmart.dz')
_APP_URL = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


def send_otp_email(email, otp, purpose, first_name='', last_name=''):
    """
    Sends a 6-digit OTP to the given email address.
    purpose: 'register' | 'reset'
    """
    context = {
        'prenom': first_name,
        'nom': last_name,
        'email': email,
        'otp_code': otp,
        'app_url': _APP_URL,
    }

    if purpose == 'register':
        subject = "MedSmart — Vérification de votre compte"
        text_body = (
            f"Bonjour {first_name} {last_name},\n\n"
            f"Votre code de vérification MedSmart est : {otp}\n\n"
            f"Ce code expire dans 10 minutes.\n"
            f"Si vous n'avez pas créé de compte, ignorez cet e-mail."
        )
        html_body = render_to_string('users/emails/otp_verify.html', context)
    else:
        subject = "MedSmart — Réinitialisation du mot de passe"
        text_body = (
            f"Bonjour {first_name} {last_name},\n\n"
            f"Votre code de réinitialisation MedSmart est : {otp}\n\n"
            f"Ce code expire dans 15 minutes.\n"
            f"Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail."
        )
        html_body = render_to_string('users/emails/otp_reset.html', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=False)


def send_welcome_email(user):
    """Sends the welcome HTML email after account activation."""
    context = {
        'prenom': user.first_name,
        'nom': user.last_name,
        'email': user.email,
        'patient_id': getattr(user, 'id', ''),
        'app_url': _APP_URL,
    }
    subject = "Bienvenue sur MedSmart ! 🎉"
    text_body = (
        f"Bonjour {user.first_name} {user.last_name},\n\n"
        f"Votre compte MedSmart a été activé avec succès.\n"
        f"Accédez à votre espace santé sur {_APP_URL}\n\n"
        f"L'équipe MedSmart"
    )
    html_body = render_to_string('users/emails/welcome.html', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)


ROLE_LABELS = {
    'doctor':     'Médecin',
    'pharmacist': 'Pharmacien',
    'caretaker':  'Garde-malade',
    'patient':    'Patient',
}


def notify_admins_new_registration(user):
    """
    Crée une Notification pour chaque admin afin de signaler une nouvelle
    inscription professionnelle en attente de validation.
    """
    from django.contrib.auth import get_user_model
    from notifications.models import Notification

    print("Notifying admins for:", user.email)

    User = get_user_model()
    role_label = ROLE_LABELS.get(user.role, user.role)
    full_name = user.get_full_name() or user.email

    admins = User.objects.filter(role='admin', is_active=True)
    print(f"  → {admins.count()} admin(s) trouvé(s) avec role='admin' is_active=True")
    Notification.objects.bulk_create([
        Notification(
            user=admin,
            title="Nouvelle inscription à valider",
            message=f"{role_label} : {full_name} ({user.email}) a soumis une demande d'inscription.",
            notification_type=Notification.NotificationType.SYSTEM,
        )
        for admin in admins
    ])
    print(f"  → Notifications créées pour {admins.count()} admin(s)")