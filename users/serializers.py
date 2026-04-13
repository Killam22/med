from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Import des modèles de profils spécifiques
from patients.models import Patient
from doctors.models import Doctor
from pharmacy.models import Pharmacist
from caretaker.models import Caretaker

User = get_user_model()

# ── 🔑 Tokens JWT Personnalisés ────────────────────────────────────────────────

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Ajoute des infos utiles dans le payload du token (lu par le front-end)"""
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


# ── 📝 Inscriptions (Logique de base) ──────────────────────────────────────────

class RegisterUserSerializer(serializers.ModelSerializer):
    """Sérialiseur de base pour l'inscription. Gère la sécurité du mot de passe."""
    # validate_password vérifie la complexité (majuscules, chiffres, etc.) selon settings.py
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm', 'role', 'phone']

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({"password_confirm": "Les mots de passe ne correspondent pas."})
        return data


# ── 🏥 Inscriptions Spécifiques (Création des profils) ─────────────────────────

class RegisterPatientSerializer(RegisterUserSerializer):
    def create(self, validated_data):
        validated_data['role'] = 'patient'
        validated_data['is_active'] = False  # Désactivé en attente de l'OTP
        validated_data.setdefault('username', validated_data['email'])
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
        validated_data['is_active'] = False  # Désactivé en attente de l'OTP
        validated_data.setdefault('username', validated_data['email'])
        
        user = User.objects.create_user(**validated_data)
        Doctor.objects.create(user=user, specialty=specialty, license_number=license_number)
        return user


class RegisterPharmacistSerializer(RegisterUserSerializer):
    license_number = serializers.CharField(write_only=True)  # correspond au champ Pharmacist.license_number

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['license_number']

    def create(self, validated_data):
        license_num = validated_data.pop('license_number')
        validated_data['role'] = 'pharmacist'
        validated_data['is_active'] = False
        validated_data.setdefault('username', validated_data['email'])
        
        user = User.objects.create_user(**validated_data)
        Pharmacist.objects.create(user=user, license_number=license_num)
        return user


class RegisterCaretakerSerializer(RegisterUserSerializer):
    sex = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['sex']

    def create(self, validated_data):
        validated_data['role'] = 'caretaker'
        validated_data['is_active'] = False
        validated_data.setdefault('username', validated_data['email'])
        
        user = User.objects.create_user(**validated_data)
        Caretaker.objects.create(user=user)
        return user


# ── 🔐 Gestion du Mot de Passe ─────────────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """Pour les utilisateurs déjà connectés qui veulent changer leur mot de passe"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value


# ── 🦎 Profil Utilisateur (Lecture et Caméléon) ────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """Sérialiseur de lecture pour lister les utilisateurs (Admin)"""
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'phone', 
            'sex', 'date_of_birth', 'address', 'postal_code', 'city', 'wilaya',
            'verification_status', 'is_active'
        ]
        read_only_fields = ['role', 'verification_status', 'is_active']


class BaseUserUpdateSerializer(serializers.ModelSerializer):
    """Base pour la mise à jour des infos générales (Endpoint Caméléon)"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'sex', 
            'date_of_birth', 'address', 'postal_code', 'city', 'wilaya'
        ]

# Import local pour éviter les imports circulaires avec l'app patients
from patients.serializers import PatientSerializer 

class PatientUnifiedSerializer(BaseUserUpdateSerializer):
    """Fusionne le User de base avec le profil Patient pour l'Update"""
    # Nommé 'patient_profile' en sortie JSON, source='patient_profile' serait
    # redondant (DRF le refuse). On rend le champ imbriqué accessible sous la
    # clé 'patient_profile' via un serializer qui accède à user.patient_profile
    patient_profile = PatientSerializer(read_only=False, required=False)

    class Meta(BaseUserUpdateSerializer.Meta):
        fields = BaseUserUpdateSerializer.Meta.fields + ['patient_profile']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('patient_profile', None)
        
        # 1. Mise à jour du CustomUser
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 2. Mise à jour du PatientProfile
        if profile_data:
            patient_data = profile_data.get('user', {})
            for attr, value in patient_data.items():
                setattr(instance, attr, value)
            if patient_data:
                instance.save(update_fields=list(patient_data.keys()))
            
            patient_profile_data = {k: v for k, v in profile_data.items() if k != 'user'}
            if patient_profile_data:
                profile, _ = Patient.objects.get_or_create(user=instance)
                for attr, value in patient_profile_data.items():
                    setattr(profile, attr, value)
                profile.save()

        return instance