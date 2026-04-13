from rest_framework import serializers
from .models import Patient, MedicalProfile, Antecedent, Treatment, LabResult, SymptomAnalysis

class PatientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    age = serializers.IntegerField(read_only=True)
    
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False, allow_null=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)
    city = serializers.CharField(source='user.city', required=False, allow_blank=True)
    blood_group = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'email', 'first_name', 'last_name', 'date_of_birth', 'age',
            'phone', 'address', 'city', 'blood_group', 'medical_history', 'photo',
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

class MedicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
         model = MedicalProfile
         fields = '__all__'

class AntecedentSerializer(serializers.ModelSerializer):
    class Meta:
         model = Antecedent
         fields = '__all__'

class TreatmentSerializer(serializers.ModelSerializer):
    class Meta:
         model = Treatment
         fields = '__all__'

class LabResultSerializer(serializers.ModelSerializer):
    class Meta:
         model = LabResult
         fields = '__all__'

class SymptomAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
         model = SymptomAnalysis
         fields = '__all__'
