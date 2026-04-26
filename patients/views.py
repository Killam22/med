from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.utils import timezone
from .models import Patient, MedicalProfile, Allergy, Antecedent, Treatment, MedicalDocument, SymptomAnalysis
from .serializers import (
    PatientSerializer,
    MedicalProfileSerializer,
    AllergySerializer,
    AntecedentSerializer,
    TreatmentSerializer,
    MedicalDocumentSerializer,
    SymptomAnalysisSerializer,
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

class AllergyListView(generics.ListCreateAPIView):
    serializer_class = AllergySerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Allergy.objects.filter(profile__patient=self.request.user.patient_profile)

    def perform_create(self, serializer):
        profile, _ = MedicalProfile.objects.get_or_create(patient=self.request.user.patient_profile)
        serializer.save(profile=profile)

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
        serializer.save(
            patient=self.request.user.patient_profile,
            uploaded_by=self.request.user
        )


class SymptomAnalysisListView(generics.ListCreateAPIView):
    """GET / POST /api/patients/symptom-analysis/ — historique IA du patient."""
    serializer_class = SymptomAnalysisSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return SymptomAnalysis.objects.filter(patient=self.request.user.patient_profile)

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


class PatientDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'patient':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        today = timezone.now().date()

        from appointments.models import Appointment
        from consultations.models import Consultation
        from pharmacy.models import PharmacyOrder
        from caretaker.models import CareRequest
        from notifications.models import Notification

        upcoming_appts = Appointment.objects.filter(
            patient__user=user, date__gte=today, status__in=['scheduled', 'pending', 'confirmed']
        ).order_by('date', 'start_time')[:3]

        notifications = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]
        recent_docs = Consultation.objects.filter(patient__user=user).order_by('-created_at')[:3]
        active_orders = PharmacyOrder.objects.filter(patient=user).exclude(status__in=['completed', 'cancelled'])
        active_care = CareRequest.objects.filter(patient=user, status='accepted').first()

        data = {
            "upcoming_appointments": [
                {
                    "id": str(a.id),
                    "date": a.date.isoformat(),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "end_time": a.end_time.strftime('%H:%M'),
                    "doctor": a.doctor.user.get_full_name(),
                    "specialty": a.doctor.specialty,
                    "status": a.status,
                }
                for a in upcoming_appts
            ],
            "notifications": [
                {"id": n.id, "title": n.title, "message": n.message, "type": n.notification_type}
                for n in notifications
            ],
            "recent_documents": [
                {
                    "date": d.created_at.date(),
                    "doctor": f"Dr. {d.doctor.user.last_name}",
                }
                for d in recent_docs
            ],
            "prescription_status": [
                {"id": str(o.id), "status": o.status}
                for o in active_orders
            ],
            "caregiver": active_care.caretaker.user.get_full_name() if active_care else None,
        }
        return Response(data)
