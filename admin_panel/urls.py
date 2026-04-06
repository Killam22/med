from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserManagementViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'users', AdminUserManagementViewSet, basename='admin-users')
router.register(r'audit-logs', AuditLogViewSet, basename='admin-audit-logs')

urlpatterns = [
    path('', include(router.urls)),
]