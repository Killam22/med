from rest_framework import serializers
from .models import Doctor, WeeklySchedule, DayOff
from appointments.services import get_available_slots


# ── Schedule Serializers ────────────────────────────────────────────────────

class WeeklyScheduleSerializer(serializers.ModelSerializer):
    """
    GET  /api/doctor/my-schedule/         → liste des jours de travail
    POST /api/doctor/my-schedule/         → ajouter/remplacer un jour
    PUT  /api/doctor/my-schedule/{id}/    → modifier les heures d'un jour
    DELETE /api/doctor/my-schedule/{id}/  → supprimer un jour
    """
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model  = WeeklySchedule
        fields = ['id', 'day_of_week', 'day_label', 'start_time', 'end_time', 'slot_duration', 'is_active']
        read_only_fields = ['id', 'day_label']

    def validate(self, data):
        if data.get('end_time') and data.get('start_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError("L'heure de fin doit être après l'heure de début.")
        return data


class DayOffSerializer(serializers.ModelSerializer):
    """
    GET    /api/doctor/days-off/        → liste des congés
    POST   /api/doctor/days-off/        → ajouter un congé
    DELETE /api/doctor/days-off/{id}/   → supprimer un congé
    """
    class Meta:
        model  = DayOff
        fields = ['id', 'date', 'reason']
        read_only_fields = ['id']

    def validate_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError("Impossible d'ajouter un congé dans le passé.")
        return value


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
        from datetime import date
        from django.utils import timezone
        request_date = self.context.get('filter_date')
        if request_date:
            try:
                target = date.fromisoformat(request_date)
            except (ValueError, TypeError):
                return []
        else:
            target = timezone.now().date()
        return get_available_slots(obj, target)


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
        return get_available_slots(obj, timezone.now().date())

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
