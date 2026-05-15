from rest_framework import serializers
from .models import Consultation


class ConsultationDoctorSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.user.get_full_name', read_only=True)

    class Meta:
        model = Consultation
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            return attrs
        user = request.user
        if hasattr(user, 'doctor_profile'):
            logged_in_doctor = user.doctor_profile
            chosen_doctor = attrs.get('doctor')
            if chosen_doctor and chosen_doctor != logged_in_doctor:
                raise serializers.ValidationError({
                    "doctor": "Vous ne pouvez pas créer une consultation pour un autre médecin."
                })
            appointment = attrs.get('appointment')
            if appointment:
                if appointment.doctor != logged_in_doctor:
                    raise serializers.ValidationError({
                        "appointment": "Ce rendez-vous n'appartient pas à votre planning."
                    })
                if appointment.status in ['cancelled', 'refused']:
                    raise serializers.ValidationError({
                        "appointment": "Impossible de créer une consultation pour un rendez-vous annulé ou refusé."
                    })
        return attrs


class ConsultationPatientSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.get_full_name', read_only=True)

    class Meta:
        model = Consultation
        exclude = ['doctor_notes']
