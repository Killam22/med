# settings/apps.py
from django.apps import AppConfig
 
 
class SettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name  = 'settings'
    label = 'settings'         # avoids clash with Django's own 'settings' name
    verbose_name = 'User Settings'
 