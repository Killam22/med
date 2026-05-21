from rest_framework import serializers
from .models import Caretaker, CaretakerService, CareRequest, CareMessage, CaretakerCertificate, CaretakerTask, MedicationSchedule, CaretakerReview
from consultations.serializers import ConsultationPatientSerializer as ConsultationSerializer

class CaretakerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerService
        fields = '__all__'


class CaretakerReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)

    class Meta:
        model = CaretakerReview
        fields = ['id', 'care_request', 'patient_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'patient_name', 'created_at']


class CaretakerOwnProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la gestion du profil par le garde-malade lui-même."""
    class Meta:
        model = Caretaker
        fields = ['id', 'certification', 'experience_years', 'bio',
                  'availability_area', 'is_available', 'tarif_de_base',
                  'maps_url', 'rating', 'total_reviews']
        read_only_fields = ['id', 'rating', 'total_reviews']


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
    caretaker_name    = serializers.CharField(source='caretaker.user.get_full_name', read_only=True)
    caretaker_user_id = serializers.IntegerField(source='caretaker.user.id', read_only=True)
    patient_name      = serializers.CharField(source='patient.get_full_name', read_only=True)
    patient_age        = serializers.SerializerMethodField()
    patient_city       = serializers.CharField(source='patient.city', read_only=True)
    patient_phone      = serializers.CharField(source='patient.phone', read_only=True)
    patient_address    = serializers.CharField(source='patient.address', read_only=True)
    patient_sex        = serializers.CharField(source='patient.sex', read_only=True)
    patient_conditions = serializers.SerializerMethodField()
    location           = serializers.CharField(source='patient.city', read_only=True)
    condition          = serializers.CharField(source='patient_message', read_only=True)
    messages           = CareMessageSerializer(many=True, read_only=True)

    # Dossier médical complet — uniquement si statut ACCEPTED
    patient_medical_dossier = serializers.SerializerMethodField()

    class Meta:
        model = CareRequest
        fields = [
            'id', 'patient', 'patient_name', 'patient_age', 'patient_sex',
            'patient_city', 'patient_address', 'patient_phone', 'patient_conditions',
            'location', 'caretaker', 'caretaker_name', 'caretaker_user_id',
            'status', 'start_date', 'end_date', 'patient_message', 'condition',
            'created_at', 'messages', 'patient_medical_dossier',
        ]
        read_only_fields = ['status', 'patient']
        extra_kwargs = {
            'start_date': {'required': False, 'allow_null': True},
            'patient_message': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "La date de fin doit être postérieure à la date de début."}
            )
        return data

    def get_patient_age(self, obj):
        from datetime import date
        dob = obj.patient.date_of_birth
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_patient_conditions(self, obj):
        try:
            return list(
                obj.patient.patient_profile.antecedents
                .filter(status__in=['active', 'chronic'])
                .values_list('name', flat=True)[:6]
            )
        except Exception:
            return []

    def validate_caretaker(self, value):
        if not value.is_verified:
            raise serializers.ValidationError("Ce garde-malade n'est pas vérifié par la plateforme.")
        if not value.is_available:
            raise serializers.ValidationError("Ce garde-malade est actuellement indisponible.")
        return value

    def get_patient_medical_dossier(self, obj):
        request = self.context.get('request')
        if obj.status == 'accepted' and request and request.user == obj.caretaker.user:
            consultations_data = []
            blood_type = None
            emergency_contact = None
            try:
                profile = obj.patient.patient_profile
                consultations_data = ConsultationSerializer(
                    profile.consultations_as_patient.all(), many=True
                ).data
                mp = profile.medical_profile
                blood_type = mp.blood_group or None
                emergency_contact = mp.emergency_contact_name or None
            except Exception:
                pass
            return {
                "access_granted": True,
                "blood_type": blood_type,
                "emergency_contact": emergency_contact,
                "consultations": consultations_data,
                "medical_notes": "Accès autorisé aux antécédents et ordonnances pour le soin.",
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


class MedicationScheduleSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='care_request.patient.get_full_name', read_only=True)
    patient_id   = serializers.IntegerField(source='care_request.patient.id', read_only=True)

    class Meta:
        model  = MedicationSchedule
        fields = ['id', 'care_request', 'patient_id', 'patient_name', 'condition', 'medications', 'updated_at']
        read_only_fields = ['id', 'patient_id', 'patient_name', 'updated_at']
