"""URL configuration for the appointments app (Appointment logic only)."""

from django.urls import path
from .views import (
    # Patient — appointments
    PatientAppointmentListCreateView,
    PatientAppointmentDetailView,
    CancelAppointmentView,
    RescheduleAppointmentView,

    # Doctor — appointments
    DoctorAppointmentListView,
    DoctorAppointmentDetailView,
    ConfirmAppointmentView,
    RefuseAppointmentView,
    CompleteAppointmentView,
    DoctorDailyScheduleView,
    DoctorPendingAppointmentsView,

    # Notifications
    NotificationListView,
    NotificationMarkReadView,

    # Reviews
    CreateReviewView,
    DoctorReviewListView,
)

urlpatterns = [
    # ── Patient appointments ──────────────────────────────────────────────────
    path('appointments/', PatientAppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('appointments/<int:pk>/', PatientAppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/<int:pk>/cancel/', CancelAppointmentView.as_view(), name='appointment-cancel'),
    path('appointments/<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='appointment-reschedule'),

    # ── Doctor appointments ───────────────────────────────────────────────────
    path('doctor/schedule/today/', DoctorDailyScheduleView.as_view(), name='doctor-schedule-today'),
    path('doctor/appointments/pending/', DoctorPendingAppointmentsView.as_view(), name='doctor-appointments-pending'),
    path('doctor/appointments/', DoctorAppointmentListView.as_view(), name='doctor-appointment-list'),
    path('doctor/appointments/<int:pk>/', DoctorAppointmentDetailView.as_view(), name='doctor-appointment-detail'),
    path('doctor/appointments/<int:pk>/confirm/', ConfirmAppointmentView.as_view(), name='appointment-confirm'),
    path('doctor/appointments/<int:pk>/refuse/', RefuseAppointmentView.as_view(), name='appointment-refuse'),
    path('doctor/appointments/<int:pk>/complete/', CompleteAppointmentView.as_view(), name='appointment-complete'),

    # ── Reviews ────────────────────────────────────────────────────────────────
    path('appointments/<int:pk>/review/', CreateReviewView.as_view(), name='appointment-review'),
    path('doctors/<int:pk>/reviews/', DoctorReviewListView.as_view(), name='doctor-reviews'),

    # ── Notifications ──────────────────────────────────────────────────────────
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
]
