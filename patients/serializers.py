from rest_framework import serializers
from .models import Patient, MedicalProfile, Allergy, Antecedent, Treatment, MedicalDocument, DocumentFile, SymptomAnalysis, PatientLinkRequest, ExternalPatient

class PatientSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    age = serializers.IntegerField(read_only=True)
    photo = serializers.ImageField(source='user.photo', read_only=True)
    messages_disabled = serializers.BooleanField(source='user.messages_disabled', read_only=True)

    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False, allow_null=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)
    postal_code = serializers.CharField(source='user.postal_code', required=False, allow_blank=True)
    city = serializers.CharField(source='user.city', required=False, allow_blank=True)
    wilaya = serializers.CharField(source='user.wilaya', required=False, allow_blank=True)
    sex = serializers.CharField(source='user.sex', required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name', 'date_of_birth', 'age',
            'phone', 'address', 'postal_code', 'city', 'wilaya', 'sex', 'photo', 'messages_disabled'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = '__all__'
        read_only_fields = ['profile']


class AntecedentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecedent
        fields = '__all__'
        read_only_fields = ['patient']

class TreatmentSerializer(serializers.ModelSerializer):
    prescribed_by_name = serializers.ReadOnlyField(source='prescribed_by.user.get_full_name')

    class Meta:
        model = Treatment
        fields = '__all__'
        read_only_fields = ['patient']

class DocumentFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentFile
        fields = ['id', 'file', 'file_name', 'file_size']

class MedicalDocumentSerializer(serializers.ModelSerializer):
    files = DocumentFileSerializer(many=True, read_only=True)
    uploaded_by_name = serializers.ReadOnlyField(source='uploaded_by.get_full_name')

    class Meta:
        model = MedicalDocument
        fields = '__all__'
        read_only_fields = ['patient', 'uploaded_by', 'uploaded_at']

    def create(self, validated_data):
        document = MedicalDocument.objects.create(**validated_data)
        
        # Obtenir les fichiers envoyés avec la requête (si multipart/form-data)
        request = self.context.get('request')
        if request and request.FILES:
            files = request.FILES.getlist('uploaded_files')
            for f in files:
                DocumentFile.objects.create(document=document, file=f)
                
        return document

class SymptomAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomAnalysis
        fields = ['id', 'symptoms', 'suggested_diagnosis', 'urgency_level', 'created_at']
        read_only_fields = ['patient']


class MedicalProfileSerializer(serializers.ModelSerializer):
    allergies = AllergySerializer(many=True, read_only=True)
    allergies_input = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        write_only=True, required=False, allow_empty=True
    )
    bmi = serializers.ReadOnlyField()
    antecedents = serializers.SerializerMethodField()
    treatments = serializers.SerializerMethodField()
    medical_documents = serializers.SerializerMethodField()

    class Meta:
        model = MedicalProfile
        fields = [
            'id', 'patient', 'weight', 'height', 'blood_group',
            'emergency_contact_name', 'emergency_contact_phone', 'bmi',
            'allergies', 'allergies_input', 'treatments', 'antecedents', 'medical_documents'
        ]
        read_only_fields = ['patient']

    def update(self, instance, validated_data):
        allergies_input = validated_data.pop('allergies_input', None)
        instance = super().update(instance, validated_data)
        if allergies_input is not None:
            instance.allergies.all().delete()
            for substance in allergies_input:
                substance = substance.strip()
                if substance:
                    Allergy.objects.create(profile=instance, substance=substance)
        return instance

    def get_antecedents(self, obj):
        return AntecedentSerializer(obj.patient.antecedents.all(), many=True).data

    def get_treatments(self, obj):
        return TreatmentSerializer(obj.patient.treatments.all(), many=True).data

    def get_medical_documents(self, obj):
        return MedicalDocumentSerializer(obj.patient.medical_documents.all(), many=True).data


class PatientSearchSerializer(serializers.ModelSerializer):
    """Résultats de recherche de patients pour un médecin (inclut le statut de liaison)."""
    first_name  = serializers.CharField(source='user.first_name', read_only=True)
    last_name   = serializers.CharField(source='user.last_name',  read_only=True)
    age         = serializers.IntegerField(read_only=True)
    link_status = serializers.SerializerMethodField()

    class Meta:
        model  = Patient
        fields = ['id', 'first_name', 'last_name', 'age', 'link_status']

    def get_link_status(self, obj):
        try:
            request = self.context.get('request')
            if not request:
                return None
            user = request.user
            if not user or not user.is_authenticated:
                return None
            try:
                doctor = user.doctor_profile
            except Exception:
                return None
            from appointments.models import Appointment
            if Appointment.objects.filter(doctor=doctor, patient=obj).exists():
                return 'linked'
            try:
                return PatientLinkRequest.objects.get(doctor=doctor, patient=obj).status
            except PatientLinkRequest.DoesNotExist:
                return None
        except Exception:
            return None


class PatientLinkRequestSerializer(serializers.ModelSerializer):
    """Vue patient : demandes d'accès reçues d'un médecin."""
    doctor_id        = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name      = serializers.SerializerMethodField()
    doctor_specialty = serializers.CharField(source='doctor.specialty', read_only=True)

    class Meta:
        model  = PatientLinkRequest
        fields = ['id', 'doctor_id', 'doctor_name', 'doctor_specialty', 'status', 'created_at']

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"


class ExternalPatientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExternalPatient
        fields = ['id', 'first_name', 'last_name', 'age', 'phone', 'condition', 'notes', 'created_at']
        read_only_fields = ['created_at']
