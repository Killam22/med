from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationSummaryView

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('summary/', NotificationSummaryView.as_view(), name='notifications-summary'),
    path('', include(router.urls)),
]