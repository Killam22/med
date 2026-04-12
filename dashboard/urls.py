from django.urls import path
from . import views

urlpatterns = [
    path('patient/', views.PatientDashboardView.as_view(), name='patient-dashboard'),
    path('doctor/', views.DoctorDashboardView.as_view(), name='doctor-dashboard'),
    path('pharmacist/', views.PharmacistDashboardView.as_view(), name='pharmacist-dashboard'),
    path('caretaker/', views.CaretakerDashboardView.as_view(), name='caretaker-dashboard'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
]
