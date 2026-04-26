from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet, CompleteSessionView

router = DefaultRouter()
router.register('consultations', ConsultationViewSet, basename='consultation')

urlpatterns = [
    # ⚠️ Route custom AVANT le router pour éviter qu'elle soit avalée
    path('complete-session/', CompleteSessionView.as_view(), name='complete_session'),
    path('', include(router.urls)),
]
