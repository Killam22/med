from django.urls import path
from .views import (
    ProfileSettingsView,
    NotificationPreferencesView,
    AccountDeactivationView,
)

urlpatterns = [
    path('profile/',       ProfileSettingsView.as_view(),         name='settings-profile'),
    path('notifications/', NotificationPreferencesView.as_view(), name='settings-notifications'),
    path('deactivate/',    AccountDeactivationView.as_view(),      name='settings-deactivate'),
]