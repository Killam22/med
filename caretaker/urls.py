from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CaretakerViewSet, CareRequestViewSet, AddCertificateView,
    CaretakerDashboardView, CaretakerProfileView,
    CaretakerTaskViewSet, MedicationScheduleViewSet,
)

router = DefaultRouter()
router.register(r'search',               CaretakerViewSet,          basename='caretaker-search')
router.register(r'requests',             CareRequestViewSet,        basename='care-request')
router.register(r'tasks',                CaretakerTaskViewSet,      basename='caretaker-task')
router.register(r'medication-schedules', MedicationScheduleViewSet, basename='medication-schedule')

urlpatterns = [
    path('', include(router.urls)),
    path('certificates/add/', AddCertificateView.as_view(), name='add-certificate'),
    path('dashboard/', CaretakerDashboardView.as_view(), name='caretaker-dashboard'),
    path('profile/',   CaretakerProfileView.as_view(),   name='caretaker-profile'),
]