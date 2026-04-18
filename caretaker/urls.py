from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaretakerViewSet, CareRequestViewSet, AddCertificateView

router = DefaultRouter()
# /api/caretakers/search/ -> Pour la recherche patient
router.register(r'search', CaretakerViewSet, basename='caretaker-search')
# /api/caretakers/requests/ -> Pour la gestion des contrats
router.register(r'requests', CareRequestViewSet, basename='care-request')

urlpatterns = [
    path('', include(router.urls)),
    path('certificates/add/', AddCertificateView.as_view(), name='add-certificate'),
]