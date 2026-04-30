from django.db import models
from django.conf import settings


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'messaging'

    def __str__(self):
        return f"Conversation {self.id} ({self.participants.count()} participants)"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'messaging'
        ordering = ['created_at']

    def __str__(self):
        return f"De {self.sender.email} à {self.created_at.strftime('%H:%M')}"


class BlockedUser(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_users')
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'messaging'
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.email} a bloqué {self.blocked.email}"


class UserReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('resolved', 'Résolu'),
        ('dismissed', 'Ignoré'),
    ]
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'messaging'

    def __str__(self):
        return f"Signalement de {self.reporter.email} contre {self.reported_user.email}"
