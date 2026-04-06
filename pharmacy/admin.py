from django.contrib import admin
from .models import Pharmacist, PharmacyBranch, PharmacyOrder


@admin.register(Pharmacist)
class PharmacistAdmin(admin.ModelAdmin):
    list_display  = ['pharmacy_name', 'user', 'city', 'license_number', 'is_verified']
    list_filter   = ['is_verified', 'city']
    search_fields = ['pharmacy_name', 'user__email', 'user__first_name', 'user__last_name', 'license_number']
    list_editable = ['is_verified']
    readonly_fields = ['user']

    fieldsets = (
        ('Informations pharmacien', {
            'fields': ('user', 'pharmacy_name', 'license_number', 'is_verified')
        }),
        ('Coordonnées', {
            'fields': ('address', 'city', 'phone')
        }),
    )


@admin.register(PharmacyBranch)
class PharmacyBranchAdmin(admin.ModelAdmin):
    list_display  = ['branch_name', 'pharmacist', 'city', 'is_open_24h']
    list_filter   = ['is_open_24h', 'city']
    search_fields = ['branch_name', 'pharmacist__pharmacy_name']


@admin.register(PharmacyOrder)
class PharmacyOrderAdmin(admin.ModelAdmin):
    list_display  = ['id', 'patient', 'prescription', 'status', 'created_at']
    list_filter   = ['status']
    search_fields = ['patient__email', 'patient__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
