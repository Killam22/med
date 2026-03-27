from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from .models import CustomUser
class registerForm(forms.ModelForm):
    password  = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    class Meta:
        model  = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password', 'role']

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class loginForm(forms.Form):  # plain Form, not AuthenticationForm
    email    = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email    = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            # find user by email first
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise forms.ValidationError('No account found with this email.')

            # then check password
            user = authenticate(username=user.username, password=password)
            if user is None:
                raise forms.ValidationError('Incorrect password.')

            self.user = user  # save user to access in view
        return cleaned_data

    def get_user(self):
        return self.user



class passwordResetRequestForm(forms.Form):
    """
    Step 1 — user enters their email.
    Delegates the actual email sending to Django's built-in PasswordResetForm
    so token generation, email rendering, and HMAC signing are all handled
    by the framework.
    """
    email = forms.EmailField(label='email')
 
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        # Intentionally do NOT raise an error when the email is not found.
        # Revealing whether an address is registered is a user-enumeration risk.
        return email
 
    def save(self, request):
        """
        Delegate to Django's PasswordResetForm so we get proper token
        generation and email dispatch without reimplementing it ourselves.
        """
        django_form = PasswordResetForm(data={'email': self.cleaned_data['email']})
        if django_form.is_valid():
            django_form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='accounts/password_reset_email.html',
                subject_template_name='accounts/password_reset_subject.txt',
            )
 
 
class passwordResetConfirmForm(SetPasswordForm):
    """
    Step 3 — user sets a new password after clicking the emailed link.
    Extends Django's SetPasswordForm (handles token validation + hashing).
    Labels and widgets are overridden to match the rest of the project style.
    """
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput,
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput,
    )
 
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data