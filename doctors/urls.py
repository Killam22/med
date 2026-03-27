from django.urls import path
from . import views


app_name = 'doctors'

urlpatterns = [
    path('complete-profile/', views.complete_doctor_profile, name='complete_doctor_profile'),
    path('dashboard/',       views.dashboard,       name='dashboard'),
   
]