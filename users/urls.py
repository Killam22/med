from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    RegisterPatientView,
    RegisterDoctorView,
    VerifyRegisterOTPView,
    UnifiedProfileView,
    PasswordResetRequestView,
    PasswordResetVerifyOTPView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('token/',         CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(),          name='token_refresh'),

    # ── Inscription ───────────────────────────────────────────────────────────
    path('register/patient/', RegisterPatientView.as_view(), name='register_patient'),
    path('register/doctor/',  RegisterDoctorView.as_view(),  name='register_doctor'),

    # ── Vérification OTP (activation du compte) ───────────────────────────────
    path('verify-otp/', VerifyRegisterOTPView.as_view(), name='verify_register_otp'),

    # ── Profil "Caméléon" (GET + PATCH adapté au rôle) ───────────────────────
    path('me/', UnifiedProfileView.as_view(), name='user_profile'),

    # ── Mot de passe oublié (3 étapes) ───────────────────────────────────────
    path('password-reset/request/', PasswordResetRequestView.as_view(),   name='password_reset_request'),
    path('password-reset/verify/',  PasswordResetVerifyOTPView.as_view(), name='password_reset_verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(),   name='password_reset_confirm'),
]
