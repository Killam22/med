
# settings/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import UserSettings, AccountDeletionRequest
from .serializers import (
    UserSettingsSerializer,
    ChangePasswordSerializer,
    UpdateProfileSerializer,
    AccountDeletionRequestSerializer,
)


# ── 1. Notification / Appearance / Privacy settings ──────────────────────────

class UserSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/settings/         → return current user's settings
    PATCH /api/settings/        → update any subset of settings fields
    """
    serializer_class   = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _ = UserSettings.objects.get_or_create(user=self.request.user)
        return obj


# ── 2. Change password ────────────────────────────────────────────────────────

class ChangePasswordView(APIView):
    """
    POST /api/settings/change-password/
    Body: { old_password, new_password, new_password2 }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({'detail': 'Password updated successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── 3. Update profile info ────────────────────────────────────────────────────

class UpdateProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/settings/profile/   → return editable profile fields
    PATCH /api/settings/profile/   → update name, phone, address, etc.
    """
    serializer_class   = UpdateProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ── 4. Account deletion request ──────────────────────────────────────────────

class AccountDeletionRequestView(APIView):
    """
    POST   /api/settings/delete-account/   → submit deletion request
    DELETE /api/settings/delete-account/   → cancel pending request
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Prevent duplicate requests
        if AccountDeletionRequest.objects.filter(
            user=request.user, status='pending'
        ).exists():
            return Response(
                {'detail': 'A deletion request is already pending.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = AccountDeletionRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                {'detail': 'Deletion request submitted. Your account will be reviewed.'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            req = AccountDeletionRequest.objects.get(
                user=request.user, status='pending'
            )
            req.status = 'cancelled'
            req.reviewed_at = timezone.now()
            req.save()
            return Response({'detail': 'Deletion request cancelled.'})
        except AccountDeletionRequest.DoesNotExist:
            return Response(
                {'detail': 'No pending deletion request found.'},
                status=status.HTTP_404_NOT_FOUND,
            )