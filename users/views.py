# users/views.py
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect

from .forms import (
    loginForm, registerForm,
    otpVerifyForm, passwordResetRequestForm, setNewPasswordForm,
)
from .models import CustomUser, EmailOTP
from .utils import send_otp_email


# ── Helpers ────────────────────────────────────────────────────────────────────

def _redirect_by_role(user):
    role_map = {
        'patient':    'patients:dashboard',
        'doctor':     'doctors:dashboard',
        'pharmacist': 'pharmacy:dashboard',
        'caretaker':  'caretaker:dashboard',
    }
    if user.role == 'admin':
        return redirect('/admin/')
    return redirect(role_map.get(user.role, '/'))


def _render_auth(request, **ctx):
    """Shortcut — always renders users/auth.html with the given context."""
    return render(request, 'users/auth.html', ctx)


# ── Login ──────────────────────────────────────────────────────────────────────

def user_login(request):
    if request.method == 'POST':
        form = loginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return _redirect_by_role(user)
        return _render_auth(request, login_error='Invalid email or password.')
    return _render_auth(request)


# ── Register — Step 1: collect details & send OTP ─────────────────────────────

def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST, request.FILES)
        if form.is_valid():
            # Save form data in session — don't create the user yet
            request.session['pending_registration'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name':  form.cleaned_data['last_name'],
                'email':      form.cleaned_data['email'],
                'password':   form.cleaned_data['password'],
                'role':       form.cleaned_data['role'],
            }
            email = form.cleaned_data['email']
            otp_obj = EmailOTP.generate(email, EmailOTP.PURPOSE_REGISTER)
            send_otp_email(email, otp_obj.otp, 'register')
            return _render_auth(request, show_verify=True, verify_purpose='register',
                                verify_email=email)
        return _render_auth(request,
                               show_register=True,
                               register_error=form.errors)
    return _render_auth(request)


# ── Register — Step 2: verify OTP & activate user ────────────────────────────

def verify_register_otp(request):
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('user_login')

    if request.method == 'POST':
        form = otpVerifyForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            email     = pending['email']

            try:
                otp_obj = EmailOTP.objects.filter(
                    email=email,
                    purpose=EmailOTP.PURPOSE_REGISTER,
                    is_used=False,
                ).latest('created_at')
            except EmailOTP.DoesNotExist:
                return _render_auth(request, show_verify=True, verify_purpose='register',
                                    verify_email=email, otp_error='Invalid code. Request a new one.')

            if otp_obj.is_expired():
                return _render_auth(request, show_verify=True, verify_purpose='register',
                                    verify_email=email, otp_error='Code expired. Request a new one.')

            if otp_obj.otp != otp_input:
                return _render_auth(request, show_verify=True, verify_purpose='register',
                                    verify_email=email, otp_error='Incorrect code.')

            # Mark OTP used
            otp_obj.is_used = True
            otp_obj.save()

            # Create and activate the user
            user = CustomUser(
                username   = pending['email'],
                email      = pending['email'],
                first_name = pending['first_name'],
                last_name  = pending['last_name'],
                role       = pending['role'],
                is_active  = True,
            )
            user.set_password(pending['password'])
            user.save()

            del request.session['pending_registration']
            auth_login(request, user)

            role = user.role
            if role == 'patient':
                return redirect('patients:complete_patient_profile')
            elif role == 'pharmacist':
                return redirect('pharmacy:complete_pharmacy_profile')
            elif role == 'caretaker':
                return redirect('caretaker:complete_caretaker_profile')
            return redirect('doctors:dashboard')

        return _render_auth(request, show_verify=True, verify_purpose='register',
                            verify_email=pending['email'],
                            otp_error='Please enter a valid 6-digit code.')

    return _render_auth(request, show_verify=True, verify_purpose='register',
                        verify_email=pending.get('email', ''))


# ── Resend OTP (shared for register & reset) ──────────────────────────────────

def resend_otp(request):
    purpose = request.POST.get('purpose')
    if purpose == EmailOTP.PURPOSE_REGISTER:
        pending = request.session.get('pending_registration')
        email   = pending['email'] if pending else None
    else:
        email = request.session.get('reset_email')

    if not email or purpose not in (EmailOTP.PURPOSE_REGISTER, EmailOTP.PURPOSE_RESET):
        return redirect('user_login')

    otp_obj = EmailOTP.generate(email, purpose)
    send_otp_email(email, otp_obj.otp, purpose)
    return _render_auth(request, show_verify=True, verify_purpose=purpose,
                        verify_email=email,
                        otp_info='A new code has been sent to your email.')


# ── Password reset — Step 1: enter email & send OTP ──────────────────────────

def password_reset_request(request):
    if request.method == 'POST':
        form = passwordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # Always show the verify panel — don't reveal if email exists
            if CustomUser.objects.filter(email=email, is_active=True).exists():
                otp_obj = EmailOTP.generate(email, EmailOTP.PURPOSE_RESET)
                send_otp_email(email, otp_obj.otp, 'reset')
            request.session['reset_email'] = email
            return _render_auth(request, show_verify=True, verify_purpose='reset',
                                verify_email=email)
        return _render_auth(request, show_reset=True, reset_error='Enter a valid email address.')
    return _render_auth(request, show_reset=True)


# ── Password reset — Step 2: verify OTP ──────────────────────────────────────

def verify_reset_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('user_login')

    if request.method == 'POST':
        form = otpVerifyForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']

            try:
                otp_obj = EmailOTP.objects.filter(
                    email=email,
                    purpose=EmailOTP.PURPOSE_RESET,
                    is_used=False,
                ).latest('created_at')
            except EmailOTP.DoesNotExist:
                return _render_auth(request, show_verify=True, verify_purpose='reset',
                                    verify_email=email, otp_error='Invalid code. Request a new one.')

            if otp_obj.is_expired():
                return _render_auth(request, show_verify=True, verify_purpose='reset',
                                    verify_email=email, otp_error='Code expired. Request a new one.')

            if otp_obj.otp != otp_input:
                return _render_auth(request, show_verify=True, verify_purpose='reset',
                                    verify_email=email, otp_error='Incorrect code.')

            otp_obj.is_used = True
            otp_obj.save()
            request.session['reset_verified'] = True   # gate the next step
            return _render_auth(request, show_new_password=True)

        return _render_auth(request, show_verify=True, verify_purpose='reset',
                            verify_email=email,
                            otp_error='Please enter a valid 6-digit code.')

    return _render_auth(request, show_verify=True, verify_purpose='reset',
                        verify_email=email)


# ── Password reset — Step 3: set new password ─────────────────────────────────

def password_reset_set(request):
    email    = request.session.get('reset_email')
    verified = request.session.get('reset_verified')

    if not email or not verified:
        return redirect('user_login')

    if request.method == 'POST':
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
        except CustomUser.DoesNotExist:
            return redirect('user_login')

        form = setNewPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            del request.session['reset_email']
            del request.session['reset_verified']
            return _render_auth(request, reset_complete=True)
        return _render_auth(request, show_new_password=True,
                            new_password_error='Passwords do not match or are too weak.')

    return _render_auth(request, show_new_password=True)


# ── Logout ─────────────────────────────────────────────────────────────────────

def user_logout(request):
    auth_logout(request)
    return redirect('user_login')