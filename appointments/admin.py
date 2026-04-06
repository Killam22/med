from django.contrib import admin
from .models import Appointment, Review


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'status', 'created_at']
    list_filter = ['status', 'date', 'created_at']
    search_fields = [
        'patient__user__first_name', 'patient__user__last_name',
        'doctor__user__first_name', 'doctor__user__last_name',
        'motif',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['patient', 'doctor']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'patient', 'doctor', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    raw_id_fields = ['appointment', 'patient', 'doctor']
