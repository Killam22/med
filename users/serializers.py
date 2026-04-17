from django.db import transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Import des modèles de profils spécifiques
from patients.models import Patient
from doctors.models import Doctor, DoctorQualification
from pharmacy.models import Pharmacist, Pharmacy , PharmacistQualification
from caretaker.models import Caretaker, CaretakerCertificate

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
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm', 'role', 'phone', 'sex', 'date_of_birth',
        'id_card_number', 'id_card_recto', 'id_card_verso', 'photo', 'address', 'postal_code', 'city', 'wilaya']

        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'sex': {'required': True},
            'date_of_birth': {'required': True},
            'id_card_number': {'required': True},
            'phone': {'required': True},
            'address': {'required': True},
            'city': {'required': True},
            'wilaya': {'required': True},
            'postal_code': {'required': True},
            'id_card_recto': {'required': True},
            'id_card_verso': {'required': True},
        
        }
       
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        email = validated_data.get('email')
        validated_data['username'] = email
        # set_password gère le hachage automatique
        user = User.objects.create_user(**validated_data)
        return user    

# ── 🏥 Inscriptions Spécifiques (Création des profils) ─────────────────────────

class RegisterPatientSerializer(RegisterUserSerializer):

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields 

    def create(self, validated_data):
        validated_data['role'] = 'patient'
        validated_data['verification_status'] = 'verified'
        validated_data['is_active'] = True 
        validated_data.setdefault('username', validated_data['email'])
        user = super().create(validated_data)
        Patient.objects.create(user=user)
        return user


class RegisterDoctorSerializer(RegisterUserSerializer):
    specialty = serializers.CharField(write_only=True)
    license_number = serializers.CharField(write_only=True)
    practice_authorization = serializers.FileField(write_only=True)
    diploma_title = serializers.CharField(write_only=True)
    diploma_institution = serializers.CharField(write_only=True)
    diploma_year = serializers.IntegerField(write_only=True)
    diploma_type = serializers.CharField(write_only=True)
    diploma_scan = serializers.FileField(write_only=True)

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + [
            'specialty', 'license_number', 'practice_authorization',
            'diploma_title', 'diploma_institution', 'diploma_year', 'diploma_type', 'diploma_scan'
        ]

    @transaction.atomic
    def create(self, validated_data):
        spec = validated_data.pop('specialty')
        lic = validated_data.pop('license_number')
        practice_auth = validated_data.pop('practice_authorization')
        qualif_data = {
            'title': validated_data.pop('diploma_title'),
            'institution': validated_data.pop('diploma_institution'),
            'graduation_year': validated_data.pop('diploma_year'),   # ← nom réel du modèle
            'degree_type': validated_data.pop('diploma_type'),       # ← nom réel du modèle
            'scan': validated_data.pop('diploma_scan')
        }
        validated_data['role'] = 'doctor'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False  
        user = super().create(validated_data)
        doctor_profile = Doctor.objects.create(
            user=user,
            specialty=spec,
            license_number=lic,
            practice_authorization=practice_auth
        )
        DoctorQualification.objects.create(doctor=doctor_profile, **qualif_data)
        return user


class RegisterPharmacistSerializer(RegisterUserSerializer):
    order_registration_number = serializers.CharField(write_only=True)
    # Pharmacie
    pharmacy_name = serializers.CharField(write_only=True)
    pharmacy_license_number = serializers.CharField(write_only=True)
    pharmacy_license = serializers.FileField(write_only=True)
    # Diplôme (identique à DoctorQualification)
    diploma_title = serializers.CharField(write_only=True)
    diploma_institution = serializers.CharField(write_only=True)
    diploma_year = serializers.IntegerField(write_only=True)
    diploma_type = serializers.CharField(write_only=True)
    diploma_scan = serializers.FileField(write_only=True)

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + [
            'order_registration_number',
            'pharmacy_name', 'pharmacy_license_number', 'pharmacy_license',
            'diploma_title', 'diploma_institution', 'diploma_year', 'diploma_type', 'diploma_scan',
        ]

    @transaction.atomic
    def create(self, validated_data):
        order_reg_num = validated_data.pop('order_registration_number')
        pharmacy_data = {
            'name': validated_data.pop('pharmacy_name'),
            'license_number': validated_data.pop('pharmacy_license_number'),
            'pharmacy_license': validated_data.pop('pharmacy_license'),
            'pharm_address': validated_data.get('address'),
            'pharm_city': validated_data.get('city'),
        }
        qualif_data = {
            'title': validated_data.pop('diploma_title'),
            'institution': validated_data.pop('diploma_institution'),
            'graduation_year': validated_data.pop('diploma_year'),
            'degree_type': validated_data.pop('diploma_type'),
            'scan': validated_data.pop('diploma_scan'),
        }
        validated_data['role'] = 'pharmacist'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False

        user = super().create(validated_data)
        pharmacist_profile = Pharmacist.objects.create(user=user, order_registration_number=order_reg_num)
        Pharmacy.objects.create(pharmacist=pharmacist_profile, **pharmacy_data)
        PharmacistQualification.objects.create(pharmacist=pharmacist_profile, **qualif_data)
        return user


class RegisterCaretakerSerializer(RegisterUserSerializer):
    professional_license_number = serializers.CharField(write_only=True)
    cert_title = serializers.CharField(write_only=True)
    cert_organization = serializers.CharField(write_only=True)
    cert_date_obtained = serializers.DateField(write_only=True)
    cert_expiration_date = serializers.DateField(write_only=True)
    cert_scan = serializers.FileField(write_only=True)

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['professional_license_number', 'cert_title', 'cert_organization', 'cert_date_obtained', 'cert_expiration_date', 'cert_scan']

    @transaction.atomic
    def create(self, validated_data):
        license_number = validated_data.pop('professional_license_number')
        cert_data = {
            'name': validated_data.pop('cert_title'),           # ← nom réel du modèle CaretakerCertificate
            'organization': validated_data.pop('cert_organization'),
            'date_obtained': validated_data.pop('cert_date_obtained'),
            'expiration_date': validated_data.pop('cert_expiration_date'),
            'scan': validated_data.pop('cert_scan')
        }
        validated_data['role'] = 'caretaker'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False
        
        user = super().create(validated_data)
        caretaker_profile = Caretaker.objects.create(
            user=user,
            professional_license_number=license_number  # ← nom réel du modèle Caretaker
        )
        CaretakerCertificate.objects.create(caretaker=caretaker_profile, **cert_data)
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