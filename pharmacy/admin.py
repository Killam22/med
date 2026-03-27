from django.contrib import admin

from .models import Pharmacist, Pharmacist_Professional_info, Pharmacy

admin.site.register(Pharmacist)
admin.site.register(Pharmacist_Professional_info)
admin.site.register(Pharmacy)
# Register your models here.
