from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaretakerViewSet, CareRequestViewSet, AddCertificateView, CaretakerDashboardView, CaretakerTaskViewSet

router = DefaultRouter()
router.register(r'search',   CaretakerViewSet,     basename='caretaker-search')
router.register(r'requests', CareRequestViewSet,   basename='care-request')
router.register(r'tasks',    CaretakerTaskViewSet, basename='caretaker-task')

urlpatterns = [
    path('', include(router.urls)),
    path('certificates/add/', AddCertificateView.as_view(), name='add-certificate'),
    path('dashboard/', CaretakerDashboardView.as_view(), name='caretaker-dashboard'),
]