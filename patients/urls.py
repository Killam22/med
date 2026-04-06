from django.urls import path
from .views import (
    PatientProfileView,
    MedicalProfileView,
    AntecedentListView,
    TreatmentListView,
    LabResultListView,
    SymptomAnalysisListView,
    DoctorPatientsListView
)
urlpatterns = [
    path('profile/', PatientProfileView.as_view(), name='patient_profile'),
    path('medical-profile/', MedicalProfileView.as_view(), name='medical_profile'),
    path('antecedents/', AntecedentListView.as_view(), name='patient_antecedents'),
    path('treatments/', TreatmentListView.as_view(), name='patient_treatments'),
    path('lab-results/', LabResultListView.as_view(), name='patient_lab_results'),
    path('symptom-analysis/', SymptomAnalysisListView.as_view(), name='patient_symptom_analysis'),
    path('my-patients/', DoctorPatientsListView.as_view(), name='doctor_my_patients'),
]
