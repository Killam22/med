"""URL configuration for the appointments app (Appointment logic only)."""

from django.urls import path
from . import views
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
    StartConsultationView,
    PatientRecordView,

    # Reviews
    CreateReviewView,
    DoctorReviewListView,
)

urlpatterns = [
    # ── Availability (public) ─────────────────────────────────────────────
    # GET /api/doctors/{id}/availability/?date=YYYY-MM-DD  → créneaux libres pour une date
    # GET /api/doctors/{id}/availability/?from=...&to=...  → créneaux libres sur une plage
    path('doctors/<int:doctor_id>/availability/', views.DoctorAvailabilityView.as_view(), name='doctor-availability'),

    # ── Patient ───────────────────────────────────────────────────────────
    path('appointments/',                          views.PatientAppointmentListCreateView.as_view(),  name='patient-appointments'),
    path('appointments/<int:pk>/',                 views.PatientAppointmentDetailView.as_view(),      name='patient-appointment-detail'),
    path('appointments/<int:pk>/cancel/',          views.CancelAppointmentView.as_view(),             name='appointment-cancel'),
    path('appointments/<int:pk>/reschedule/',      views.RescheduleAppointmentView.as_view(),         name='appointment-reschedule'),

    # ── Doctor ────────────────────────────────────────────────────────────
    path('doctor/schedule/',                          views.DoctorDailyScheduleView.as_view(),           name='doctor-schedule'),
    path('doctor/appointments/',                      views.DoctorAppointmentListView.as_view(),          name='doctor-appointments'),
    path('doctor/appointments/pending/',              views.DoctorPendingAppointmentsView.as_view(),      name='doctor-appointments-pending'),
    path('doctor/appointments/<int:pk>/',             views.DoctorAppointmentDetailView.as_view(),        name='doctor-appointment-detail'),
    path('doctor/appointments/<int:pk>/confirm/',     views.ConfirmAppointmentView.as_view(),             name='appointment-confirm'),
    path('doctor/appointments/<int:pk>/refuse/',      views.RefuseAppointmentView.as_view(),              name='appointment-refuse'),
    path('doctor/appointments/<int:pk>/complete/',    views.CompleteAppointmentView.as_view(),            name='appointment-complete'),
    path('appointments/<int:pk>/start/',              StartConsultationView.as_view(),                   name='appointment-start'),
    path('doctor/patients/<int:patient_id>/record/',  PatientRecordView.as_view(),                       name='patient-record'),

    # ── Reviews ────────────────────────────────────────────────────────────────
    path('appointments/<int:pk>/review/', CreateReviewView.as_view(),      name='appointment-review'),
    path('doctors/<int:pk>/reviews/',     DoctorReviewListView.as_view(),  name='doctor-reviews'),
]
