from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DoctorListView,
    DoctorDetailView,
    DoctorProfileView,
    WeeklyScheduleViewSet,
    DayOffViewSet,
)

# Router pour les ViewSets du planning
# Ces routes seront accessibles sous /api/doctors/my-schedule/ et /api/doctors/days-off/
router = DefaultRouter()
router.register(r'my-schedule', WeeklyScheduleViewSet, basename='doctor-schedule-mgmt')
router.register(r'days-off',    DayOffViewSet,          basename='doctor-days-off')

urlpatterns = [
    # Inclusion des routes générées par le router
    path('', include(router.urls)),

    # Search and List  → /api/doctors/list/
    path('list/',         DoctorListView.as_view(),    name='doctor_list'),
    # Detail            → /api/doctors/{id}/
    path('<int:pk>/',     DoctorDetailView.as_view(),  name='doctor_detail'),
    # Own profile       → /api/doctors/profile/
    path('profile/',     DoctorProfileView.as_view(),  name='doctor_profile'),
]
