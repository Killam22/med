from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'username', 'role', 'is_staff', 'is_active', 'verification_status']
    list_filter = ['role', 'is_staff', 'is_active', 'verification_status']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations Supplémentaires', {'fields': (
            'role', 'sex', 'date_of_birth', 'phone', 'blood_type', 
            'emergency_contact', 'access_level'
        )}),
        ('Vérification & Adresse', {'fields': (
            'id_card_number', 'id_card_photo', 'verification_status',
            'address', 'postal_code', 'city', 'wilaya'
        )}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations Supplémentaires', {'fields': (
            'role', 'email', 'first_name', 'last_name'
        )}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
