# users/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@Healy.dz')
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
        subject = "Healy — Vérification de votre compte"
        text_body = (
            f"Bonjour {first_name} {last_name},\n\n"
            f"Votre code de vérification Healy est : {otp}\n\n"
            f"Ce code expire dans 10 minutes.\n"
            f"Si vous n'avez pas créé de compte, ignorez cet e-mail."
        )
        html_body = render_to_string('users/emails/otp_verify.html', context)
    else:
        subject = "Healy — Réinitialisation du mot de passe"
        text_body = (
            f"Bonjour {first_name} {last_name},\n\n"
            f"Votre code de réinitialisation Healy est : {otp}\n\n"
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
    subject = "Bienvenue sur Healy ! 🎉"
    text_body = (
        f"Bonjour {user.first_name} {user.last_name},\n\n"
        f"Votre compte Healy a été activé avec succès.\n"
        f"Accédez à votre espace santé sur {_APP_URL}\n\n"
        f"L'équipe Healy"
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


def send_rejection_email(user, reason=""):
    """
    Envoie un email au professionnel dont l'inscription a été refusée par l'admin.
    Format HTML + fallback texte. `reason` est le motif personnalisé saisi par l'admin
    (sinon un motif générique est utilisé).

    Returns:
        True si l'envoi a réussi, False sinon (l'erreur est loggée).
    """
    import logging
    logger = logging.getLogger(__name__)

    role_label = ROLE_LABELS.get(user.role, user.role or 'Utilisateur')
    final_reason = (reason or "Votre dossier ne satisfait pas l'ensemble des critères de validation.").strip()

    context = {
        'prenom': user.first_name or '',
        'nom':    user.last_name or '',
        'email':  user.email,
        'role_label': role_label,
        'reason':  final_reason,
        'app_url': _APP_URL,
    }

    subject = "Healy — Votre inscription n'a pas été validée"
    text_body = (
        f"Bonjour {user.first_name} {user.last_name},\n\n"
        f"Nous vous remercions d'avoir soumis votre demande d'inscription en tant que {role_label} sur Healy.\n\n"
        f"Après examen, votre dossier n'a pas pu être validé en l'état.\n\n"
        f"Motif : {final_reason}\n\n"
        f"Vous pouvez soumettre une nouvelle demande corrigée ou contacter notre support à\n"
        f"support@healy.dz pour plus d'informations.\n\n"
        f"L'équipe Healy"
    )

    try:
        html_body = render_to_string('users/emails/rejection.html', context)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        # fail_silently=False ici : on capture l'erreur dans le try/except au lieu de la
        # masquer. Comme ça si SMTP plante on le voit dans les logs.
        msg.send(fail_silently=False)
        logger.info("Email de rejet envoyé à %s (motif: %s)", user.email, final_reason[:60])
        return True
    except Exception as e:
        logger.error("Échec envoi email de rejet à %s : %s: %s", user.email, type(e).__name__, e)
        return False


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