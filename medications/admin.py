
from django.contrib import admin
from .models import Medication

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'molecule', 'category', 'price_dzd', 'cnas_covered', 'is_active')
    search_fields = ('name', 'molecule', 'barcode')
    list_filter = ('category', 'cnas_covered', 'is_shifa_compatible', 'requires_prescription')