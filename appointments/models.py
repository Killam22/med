"""Database models for the medical appointment system."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Import models from other apps
from patients.models import Patient
from doctors.models import Doctor


# ── Availability Slot ─────────────────────────────────────────────────────────

class AvailabilitySlot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Créneau de disponibilité"
        verbose_name_plural = "Créneaux de disponibilité"
        ordering = ['date', 'start_time']
        unique_together = ('doctor', 'date', 'start_time')

    def __str__(self):
        return (
            f"Dr. {self.doctor.user.get_full_name()} — "
            f"{self.date} {self.start_time}-{self.end_time} "
            f"({'réservé' if self.is_booked else 'disponible'})"
        )


# ── Appointment ───────────────────────────────────────────────────────────────

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
        ('refused', 'Refusé'),
        ('completed', 'Terminé'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    slot = models.OneToOneField(
        AvailabilitySlot, on_delete=models.SET_NULL, null=True, related_name='appointment'
    )
    motif = models.CharField(max_length=300, help_text="Motif de la consultation")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Notes du médecin (visible patient)")
    refusal_reason = models.TextField(blank=True, help_text="Raison du refus (si refusé)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.slot and self.slot.doctor != self.doctor:
            raise ValidationError({
                'slot': f"Ce créneau n'appartient pas à ce médecin. Veuillez choisir un créneau du Dr. {self.doctor.user.get_full_name()}."
            })

    def __str__(self):
        return (
            f"RDV {self.get_status_display()} — "
            f"{self.patient} → Dr. {self.doctor.user.get_full_name()} "
            f"({self.slot.date if self.slot else 'pas de créneau'})"
        )

    def cancel(self):
        """Cancel appointment and free the slot."""
        self.status = 'cancelled'
        if self.slot:
            self.slot.is_booked = False
            self.slot.save()
        self.save()

    def confirm(self):
        self.status = 'confirmed'
        self.save()

    def refuse(self, reason=''):
        self.status = 'refused'
        self.refusal_reason = reason
        if self.slot:
            self.slot.is_booked = False
            self.slot.save()
        self.save()


# ── Notification ──────────────────────────────────────────────────────────────

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('booking', 'Réservation'),
        ('status_change', 'Changement de statut'),
        ('reminder', 'Rappel'),
        ('general', 'Général'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='general')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif [{self.user.email}] - {self.message[:20]}"


# ── Review ────────────────────────────────────────────────────────────────────

class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='reviews_given')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        unique_together = ('patient', 'appointment')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Recalculer la note moyenne du médecin
        reviews = self.doctor.reviews_received.all()
        total = reviews.count()
        if total > 0:
            avg = sum(r.rating for r in reviews) / total
            self.doctor.rating = round(avg, 2)
            self.doctor.total_reviews = total
            self.doctor.save()

    def __str__(self):
        return f"Éval {self.rating}★ par {self.patient} pour Dr. {self.doctor.user.last_name}"
