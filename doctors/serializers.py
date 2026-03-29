from rest_framework import serializers
from .models import Doctor
from appointments.models import AvailabilitySlot
from appointments.serializers import AvailabilitySlotSerializer

class DoctorListSerializer(serializers.ModelSerializer):
    """Compact doctor info for search results."""
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    gender_display = serializers.CharField(source='user.get_sex_display', read_only=True)
    gender = serializers.CharField(source='user.sex', read_only=True)
    city = serializers.CharField(source='user.city', read_only=True)
    available_slots_for_date = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialty', 'specialty_display',
            'gender', 'gender_display',
            'clinic_name', 'city', 'rating', 'total_reviews',
            'experience_years', 'consultation_fee', 'photo',
            'available_slots_for_date',
        ]

    def get_available_slots_for_date(self, obj):
        from django.utils import timezone
        request_date = self.context.get('filter_date')
        if request_date:
            slots = obj.slots.filter(date=request_date, is_booked=False).order_by('start_time')
        else:
            slots = obj.slots.filter(
                is_booked=False,
                date__gte=timezone.now().date()
            ).order_by('date', 'start_time')[:4]
        return AvailabilitySlotSerializer(slots, many=True).data


class DoctorDetailSerializer(serializers.ModelSerializer):
    """Full doctor profile."""
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    available_slots = serializers.SerializerMethodField()
    
    gender = serializers.CharField(source='user.sex', required=False, allow_blank=True)
    address = serializers.CharField(source='user.address', required=False, allow_blank=True)
    city = serializers.CharField(source='user.city', required=False, allow_blank=True)
    phone = serializers.CharField(source='user.phone', required=False, allow_blank=True)

    class Meta:
        model = Doctor
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'specialty', 'specialty_display', 'license_number',
            'gender',
            'clinic_name', 'address', 'city', 'phone', 'bio',
            'experience_years', 'consultation_fee', 'photo',
            'rating', 'total_reviews', 'languages',
            'is_verified', 'available_slots',
        ]

    def get_available_slots(self, obj):
        from django.utils import timezone
        slots = obj.slots.filter(
            is_booked=False,
            date__gte=timezone.now().date()
        ).order_by('date', 'start_time')
        return AvailabilitySlotSerializer(slots, many=True).data

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
