from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.utils import timezone
from .models import Patient, MedicalProfile, Allergy, Antecedent, Treatment, MedicalDocument, SymptomAnalysis, PatientLinkRequest, ExternalPatient
from appointments.permissions import IsPatient, IsDoctor
from .serializers import (
    PatientSerializer,
    PatientSearchSerializer,
    PatientLinkRequestSerializer,
    ExternalPatientSerializer,
    MedicalProfileSerializer,
    AllergySerializer,
    AntecedentSerializer,
    TreatmentSerializer,
    MedicalDocumentSerializer,
    SymptomAnalysisSerializer,
)

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
    """GET /api/patients/my-patients/ — Patients liés au médecin (lien accepté ou RDV)."""
    serializer_class = PatientSerializer
    permission_classes = [IsDoctor]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        doctor = getattr(user, 'doctor_profile', None)
        if doctor is None:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Accès réservé aux médecins.")

        # Patients dont le médecin a révoqué la liaison — on les exclut partout
        revoked_ids = PatientLinkRequest.objects.filter(
            doctor=doctor, status='revoked'
        ).values_list('patient_id', flat=True)

        # Patients ayant accepté la demande de liaison
        linked_ids = PatientLinkRequest.objects.filter(
            doctor=doctor, status='accepted'
        ).values_list('patient_id', flat=True)

        # Patients ayant eu un rendez-vous avec ce médecin (hors révoqués)
        appt_ids = Patient.objects.filter(
            appointments__doctor=doctor
        ).exclude(id__in=revoked_ids).values_list('id', flat=True)

        from django.db.models import Q
        return Patient.objects.filter(
            Q(id__in=linked_ids) | Q(id__in=appt_ids)
        ).distinct()


class PatientDashboardView(APIView):
    permission_classes = [IsPatient]
    renderer_classes = [JSONRenderer]

    def get(self, request):

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


# ── Patient search (doctor side) ──────────────────────────────────────────────

class PatientSearchView(generics.ListAPIView):
    """GET /api/patients/search/?q=... — médecin recherche un patient par nom/email."""
    serializer_class = PatientSearchSerializer
    permission_classes = [IsDoctor]
    pagination_class = None

    def get_queryset(self):
        from django.db.models import Q
        q = self.request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Patient.objects.none()
        return Patient.objects.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q)
        ).select_related('user')[:15]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx


# ── Doctor → Patient link requests ───────────────────────────────────────────

class DoctorSendLinkRequestView(APIView):
    """POST /api/patients/link-requests/ — médecin envoie une demande d'accès à un patient."""
    permission_classes = [IsDoctor]

    def post(self, request):
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({"detail": "patient_id requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({"detail": "Patient introuvable."}, status=status.HTTP_404_NOT_FOUND)

        doctor = request.user.doctor_profile
        link_req, created = PatientLinkRequest.objects.get_or_create(
            doctor=doctor, patient=patient, defaults={'status': 'pending'}
        )
        if not created:
            if link_req.status == 'pending':
                return Response({"detail": "Demande déjà envoyée."}, status=status.HTTP_400_BAD_REQUEST)
            if link_req.status == 'accepted':
                return Response({"detail": "Ce patient est déjà lié à votre compte."}, status=status.HTTP_400_BAD_REQUEST)
            # statut 'refused' → on réinitialise
            link_req.status = 'pending'
            link_req.save()

        from notifications.models import Notification
        Notification.objects.create(
            user=patient.user,
            title="Demande d'accès médecin",
            message=f"Dr. {request.user.get_full_name()} souhaite accéder à votre profil médical.",
            notification_type=Notification.NotificationType.APPOINTMENT
        )
        return Response({"detail": "Demande envoyée.", "id": link_req.id}, status=status.HTTP_201_CREATED)


class PatientLinkRequestListView(generics.ListAPIView):
    """GET /api/patients/my-link-requests/ — patient consulte les demandes en attente."""
    serializer_class = PatientLinkRequestSerializer
    permission_classes = [IsPatient]
    pagination_class = None

    def get_queryset(self):
        return PatientLinkRequest.objects.filter(
            patient=self.request.user.patient_profile,
            status='pending'
        ).select_related('doctor__user')


class PatientRespondLinkRequestView(APIView):
    """POST /api/patients/link-requests/{id}/respond/ — patient accepte ou refuse."""
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            link_req = PatientLinkRequest.objects.get(pk=pk, patient=request.user.patient_profile)
        except PatientLinkRequest.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action not in ('accept', 'refuse'):
            return Response({"detail": "action doit être 'accept' ou 'refuse'."}, status=status.HTTP_400_BAD_REQUEST)

        link_req.status = 'accepted' if action == 'accept' else 'refused'
        link_req.save()

        if action == 'accept':
            from notifications.models import Notification
            Notification.objects.create(
                user=link_req.doctor.user,
                title="Demande acceptée",
                message=f"{request.user.get_full_name()} a accepté votre demande d'accès au profil.",
                notification_type=Notification.NotificationType.APPOINTMENT
            )
        return Response({"detail": "Réponse enregistrée."}, status=status.HTTP_200_OK)


# ── External patients (sans compte) ──────────────────────────────────────────

class DoctorUnlinkPatientView(APIView):
    """
    POST /api/patients/{patient_id}/unlink/
    Médecin : résilie la liaison avec un patient (revoke).
    Si aucun PatientLinkRequest n'existe (liaison via RDV), on en crée un avec status=revoked
    pour bloquer le patient des listes futures.
    """
    permission_classes = [IsDoctor]

    def post(self, request, patient_id):
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        doctor = request.user.doctor_profile
        link_req, _ = PatientLinkRequest.objects.get_or_create(
            doctor=doctor,
            patient=patient,
            defaults={'status': 'revoked'}
        )
        if link_req.status != 'revoked':
            link_req.status = 'revoked'
            link_req.save()

        return Response({'detail': 'Liaison résiliée.'}, status=status.HTTP_200_OK)


class ExternalPatientView(generics.ListCreateAPIView):
    """GET/POST /api/patients/external/ — médecin gère ses patients sans compte."""
    serializer_class = ExternalPatientSerializer
    permission_classes = [IsDoctor]
    pagination_class = None

    def get_queryset(self):
        return ExternalPatient.objects.filter(doctor=self.request.user.doctor_profile)

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)


class ExternalPatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/DELETE /api/patients/external/{id}/"""
    serializer_class = ExternalPatientSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return ExternalPatient.objects.filter(doctor=self.request.user.doctor_profile)


class ExternalPatientPrescriptionsView(APIView):
    """
    GET /api/patients/external/{id}/prescriptions/
    Médecin : liste les ordonnances d'un patient sans compte.
    """
    permission_classes = [IsDoctor]

    def get(self, request, pk):
        try:
            external_patient = ExternalPatient.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except ExternalPatient.DoesNotExist:
            return Response({'error': 'Patient externe introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        from prescriptions.models import Prescription
        from prescriptions.serializers import PrescriptionSerializer
        prescriptions = Prescription.objects.filter(
            consultation__external_patient=external_patient
        ).select_related('consultation__doctor').prefetch_related('items', 'qr_token')
        return Response(PrescriptionSerializer(prescriptions, many=True).data)


class ExternalPatientConsultationsView(APIView):
    """
    GET  /api/patients/external/{id}/consultations/
    POST /api/patients/external/{id}/consultations/
    Médecin : liste et crée des comptes rendus pour un patient sans compte.
    """
    permission_classes = [IsDoctor]

    def get(self, request, pk):
        try:
            external_patient = ExternalPatient.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except ExternalPatient.DoesNotExist:
            return Response({'error': 'Patient externe introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        from consultations.models import Consultation
        consultations = Consultation.objects.filter(
            external_patient=external_patient
        ).select_related('doctor').order_by('-consulted_at')

        data = [
            {
                'id':              str(c.id),
                'date':            c.consulted_at.date().isoformat(),
                'chief_complaint': c.chief_complaint,
                'diagnosis':       c.diagnosis,
                'treatment_plan':  c.treatment_plan,
                'doctor_notes':    c.doctor_notes,
                'status':          c.status,
            }
            for c in consultations
        ]
        return Response(data)

    def post(self, request, pk):
        try:
            external_patient = ExternalPatient.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except ExternalPatient.DoesNotExist:
            return Response({'error': 'Patient externe introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        from consultations.models import Consultation
        from django.utils import timezone

        doctor = request.user.doctor_profile
        consultation = Consultation.objects.create(
            doctor=doctor,
            external_patient=external_patient,
            consultation_type=Consultation.ConsultationType.IN_PERSON,
            status=Consultation.Status.COMPLETED,
            chief_complaint=request.data.get('chief_complaint', ''),
            history=request.data.get('history', ''),
            examination=request.data.get('examination', ''),
            diagnosis=request.data.get('diagnosis', ''),
            treatment_plan=request.data.get('treatment_plan', ''),
            doctor_notes=request.data.get('doctor_notes', ''),
            consulted_at=timezone.now(),
        )
        return Response({
            'id':              str(consultation.id),
            'date':            consultation.consulted_at.date().isoformat(),
            'chief_complaint': consultation.chief_complaint,
            'diagnosis':       consultation.diagnosis,
            'treatment_plan':  consultation.treatment_plan,
            'doctor_notes':    consultation.doctor_notes,
            'status':          consultation.status,
        }, status=status.HTTP_201_CREATED)
