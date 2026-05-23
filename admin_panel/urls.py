from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminUserManagementViewSet,
    AuditLogViewSet,
    AdminDashboardView,
    AdminAppointmentListView,
    AdminProfileUpdateListView,
    AdminProfileUpdateActionView,
    SystemStatusView,
    AdminContactRequestViewSet,
    MyAdminContactRequestView,
)

router = DefaultRouter()
router.register(r'users', AdminUserManagementViewSet, basename='admin-users')
router.register(r'audit-logs', AuditLogViewSet, basename='admin-audit-logs')
router.register(r'contact-requests', AdminContactRequestViewSet, basename='admin-contact-requests')

urlpatterns = [
    # Doit être déclaré avant le router pour éviter que /contact-requests/me/
    # ne soit intercepté comme {pk}="me" par le ViewSet admin.
    path('contact-requests/me/', MyAdminContactRequestView.as_view(), name='admin_contact_requests_me'),
    path('', include(router.urls)),
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('stats/',     AdminDashboardView.as_view(), name='admin-stats'),
    path('appointments/', AdminAppointmentListView.as_view(), name='admin-appointments'),
    path('profile-updates/', AdminProfileUpdateListView.as_view(), name='admin_profile_updates'),
    path('profile-updates/<int:pk>/action/', AdminProfileUpdateActionView.as_view(), name='admin_profile_update_action'),
    path('system-status/', SystemStatusView.as_view(), name='admin_system_status'),
]