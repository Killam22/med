# settings/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSettings, AccountDeletionRequest

User = get_user_model()


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserSettings
        exclude = ['user', 'updated_at']


class ChangePasswordSerializer(serializers.Serializer):
    old_password  = serializers.CharField(write_only=True)
    new_password  = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError('New passwords do not match.')
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    """
    Lets the user update their own basic info (name, phone, address…).
    Excludes sensitive fields like role, verification_status, password.
    """
    class Meta:
        model  = User
        fields = [
            'first_name', 'last_name', 'phone',
            'address', 'postal_code', 'city', 'wilaya',
            'date_of_birth', 'sex', 'photo',
            'emergency_contact',
        ]


class AccountDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AccountDeletionRequest
        fields = ['id', 'reason', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']