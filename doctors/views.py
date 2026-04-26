from django.utils import timezone
from rest_framework import generics, filters, viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Doctor, WeeklySchedule, DayOff, DoctorQualification
from .serializers import (
    DoctorListSerializer, DoctorDetailSerializer,
    WeeklyScheduleSerializer, DayOffSerializer, DocQualificationSerializer
)
from .filters import DoctorFilter
from appointments.permissions import IsDoctor


class DoctorListView(generics.ListAPIView):
    """GET /api/doctors/ — search doctors with filters."""
    serializer_class = DoctorListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = DoctorFilter
    ordering_fields = ['rating', 'experience_years']
    ordering = ['-rating']

    def get_queryset(self):
        return Doctor.objects.select_related('user').prefetch_related('schedules', 'days_off')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['filter_date'] = self.request.query_params.get('date')
        return context


class DoctorDetailView(generics.RetrieveAPIView):
    """GET /api/doctors/{id}/ — full doctor profile."""
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = Doctor.objects.select_related('user').prefetch_related('schedules', 'days_off')


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """GET / PUT /api/doctors/profile/ — own doctor profile."""
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsDoctor]

    def get_object(self):
        return self.request.user.doctor_profile

class AddQualificationView(generics.CreateAPIView):
    queryset = DoctorQualification.objects.all()
    serializer_class = DocQualificationSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)
# ── Doctor Schedule Management ────────────────────────────────────────────────────

class WeeklyScheduleViewSet(viewsets.ModelViewSet):
    """
    CRUD complet sur le planning hebdomadaire du médecin connecté.

    GET    /api/doctor/my-schedule/            → voir tous ses jours de travail
    POST   /api/doctor/my-schedule/            → ajouter un jour (day_of_week unique par médecin)
    GET    /api/doctor/my-schedule/{id}/       → détail d'un jour
    PUT    /api/doctor/my-schedule/{id}/       → modifier les heures d'un jour
    PATCH  /api/doctor/my-schedule/{id}/       → modifier partiellement (ex: juste is_active)
    DELETE /api/doctor/my-schedule/{id}/       → supprimer un jour de son planning
    """
    serializer_class   = WeeklyScheduleSerializer
    permission_classes = [IsDoctor]
    pagination_class   = None

    def get_queryset(self):
        return WeeklySchedule.objects.filter(
            doctor=self.request.user.doctor_profile
        ).order_by('day_of_week')

    def perform_create(self, serializer):
        doctor = self.request.user.doctor_profile
        day    = serializer.validated_data['day_of_week']
        # Si un planning existe déjà pour ce jour, on le met à jour
        existing = WeeklySchedule.objects.filter(doctor=doctor, day_of_week=day).first()
        if existing:
            for attr, value in serializer.validated_data.items():
                setattr(existing, attr, value)
            existing.save()
        else:
            serializer.save(doctor=doctor)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = request.user.doctor_profile
        day    = serializer.validated_data['day_of_week']
        existing = WeeklySchedule.objects.filter(doctor=doctor, day_of_week=day).first()
        if existing:
            # mise à jour en place
            for attr, value in serializer.validated_data.items():
                setattr(existing, attr, value)
            existing.save()
            return Response(
                WeeklyScheduleSerializer(existing).data,
                status=status.HTTP_200_OK
            )
        serializer.save(doctor=doctor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DayOffViewSet(viewsets.ModelViewSet):
    """
    Gestion des congés / jours de fermeture du médecin connecté.

    GET    /api/doctor/days-off/          → liste de ses congés
    POST   /api/doctor/days-off/          → déclarer un congé (date unique par médecin)
    DELETE /api/doctor/days-off/{id}/     → annuler un congé
    """
    serializer_class   = DayOffSerializer
    permission_classes = [IsDoctor]
    http_method_names  = ['get', 'post', 'delete', 'head', 'options']  # pas de PUT/PATCH

    def get_queryset(self):
        return DayOff.objects.filter(
            doctor=self.request.user.doctor_profile
        ).order_by('date')

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)


class DoctorDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'doctor':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        today = timezone.now().date()

        from appointments.models import Appointment
        today_appointments = Appointment.objects.filter(doctor__user=user, date=today)
        pending_appointments = Appointment.objects.filter(doctor__user=user, status='pending')

        data = {
            "kpis": {
                "today_consultations": today_appointments.exclude(status='cancelled').count(),
                "total_patients": Appointment.objects.filter(
                    doctor__user=user
                ).values('patient').distinct().count(),
                "pending_requests": pending_appointments.count(),
            },
            "todays_schedule": [
                {
                    "id": str(a.id),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "end_time": a.end_time.strftime('%H:%M'),
                    "patient_name": a.patient.user.get_full_name(),
                    "motif": a.motif,
                    "status": a.status,
                }
                for a in today_appointments.exclude(status='cancelled').order_by('start_time')
            ],
            "patient_requests": [
                {
                    "id": str(a.id),
                    "patient_name": a.patient.user.get_full_name(),
                    "date": a.date.isoformat(),
                    "start_time": a.start_time.strftime('%H:%M'),
                    "motif": a.motif,
                }
                for a in pending_appointments.order_by('date')
            ],
        }
        return Response(data)
