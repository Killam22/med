from rest_framework import generics, permissions
from .models import Patient, MedicalProfile, Antecedent, Treatment, MedicalDocument
from .serializers import (
    PatientSerializer,
    MedicalProfileSerializer,
    AntecedentSerializer,
    TreatmentSerializer,
    MedicalDocumentSerializer
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

class MedicalDocumentListView(generics.ListCreateAPIView):
    serializer_class = MedicalDocumentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return MedicalDocument.objects.filter(patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user.patient_profile)


class DoctorPatientsListView(generics.ListAPIView):
    """GET /api/patients/my-patients/ — Liste des patients ayant un RDV avec le médecin."""
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        from rest_framework.exceptions import PermissionDenied
        if getattr(user, 'role', None) != 'doctor':
            raise PermissionDenied("Accès réservé aux médecins.")
        
        # Récupère tous les patients liés aux rendez-vous de ce médecin (sans doublons)
        return Patient.objects.filter(appointments__doctor__user=user).distinct()
