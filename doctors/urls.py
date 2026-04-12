from django.urls import path
from . import views


app_name = 'doctors'

urlpatterns = [
    path('complete_doctor_profile/', views.complete_doctor_profile, name='complete_doctor_profile'),
    
   
]