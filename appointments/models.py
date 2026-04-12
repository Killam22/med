
"""Database models for the medical appointment system."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import datetime

# Import models from other apps
from patients.models import Patient
from doctors.models import Doctor


# ── Appointment ───────────────────────────────────────────────────────────────

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'En attente'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
        ('refused',   'Refusé'),
        ('completed', 'Terminé'),
    ]

    patient    = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor     = models.ForeignKey(Doctor,  on_delete=models.CASCADE, related_name='appointments')

    # The booked window — this IS the slot now
    date       = models.DateField(default=timezone.now)
    start_time = models.TimeField(default=timezone.now)
    end_time   = models.TimeField(default=timezone.now)

    motif          = models.CharField(max_length=300)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes          = models.TextField(blank=True)
    refusal_reason = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering            = ['-created_at']
        # A doctor can't have two active appointments that overlap on the same date/time
        unique_together = ('doctor', 'date', 'start_time')

    # ── Validation ────────────────────────────────────────────────────────────

    def clean(self):
        super().clean()
        if self.end_time <= self.start_time:
            raise ValidationError("L'heure de fin doit être après l'heure de début.")

    # ── Computed helpers ──────────────────────────────────────────────────────

    @property
    def duration_minutes(self):
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt   = datetime.combine(self.date, self.end_time)
        return int((end_dt - start_dt).seconds / 60)

    @property
    def is_active(self):
        return self.status in ('pending', 'confirmed')

    # ── State transitions ─────────────────────────────────────────────────────

    def cancel(self):
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])

    def confirm(self):
        self.status = 'confirmed'
        self.save(update_fields=['status', 'updated_at'])

    def refuse(self, reason=''):
        self.status    = 'refused'
        self.refusal_reason = reason
        self.save(update_fields=['status', 'refusal_reason', 'updated_at'])

    def complete(self, notes=''):
        self.status = 'completed'
        self.notes  = notes
        self.save(update_fields=['status', 'notes', 'updated_at'])

    def __str__(self):
        return (
            f"RDV {self.get_status_display()} — "
            f"{self.patient} → Dr.{self.doctor.user.last_name} "
            f"({self.date} {self.start_time})"
        )



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