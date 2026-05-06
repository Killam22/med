from django.urls import path
from .views import (
    PatientProfileView,
    MedicalProfileView,
    AllergyListView,
    AntecedentListView,
    TreatmentListView,
    MedicalDocumentListView,
    DoctorPatientsListView,
    PatientDashboardView,
    SymptomAnalysisListView,
    PatientSearchView,
    DoctorSendLinkRequestView,
    PatientLinkRequestListView,
    PatientRespondLinkRequestView,
    ExternalPatientView,
    ExternalPatientDetailView,
)
urlpatterns = [
    path('profile/',          PatientProfileView.as_view(),         name='patient_profile'),
    path('medical-profile/',  MedicalProfileView.as_view(),         name='medical_profile'),
    path('allergies/',        AllergyListView.as_view(),            name='patient_allergies'),
    path('antecedents/',      AntecedentListView.as_view(),         name='patient_antecedents'),
    path('treatments/',       TreatmentListView.as_view(),          name='patient_treatments'),
    path('medical-documents/', MedicalDocumentListView.as_view(),   name='patient_medical_documents'),
    path('my-patients/',      DoctorPatientsListView.as_view(),     name='doctor_my_patients'),
    path('dashboard/',        PatientDashboardView.as_view(),       name='patient-dashboard'),
    path('symptom-analysis/', SymptomAnalysisListView.as_view(),    name='symptom-analysis'),
    # Recherche + demandes de liaison
    path('search/',                              PatientSearchView.as_view(),             name='patient-search'),
    path('link-requests/',                       DoctorSendLinkRequestView.as_view(),     name='doctor-send-link-request'),
    path('my-link-requests/',                    PatientLinkRequestListView.as_view(),    name='patient-link-requests'),
    path('link-requests/<int:pk>/respond/',      PatientRespondLinkRequestView.as_view(), name='patient-respond-link-request'),
    # Patients sans compte
    path('external/',         ExternalPatientView.as_view(),        name='external-patients'),
    path('external/<int:pk>/', ExternalPatientDetailView.as_view(), name='external-patient-detail'),
]
