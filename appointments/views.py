"""Views for the appointment management logic."""

from datetime import date, timedelta

from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from patients.models import Patient
from doctors.models import Doctor
from .models import Appointment, Review
from .serializers import (
    AppointmentSerializer,
    AppointmentDoctorSerializer,
    BookAppointmentSerializer,
    ReviewSerializer,
)
from .services import book_appointment, get_available_slots, get_available_slots_range
from .permissions import IsPatient, IsDoctor


# ── Availability (public) ─────────────────────────────────────────────────────

class DoctorAvailabilityView(APIView):
    """
    GET /api/doctors/{doctor_id}/availability/?date=2025-06-16
    GET /api/doctors/{doctor_id}/availability/?from=2025-06-16&to=2025-06-23
    No auth required — public endpoint for patients browsing.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        try:
            doctor = Doctor.objects.get(pk=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"detail": "Médecin introuvable."}, status=status.HTTP_404_NOT_FOUND)

        single_date = request.query_params.get('date')
        from_date   = request.query_params.get('from')
        to_date     = request.query_params.get('to')

        try:
            if single_date:
                target = date.fromisoformat(single_date)
                slots  = get_available_slots(doctor, target)
                return Response({
                    'doctor_id': doctor_id,
                    'date':      single_date,
                    'slots':     slots,
                })

            elif from_date and to_date:
                f = date.fromisoformat(from_date)
                t = date.fromisoformat(to_date)
                if (t - f).days > 60:
                    return Response(
                        {"detail": "La plage maximale est de 60 jours."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return Response(get_available_slots_range(doctor, f, t))

            else:
                # Default: next 7 days
                today = timezone.now().date()
                return Response(get_available_slots_range(doctor, today, today + timedelta(days=6)))

        except ValueError:
            return Response(
                {"detail": "Format de date invalide. Utilisez YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ── Patient Appointment Views ──────────────────────────────────────────────────

class PatientAppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/appointments/ — patient's appointment list
    POST /api/appointments/ — book a new appointment
    """
    permission_classes = [IsPatient]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookAppointmentSerializer
        return AppointmentSerializer

    def get_queryset(self):
        patient = self.request.user.patient_profile
        qs = Appointment.objects.filter(patient=patient).select_related('doctor__user')
        if status_filter := self.request.query_params.get('status'):
            qs = qs.filter(status=status_filter)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            appointment = book_appointment(
                patient    = request.user.patient_profile,
                doctor     = d['doctor'],
                date       = d['date'],
                start_time = d['start_time'],
                end_time   = d['end_time'],
                motif      = d['motif'],
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        from notifications.models import Notification
        Notification.objects.create(
            user=appointment.doctor.user,
            title="Nouvelle réservation",
            message=f"Nouvelle réservation : {appointment.patient.user.get_full_name()} le {appointment.date}",
            notification_type=Notification.NotificationType.APPOINTMENT
        )

        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class PatientAppointmentDetailView(generics.RetrieveAPIView):
    """GET /api/appointments/{id}/ — appointment detail (patient)."""
    serializer_class = AppointmentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user.patient_profile)


class CancelAppointmentView(APIView):
    """POST /api/appointments/{id}/cancel/"""
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user.patient_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not appointment.is_active:
            return Response(
                {"detail": f"Impossible d'annuler un rendez-vous '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.cancel()
        from notifications.models import Notification
        Notification.objects.create(
            user=appointment.doctor.user,
            title="Annulation",
            message=f"Le patient {appointment.patient.user.get_full_name()} a annulé son rendez-vous.",
            notification_type=Notification.NotificationType.APPOINTMENT
        )
        return Response({"detail": "Rendez-vous annulé."}, status=status.HTTP_200_OK)


class RescheduleAppointmentView(APIView):
    """POST /api/appointments/{id}/reschedule/"""
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user.patient_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not appointment.is_active:
            return Response({"detail": "Impossible de modifier ce rendez-vous."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            from django.db import transaction
            with transaction.atomic():
                appointment.cancel()
                new_appointment = book_appointment(
                    patient    = request.user.patient_profile,
                    doctor     = appointment.doctor,  # same doctor
                    date       = d['date'],
                    start_time = d['start_time'],
                    end_time   = d['end_time'],
                    motif      = appointment.motif,
                )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AppointmentSerializer(new_appointment).data, status=status.HTTP_200_OK)


# ── Doctor Appointment Management ─────────────────────────────────────────────

class DoctorAppointmentListView(generics.ListAPIView):
    """GET /api/doctor/appointments/ — doctor sees all their appointments."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        qs = Appointment.objects.filter(doctor=doctor).select_related('patient__user')
        if s := self.request.query_params.get('status'):
            qs = qs.filter(status=s)
        if d := self.request.query_params.get('date'):
            qs = qs.filter(date=d)
        return qs.order_by('date', 'start_time')


class DoctorDailyScheduleView(generics.ListAPIView):
    """GET /api/doctor/schedule/ — doctor's appointments for a given day (default: today)."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        target = self.request.query_params.get('date', timezone.now().date())
        return Appointment.objects.filter(
            doctor=doctor,
            date=target,
            status__in=['confirmed', 'pending', 'completed'],
        ).select_related('patient__user').order_by('start_time')


class DoctorPendingAppointmentsView(generics.ListAPIView):
    """GET /api/doctor/appointments/pending/ — doctor's pending appointment requests."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        return Appointment.objects.filter(
            doctor=doctor,
            status='pending',
        ).select_related('patient__user').order_by('date', 'start_time')


class DoctorAppointmentDetailView(generics.RetrieveAPIView):
    """GET /api/doctor/appointments/{id}/ — single appointment detail."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(doctor=self.request.user.doctor_profile)


class ConfirmAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/confirm/"""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appt = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appt.status != 'pending':
            return Response({"detail": "Seuls les rendez-vous en attente peuvent être confirmés."},
                            status=status.HTTP_400_BAD_REQUEST)
        appt.confirm()
        from notifications.models import Notification
        Notification.objects.create(
            user=appt.patient.user,
            title="Rendez-vous confirmé",
            message=f"Votre RDV avec Dr.{appt.doctor.user.last_name} est confirmé.",
            notification_type=Notification.NotificationType.APPOINTMENT
        )
        return Response({"detail": "Confirmé."}, status=status.HTTP_200_OK)


class RefuseAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/refuse/"""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appt = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appt.status not in ('pending', 'confirmed'):
            return Response({"detail": "Ce rendez-vous ne peut pas être refusé."},
                            status=status.HTTP_400_BAD_REQUEST)
        appt.refuse(reason=request.data.get('reason', ''))
        from notifications.models import Notification
        Notification.objects.create(
            user=appt.patient.user,
            title="Rendez-vous annulé",
            message=f"Le Dr. {appt.doctor.user.last_name} a dû annuler votre rendez-vous. Veuillez choisir un autre créneau.",
            notification_type=Notification.NotificationType.APPOINTMENT
        )
        return Response({"detail": "Refusé."}, status=status.HTTP_200_OK)


class CompleteAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/complete/"""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appt = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appt.status != 'confirmed':
            return Response({"detail": "Seuls les rendez-vous confirmés peuvent être terminés."},
                            status=status.HTTP_400_BAD_REQUEST)
        appt.complete(notes=request.data.get('notes', ''))
        from notifications.models import Notification
        Notification.objects.create(
            user=appt.patient.user,
            title="Consultation terminée",
            message="Consultation terminée. Ordonnance disponible.",
            notification_type=Notification.NotificationType.APPOINTMENT
        )
        return Response({"detail": "Terminé."}, status=status.HTTP_200_OK)



# ── Review Views ──────────────────────────────────────────────────────────────

class CreateReviewView(generics.CreateAPIView):
    """POST /api/appointments/{id}/review/ — patient evaluates a completed appointment."""
    serializer_class = ReviewSerializer
    permission_classes = [IsPatient]

    def perform_create(self, serializer):
        appointment_id = self.kwargs['pk']
        try:
            appointment = Appointment.objects.get(pk=appointment_id, patient=self.request.user.patient_profile)
        except Appointment.DoesNotExist:
            raise ValidationError({"detail": "Rendez-vous introuvable."})

        serializer.save(
            appointment=appointment,
            patient=appointment.patient,
            doctor=appointment.doctor,
        )


class DoctorReviewListView(generics.ListAPIView):
    """GET /api/doctors/{id}/reviews/ — public read-only reviews for a doctor."""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        doctor_id = self.kwargs['pk']
        return Review.objects.filter(doctor_id=doctor_id).order_by('-created_at')


# ── Start Consultation ────────────────────────────────────────────────────────

class StartConsultationView(APIView):
    """
    PATCH /api/appointments/{id}/start/
    Démarre une consultation : passe le RDV de 'confirmed' → 'in_progress'.
    Réservé au médecin propriétaire du RDV.
    """
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        try:
            appt = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appt.status != 'confirmed':
            return Response(
                {"detail": f"Seuls les rendez-vous confirmés peuvent être démarrés (statut actuel : {appt.get_status_display()})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appt.start()
        return Response(AppointmentDoctorSerializer(appt).data, status=status.HTTP_200_OK)


# ── Patient Full Record (doctor view) ─────────────────────────────────────────

class PatientRecordView(APIView):
    """
    GET /api/doctor/patients/{patient_id}/record/
    Dossier médical complet d'un patient, accessible uniquement par un médecin
    ayant eu au moins un rendez-vous avec lui.
    """
    permission_classes = [IsDoctor]

    def get(self, request, patient_id):
        doctor = request.user.doctor_profile

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({"detail": "Patient introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not Appointment.objects.filter(doctor=doctor, patient=patient).exists():
            return Response(
                {"detail": "Accès refusé : aucun rendez-vous entre ce médecin et ce patient."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from patients.models import MedicalProfile, MedicalDocument
        from consultations.models import Consultation
        from prescriptions.models import Prescription

        # Profil de base
        from patients.serializers import PatientSerializer
        profile = PatientSerializer(patient).data

        # Profil médical
        medical_profile_obj, _ = MedicalProfile.objects.get_or_create(patient=patient)
        from patients.serializers import MedicalProfileSerializer
        medical_profile = MedicalProfileSerializer(medical_profile_obj).data

        # Historique des consultations (toutes, pas seulement avec ce médecin)
        consultations = Consultation.objects.filter(patient=patient).select_related('doctor__user').order_by('-consulted_at')[:20]
        history = [
            {
                "diagnosis_date": c.consulted_at.date().isoformat(),
                "condition":      c.diagnosis or c.chief_complaint,
                "description":    c.doctor_notes,
                "doctor_name":    c.doctor.user.get_full_name(),
                "type":           c.consultation_type,
            }
            for c in consultations
        ]

        # Documents / résultats d'analyses
        docs = MedicalDocument.objects.filter(patient=patient).order_by('-uploaded_at')[:20]
        lab_results = [
            {
                "test_name": d.name,
                "lab_name":  d.document_type,
                "result":    "—",
                "status":    "Disponible",
            }
            for d in docs
        ]

        # Ordonnances via consultations du patient
        prescriptions_qs = Prescription.objects.filter(
            consultation__patient=patient
        ).prefetch_related('items').select_related('consultation__doctor__user').order_by('-created_at')[:20]

        prescriptions = []
        for rx in prescriptions_qs:
            for item in rx.items.all():
                prescriptions.append({
                    "medication":        item.drug_name,
                    "frequency":         item.frequency,
                    "duration":          item.duration,
                    "prescription_date": rx.created_at.date().isoformat(),
                })

        return Response({
            "profile":         profile,
            "medical_profile": medical_profile,
            "history":         history,
            "lab_results":     lab_results,
            "prescriptions":   prescriptions,
        })


# ── Doctor writes to patient record ──────────────────────────────────────────

class DoctorAddDiagnosisView(APIView):
    """
    POST /api/doctor/patients/{patient_id}/add-diagnosis/
    Médecin : ajoute un antécédent/diagnostic dans le dossier du patient.
    Permission : au moins un RDV entre ce médecin et ce patient.

    Body: { "condition": str, "description": str (optionnel), "diagnosis_date": "YYYY-MM-DD" (optionnel) }
    """
    permission_classes = [IsDoctor]

    def post(self, request, patient_id):
        doctor = request.user.doctor_profile

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({"detail": "Patient introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not Appointment.objects.filter(doctor=doctor, patient=patient).exists():
            return Response(
                {"detail": "Accès refusé : aucun rendez-vous entre ce médecin et ce patient."},
                status=status.HTTP_403_FORBIDDEN,
            )

        condition = (request.data.get('condition') or '').strip()
        if not condition:
            return Response({"detail": "condition est requis."}, status=status.HTTP_400_BAD_REQUEST)

        description = request.data.get('description') or ''
        diagnosis_date = request.data.get('diagnosis_date') or None

        from patients.models import Antecedent
        from django.utils import timezone as tz
        antecedent = Antecedent.objects.create(
            patient=patient,
            name=condition,
            type='personnel',
            description=description,
            date_diagnosis=diagnosis_date or tz.now().date(),
        )

        # Notifier le patient
        from notifications.models import Notification
        Notification.objects.create(
            user=patient.user,
            title="Dossier médical mis à jour",
            message=f"Le Dr. {doctor.user.last_name} a ajouté un diagnostic dans votre dossier médical.",
            notification_type=Notification.NotificationType.SYSTEM,
        )

        return Response(
            {"detail": "Diagnostic ajouté.", "id": antecedent.pk},
            status=status.HTTP_201_CREATED,
        )


class DoctorAddTreatmentView(APIView):
    """
    POST /api/doctor/patients/{patient_id}/add-treatment/
    Médecin : ajoute un traitement en cours dans le dossier du patient.
    Permission : au moins un RDV entre ce médecin et ce patient.

    Body: { "medication_name": str, "dosage": str, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" (optionnel) }
    """
    permission_classes = [IsDoctor]

    def post(self, request, patient_id):
        doctor = request.user.doctor_profile

        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response({"detail": "Patient introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not Appointment.objects.filter(doctor=doctor, patient=patient).exists():
            return Response(
                {"detail": "Accès refusé : aucun rendez-vous entre ce médecin et ce patient."},
                status=status.HTTP_403_FORBIDDEN,
            )

        medication_name = (request.data.get('medication_name') or '').strip()
        if not medication_name:
            return Response({"detail": "medication_name est requis."}, status=status.HTTP_400_BAD_REQUEST)

        dosage = request.data.get('dosage') or ''
        start_date = request.data.get('start_date') or None
        end_date = request.data.get('end_date') or None

        from patients.models import Treatment
        from django.utils import timezone as tz
        treatment = Treatment.objects.create(
            patient=patient,
            prescribed_by=doctor,
            medication_name=medication_name,
            dosage=dosage,
            start_date=start_date or tz.now().date(),
            end_date=end_date,
        )

        from notifications.models import Notification
        Notification.objects.create(
            user=patient.user,
            title="Dossier médical mis à jour",
            message=f"Le Dr. {doctor.user.last_name} a ajouté un traitement dans votre dossier médical.",
            notification_type=Notification.NotificationType.SYSTEM,
        )

        return Response(
            {"detail": "Traitement ajouté.", "id": treatment.pk},
            status=status.HTTP_201_CREATED,
        )
