from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from patients.models import Patient
from doctors.models import Doctor
from pharmacy.models import Pharmacist
from caretaker.models import Caretaker

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.get_full_name()
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['full_name'] = self.user.get_full_name()
        data['email'] = self.user.email
        return data

class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm', 'role', 'phone']

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        return data

class RegisterPatientSerializer(RegisterUserSerializer):
    def create(self, validated_data):
        validated_data['role'] = 'patient'
        user = User.objects.create_user(**validated_data)
        Patient.objects.create(user=user)
        return user

class RegisterDoctorSerializer(RegisterUserSerializer):
    specialty = serializers.CharField(write_only=True)
    license_number = serializers.CharField(write_only=True)

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['specialty', 'license_number']

    def create(self, validated_data):
        specialty = validated_data.pop('specialty')
        license_number = validated_data.pop('license_number')
        validated_data['role'] = 'doctor'
        user = User.objects.create_user(**validated_data)
        Doctor.objects.create(user=user, specialty=specialty, license_number=license_number)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'phone', 
            'sex', 'date_of_birth', 'city', 'verification_status'
        ]
        read_only_fields = ['role', 'verification_status']
