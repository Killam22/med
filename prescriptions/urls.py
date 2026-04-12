from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrescriptionViewSet, QRScanView, QRImageView, PrescriptionPDFView

router = DefaultRouter()
router.register('prescriptions', PrescriptionViewSet, basename='prescription')

urlpatterns = [
    # ⚠️ Les URLs custom AVANT le router — sinon prescriptions/{pk}/ avale tout
    path('prescriptions/scan/',                  QRScanView.as_view(),        name='qr_scan'),
    path('prescriptions/<str:pk>/qr-image/',     QRImageView.as_view(),       name='qr_image'),
    path('prescriptions/<str:pk>/pdf-download/', PrescriptionPDFView.as_view(), name='pdf_download'),

    # Router DRF (doit être en dernier)
    path('', include(router.urls)),
]