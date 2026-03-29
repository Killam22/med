"""Views for the appointment management logic."""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from patients.models import Patient
from doctors.models import Doctor
from .models import AvailabilitySlot, Appointment, Notification, Review
from .serializers import (
    AvailabilitySlotSerializer,
    AppointmentSerializer,
    AppointmentDoctorSerializer,
    NotificationSerializer,
    ReviewSerializer,
)
from .permissions import IsPatient, IsDoctor


# ── Patient Appointment Views ──────────────────────────────────────────────────

class PatientAppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/appointments/ — patient's appointment list
    POST /api/appointments/ — book a new appointment
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        patient = self.request.user.patient_profile
        qs = Appointment.objects.filter(patient=patient).select_related(
            'doctor__user', 'slot'
        )
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        patient = self.request.user.patient_profile
        slot = serializer.validated_data['slot']
        appointment = serializer.save(
            patient=patient,
            doctor=slot.doctor,
        )
        Notification.objects.create(
            user=slot.doctor.user,
            message=f"Nouvelle demande de rendez-vous de {patient.user.get_full_name()}.",
            notification_type='booking',
            related_appointment=appointment
        )


class PatientAppointmentDetailView(generics.RetrieveAPIView):
    """GET /api/appointments/{id}/ — appointment detail (patient)."""
    serializer_class = AppointmentSerializer
    permission_classes = [IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(patient=self.request.user.patient_profile)


class CancelAppointmentView(APIView):
    """POST /api/appointments/{id}/cancel/ — patient cancels appointment."""
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user.patient_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status in ('cancelled', 'refused', 'completed'):
            return Response(
                {"detail": f"Impossible d'annuler un rendez-vous '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.cancel()
        Notification.objects.create(
            user=appointment.doctor.user,
            message=f"Le patient {appointment.patient.user.get_full_name()} a annulé son rendez-vous du {appointment.slot.date if appointment.slot else ''}.",
            notification_type='status_change',
            related_appointment=appointment
        )
        return Response({"detail": "Rendez-vous annulé avec succès."}, status=status.HTTP_200_OK)


class RescheduleAppointmentView(APIView):
    """POST /api/appointments/{id}/reschedule/ — patient picks a new slot."""
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, patient=request.user.patient_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status in ('cancelled', 'refused', 'completed'):
            return Response(
                {"detail": "Impossible de modifier ce rendez-vous."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_slot_id = request.data.get('slot_id')
        if not new_slot_id:
            return Response({"detail": "Veuillez fournir un 'slot_id'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_slot = AvailabilitySlot.objects.get(pk=new_slot_id, doctor=appointment.doctor, is_booked=False)
        except AvailabilitySlot.DoesNotExist:
            return Response({"detail": "Créneau indisponible."}, status=status.HTTP_400_BAD_REQUEST)

        # Free the old slot
        if appointment.slot:
            appointment.slot.is_booked = False
            appointment.slot.save()

        # Assign new slot
        new_slot.is_booked = True
        new_slot.save()
        appointment.slot = new_slot
        appointment.status = 'pending'
        appointment.save()

        serializer = AppointmentSerializer(appointment)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ── Doctor Appointment Management ─────────────────────────────────────────────

class DoctorAppointmentListView(generics.ListAPIView):
    """GET /api/doctor/appointments/ — doctor sees all their appointments."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        qs = Appointment.objects.filter(doctor=doctor).select_related(
            'patient__user', 'slot'
        )
        status_filter = self.request.query_params.get('status')
        date = self.request.query_params.get('date')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if date:
            qs = qs.filter(slot__date=date)
        return qs.order_by('slot__date', 'slot__start_time')


class DoctorDailyScheduleView(generics.ListAPIView):
    """GET /api/doctor/schedule/today/ — doctor's appointments for today."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        today = timezone.now().date()
        date_param = self.request.query_params.get('date')
        target_date = date_param if date_param else today

        return Appointment.objects.filter(
            doctor=doctor,
            slot__date=target_date,
            status__in=['confirmed', 'pending', 'completed']
        ).select_related('patient__user', 'slot').order_by('slot__start_time')


class DoctorPendingAppointmentsView(generics.ListAPIView):
    """GET /api/doctor/appointments/pending/ — doctor's pending appointment requests."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        return Appointment.objects.filter(
            doctor=doctor,
            status='pending'
        ).select_related('patient__user', 'slot').order_by('slot__date', 'slot__start_time')


class DoctorAppointmentDetailView(generics.RetrieveAPIView):
    """GET /api/doctor/appointments/{id}/ — single appointment detail."""
    serializer_class = AppointmentDoctorSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return Appointment.objects.filter(doctor=self.request.user.doctor_profile)


class ConfirmAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/confirm/ — doctor confirms."""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status != 'pending':
            return Response(
                {"detail": f"Impossible de confirmer un rendez-vous '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.confirm()
        Notification.objects.create(
            user=appointment.patient.user,
            message=f"Votre rendez-vous avec le Dr. {appointment.doctor.user.last_name} a été confirmé.",
            notification_type='status_change',
            related_appointment=appointment
        )
        return Response({"detail": "Rendez-vous confirmé."}, status=status.HTTP_200_OK)


class RefuseAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/refuse/ — doctor refuses."""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status not in ('pending', 'confirmed'):
            return Response(
                {"detail": f"Impossible de refuser un rendez-vous '{appointment.get_status_display()}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason', '')
        appointment.refuse(reason=reason)
        Notification.objects.create(
            user=appointment.patient.user,
            message=f"Votre demande de rendez-vous avec le Dr. {appointment.doctor.user.last_name} a été refusée.",
            notification_type='status_change',
            related_appointment=appointment
        )
        return Response({"detail": "Rendez-vous refusé."}, status=status.HTTP_200_OK)


class CompleteAppointmentView(APIView):
    """POST /api/doctor/appointments/{id}/complete/ — mark as completed."""
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk, doctor=request.user.doctor_profile)
        except Appointment.DoesNotExist:
            return Response({"detail": "Rendez-vous introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if appointment.status != 'confirmed':
            return Response(
                {"detail": "Seuls les rendez-vous confirmés peuvent être marqués terminés."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        notes = request.data.get('notes', '')
        appointment.status = 'completed'
        appointment.notes = notes
        appointment.save()
        return Response({"detail": "Rendez-vous marqué comme terminé."}, status=status.HTTP_200_OK)


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
            doctor=appointment.doctor
        )


class DoctorReviewListView(generics.ListAPIView):
    """GET /api/doctors/{id}/reviews/ — public read-only reviews for a doctor."""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        doctor_id = self.kwargs['pk']
        return Review.objects.filter(doctor_id=doctor_id).order_by('-created_at')
