from rest_framework import serializers
from .models import Caretaker, CaretakerService, CareRequest, CareMessage, CaretakerCertificate, CaretakerTask
from consultations.serializers import ConsultationSerializer 
from prescriptions.serializers import PrescriptionSerializer 

class CaretakerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerService
        fields = '__all__'

class CaretakerProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    services = CaretakerServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Caretaker
        fields = ['id', 'user_id', 'full_name', 'certification', 'experience_years', 'bio',
                  'availability_area', 'is_verified', 'is_available', 'services', 'tarif_de_base']

class CareMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    class Meta:
        model = CareMessage
        fields = ['id', 'sender', 'sender_name', 'content', 'created_at']

class CareRequestSerializer(serializers.ModelSerializer):
    caretaker_name = serializers.CharField(source='caretaker.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    messages = CareMessageSerializer(many=True, read_only=True)
    
    # Le dossier médical ne sera injecté que si le statut est "ACCEPTED"
    patient_medical_dossier = serializers.SerializerMethodField()

    class Meta:
        model = CareRequest
        fields = [
            'id', 'patient', 'patient_name', 'caretaker', 'caretaker_name', 
            'status', 'start_date', 'end_date', 'patient_message', 
            'created_at', 'messages', 'patient_medical_dossier'
        ]
        read_only_fields = ['status', 'patient']

    def validate_caretaker(self, value):
        """Empêcher l'envoi de requêtes à des gardes-malades inactifs ou non vérifiés."""
        if not value.is_verified:
            raise serializers.ValidationError("Ce garde-malade n'est pas vérifié par la plateforme.")
        if not value.is_available:
            raise serializers.ValidationError("Ce garde-malade est actuellement indisponible.")
        return value

    def get_patient_medical_dossier(self, obj):
        # SECURITE : Accès strict accordé UNIQUEMENT au garde-malade ciblé et SI le contrat est accepté
        request = self.context.get('request')
        if obj.status == 'accepted' and request and request.user == obj.caretaker.user:
            
            consultations_data = []
            # Il FAUT passer par patient_profile car consultations_as_patient est sur le modèle Patient
            if hasattr(obj.patient, 'patient_profile'):
                consultations = obj.patient.patient_profile.consultations_as_patient.all()
                consultations_data = ConsultationSerializer(consultations, many=True).data
            
            return {
                "access_granted": True,
                "blood_type": obj.patient.blood_type,
                "emergency_contact": obj.patient.emergency_contact,
                "consultations": consultations_data,
                "medical_notes": "Accès autorisé aux antécédents et ordonnances pour le soin."
            }
        return {"access_granted": False, "message": "Accès bloqué. Demande non acceptée."}

class CaretakerCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerCertificate
        fields = ['name', 'organization', 'date_obtained', 'expiration_date', 'scan']


class CaretakerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerTask
        fields = ['id', 'care_request', 'title', 'description', 'status', 'due_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']