from django.contrib import admin
from .models import AvailabilitySlot, Appointment, Notification, Review

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'date', 'start_time', 'end_time', 'is_booked']
    list_filter = ['is_booked', 'date']
    search_fields = ['doctor__user__first_name', 'doctor__user__last_name']
    date_hierarchy = 'date'
    raw_id_fields = ['doctor']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'get_date', 'get_time', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = [
        'patient__user__first_name', 'patient__user__last_name',
        'doctor__user__first_name', 'doctor__user__last_name',
        'motif',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['patient', 'doctor', 'slot']

    @admin.display(description='Date')
    def get_date(self, obj):
        return obj.slot.date if obj.slot else '—'

    @admin.display(description='Heure')
    def get_time(self, obj):
        return f"{obj.slot.start_time} – {obj.slot.end_time}" if obj.slot else '—'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'message']
    raw_id_fields = ['user', 'related_appointment']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'patient', 'doctor', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    raw_id_fields = ['appointment', 'patient', 'doctor']
