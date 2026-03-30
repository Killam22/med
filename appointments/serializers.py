"""Serializers for the appointment management logic."""
from datetime import datetime
from rest_framework import serializers
from patients.models import Patient
from doctors.models import Doctor
from .models import Appointment, Review, Notification


# ── Slot Serializers ─────────────────────────────────────────────

class SlotSerializer(serializers.Serializer):
    """Read-only representation of a free computed slot."""
    start_time = serializers.TimeField(format='%H:%M')
    end_time   = serializers.TimeField(format='%H:%M')


class BookAppointmentSerializer(serializers.Serializer):
    """
    Utilisé en POST /api/appointments/ et POST /api/appointments/{id}/reschedule/
    Le client envoie : doctor_id, date, start_time, end_time, motif
    """
    doctor_id  = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True),
        source='doctor',
    )
    date       = serializers.DateField()
    start_time = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'])
    end_time   = serializers.TimeField(format='%H:%M', input_formats=['%H:%M', '%H:%M:%S'])
    motif      = serializers.CharField(max_length=300, trim_whitespace=True)

    def validate_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Impossible de réserver une date dans le passé."
            )
        return value

    def validate(self, data):
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError({
                'end_time': "L'heure de fin doit être après l'heure de début."
            })
        # Durée raisonnable : entre 10 min et 4h
        start_dt = datetime.combine(data['date'], data['start_time'])
        end_dt   = datetime.combine(data['date'], data['end_time'])
        duration = (end_dt - start_dt).seconds // 60
        if duration < 10:
            raise serializers.ValidationError("La durée minimale d'un rendez-vous est 10 minutes.")
        if duration > 240:
            raise serializers.ValidationError("La durée maximale d'un rendez-vous est 4 heures.")
        return data


# ── Appointment read (patient view) ──────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    """
    Utilisé en GET /api/appointments/ et GET /api/appointments/{id}/
    Visible par le patient — pas de refusal_reason.
    """
    doctor_name      = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.speciality', read_only=True)
    patient_name     = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    has_review       = serializers.SerializerMethodField()

    class Meta:
        model  = Appointment
        fields = [
            'id',
            'doctor_name',
            'doctor_specialty',
            'patient_name',
            'date',
            'start_time',
            'end_time',
            'duration_minutes',
            'motif',
            'status',
            'status_display',
            'notes',          # notes du médecin, visibles au patient
            'has_review',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # ce serializer est lecture seule

    def get_has_review(self, obj) -> bool:
        return hasattr(obj, 'review')


# ── Appointment read (doctor view) ────────────────────────────────────────────

class AppointmentDoctorSerializer(serializers.ModelSerializer):
    """
    Utilisé dans toutes les vues doctor/appointments/
    Ajoute refusal_reason et les infos patient complètes.
    """
    patient_name    = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    patient_email   = serializers.EmailField(source='patient.user.email', read_only=True)
    patient_phone   = serializers.CharField(source='patient.phone_number', read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    status_display  = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Appointment
        fields = [
            'id',
            'patient_name',
            'patient_email',
            'patient_phone',
            'date',
            'start_time',
            'end_time',
            'duration_minutes',
            'motif',
            'status',
            'status_display',
            'notes',
            'refusal_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


# ── Doctor notes update ───────────────────────────────────────────────────────

class AppointmentNotesSerializer(serializers.ModelSerializer):
    """
    Utilisé en PATCH /api/doctor/appointments/{id}/notes/
    Permet au médecin d'ajouter des notes sans passer par CompleteAppointmentView.
    """
    class Meta:
        model  = Appointment
        fields = ['notes']


# ── Notification Serializers ──────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'notification_type', 'is_read', 'created_at', 'related_appointment']
        read_only_fields = ['id', 'message', 'notification_type', 'created_at', 'related_appointment']


# ── Review Serializers ────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'appointment', 'patient_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'patient', 'doctor', 'created_at']

    def validate(self, data):
        appointment = data.get('appointment')
        if not appointment:
             raise serializers.ValidationError("Le rendez-vous est obligatoire.")
        if appointment.status != 'completed':
            raise serializers.ValidationError("Vous ne pouvez évaluer qu'un rendez-vous terminé.")
        if hasattr(appointment, 'review'):
            raise serializers.ValidationError("Vous avez déjà évalué ce rendez-vous.")
        return data
