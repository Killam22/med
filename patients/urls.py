from django.urls import path
from .views import (
    PatientProfileView,
    MedicalProfileView,
    AntecedentListView,
    TreatmentListView,
    MedicalDocumentListView,
    DoctorPatientsListView
)
urlpatterns = [
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
    path('medical-profile/', MedicalProfileView.as_view(), name='medical_profile'),
    path('antecedents/', AntecedentListView.as_view(), name='patient_antecedents'),
    path('treatments/', TreatmentListView.as_view(), name='patient_treatments'),
    path('medical-documents/', MedicalDocumentListView.as_view(), name='patient_medical_documents'),
    path('my-patients/', DoctorPatientsListView.as_view(), name='doctor_my_patients'),
]
