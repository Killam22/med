# users/forms.py
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm
from .models import CustomUser


class registerForm(forms.ModelForm):
    password  = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    class Meta:
        model  = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'role', 'phone', 'sex', 'date_of_birth','id_card_number','id_card_recto','id_card_verso', 'address', 'postal_code', 'city', 'wilaya']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if CustomUser.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class loginForm(forms.Form):
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email    = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError('No account found with this email.')

            if not user.is_active:
                raise forms.ValidationError('Please verify your email before logging in.')

            user = authenticate(username=user.username, password=password)
            if user is None:
                raise forms.ValidationError('Incorrect password.')

            self.user = user
        return cleaned_data

    def get_user(self):
        return self.user


class otpVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}),
        label='Verification code',
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp', '').strip()
        if not otp.isdigit():
            raise forms.ValidationError('Code must be 6 digits.')
        return otp


class passwordResetRequestForm(forms.Form):
    email = forms.EmailField(label='Email address')

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip().lower()


class setNewPasswordForm(SetPasswordForm):
    """Used after OTP-verified password reset."""
    new_password1 = forms.CharField(label='New password',        widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data