# users/views.py
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.core.mail import send_mail
from .forms import loginForm, registerForm, passwordResetRequestForm, passwordResetConfirmForm
from .models import CustomUser


# ── Role-based redirect helper ─────────────────────────────────────────────────

def _redirect_by_role(user):
    if user.role == 'patient':
        return redirect('patients:dashboard')
    elif user.role == 'doctor':
        return redirect('doctors:dashboard')
    elif user.role == 'pharmacist':
        return redirect('pharmacy:dashboard')
    elif user.role == 'caretaker':
        return redirect('caretaker:dashboard')
    elif user.role == 'admin':
        return redirect('/admin/')
    return redirect('/')


# ── Login ──────────────────────────────────────────────────────────────────────

def user_login(request):
    if request.method == 'POST':
        form = loginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return _redirect_by_role(user)
        return render(request, 'users/auth.html', {'login_error': 'Invalid email or password.'})
    return render(request, 'users/auth.html')


# ── Register ───────────────────────────────────────────────────────────────────

def register(request):
    if request.method == 'POST':
        form = registerForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            user.set_password(form.cleaned_data['password'])
            user.save()
            auth_login(request, user)
            if user.role == 'patient':
                return redirect('patients:complete_patient_profile')
            elif user.role == 'doctor':
                return redirect('doctors:dashboard')
            elif user.role == 'pharmacist':
                return redirect('pharmacy:complete_pharmacy_profile')
            elif user.role == 'caretaker':
                return redirect('caretaker:complete_caretaker_profile')
            return redirect('user_login')
        return render(request, 'users/auth.html', {
            'register_error': 'Registration failed. Check your inputs.',
            'show_register': True,
        })
    return render(request, 'users/auth.html')


# ── Logout ─────────────────────────────────────────────────────────────────────

def user_logout(request):
    auth_logout(request)
    return redirect('user_login')


# ── Password reset — Step 1: enter email ──────────────────────────────────────

def password_reset_request(request):
    if request.method == "POST":
        form = passwordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                # Ici tu peux générer un token ou un lien unique
                reset_link = f"http://127.0.0.1:8000/users/reset/{user.user_}/"
                send_mail(
                    'Reset your password',
                    f'Cliquez sur ce lien pour réinitialiser votre mot de passe: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                return render(request, 'users/email_sent.html', {'email': email})
            except user.DoesNotExist:
                form.add_error('email', 'Aucun compte trouvé avec cet email')
    else:
        form = passwordResetRequestForm()
    return render(request, 'users/password_reset_request.html', {'form': form})

# ── Password reset — Step 2: set new password via emailed link ────────────────

