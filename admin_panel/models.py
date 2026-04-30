from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    """Journal d'audit pour tracer toutes les actions administratives"""
    class Level(models.TextChoices):
        SUCCESS = 'success', 'Succès'
        WARNING = 'warning', 'Alerte'
        ERROR = 'error', 'Erreur'
        INFO = 'info', 'Info'

    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    message = models.CharField(max_length=255)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level.upper()}] {self.message}"