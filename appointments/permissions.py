"""Custom DRF permission classes."""

from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    """Allow access only to users with role='patient'."""

    message = "Accès réservé aux patients."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'patient'
        )


class IsDoctor(BasePermission):
    """Allow access only to users with role='doctor'."""

    message = "Accès réservé aux médecins."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'doctor'
        )
