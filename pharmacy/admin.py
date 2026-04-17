from django.contrib import admin
from .models import Pharmacist, Pharmacy, PharmacyOrder


@admin.register(Pharmacist)
class PharmacistAdmin(admin.ModelAdmin):
    list_display  = ['user', 'order_registration_number', 'is_verified']
    list_filter   = ['is_verified', 'user__city']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    list_editable = ['is_verified']
    readonly_fields = ['user']

    fieldsets = (
        ('Informations pharmacien', {
            'fields': ('user', 'order_registration_number', 'is_verified')
        }),
        ('Coordonnées', {
            'fields': ('address', 'city', 'phone')
        }),
    )


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'pharmacist', 'pharm_city', 'is_open_24h']
    list_filter   = ['is_open_24h', 'pharm_city']
    search_fields = ['name', 'pharmacist__pharmacy_name']


@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):
    list_display  = ['id', 'patient', 'prescription', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['patient__email', 'patient__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
