from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PrescriptionViewSet,
    QRScanView,
    QRImageView,
    PrescriptionPDFView,
    QuickPrescriptionView,
)

router = DefaultRouter()
router.register('prescriptions', PrescriptionViewSet, basename='prescription')

urlpatterns = [
    # ⚠️ Les URLs custom AVANT le router — sinon prescriptions/{pk}/ avale tout
    path('scan/',                  QRScanView.as_view(),        name='qr_scan'),
    path('quick/',                 QuickPrescriptionView.as_view(), name='quick_prescription'),
    path('<str:pk>/qr-image/',     QRImageView.as_view(),       name='qr_image'),
    path('<str:pk>/pdf-download/', PrescriptionPDFView.as_view(), name='pdf_download'),

    # Router DRF (doit être en dernier)
    path('', include(router.urls)),
]