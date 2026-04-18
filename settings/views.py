from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView

from .models import NotificationPreferences
from .serializers import (
    PatientProfileSerializer,
    CaretakerProfileSerializer,
    PharmacistProfileSerializer,
    AdminProfileSerializer,
    NotificationPreferencesSerializer,
    AccountDeactivationSerializer,
)

# ─────────────────────────────────────────────────────────────
# Helper: pick the right serializer based on role
# ─────────────────────────────────────────────────────────────
ROLE_SERIALIZER_MAP = {
    'patient':    PatientProfileSerializer,
    'caretaker':  CaretakerProfileSerializer,
    'pharmacist': PharmacistProfileSerializer,
    'doctor':     AdminProfileSerializer,   # doctor uses base fields for now
    'admin':      AdminProfileSerializer,
}


# ─────────────────────────────────────────────────────────────
# 1. EDIT PROFILE  —  GET / PATCH  /settings/profile/
# ─────────────────────────────────────────────────────────────
class ProfileSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        role = self.request.user.role
        return ROLE_SERIALIZER_MAP.get(role, AdminProfileSerializer)

    def get(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────
# 2. NOTIFICATION PREFERENCES  —  GET / PATCH  /settings/notifications/
# ─────────────────────────────────────────────────────────────
class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Auto-create if missing (safe fallback)
        prefs, _ = NotificationPreferences.objects.get_or_create(user=self.request.user)
        return prefs

    def get(self, request):
        serializer = NotificationPreferencesSerializer(self.get_object())
        return Response(serializer.data)

    def patch(self, request):
        serializer = NotificationPreferencesSerializer(
            self.get_object(),
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────
# 4. ACCOUNT DEACTIVATION  —  POST  /settings/deactivate/
# ─────────────────────────────────────────────────────────────
class AccountDeactivationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AccountDeactivationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Account deactivated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)