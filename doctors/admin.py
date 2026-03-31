from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialty', 'clinic_name', 'rating', 'is_verified', 'experience_years']
    list_filter = ['specialty', 'is_verified']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'clinic_name']
    raw_id_fields = ['user']
    readonly_fields = ['rating', 'total_reviews']
