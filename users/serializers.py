from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Import des modèles de profils spécifiques
from patients.models import Patient
from doctors.models import Doctor, DoctorQualification, Diploma
from pharmacy.models import Pharmacist, Pharmacy , PharmacistQualification
from caretaker.models import Caretaker, CaretakerCertificate, CaretakerDiploma

from .models import EmailOTP, ProfileUpdateRequest
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
        user = self.user
        vs = getattr(user, 'verification_status', None)
        if vs == 'pending':
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed(
                'Votre dossier est en cours de validation par notre équipe. '
                'Vous recevrez un e-mail dès qu\'il sera approuvé.'
            )
        if vs == 'rejected':
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed(
                'Votre inscription a été refusée. Veuillez contacter le support.'
            )
        data['role'] = user.role
        data['full_name'] = user.get_full_name()
        data['email'] = user.email
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
    # Champ optionnel — stocké dans MedicalProfile, pas sur User.
    blood_group = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['blood_group']

    def create(self, validated_data):
        blood_group = validated_data.pop('blood_group', '') or ''
        validated_data['role'] = 'patient'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = True
        validated_data.setdefault('username', validated_data['email'])
        user = super().create(validated_data)
        patient = Patient.objects.create(user=user)

        # Crée le profil médical avec le groupe sanguin si fourni et valide.
        if blood_group:
            from patients.models import MedicalProfile
            valid_choices = {c[0] for c in MedicalProfile.BLOOD_GROUP_CHOICES}
            if blood_group in valid_choices:
                MedicalProfile.objects.create(patient=patient, blood_group=blood_group)
        return user


_SPECIALTY_MAP = {
    "Généraliste":       "general",
    "Cardiologue":       "cardiology",
    "Dermatologue":      "dermatology",
    "Gynécologue":       "gynecology",
    "Neurologue":        "neurology",
    "Ophtalmologue":     "ophthalmology",
    "Orthopédiste":      "orthopedics",
    "Pédiatre":          "pediatrics",
    "Psychiatre":        "psychiatry",
    "Urologue":          "urology",
    "Radiologue":        "general",
    "Rhumatologue":      "general",
    "Endocrinologue":    "general",
    "Gastro-entérologue":"general",
}

class RegisterDoctorSerializer(RegisterUserSerializer):
    specialty = serializers.CharField(write_only=True)
    order_number = serializers.CharField(
        write_only=True,
        validators=[UniqueValidator(
            queryset=Doctor.objects.all(),
            message="Ce numéro d'inscription à l'Ordre est déjà utilisé.",
        )],
    )
    practice_authorization = serializers.FileField(write_only=True)
    experience_years = serializers.IntegerField(write_only=True)
    clinic_name = serializers.CharField(write_only=True)
    cnas_coverage = serializers.BooleanField(write_only=True)
    maps_url = serializers.URLField(write_only=True, required=False, allow_blank=True, default='')

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + [
            'specialty', 'order_number', 'practice_authorization',
            'experience_years', 'clinic_name', 'cnas_coverage', 'maps_url'
        ]

    @transaction.atomic
    def create(self, validated_data):
        spec_raw = validated_data.pop('specialty')
        spec = _SPECIALTY_MAP.get(spec_raw, spec_raw)
        order = validated_data.pop('order_number')
        practice_auth = validated_data.pop('practice_authorization')
        exp_years = validated_data.pop('experience_years')
        clinic = validated_data.pop('clinic_name')
        cnas = validated_data.pop('cnas_coverage')
        maps_url = validated_data.pop('maps_url', '')
        validated_data['role'] = 'doctor'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False
        user = super().create(validated_data)
        doctor_profile = Doctor.objects.create(
            user=user,
            specialty=spec,
            order_number=order,
            practice_authorization=practice_auth,
            experience_years=exp_years,
            clinic_name=clinic,
            cnas_coverage=cnas,
            maps_url=maps_url,
        )

        # Handle Multiple Diplomas
        request = self.context.get('request')
        if request:
            idx = 0
            while True:
                title = request.data.get(f'diplomas[{idx}][title]')
                if not title:
                    break
                
                # Convert DD/MM/YYYY to YYYY-MM-DD
                date_str = request.data.get(f'diplomas[{idx}][date_obtained]')
                date_obj = None
                if date_str and '/' in date_str:
                    try:
                        d, m, y = date_str.split('/')
                        date_obj = f"{y}-{m}-{d}"
                    except:
                        date_obj = date_str
                else:
                    date_obj = date_str

                Diploma.objects.create(
                    doctor=doctor_profile,
                    title=title,
                    institution=request.data.get(f'diplomas[{idx}][institution]', ''),
                    date_obtained=date_obj,
                    specialization=request.data.get(f'diplomas[{idx}][specialization]', ''),
                    file=request.data.get(f'diplomas[{idx}][file]')
                )
                idx += 1

        return user



class RegisterPharmacistSerializer(RegisterUserSerializer):
    #pharmacien
    order_registration_number = serializers.CharField(write_only=True)
    cnas_coverage = serializers.BooleanField(write_only=True)
    #pharmacie
    name = serializers.CharField(write_only=True)
    agreement_number = serializers.CharField(write_only=True)
    agreement_scan = serializers.FileField(write_only=True)
    registre_commerce = serializers.FileField(write_only=True)
    maps_url = serializers.URLField(write_only=True, required=False, allow_blank=True, default='')

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + [
            'order_registration_number',
            'name', 'agreement_number', 'agreement_scan', 'registre_commerce', 'cnas_coverage', 'maps_url',
        ]

    @transaction.atomic
    def create(self, validated_data):
        order_reg_num = validated_data.pop('order_registration_number')
        cnas = validated_data.pop('cnas_coverage')
        maps_url = validated_data.pop('maps_url', '')
        pharmacy_data = {
            'name': validated_data.pop('name'),
            'agreement_number': validated_data.pop('agreement_number'),
            'agreement_scan': validated_data.pop('agreement_scan'),
            'registre_commerce': validated_data.pop('registre_commerce'),
            'maps_url': maps_url,
        }

        validated_data['role'] = 'pharmacist'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False

        user = super().create(validated_data)
        pharmacist_profile = Pharmacist.objects.create(user=user, order_registration_number=order_reg_num, cnas_coverage=cnas)
        Pharmacy.objects.create(pharmacist=pharmacist_profile, **pharmacy_data)
        return user



class RegisterCaretakerSerializer(RegisterUserSerializer):
    criminal_record_scan = serializers.FileField(write_only=True)
    availability_area = serializers.CharField(write_only=True)
    experience_years = serializers.IntegerField(write_only=True)
    tarif_de_base = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True)
    maps_url = serializers.URLField(write_only=True, required=False, allow_blank=True, default='')

    class Meta(RegisterUserSerializer.Meta):
        fields = RegisterUserSerializer.Meta.fields + ['criminal_record_scan', 'availability_area', 'experience_years', 'tarif_de_base', 'maps_url']

    @transaction.atomic
    def create(self, validated_data):
        criminal_record_scan = validated_data.pop('criminal_record_scan')
        availability_area = validated_data.pop('availability_area')
        experience_years = validated_data.pop('experience_years')
        tarif_de_base = validated_data.pop('tarif_de_base')
        maps_url = validated_data.pop('maps_url', '')
        validated_data['role'] = 'caretaker'
        validated_data['verification_status'] = 'pending'
        validated_data['is_active'] = False

        user = super().create(validated_data)
        caretaker_profile = Caretaker.objects.create(
            user=user,
            criminal_record_scan=criminal_record_scan,
            availability_area=availability_area,
            experience_years=experience_years,
            tarif_de_base=tarif_de_base,
            maps_url=maps_url,
        )

        # Handle Multiple Diplomas
        request = self.context.get('request')
        if request:
            idx = 0
            while True:
                title = request.data.get(f'diplomas[{idx}][title]')
                if not title:
                    break
                
                # Convert DD/MM/YYYY to YYYY-MM-DD
                date_str = request.data.get(f'diplomas[{idx}][date_obtained]')
                date_obj = None
                if date_str and '/' in date_str:
                    try:
                        d, m, y = date_str.split('/')
                        date_obj = f"{y}-{m}-{d}"
                    except:
                        date_obj = date_str
                else:
                    date_obj = date_str

                CaretakerDiploma.objects.create(
                    caretaker=caretaker_profile,
                    title=title,
                    institution=request.data.get(f'diplomas[{idx}][institution]', ''),
                    date_obtained=date_obj,
                    specialization=request.data.get(f'diplomas[{idx}][specialization]', ''),
                    file=request.data.get(f'diplomas[{idx}][file]')
                )
                idx += 1

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
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'first_name', 'last_name', 'role', 'phone',
            'sex', 'date_of_birth', 'address', 'postal_code', 'city', 'wilaya',
            'verification_status', 'is_active', 'messages_disabled'
        ]
        read_only_fields = ['full_name', 'role', 'verification_status', 'is_active']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class BaseUserUpdateSerializer(serializers.ModelSerializer):
    """Base pour la mise à jour des infos générales (Endpoint Caméléon)"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'role', 'full_name', 'first_name', 'last_name', 'phone', 'sex',
            'date_of_birth', 'address', 'postal_code', 'city', 'wilaya',
            'verification_status', 'is_active', 'photo', 'messages_disabled'
        ]
        read_only_fields = ['id', 'role', 'full_name', 'verification_status', 'is_active']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def validate_email(self, value):
        user = self.instance
        if value and user and value != user.email:
            if User.objects.filter(email=value).exclude(pk=user.pk).exists():
                raise serializers.ValidationError("Un compte avec cet email existe déjà.")
        return value

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


class DoctorUnifiedSerializer(BaseUserUpdateSerializer):
    specialty = serializers.CharField(source='doctor_profile.specialty', read_only=True)
    order_number = serializers.CharField(source='doctor_profile.order_number', read_only=True)
    clinic_name = serializers.CharField(source='doctor_profile.clinic_name', read_only=True)
    cnas_coverage = serializers.BooleanField(source='doctor_profile.cnas_coverage', read_only=True)
    maps_url = serializers.URLField(source='doctor_profile.maps_url', required=False, allow_blank=True)

    class Meta(BaseUserUpdateSerializer.Meta):
        fields = BaseUserUpdateSerializer.Meta.fields + [
            'specialty', 'order_number', 'clinic_name', 'cnas_coverage', 'maps_url'
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('doctor_profile', None)
        instance = super().update(instance, validated_data)

        if profile_data:
            doctor_profile = getattr(instance, 'doctor_profile', None)
            if doctor_profile:
                for attr, value in profile_data.items():
                    setattr(doctor_profile, attr, value)
                doctor_profile.save()

        return instance


class PharmacistUnifiedSerializer(BaseUserUpdateSerializer):
    order_registration_number = serializers.CharField(source='pharmacist_profile.order_registration_number', read_only=True)
    cnas_coverage = serializers.BooleanField(source='pharmacist_profile.cnas_coverage', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacist_profile.pharmacy.name', read_only=True)
    maps_url = serializers.URLField(source='pharmacist_profile.pharmacy.maps_url', required=False, allow_blank=True)

    class Meta(BaseUserUpdateSerializer.Meta):
        fields = BaseUserUpdateSerializer.Meta.fields + [
            'order_registration_number', 'cnas_coverage', 'pharmacy_name', 'maps_url'
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('pharmacist_profile', None)
        instance = super().update(instance, validated_data)

        if profile_data:
            pharmacist_profile = getattr(instance, 'pharmacist_profile', None)
            if pharmacist_profile and hasattr(pharmacist_profile, 'pharmacy'):
                pharmacy = pharmacist_profile.pharmacy
                pharmacy_data = profile_data.get('pharmacy', {}) if isinstance(profile_data, dict) else {}
                for attr, value in pharmacy_data.items():
                    setattr(pharmacy, attr, value)
                pharmacy.save()

        return instance


class CaretakerUnifiedSerializer(BaseUserUpdateSerializer):
    availability_area = serializers.CharField(source='caretaker_profile.availability_area', required=False, allow_blank=True)
    tarif_de_base = serializers.DecimalField(source='caretaker_profile.tarif_de_base', required=False, max_digits=10, decimal_places=2)
    maps_url = serializers.URLField(source='caretaker_profile.maps_url', required=False, allow_blank=True)
    experience_years = serializers.IntegerField(source='caretaker_profile.experience_years', required=False)

    class Meta(BaseUserUpdateSerializer.Meta):
        fields = BaseUserUpdateSerializer.Meta.fields + [
            'availability_area', 'tarif_de_base', 'maps_url', 'experience_years'
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('caretaker_profile', None)
        instance = super().update(instance, validated_data)

        if profile_data:
            caretaker_profile = getattr(instance, 'caretaker_profile', None)
            if caretaker_profile:
                for attr, value in profile_data.items():
                    setattr(caretaker_profile, attr, value)
                caretaker_profile.save()

        return instance


class ProfileUpdateRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    user_full_name = serializers.ReadOnlyField(source='user.get_full_name')
    old_first_name = serializers.ReadOnlyField(source='user.first_name')
    old_last_name = serializers.ReadOnlyField(source='user.last_name')
    full_name_requested = serializers.SerializerMethodField()

    class Meta:
        model = ProfileUpdateRequest
        fields = '__all__'
        read_only_fields = ['user', 'status', 'created_at', 'reviewed_at', 'reviewed_by', 'admin_notes']

    def get_full_name_requested(self, obj):
        return f"{obj.new_first_name} {obj.new_last_name}"
