from django.contrib import admin
from .models import Patient, MedicalProfile, Antecedent, Treatment, MedicalDocument

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_phone', 'get_city', 'blood_group']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    raw_id_fields = ['user']

    @admin.display(description='Téléphone')
    def get_phone(self, obj):
        return obj.user.phone

    @admin.display(description='Ville')
    def get_city(self, obj):
        return obj.user.city

@admin.register(MedicalProfile)
class MedicalProfileAdmin(admin.ModelAdmin):
    list_display = ['patient', 'weight', 'height']
    raw_id_fields = ['patient']

admin.site.register(Antecedent)
admin.site.register(Treatment)
admin.site.register(MedicalDocument)