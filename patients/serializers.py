from rest_framework import serializers
from .models import Patient, MedicalProfile, Allergy, Antecedent, Treatment, MedicalDocument, DocumentFile, SymptomAnalysis

class PatientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    age = serializers.IntegerField(read_only=True)
    
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False, allow_null=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)
    city = serializers.CharField(source='user.city', required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'email', 'first_name', 'last_name', 'date_of_birth', 'age',
            'phone', 'address', 'city'
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
    bmi = serializers.ReadOnlyField()
    antecedents = serializers.SerializerMethodField()
    treatments = serializers.SerializerMethodField()
    medical_documents = serializers.SerializerMethodField()

    class Meta:
        model = MedicalProfile
        fields = [
            'id', 'patient', 'weight', 'height', 'blood_group', 
            'emergency_contact_name', 'emergency_contact_phone', 'bmi',
            'allergies', 'treatments', 'antecedents', 'medical_documents'
        ]
        read_only_fields = ['patient']


    def get_antecedents(self, obj):
        return AntecedentSerializer(obj.patient.antecedents.all(), many=True).data

    def get_treatments(self, obj):
        return TreatmentSerializer(obj.patient.treatments.all(), many=True).data

    def get_medical_documents(self, obj):
        return MedicalDocumentSerializer(obj.patient.medical_documents.all(), many=True).data
