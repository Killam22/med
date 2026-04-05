<<<<<<< HEAD
"""Serializers for the appointment management logic."""
from datetime import datetime
from django.utils import timezone
from rest_framework import serializers
from patients.models import Patient
from doctors.models import Doctor
from .models import Appointment, Review


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
        queryset=Doctor.objects.all(),
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

        # Vérifier que le créneau demandé existe bien dans les disponibilités réelles du médecin
        from appointments.services import get_available_slots
        doctor     = data['doctor']
        date       = data['date']
        start_time = data['start_time']
        end_time   = data['end_time']

        available = get_available_slots(doctor, date)

        if not available:
            raise serializers.ValidationError(
                f"Le médecin n'a aucun créneau disponible le {date}. "
                f"Consultez GET /api/doctors/{doctor.pk}/availability/?date={date} pour voir ses disponibilités."
            )

        # Le créneau demandé doit correspondre exactement à un créneau libre
        valid_slot = any(
            s['start_time'] == start_time and s['end_time'] == end_time
            for s in available
        )
        if not valid_slot:
            slots_str = ", ".join(
                f"{s['start_time'].strftime('%H:%M')}–{s['end_time'].strftime('%H:%M')}"
                for s in available
            )
            raise serializers.ValidationError(
                f"Le créneau {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')} n'est pas disponible. "
                f"Créneaux libres : {slots_str}"
            )

        return data



# ── Appointment read (patient view) ──────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    """
    Utilisé en GET /api/appointments/ et GET /api/appointments/{id}/
    Visible par le patient — pas de refusal_reason.
    """
    doctor_name      = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.specialty', read_only=True)
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
=======
"""Serializers for the appointment management logic."""
from datetime import datetime
from django.utils import timezone
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
        queryset=Doctor.objects.all(),
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

        # Vérifier que le créneau demandé existe bien dans les disponibilités réelles du médecin
        from appointments.services import get_available_slots
        doctor     = data['doctor']
        date       = data['date']
        start_time = data['start_time']
        end_time   = data['end_time']

        available = get_available_slots(doctor, date)

        if not available:
            raise serializers.ValidationError(
                f"Le médecin n'a aucun créneau disponible le {date}. "
                f"Consultez GET /api/doctors/{doctor.pk}/availability/?date={date} pour voir ses disponibilités."
            )

        # Le créneau demandé doit correspondre exactement à un créneau libre
        valid_slot = any(
            s['start_time'] == start_time and s['end_time'] == end_time
            for s in available
        )
        if not valid_slot:
            slots_str = ", ".join(
                f"{s['start_time'].strftime('%H:%M')}–{s['end_time'].strftime('%H:%M')}"
                for s in available
            )
            raise serializers.ValidationError(
                f"Le créneau {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')} n'est pas disponible. "
                f"Créneaux libres : {slots_str}"
            )

        return data



# ── Appointment read (patient view) ──────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    """
    Utilisé en GET /api/appointments/ et GET /api/appointments/{id}/
    Visible par le patient — pas de refusal_reason.
    """
    doctor_name      = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.specialty', read_only=True)
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
>>>>>>> 028fdeda6401843c937a101c5786c24dbf3a6f4f
