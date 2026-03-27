# patients/urls.py
from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('complete-profile/', views.complete_patient_profile, name='complete_patient_profile'),
    path('dashboard/',       views.dashboard,       name='dashboard'),
    path('profile/',         views.profile,         name='profile'),
    path('profile/edit/',    views.edit_profile,    name='edit_profile'),
    path('medical-profile/', views.medical_profile, name='medical_profile'),
    path('medical-profile/edit/',   views.edit_medical_profile,     name='edit_medical_profile'),
    path('antecedents/add/',        views.add_antecedent,           name='add_antecedent'),
    path('treatments/add/',         views.add_treatment,            name='add_treatment'),
]
