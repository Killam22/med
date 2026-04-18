from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminUserManagementViewSet, AuditLogViewSet, AdminDashboardView

router = DefaultRouter()
router.register(r'users', AdminUserManagementViewSet, basename='admin-users')
router.register(r'audit-logs', AuditLogViewSet, basename='admin-audit-logs')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]