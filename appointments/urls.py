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
    # ── Availability (public) ─────────────────────────────────────────────
    path('doctors/<int:doctor_id>/availability/', views.DoctorAvailabilityView.as_view()),

    # ── Patient ───────────────────────────────────────────────────────────
    path('appointments/',                          views.PatientAppointmentListCreateView.as_view()),
    path('appointments/<int:pk>/',                 views.PatientAppointmentDetailView.as_view()),
    path('appointments/<int:pk>/cancel/',          views.CancelAppointmentView.as_view()),
    path('appointments/<int:pk>/reschedule/',      views.RescheduleAppointmentView.as_view()),

    # ── Doctor ────────────────────────────────────────────────────────────
    path('doctor/schedule/',                       views.DoctorDailyScheduleView.as_view()),
    path('doctor/appointments/',                   views.DoctorAppointmentListView.as_view()),
    path('doctor/appointments/<int:pk>/confirm/',  views.ConfirmAppointmentView.as_view()),
    path('doctor/appointments/<int:pk>/refuse/',   views.RefuseAppointmentView.as_view()),
    path('doctor/appointments/<int:pk>/complete/', views.CompleteAppointmentView.as_view()),
          
    # ── Reviews ────────────────────────────────────────────────────────────────
    path('appointments/<int:pk>/review/', CreateReviewView.as_view(), name='appointment-review'),
    path('doctors/<int:pk>/reviews/', DoctorReviewListView.as_view(), name='doctor-reviews'),

    # ── Notifications ──────────────────────────────────────────────────────────
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
]