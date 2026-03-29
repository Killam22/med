"""Root URL configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Authentication ──────────────────────────────────────────────────────
    path('api/auth/', include('users.urls')),

    # ── App endpoints ───────────────────────────────────────────────────────
    path('api/doctors/', include('doctors.urls')),
    path('api/patients/', include('patients.urls')),
    path('api/pharmacy/', include('pharmacy.urls')),
    path('api/caretaker/', include('caretaker.urls')),
    path('api/', include('appointments.urls')),

    # ── DRF Browsable API ────────────────────────────────────────────────────
    path('api-auth/', include('rest_framework.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
