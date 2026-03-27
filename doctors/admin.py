from django.contrib import admin
from .models import Doctor, Doctor_professionel_info , Exercice

admin.site.register(Doctor)     
admin.site.register(Doctor_professionel_info)                                   
admin.site.register(Exercice)

# Register your models here.
