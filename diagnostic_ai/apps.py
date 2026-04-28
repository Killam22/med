# diagnostic_ai/apps.py

from django.apps import AppConfig


class DiagnosticAiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "diagnostic_ai"
    label              = "diagnostic_ai"
    verbose_name       = "Diagnostic IA"
