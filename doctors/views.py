from django.utils import timezone
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Doctor
from appointments.models import AvailabilitySlot
from .serializers import DoctorListSerializer, DoctorDetailSerializer
from appointments.serializers import AvailabilitySlotSerializer
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
        return Doctor.objects.select_related('user').prefetch_related('slots')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['filter_date'] = self.request.query_params.get('date')
        return context

class DoctorDetailView(generics.RetrieveAPIView):
    """GET /api/doctors/{id}/ — full doctor profile."""
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = Doctor.objects.select_related('user').prefetch_related('slots')

class DoctorSlotsView(generics.ListAPIView):
    """GET /api/doctors/{doctor_id}/slots/ — available slots for a doctor."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        doctor_id = self.kwargs['doctor_id']
        qs = AvailabilitySlot.objects.filter(
            doctor_id=doctor_id,
            is_booked=False,
            date__gte=timezone.now().date(),
        ).order_by('date', 'start_time')

        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(date=date)
        return qs

class DoctorProfileView(generics.RetrieveUpdateAPIView):
    """GET / PUT /api/doctors/profile/ — own doctor profile."""
    serializer_class = DoctorDetailSerializer
    permission_classes = [IsDoctor]

    def get_object(self):
        return self.request.user.doctor_profile

class DoctorSlotListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/doctors/slots/ — list and create slots."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        doctor = self.request.user.doctor_profile
        qs = AvailabilitySlot.objects.filter(doctor=doctor).order_by('date', 'start_time')
        date = self.request.query_params.get('date')
        is_booked = self.request.query_params.get('is_booked')
        if date:
            qs = qs.filter(date=date)
        if is_booked is not None:
            qs = qs.filter(is_booked=is_booked.lower() == 'true')
        return qs

    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user.doctor_profile)

class DoctorSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / DELETE /api/doctors/slots/{id}/."""
    serializer_class = AvailabilitySlotSerializer
    permission_classes = [IsDoctor]

    def get_queryset(self):
        return AvailabilitySlot.objects.filter(doctor=self.request.user.doctor_profile)

    def destroy(self, request, *args, **kwargs):
        slot = self.get_object()
        if slot.is_booked:
            return Response(
                {"detail": "Impossible de supprimer un créneau déjà réservé."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
