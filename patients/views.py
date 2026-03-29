from rest_framework import generics, permissions
from .models import Patient, MedicalProfile, Antecedent, Treatment, LabResult, SymptomAnalysis
from .serializers import (
    PatientSerializer,
    MedicalProfileSerializer,
    AntecedentSerializer,
    TreatmentSerializer,
    LabResultSerializer,
    SymptomAnalysisSerializer
)
from appointments.permissions import IsPatient

class PatientProfileView(generics.RetrieveUpdateAPIView):
    """GET / PUT /api/patients/profile/ — own patient profile."""
    serializer_class = PatientSerializer
    permission_classes = [IsPatient]

    def get_object(self):
        return self.request.user.patient_profile

class MedicalProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MedicalProfileSerializer
    permission_classes = [IsPatient]

    def get_object(self):
        return MedicalProfile.objects.get_or_create(patient=self.request.user.patient_profile)[0]

class AntecedentListView(generics.ListCreateAPIView):
    serializer_class = AntecedentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Antecedent.objects.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

class TreatmentListView(generics.ListCreateAPIView):
    serializer_class = TreatmentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Treatment.objects.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

class LabResultListView(generics.ListCreateAPIView):
    serializer_class = LabResultSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return LabResult.objects.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)

class SymptomAnalysisListView(generics.ListCreateAPIView):
    serializer_class = SymptomAnalysisSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return SymptomAnalysis.objects.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)
