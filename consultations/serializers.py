from rest_framework import serializers
from .models import Consultation

class ConsultationSerializer(serializers.ModelSerializer):
    doctor_name = serializers.ReadOnlyField(source='doctor.user.get_full_name')
    patient_name = serializers.ReadOnlyField(source='patient.user.get_full_name')

    class Meta:
        model = Consultation
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get('request')
        if not request or not request.user:
            return attrs

        user = request.user
        
        # Check if the user is a doctor
        if hasattr(user, 'doctor_profile'):
            logged_in_doctor = user.doctor_profile
            
            # 1. Check doctor consistency
            chosen_doctor = attrs.get('doctor')
            if chosen_doctor and chosen_doctor != logged_in_doctor:
                raise serializers.ValidationError({
                    "doctor": "Vous ne pouvez pas créer une consultation pour un autre médecin."
                })

            # 2. Check appointment consistency
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
