"""Root URL configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Authentication ──────────────────────────────────────────────────────
    path('api/auth/', include('users.urls')),

    # ── App endpoints ───────────────────────────────────────────────────────
    path('api/users/', include('users.urls')),
    path('api/doctors/', include('doctors.urls')),
    path('api/patients/', include('patients.urls')),
    path('api/pharmacy/', include('pharmacy.urls')),
    path('api/caretaker/', include('caretaker.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/consultations/', include('consultations.urls')),
    path('api/prescriptions/', include('prescriptions.urls')),
    path('api/medications/', include('medications.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/admin/', include('admin_panel.urls')),
    path('api/messaging/', include('messaging.urls')),

    # ── DRF Browsable API ────────────────────────────────────────────────────
    path('api-auth/', include('rest_framework.urls')),

    # ── API Documentation (OpenAPI 3.0) ──────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)