from rest_framework import serializers
from django.contrib.auth import get_user_model
from patients.models import Patient, MedicalProfile
from caretaker.models import Caretaker
from pharmacy.models import Pharmacist, Pharmacy

User = get_user_model()


# ─────────────────────────────────────────────
# 1. SHARED — Edit Profile (CustomUser fields)
# ─────────────────────────────────────────────
class BaseProfileSerializer(serializers.ModelSerializer):
    """
    Editable shared fields for ALL roles.
    Read-only: email, sex, date_of_birth, id_card_*, verification_status, role.
    """
    class Meta:
        model = User
        fields = [
            'id',
            # read-only identity
            'email', 'role', 'sex', 'date_of_birth',
            'id_card_number', 'id_card_recto', 'id_card_verso',
            'verification_status',
            # editable
            'first_name', 'last_name',
            'phone', 'photo',
            'address', 'postal_code', 'city', 'wilaya',
        ]
        read_only_fields = [
            'id', 'email', 'role', 'sex', 'date_of_birth',
            'id_card_number', 'id_card_recto', 'id_card_verso',
            'verification_status',
        ]


# ─────────────────────────────────────────────
# 2. PATIENT — Edit Profile
# ─────────────────────────────────────────────
class MedicalProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalProfile
        fields = ['weight', 'height', 'allergies', 'chronic_diseases', 'current_medications']


class PatientProfileSerializer(BaseProfileSerializer):
    
    medical_profile   = MedicalProfileSerializer(source='patient_profile.medical_profile', required=False)

    class Meta(BaseProfileSerializer.Meta):
        fields = BaseProfileSerializer.Meta.fields + [
             'medical_profile'
        ]

    def update(self, instance, validated_data):
        # Pop nested data
        patient_data        = validated_data.pop('patient_profile', {})
        medical_profile_data = patient_data.pop('medical_profile', {})

        # Update base user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Patient model
        patient = instance.patient_profile
        for attr, value in patient_data.items():
            setattr(patient, attr, value)
        patient.save()

        # Update MedicalProfile
        if medical_profile_data:
            mp = patient.medical_profile
            for attr, value in medical_profile_data.items():
                setattr(mp, attr, value)
            mp.save()

        return instance


# ─────────────────────────────────────────────
# 3. CARETAKER — Edit Profile
# ─────────────────────────────────────────────
class CaretakerProfileSerializer(BaseProfileSerializer):
    bio               = serializers.CharField(source='caretaker_profile.bio', allow_blank=True, required=False)
    certification     = serializers.CharField(source='caretaker_profile.certification', allow_blank=True, required=False)
    experience_years  = serializers.IntegerField(source='caretaker_profile.experience_years', required=False)
    availability_area = serializers.CharField(source='caretaker_profile.availability_area', allow_blank=True, required=False)
    is_available      = serializers.BooleanField(source='caretaker_profile.is_available', required=False)

    # read-only verified fields
    professional_license_number = serializers.CharField(source='caretaker_profile.professional_license_number', read_only=True)
    is_verified                 = serializers.BooleanField(source='caretaker_profile.is_verified', read_only=True)

    class Meta(BaseProfileSerializer.Meta):
        fields = BaseProfileSerializer.Meta.fields + [
            'bio', 'certification', 'experience_years',
            'availability_area', 'is_available',
            'professional_license_number', 'is_verified',
        ]

    def update(self, instance, validated_data):
        caretaker_data = validated_data.pop('caretaker_profile', {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        caretaker = instance.caretaker_profile
        for attr, value in caretaker_data.items():
            setattr(caretaker, attr, value)
        caretaker.save()

        return instance


# ─────────────────────────────────────────────
# 4. PHARMACIST — Edit Profile
# ─────────────────────────────────────────────
class PharmacySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy
        fields = [
            'name', 'pharm_address', 'pharm_city', 'pharm_phone',
            'latitude', 'longitude', 'is_open_24h',
        ]
        # license_number & pharmacy_license are verified docs → read-only
        read_only_fields = []


class PharmacistProfileSerializer(BaseProfileSerializer):
    pharmacy = PharmacySerializer(source='pharmacist_profile.pharmacy', required=False)

    # read-only verified fields
    order_registration_number = serializers.CharField(source='pharmacist_profile.order_registration_number', read_only=True)
    is_verified               = serializers.BooleanField(source='pharmacist_profile.is_verified', read_only=True)

    class Meta(BaseProfileSerializer.Meta):
        fields = BaseProfileSerializer.Meta.fields + [
            'pharmacy', 'order_registration_number', 'is_verified',
        ]

    def update(self, instance, validated_data):
        pharmacist_data = validated_data.pop('pharmacist_profile', {})
        pharmacy_data   = pharmacist_data.pop('pharmacy', {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if pharmacy_data:
            pharmacy = instance.pharmacist_profile.pharmacy
            for attr, value in pharmacy_data.items():
                setattr(pharmacy, attr, value)
            pharmacy.save()

        return instance


# ─────────────────────────────────────────────
# 5. ADMIN — Edit Profile
# ─────────────────────────────────────────────
class AdminProfileSerializer(BaseProfileSerializer):
    """Admin can only edit basic shared fields."""
    class Meta(BaseProfileSerializer.Meta):
        pass


# ─────────────────────────────────────────────
# 6. NOTIFICATION PREFERENCES
# ─────────────────────────────────────────────
class NotificationPreferencesSerializer(serializers.ModelSerializer):
    """
    Controls which notification TYPES the user receives and via which CHANNELS.
    Type names map directly to notifications.Notification.NotificationType choices.
    The actual Notification objects are managed by the `notifications` app.
    """
    class Meta:
        from settings.models import NotificationPreferences
        model = NotificationPreferences
        fields = [
            # Type toggles — mirror NotificationType in notifications app
            'notify_appointment',
            'notify_pharmacy',
            'notify_caretaker',
            'notify_system',
            # Channel preferences
            'email_notifications',
            'sms_notifications',
            'in_app_notifications',
            # read-only timestamp
            'updated_at',
        ]
        read_only_fields = ['updated_at']


# ─────────────────────────────────────────────
# 8. ACCOUNT DEACTIVATION
# ─────────────────────────────────────────────
class AccountDeactivationSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)
    reason   = serializers.CharField(required=False, allow_blank=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.is_active = False
        user.save()
        return user