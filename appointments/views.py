"""Views for the appointment management logic."""

from datetime import date, timedelta

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from patients.models import Patient
from doctors.models import Doctor
from .models import Appointment, Notification, Review
from .serializers import (
    AppointmentSerializer,
    AppointmentDoctorSerializer,
    BookAppointmentSerializer,
    NotificationSerializer,
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
        Notification.objects.create(
            user=appointment.doctor.user,
            message=f"{appointment.patient.user.get_full_name()} a annulé son RDV du {appointment.date}.",
            notification_type='status_change',
            related_appointment=appointment,
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
        Notification.objects.create(
            user=appt.patient.user,
            message=f"Votre RDV avec Dr.{appt.doctor.user.last_name} est confirmé.",
            notification_type='status_change',
            related_appointment=appt,
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
        Notification.objects.create(
            user=appt.patient.user,
            message=f"Votre demande avec Dr.{appt.doctor.user.last_name} a été refusée.",
            notification_type='status_change',
            related_appointment=appt,
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
        return Response({"detail": "Terminé."}, status=status.HTTP_200_OK)


# ── Notification Views ────────────────────────────────────────────────────────

class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ — user sees their notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
    """POST /api/notifications/{id}/read/ — mark notification as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification introuvable."}, status=status.HTTP_404_NOT_FOUND)

        notif.is_read = True
        notif.save()
        return Response({"detail": "Notification marquée comme lue."}, status=status.HTTP_200_OK)


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
