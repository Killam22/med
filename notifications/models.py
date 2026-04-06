from django.db import models
from django.conf import settings

class Notification(models.Model):
    # Les différents "tiroirs" de notifications pour pouvoir les filtrer sur le frontend
    class NotificationType(models.TextChoices):
        APPOINTMENT = 'appointment', 'Rendez-vous'
        PHARMACY = 'pharmacy', 'Pharmacie'
        CARETAKER = 'caretaker', 'Garde-malade'
        SYSTEM = 'system', 'Système'

    # Celui qui reçoit la notification
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Les plus récentes en premier

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title} ({'Lue' if self.is_read else 'Non lue'})"