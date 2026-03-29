"""Serializers for the appointment management logic."""

from rest_framework import serializers
from patients.models import Patient
from doctors.models import Doctor
from .models import AvailabilitySlot, Appointment, Review, Notification


# ── Availability Slot Serializers ─────────────────────────────────────────────

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = [
            'id', 'date', 'start_time', 'end_time',
            'is_booked',
        ]
        read_only_fields = ['is_booked']

    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    "L'heure de début doit être avant l'heure de fin."
                )
        return data


# ── Appointment Serializers ───────────────────────────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    """Patient-facing appointment serializer."""
    doctor_name = serializers.SerializerMethodField()
    doctor_specialty = serializers.SerializerMethodField()
    slot_date = serializers.SerializerMethodField()
    slot_start_time = serializers.SerializerMethodField()
    slot_end_time = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_specialty',
            'slot', 'slot_date', 'slot_start_time', 'slot_end_time',
            'motif', 'status', 'status_display',
            'notes', 'refusal_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'status', 'notes', 'refusal_reason', 'created_at', 'updated_at',
            'doctor_name', 'doctor_specialty',
        ]

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"

    def get_doctor_specialty(self, obj):
        return obj.doctor.get_specialty_display()

    def get_slot_date(self, obj):
        return obj.slot.date if obj.slot else None

    def get_slot_start_time(self, obj):
        return obj.slot.start_time if obj.slot else None

    def get_slot_end_time(self, obj):
        return obj.slot.end_time if obj.slot else None

    def validate_slot(self, slot):
        if slot.is_booked:
            raise serializers.ValidationError("Ce créneau est déjà réservé.")
        return slot

    def create(self, validated_data):
        slot = validated_data['slot']
        appointment = Appointment.objects.create(**validated_data)
        slot.is_booked = True
        slot.save()
        return appointment


class AppointmentDoctorSerializer(serializers.ModelSerializer):
    """Doctor-facing appointment serializer (includes patient info)."""
    patient_name = serializers.SerializerMethodField()
    patient_age = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    slot_date = serializers.SerializerMethodField()
    slot_start_time = serializers.SerializerMethodField()
    slot_end_time = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_age', 'patient_phone',
            'slot', 'slot_date', 'slot_start_time', 'slot_end_time',
            'motif', 'status', 'status_display',
            'notes', 'refusal_reason', 'created_at', 'updated_at',
        ]
        read_only_fields = ['patient', 'slot', 'motif', 'status', 'created_at', 'updated_at']

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name()

    def get_patient_age(self, obj):
        return obj.patient.age

    def get_patient_phone(self, obj):
        return obj.patient.user.phone

    def get_slot_date(self, obj):
        return obj.slot.date if obj.slot else None

    def get_slot_start_time(self, obj):
        return obj.slot.start_time if obj.slot else None

    def get_slot_end_time(self, obj):
        return obj.slot.end_time if obj.slot else None


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
