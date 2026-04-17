from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

# Importation de TOUTES les vues depuis notre views.py définitif
from .views import (
    # Auth JWT
    CustomTokenObtainPairView,
    
    # Inscriptions par rôle
    RegisterPatientView,
    RegisterDoctorView,
    RegisterPharmacistView,
    RegisterCaretakerView,
    
    # Vérification Email OTP
    VerifyRegisterOTPView,
    
    # Le Caméléon
    UnifiedProfileView,
    
    # Mots de passe
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetVerifyOTPView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # ── 🔐 Authentification (JWT avec Rate Limiting) ───────────────────────────
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),

    # ── 📝 Inscriptions (Création de profil + Envoi auto de l'OTP) ────────────
    path('register/patient/', RegisterPatientView.as_view(), name='register_patient'),
    path('register/doctor/', RegisterDoctorView.as_view(), name='register_doctor'),
    path('register/pharmacist/', RegisterPharmacistView.as_view(), name='register_pharmacist'),
    path('register/caretaker/', RegisterCaretakerView.as_view(), name='register_caretaker'),

    # ── ✉️ Activation du compte (Vérification OTP) ───────────────────────────
    path('register/verify/', VerifyRegisterOTPView.as_view(), name='verify_register_otp'),

    # ── 🦎 Profil Utilisateur (Endpoint Caméléon) ─────────────────────────────
    # Rappel : S'adapte tout seul au rôle de la personne connectée !
    path('me/', UnifiedProfileView.as_view(), name='user_profile'),

    # ── 🔑 Gestion des mots de passe ──────────────────────────────────────────
    # 1. Pour un utilisateur déjà connecté (Dans les paramètres de son profil)
    path('password/change/', ChangePasswordView.as_view(), name='password_change'),
    
    # 2. Mot de passe oublié (Le flux sécurisé en 3 étapes avec OTP)
    path('password/reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/verify/', PasswordResetVerifyOTPView.as_view(), name='password_reset_verify'),
    path('password/reset/set/', PasswordResetConfirmView.as_view(), name='password_reset_set'),
]