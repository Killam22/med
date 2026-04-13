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