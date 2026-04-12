# settings/urls.py
from django.urls import path
from .views import (
    UserSettingsView,
    ChangePasswordView,
    UpdateProfileView,
    AccountDeletionRequestView,
)

urlpatterns = [
    path('',                 UserSettingsView.as_view(),          name='user_settings'),
    path('profile/',         UpdateProfileView.as_view(),         name='settings_profile'),
    path('change-password/', ChangePasswordView.as_view(),        name='change_password'),
    path('delete-account/',  AccountDeletionRequestView.as_view(), name='delete_account'),
]