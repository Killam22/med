"""
users/tests.py
==============
Suite de tests complète pour l'application Users de MedSmart.
Couvre les 4 piliers architecturaux :
  1. Sécurité (Throttle JWT)
  2. Inscription + Vérification OTP
  3. Profil "Caméléon" (/me/)
  4. Flux Mot de Passe Oublié (3 étapes)

NOTE DE COMPATIBILITÉ (Python 3.14 + Django 4.2) :
  @override_settings(DEBUG=False, LOGGING_CONFIG=None) est appliqué sur
  chaque classe de test pour contourner le bug Python 3.14 où
  django.template.context.__copy__() échoue quand Django tente de rendre
  la page d'erreur debug (500) lors d'une exception dans une vue.
  Sans ce patch, les ERRORs de test masquent la vraie exception.
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import EmailOTP
from patients.models import Patient

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Settings globaux pour tous les tests
# ─────────────────────────────────────────────────────────────────────────────
# • DEBUG=False → désactive le rendu du template Django debug (bug Python 3.14)
# • LOGGING_CONFIG=None → supprime le handler AdminEmailHandler qui crash aussi
# • DEFAULT_THROTTLE_CLASSES=[] → isolé par classe selon le besoin
TEST_SETTINGS = dict(
    DEBUG=False,
    LOGGING_CONFIG=None,
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_access_token(user):
    """Génère un access token JWT directement pour un user (sans appel HTTP)."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


def make_active_patient(email=None, password="Str0ngPass!"):
    """
    Crée un Patient actif prêt à se connecter.
    IMPORTANT : username = email (car CustomUser utilise email comme identifiant unique).
    """
    email = email or f"patient_{uuid.uuid4().hex[:6]}@test.com"
    user = User.objects.create_user(
        username=email,        # SimpleJWT s'authentifie via username par défaut
        email=email,
        password=password,
        first_name="Test",
        last_name="Patient",
        role="patient",
        is_active=True,
    )
    Patient.objects.get_or_create(user=user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# 1. TESTS D'INSCRIPTION + VERIFICATION OTP
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(
    DEBUG=False,
    LOGGING_CONFIG=None,
    DEFAULT_THROTTLE_CLASSES=[],
    DEFAULT_THROTTLE_RATES={},
)
class PatientRegistrationFlowTest(APITestCase):
    """
    Teste le flux complet :
      POST /register/patient/ → compte inactif + OTP créé (email mocké)
      POST /verify-otp/       → compte activé + tokens renvoyés
    """

    def setUp(self):
        self.register_url = reverse('register_patient')
        self.verify_url   = reverse('verify_register_otp')

        self.valid_payload = {
            "email": "nouveau.patient@medsmart.dz",
            "first_name": "Amira",
            "last_name": "Boudiaf",
            "password": "Str0ngPass!2024",
            "password_confirm": "Str0ngPass!2024",
            "phone": "0555123456",
        }

    # ── Test 1.1 : L'inscription crée un compte inactif ──────────────────────
    @patch('users.views.send_otp_email')
    def test_register_creates_inactive_user(self, mock_send):
        """
        ATTENDU : HTTP 201, is_active=False en DB, un EmailOTP créé,
                  email envoyé exactement une fois.
        """
        response = self.client.post(self.register_url, self.valid_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         msg=f"Réponse inattendue : {response.data}")

        user = User.objects.get(email=self.valid_payload['email'])
        self.assertEqual(user.role, 'patient')
        self.assertFalse(user.is_active,
                         msg="Le compte doit être inactif jusqu'à la vérification OTP.")
        self.assertTrue(Patient.objects.filter(user=user).exists(),
                        msg="Le profil Patient doit être créé en même temps.")

        otp_exists = EmailOTP.objects.filter(
            email=self.valid_payload['email'],
            purpose=EmailOTP.PURPOSE_REGISTER,
        ).exists()
        self.assertTrue(otp_exists, msg="Un EmailOTP doit exister après l'inscription.")
        mock_send.assert_called_once()

    # ── Test 1.2 : Flux complet inscription → activation OTP ─────────────────
    @patch('users.views.send_otp_email')
    def test_verify_otp_activates_account_and_returns_tokens(self, mock_send):
        """
        ATTENDU : après POST /verify-otp/ avec le bon OTP,
                  is_active passe à True et la réponse contient 'access'.
        """
        self.client.post(self.register_url, self.valid_payload)

        user = User.objects.get(email=self.valid_payload['email'])
        otp_obj = EmailOTP.objects.filter(
            email=user.email, purpose=EmailOTP.PURPOSE_REGISTER
        ).first()
        self.assertIsNotNone(otp_obj, "L'OTP doit exister après l'inscription.")

        response = self.client.post(self.verify_url, {
            "email": user.email,
            "otp": otp_obj.otp,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"Vérification OTP échouée : {response.data}")

        user.refresh_from_db()
        self.assertTrue(user.is_active,
                        msg="Le compte doit être activé après validation de l'OTP.")
        self.assertIn('access', response.data,
                      msg="Un token d'accès doit être retourné après vérification.")

    # ── Test 1.3 : Un mauvais OTP est rejeté ─────────────────────────────────
    @patch('users.views.send_otp_email')
    def test_wrong_otp_returns_400(self, mock_send):
        """ATTENDU : HTTP 400 avec un code OTP incorrect."""
        self.client.post(self.register_url, self.valid_payload)

        response = self.client.post(self.verify_url, {
            "email": self.valid_payload['email'],
            "otp": "000000",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Test 1.4 : Login impossible si is_active=False ────────────────────────
    @patch('users.views.send_otp_email')
    def test_inactive_user_cannot_login(self, mock_send):
        """
        ATTENDU : HTTP 401 si l'utilisateur essaie de se connecter
                  avant d'avoir validé son OTP (is_active=False).
        SimpleJWT refuse automatiquement les comptes inactifs.
        """
        self.client.post(self.register_url, self.valid_payload)

        login_url = reverse('token_obtain_pair')
        response = self.client.post(login_url, {
            "email": self.valid_payload['email'],
            "password": self.valid_payload['password'],
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED,
                         msg="Un compte non vérifié ne doit pas pouvoir se connecter.")

    # ── Test 1.5 : Mots de passe non concordants ─────────────────────────────
    def test_register_with_mismatched_passwords_returns_400(self):
        """ATTENDU : HTTP 400 si password != password_confirm."""
        payload = {**self.valid_payload, "password_confirm": "DifferentPass!"}
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────────────────────────────────────
# 2. TESTS DE SÉCURITÉ — THROTTLE (Rate Limiting)
# ─────────────────────────────────────────────────────────────────────────────

class LoginThrottleTest(APITestCase):
    """
    Vérifie que le LoginRateThrottle bloque correctement après
    5 tentatives (configuré dans settings.py : 'login': '5/minute').

    Note : ce test DOIT tourner avec le throttle actif (pas d'override).
    Il utilise son propre TestCase isolé pour éviter les fuites de compteurs.
    """

    def setUp(self):
        self.login_url = reverse('token_obtain_pair')
        cache.clear()  # évite la contamination du throttle entre tests

    def test_login_throttled_after_5_failed_attempts(self):
        """
        SCÉNARIO : 5 requêtes consécutives → throttle déclenché.
        On accepte que la limite soit atteinte entre les tentatives 5 et 6.
        """
        bad_creds = {
            "email": "inexistant@test.com",
            "password": "WrongPassword123!",
        }
        responses = []
        for i in range(6):
            r = self.client.post(self.login_url, bad_creds)
            responses.append(r.status_code)

        # Au moins une réponse doit être 429
        self.assertIn(
            status.HTTP_429_TOO_MANY_REQUESTS, responses,
            msg=(
                f"Attendu au moins un 429 dans les 6 tentatives. "
                f"Status codes obtenus : {responses}. "
                "Vérifiez que le cache est configuré et 'login': '5/minute' est dans les settings."
            )
        )

    @override_settings(DEBUG=False, LOGGING_CONFIG=None,
                       DEFAULT_THROTTLE_CLASSES=[], DEFAULT_THROTTLE_RATES={})
    def test_successful_login_not_throttled_early(self):
        """
        ATTENDU : un utilisateur légitime peut se connecter
                  sans être bloqué (throttle désactivé pour ce test).
        """
        user = make_active_patient(email="legit@test.com")

        response = self.client.post(self.login_url, {
            "email": "legit@test.com",
            "password": "Str0ngPass!",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"Connexion légitime bloquée : {response.data}")
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data.get('role'), 'patient')


# ─────────────────────────────────────────────────────────────────────────────
# 3. TESTS DU PROFIL "CAMÉLÉON" — /api/users/me/
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(DEBUG=False, LOGGING_CONFIG=None,
                   DEFAULT_THROTTLE_CLASSES=[], DEFAULT_THROTTLE_RATES={})
class ChameleonProfileViewTest(APITestCase):
    """
    Teste UnifiedProfileView (GET + PATCH sur /me/).
    Vérifie que le sérialiseur adapté au rôle est utilisé.
    """

    def setUp(self):
        self.me_url = reverse('user_profile')

        self.patient_user = make_active_patient(email="cameo_patient@test.com")
        self.patient_profile = Patient.objects.get(user=self.patient_user)
        self.patient_profile.medical_history = "Diabète type 2"
        self.patient_profile.blood_group = "A+"
        self.patient_profile.save()

        token = get_access_token(self.patient_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ── Test 3.1 : GET /me/ inclut les données du profil patient ─────────────
    def test_get_me_includes_patient_profile_data(self):
        """
        ATTENDU : la réponse JSON contient 'patient_profile' avec
                  les champs du modèle Patient.
        """
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"GET /me/ échoué : {response.data}")
        self.assertIn('patient_profile', response.data,
                      msg="Le champ 'patient_profile' doit être présent pour un patient.")
        self.assertIsNotNone(response.data['patient_profile'],
                             msg="patient_profile ne doit pas être null.")

    # ── Test 3.2 : GET /me/ sans authentification → 401 ─────────────────────
    def test_get_me_unauthenticated_returns_401(self):
        """ATTENDU : HTTP 401 si l'Authorization header est absent."""
        self.client.credentials()
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Test 3.3 : PATCH /me/ met à jour les infos de base ───────────────────
    def test_patch_me_updates_user_base_fields(self):
        """ATTENDU : PATCH avec first_name mis à jour est persisté en DB."""
        response = self.client.patch(self.me_url, {"first_name": "Fatima"})

        self.assertIn(response.status_code,
                      [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT],
                      msg=f"PATCH /me/ échoué : {response.data}")

        self.patient_user.refresh_from_db()
        self.assertEqual(self.patient_user.first_name, "Fatima",
                         msg="Le prénom n'a pas été mis à jour en DB.")

    # ── Test 3.4 : PATCH /me/ met à jour le profil médical ───────────────────
    def test_patch_me_updates_patient_profile_nested(self):
        """
        ATTENDU : PATCH avec patient_profile imbriqué met à jour le modèle Patient.
        """
        update_payload = {
            "patient_profile": {
                "medical_history": "Hypertension artérielle",
            }
        }
        response = self.client.patch(self.me_url, update_payload, format='json')

        self.assertIn(response.status_code,
                      [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT],
                      msg=f"PATCH imbriqué échoué : {response.data}")

        self.patient_profile.refresh_from_db()
        self.assertEqual(self.patient_profile.medical_history, "Hypertension artérielle")


# ─────────────────────────────────────────────────────────────────────────────
# 4. TESTS DU FLUX MOT DE PASSE OUBLIÉ (3 ÉTAPES)
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(DEBUG=False, LOGGING_CONFIG=None,
                   DEFAULT_THROTTLE_CLASSES=[], DEFAULT_THROTTLE_RATES={})
class PasswordResetFlowTest(APITestCase):
    """
    Teste le flux complet en 3 étapes :
      Étape 1 — POST /password-reset/request/ → OTP envoyé par email
      Étape 2 — POST /password-reset/verify/  → OTP validé, reset_token renvoyé
      Étape 3 — POST /password-reset/confirm/ → nouveau mot de passe défini
    """

    def setUp(self):
        self.user = make_active_patient(
            email="oubli@medsmart.dz",
            password="AncienMotDePasse!1",
        )
        self.request_url = reverse('password_reset_request')
        self.verify_url  = reverse('password_reset_verify')
        self.confirm_url = reverse('password_reset_confirm')

    # ── Test 4.1 : Demande de reset → OTP créé, email envoyé ─────────────────
    @patch('users.views.send_otp_email')
    def test_password_reset_request_sends_otp(self, mock_send):
        """
        ATTENDU : HTTP 200, un EmailOTP de type 'reset' créé en DB,
                  email envoyé une seule fois.
        """
        response = self.client.post(self.request_url, {"email": self.user.email})

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"Demande de reset échouée : {response.data}")

        otp_exists = EmailOTP.objects.filter(
            email=self.user.email,
            purpose=EmailOTP.PURPOSE_RESET,
            is_used=False,
        ).exists()
        self.assertTrue(otp_exists, msg="Un OTP de reset doit être créé en DB.")
        mock_send.assert_called_once()

    # ── Test 4.2 : Email inconnu → DOIT répondre 200 (anti-énumération) ──────
    @patch('users.views.send_otp_email')
    def test_password_reset_request_unknown_email_returns_200(self, mock_send):
        """
        BEST PRACTICE : ne pas révéler si l'email existe ou non.
        ATTENDU : HTTP 200 même pour un email inexistant, sans email envoyé.
        """
        response = self.client.post(self.request_url,
                                    {"email": "inexistant@nowhere.dz"})
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg="Un email inconnu ne doit pas lever une 404.")
        mock_send.assert_not_called()

    # ── Test 4.3 : Vérification OTP → reset_token renvoyé ────────────────────
    @patch('users.views.send_otp_email')
    def test_password_reset_verify_otp_returns_reset_token(self, mock_send):
        """
        ATTENDU : après validation de l'OTP, la réponse contient 'reset_token'.
        """
        self.client.post(self.request_url, {"email": self.user.email})

        otp_obj = EmailOTP.objects.filter(
            email=self.user.email, purpose=EmailOTP.PURPOSE_RESET
        ).first()

        response = self.client.post(self.verify_url, {
            "email": self.user.email,
            "otp": otp_obj.otp,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"Vérification OTP reset échouée : {response.data}")
        self.assertIn('reset_token', response.data,
                      msg="Un reset_token doit être renvoyé après OTP valide.")

    # ── Test 4.4 : Flux complet E2E — changement du mot de passe ─────────────
    @patch('users.views.send_otp_email')
    def test_full_password_reset_flow(self, mock_send):
        """
        SCÉNARIO BOUT EN BOUT :
          1. Demande → OTP créé.
          2. Vérification OTP → reset_token.
          3. Nouveau mot de passe → login réussi avec le nouveau mot de passe.
        """
        NEW_PASSWORD = "NouveauMotDePasse!2024"

        # Étape 1
        self.client.post(self.request_url, {"email": self.user.email})
        otp_obj = EmailOTP.objects.filter(
            email=self.user.email, purpose=EmailOTP.PURPOSE_RESET
        ).first()
        self.assertIsNotNone(otp_obj)

        # Étape 2
        verify_response = self.client.post(self.verify_url, {
            "email": self.user.email,
            "otp": otp_obj.otp,
        })
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        reset_token = verify_response.data.get('reset_token')
        self.assertIsNotNone(reset_token)

        # Étape 3
        confirm_response = self.client.post(self.confirm_url, {
            "reset_token": reset_token,
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        })
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK,
                         msg=f"Confirmation de reset échouée : {confirm_response.data}")

        # Login avec le nouveau mot de passe
        login_url = reverse('token_obtain_pair')
        login_response = self.client.post(login_url, {
            "email": self.user.email,
            "password": NEW_PASSWORD,
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK,
                         msg="Login avec le nouveau mot de passe doit réussir.")
        self.assertIn('access', login_response.data)

    # ── Test 4.5 : reset_token déjà utilisé est rejeté ───────────────────────
    @patch('users.views.send_otp_email')
    def test_reset_token_cannot_be_reused(self, mock_send):
        """
        ATTENDU : utiliser deux fois le même reset_token retourne 400.
        Le token encode pw_hash → invalide dès que le MDP change.
        """
        NEW_PASSWORD_1 = "Premier!MotDePasse2024"
        NEW_PASSWORD_2 = "Deuxieme!MotDePasse2024"

        self.client.post(self.request_url, {"email": self.user.email})
        otp_obj = EmailOTP.objects.filter(
            email=self.user.email, purpose=EmailOTP.PURPOSE_RESET
        ).first()
        verify_resp = self.client.post(self.verify_url, {
            "email": self.user.email, "otp": otp_obj.otp
        })
        reset_token = verify_resp.data.get('reset_token')

        # Première utilisation → succès
        self.client.post(self.confirm_url, {
            "reset_token": reset_token,
            "new_password": NEW_PASSWORD_1,
            "new_password_confirm": NEW_PASSWORD_1,
        })

        # Deuxième utilisation → doit être rejetée (pw_hash ne correspond plus)
        second_response = self.client.post(self.confirm_url, {
            "reset_token": reset_token,
            "new_password": NEW_PASSWORD_2,
            "new_password_confirm": NEW_PASSWORD_2,
        })
        self.assertIn(second_response.status_code,
                      [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
                      msg="Un reset_token déjà utilisé doit être rejeté.")

    # ── Test 4.6 : OTP expiré est rejeté ─────────────────────────────────────
    @patch('users.views.send_otp_email')
    def test_expired_otp_returns_400(self, mock_send):
        """
        Simule un OTP dont la date de création est de 11 minutes.
        ATTENDU : HTTP 400 avec un message d'erreur approprié.
        """
        self.client.post(self.request_url, {"email": self.user.email})
        otp_obj = EmailOTP.objects.filter(
            email=self.user.email, purpose=EmailOTP.PURPOSE_RESET
        ).first()

        # Simule l'expiration
        EmailOTP.objects.filter(pk=otp_obj.pk).update(
            created_at=timezone.now() - timezone.timedelta(minutes=11)
        )

        response = self.client.post(self.verify_url, {
            "email": self.user.email,
            "otp": otp_obj.otp,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                         msg="Un OTP expiré doit retourner 400.")


# ─────────────────────────────────────────────────────────────────────────────
# 5. TESTS DU CUSTOM TOKEN (Payload JWT enrichi)
# ─────────────────────────────────────────────────────────────────────────────

@override_settings(DEBUG=False, LOGGING_CONFIG=None,
                   DEFAULT_THROTTLE_CLASSES=[], DEFAULT_THROTTLE_RATES={})
class CustomTokenPayloadTest(APITestCase):
    """
    Vérifie que le CustomTokenObtainPairSerializer enrichit correctement
    le payload JWT et la réponse de login.
    """

    def setUp(self):
        self.login_url = reverse('token_obtain_pair')
        self.user = make_active_patient(email="token_test@medsmart.dz")

    def test_login_response_contains_role_and_full_name(self):
        """
        ATTENDU : la réponse de /token/ contient 'role', 'full_name', 'email'
                  en plus des tokens standard.
        NOTE : SimpleJWT utilise 'username' comme champ d'authentification par défaut.
               Ici username == email (défini dans make_active_patient).
        """
        response = self.client.post(self.login_url, {
            "email": "token_test@medsmart.dz",
            "password": "Str0ngPass!",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         msg=f"Login échoué : {response.data}")

        for field in ['access', 'refresh', 'role', 'full_name', 'email']:
            self.assertIn(field, response.data,
                          msg=f"Le champ '{field}' est absent de la réponse JWT.")

        self.assertEqual(response.data['role'], 'patient')
        self.assertEqual(response.data['email'], self.user.email)
