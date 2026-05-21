"""
users/views.py
==============
Architecture Healy — 4 piliers :
  1. JWT + LoginRateThrottle (brute-force protection)
  2. Inscription avec OTP email (is_active=False → True)
  3. Profil "Caméléon" — /me/ dispatch par rôle
  4. Mot de passe oublié — flux 3 étapes sécurisé
"""

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import AnonRateThrottle

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core import signing

from .models import EmailOTP
from .utils import send_otp_email, send_welcome_email, notify_admins_new_registration
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterPatientSerializer,
    RegisterDoctorSerializer,
    RegisterPharmacistSerializer,
    RegisterCaretakerSerializer,
    UserSerializer,
    PatientUnifiedSerializer,
    DoctorUnifiedSerializer,
    PharmacistUnifiedSerializer,
    CaretakerUnifiedSerializer,
    ProfileUpdateRequestSerializer,
)
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


class LogoutView(APIView):
    """Blackliste le refresh token côté serveur."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh') or request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'Refresh token requis.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({'error': 'Token invalide ou déjà révoqué.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)

# Sel cryptographique pour les tokens de reset (ne pas changer en prod sans invalider tous les tokens actifs)
_RESET_SALT = 'Healy-password-reset-v1'
_RESET_MAX_AGE = 600  # 10 minutes en secondes


# ── 1. SÉCURITÉ — Throttle & JWT ─────────────────────────────────────────────

class LoginRateThrottle(AnonRateThrottle):
    """Limite à 5 tentatives/minute (configurer 'login' dans DEFAULT_THROTTLE_RATES)."""
    scope = 'login'

class OtpSendThrottle(AnonRateThrottle):
    """Limite l'envoi d'OTP à 5/minute par IP pour éviter le spam."""
    scope = 'otp_send'


class OtpVerifyThrottle(AnonRateThrottle):
    """Limite la vérification d'OTP à 10/minute par IP — anti-brute-force."""
    scope = 'otp_verify'

class CustomTokenObtainPairView(TokenObtainPairView):
    """Endpoint JWT enrichi (role, full_name, email) + protégé par le LoginRateThrottle."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


# ── 2. INSCRIPTION + OTP ─────────────────────────────────────────────────────

# ── 👨‍⚕️ INSCRIPTION PATIENT ─────────────────────────────────────────────────

class RegisterPatientView(generics.CreateAPIView):
    """
    Crée un Patient avec is_active=True et verification_status='pending'.
    Le dossier attend la validation Admin (pas d'OTP post-inscription pour les patients).
    """
    queryset = User.objects.all()
    serializer_class = RegisterPatientSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            notify_admins_new_registration(user)
        except Exception:
            pass


# ── 🩺 INSCRIPTION DOCTEUR ─────────────────────────────────────────────────

class RegisterDoctorView(generics.CreateAPIView):
    """
    Crée un Médecin avec is_active=False et verification_status='pending'.
    L'activation est déclenchée par l'Admin (pas d'OTP post-inscription).
    """
    queryset = User.objects.all()
    serializer_class = RegisterDoctorSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            notify_admins_new_registration(user)
        except Exception:
            pass


# ── 💊 INSCRIPTION PHARMACIEN ──────────────────────────────────────────────

class RegisterPharmacistView(generics.CreateAPIView):
    """
    Crée un Pharmacien et sa Pharmacie avec is_active=False et verification_status='pending'.
    L'activation est déclenchée par l'Admin (pas d'OTP post-inscription).
    """
    queryset = User.objects.all()
    serializer_class = RegisterPharmacistSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            notify_admins_new_registration(user)
        except Exception:
            pass


# ── 🏠 INSCRIPTION GARDE-MALADE (CARETAKER) ────────────────────────────────

class RegisterCaretakerView(generics.CreateAPIView):
    """
    Crée un Garde-malade avec is_active=False et verification_status='pending'.
    L'activation est déclenchée par l'Admin (pas d'OTP post-inscription).
    """
    queryset = User.objects.all()
    serializer_class = RegisterCaretakerSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            notify_admins_new_registration(user)
        except Exception:
            pass


class VerifyRegisterOTPView(APIView):
    """
    Étape 2 de l'inscription :
      POST { email, otp } → is_active passe à True + tokens JWT renvoyés.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpVerifyThrottle]

    def post(self, request):
        email    = request.data.get('email', '').strip()
        otp_code = request.data.get('otp', '').strip()

        if not email or not otp_code:
            return Response(
                {'error': 'Les champs email et otp sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupère l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Aucun compte trouvé pour cet email.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupère l'OTP le plus récent non utilisé
        otp_obj = EmailOTP.objects.filter(
            email=email,
            purpose=EmailOTP.PURPOSE_REGISTER,
            is_used=False,
        ).first()

        if not otp_obj:
            return Response(
                {'error': 'Aucun code valide trouvé. Veuillez vous réinscrire.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.is_expired():
            return Response(
                {'error': 'Le code OTP a expiré (10 minutes). Veuillez vous réinscrire.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if otp_obj.otp != otp_code:
            return Response(
                {'error': 'Code OTP incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Tout est valide → activation du compte
        otp_obj.is_used = True
        otp_obj.save(update_fields=['is_used'])

        user.is_active = True
        user.save(update_fields=['is_active'])

        send_welcome_email(user)

        # Génère les tokens JWT directement
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Compte activé avec succès. Bienvenue sur Healy !',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'email': user.email,
        }, status=status.HTTP_200_OK)
# ── 2b. PRÉ-VÉRIFICATION EMAIL AVANT INSCRIPTION ─────────────────────────────

class SendRegisterOTPView(APIView):
    """
    POST { email } → Génère et envoie un OTP de vérification pour un email non encore inscrit.
    Utilisé côté front avant l'étape 2 du formulaire d'inscription.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpSendThrottle]

    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)

        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'Email requis.'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Un compte existe déjà avec cet email.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            otp_obj = EmailOTP.generate(email=email, purpose=EmailOTP.PURPOSE_REGISTER)
            send_otp_email(email, otp_obj.otp, purpose='register')
        except Exception as e:
            logger.error("Échec envoi OTP register à %s : %s", email, e)
            return Response(
                {'error': "Impossible d'envoyer l'email. Vérifiez votre adresse ou réessayez."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({'message': 'Code envoyé.'}, status=status.HTTP_200_OK)


class VerifyRegisterPreOTPView(APIView):
    """
    POST { email, code } → Vérifie le code OTP sans le marquer comme utilisé
    (l'activation finale reste gérée par VerifyRegisterOTPView après la soumission complète).
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpVerifyThrottle]

    def post(self, request):
        email    = request.data.get('email', '').strip().lower()
        code     = request.data.get('code', '').strip()
        if not email or not code:
            return Response({'error': 'Email et code requis.'}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj = EmailOTP.objects.filter(
            email=email,
            purpose=EmailOTP.PURPOSE_REGISTER,
            is_used=False,
        ).first()

        if not otp_obj or otp_obj.is_expired() or otp_obj.otp != code:
            return Response({'error': 'Code incorrect ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': 'Email vérifié.'}, status=status.HTTP_200_OK)


# ── 3. PROFIL "CAMÉLÉON" ─────────────────────────────────────────────────────

class UnifiedProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/ → retourne le profil complet adapté au rôle de l'utilisateur.
    PATCH /api/users/me/ → met à jour à la fois CustomUser ET le profil médical lié
                            (Patient, Doctor, etc.) en un seul appel.

    Dispatch des sérialiseurs par rôle :
      patient    → PatientUnifiedSerializer
      doctor     → UserSerializer (à enrichir avec DoctorUnifiedSerializer si besoin)
      pharmacist → UserSerializer
      caretaker  → UserSerializer
      admin      → UserSerializer
    """
    permission_classes = [permissions.IsAuthenticated]
    # On n'accepte que le PATCH (mise à jour partielle) et le GET
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        role = self.request.user.role
        dispatch = {
            'patient': PatientUnifiedSerializer,
            'doctor': DoctorUnifiedSerializer,
            'pharmacist': PharmacistUnifiedSerializer,
            'caretaker': CaretakerUnifiedSerializer,
        }
        return dispatch.get(role, UserSerializer)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Force toujours le mode PATCH (partial=True) pour éviter les champs obligatoires
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


# ── 4. MOT DE PASSE OUBLIÉ — Flux 3 étapes ───────────────────────────────────

class PasswordResetRequestView(APIView):
    """
    Étape 1 : POST { email }
    → Génère un OTP de reset et l'envoie par email.
    → Répond toujours 200 (anti-énumération : ne révèle pas si l'email existe).
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpSendThrottle]

    def post(self, request):
        email = request.data.get('email', '').strip()
        GENERIC_MSG = {'message': 'Si cet email est enregistré, un code de réinitialisation vous a été envoyé.'}

        if not email:
            return Response({'error': 'Le champ email est requis.'}, status=status.HTTP_400_BAD_REQUEST)

        # Anti-énumération : même message si l'email n'existe pas
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response(GENERIC_MSG, status=status.HTTP_200_OK)

        try:
            otp_obj = EmailOTP.generate(email=user.email, purpose=EmailOTP.PURPOSE_RESET)
            send_otp_email(user.email, otp_obj.otp, purpose='reset', first_name=user.first_name, last_name=user.last_name)
        except Exception:
            pass  # OTP visible dans la console (backend console.EmailBackend en dev)

        return Response(GENERIC_MSG, status=status.HTTP_200_OK)


class PasswordResetRequestThrottle(AnonRateThrottle):
    scope = 'otp_send'


class PasswordResetVerifyOTPView(APIView):
    """
    Étape 2 : POST { email, otp }
    → Valide l'OTP et retourne un reset_token signé cryptographiquement (10 min).
    Le token encode un hash partiel du mot de passe actuel → usage unique automatique.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpVerifyThrottle]

    def post(self, request):
        email    = request.data.get('email', '').strip()
        otp_code = request.data.get('otp', '').strip()

        if not email or not otp_code:
            return Response(
                {'error': 'Les champs email et otp sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_obj = EmailOTP.objects.filter(
            email=email,
            purpose=EmailOTP.PURPOSE_RESET,
            is_used=False,
        ).first()

        # Validation OTP (existence, expiration, valeur)
        if not otp_obj or otp_obj.is_expired() or otp_obj.otp != otp_code:
            return Response(
                {'error': 'Code OTP invalide ou expiré.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        # Marque l'OTP comme utilisé
        otp_obj.is_used = True
        otp_obj.save(update_fields=['is_used'])

        # Génère un token signé : contient l'email + un extrait unique du hash du MDP.
        # On prend chars 20-52 du hash (après le sel, dans les bytes de dérivation)
        # pour s'assurer que le token devient invalide après changement de MDP.
        pw_fingerprint = user.password[20:52] if len(user.password) > 52 else user.password
        reset_token = signing.dumps(
            {'email': email, 'pw_hash': pw_fingerprint},
            salt=_RESET_SALT,
        )

        return Response({
            'message': 'OTP validé. Utilisez le reset_token pour définir votre nouveau mot de passe.',
            'reset_token': reset_token,
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    Étape 3 : POST { reset_token, new_password, new_password_confirm }
    → Vérifie la signature + l'unicité du token, puis met à jour le mot de passe.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        reset_token          = request.data.get('reset_token', '').strip()
        new_password         = request.data.get('new_password', '')
        new_password_confirm = request.data.get('new_password_confirm', '')

        if not reset_token or not new_password:
            return Response(
                {'error': 'Les champs reset_token et new_password sont requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password_confirm:
            return Response(
                {'error': 'Les mots de passe ne correspondent pas.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Décode et valide le token (vérifie signature + expiration 10 min)
        try:
            data = signing.loads(reset_token, salt=_RESET_SALT, max_age=_RESET_MAX_AGE)
        except signing.SignatureExpired:
            return Response(
                {'error': 'Le token de réinitialisation a expiré (10 minutes). Recommencez.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except signing.BadSignature:
            return Response(
                {'error': 'Token de réinitialisation invalide ou altéré.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        email = data.get('email')
        stored_pw_hash = data.get('pw_hash')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur introuvable.'}, status=status.HTTP_400_BAD_REQUEST)

        # Vérifie que le mot de passe n'a pas déjà été changé (= usage unique du token)
        pw_fingerprint = user.password[20:52] if len(user.password) > 52 else user.password
        if pw_fingerprint != stored_pw_hash:
            return Response(
                {'error': 'Ce token a déjà été utilisé. Recommencez la procédure de réinitialisation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Valide la complexité du nouveau mot de passe (AUTH_PASSWORD_VALIDATORS de settings.py)
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response({'error': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return Response(
            {'message': 'Mot de passe réinitialisé avec succès. Vous pouvez vous connecter.'},
            status=status.HTTP_200_OK
        )
class ChangePasswordView(APIView):
    """
    Vue pour changer le mot de passe d'un utilisateur connecté.
    Requiert l'ancien mot de passe pour validation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        new_password_confirm = request.data.get("new_password_confirm")

        # 1. Vérification de l'ancien mot de passe (Sécurité critique)
        if not user.check_password(old_password):
            return Response(
                {"old_password": ["L'ancien mot de passe est incorrect."]}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Vérification de la correspondance
        if new_password != new_password_confirm:
            return Response(
                {"new_password": ["Les deux nouveaux mots de passe ne correspondent pas."]}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validation de la complexité (selon tes règles dans settings.py)
        try:
            validate_password(new_password, user=user)
        except ValidationError as exc:
            return Response(
                {"new_password": list(exc.messages)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Mise à jour sécurisée (hachage automatique)
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Votre mot de passe a été mis à jour avec succès."}, 
            status=status.HTTP_200_OK
        )


class RequestProfileUpdateView(generics.CreateAPIView):
    """
    Permet à l'utilisateur de soumettre une demande de changement de nom/prénom.
    GET  → retourne les demandes de l'utilisateur connecté
    POST → soumet une nouvelle demande
    """
    serializer_class = ProfileUpdateRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import ProfileUpdateRequest
        qs = ProfileUpdateRequest.objects.filter(user=request.user).order_by('-created_at')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Vérifie s'il y a déjà une demande en attente
        from .models import ProfileUpdateRequest
        if ProfileUpdateRequest.objects.filter(user=self.request.user, status='pending').exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Vous avez déjà une demande de changement de profil en attente.")
            
        serializer.save(user=self.request.user)
