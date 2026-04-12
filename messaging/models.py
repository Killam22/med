from django.db import models
from django.conf import settings

class Conversation(models.Model):
    """Un fil de discussion entre 2 ou plusieurs utilisateurs (Patient-Médecin, Admin-Pharmacien, etc.)"""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Pratique pour trier par "Dernier message reçu"

    class Meta:
        app_label = 'messaging'

    def __str__(self):
        return f"Conversation {self.id} ({self.participants.count()} participants)"

class Message(models.Model):
    """Un message précis lié à une conversation"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'messaging'
        ordering = ['created_at'] # Les plus anciens en haut, les récents en bas (comme WhatsApp)

    def __str__(self):
        return f"De {self.sender.email} à {self.created_at.strftime('%H:%M')}"
