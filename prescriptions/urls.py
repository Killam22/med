from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrescriptionViewSet, MedicationViewSet, QRScanView

router = DefaultRouter()
router.register('prescriptions', PrescriptionViewSet, basename='prescription')
router.register('medications', MedicationViewSet, basename='medication')

urlpatterns = [
    path('', include(router.urls)),
    path('scan/', QRScanView.as_view(), name='qr_scan'),
]