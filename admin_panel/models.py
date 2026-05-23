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


class AdminContactRequest(models.Model):
    """Demande envoyée par un utilisateur (patient/médecin/pharmacien/garde-malade)
    depuis l'écran Paramètres vers l'administrateur."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'En attente'
        IN_PROGRESS = 'in_progress', 'En cours'
        RESOLVED = 'resolved', 'Traitée'
        REJECTED = 'rejected', 'Refusée'

    class Category(models.TextChoices):
        TECHNICAL = 'technical', 'Problème technique'
        ACCOUNT = 'account', 'Compte / Accès'
        BILLING = 'billing', 'Facturation'
        FEATURE = 'feature', 'Suggestion / Fonctionnalité'
        OTHER = 'other', 'Autre'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_contact_requests',
    )
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_response = models.TextField(blank=True, default='')
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='handled_contact_requests',
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status}] {self.subject} — {self.user_id}"