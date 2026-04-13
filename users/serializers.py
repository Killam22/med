from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model  = CustomUser
        fields = ['email', 'first_name', 'last_name', 'role', 'password', 'confirm_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = CustomUser(username=validated_data['email'], **validated_data)
        user.set_password(password)
        user.is_active = False  # activated after OTP
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomUser
        fields = [
            'user_id', 'email', 'first_name', 'last_name', 'role',
            'sex', 'date_of_birth', 'phone', 'address',
            'postal_code', 'city', 'wilaya',
            'verification_status', 'is_active', 'created_at',
        ]
        read_only_fields = ['user_id', 'created_at', 'verification_status', 'is_active']
        
        
def validate_email(self, value):
    if CustomUser.objects.filter(email=value).exists():
        raise serializers.ValidationError("A user with this email already exists.")
    return value