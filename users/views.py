from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate

from .models import CustomUser, EmailOTP
from .serializers import RegisterSerializer, UserSerializer
from .utils import send_otp_email


# ── Register — Step 1: collect details & send OTP ─────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            otp_obj = EmailOTP.generate(user.email, EmailOTP.PURPOSE_REGISTER)
            send_otp_email(user.email, otp_obj.otp, 'register')
            return Response(
                {"message": "OTP sent to your email.", "email": user.email},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Register — Step 2: verify OTP & activate user ─────────────────────────────

class VerifyRegisterOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp   = request.data.get('otp')

        if not email or not otp:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp_obj = EmailOTP.objects.filter(
                email=email, purpose=EmailOTP.PURPOSE_REGISTER, is_used=False
            ).latest('created_at')
        except EmailOTP.DoesNotExist:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({"error": "OTP expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.otp != otp:
            return Response({"error": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save()

        user = CustomUser.objects.get(email=email)
        user.is_active = True
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Account verified successfully.",
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user":    UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


# ── Resend OTP ─────────────────────────────────────────────────────────────────

class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email   = request.data.get('email')
        purpose = request.data.get('purpose')

        if not email or purpose not in (EmailOTP.PURPOSE_REGISTER, EmailOTP.PURPOSE_RESET):
            return Response({"error": "Valid email and purpose are required."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj = EmailOTP.generate(email, purpose)
        send_otp_email(email, otp_obj.otp, purpose)
        return Response({"message": "OTP resent successfully."}, status=status.HTTP_200_OK)


# ── Login ──────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account not verified yet."}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            "access":  str(refresh.access_token),
            "refresh": str(refresh),
            "user":    UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


# ── Logout ─────────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


# ── Password Reset — Step 1: send OTP ─────────────────────────────────────────

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Don't reveal if email exists
        if CustomUser.objects.filter(email=email, is_active=True).exists():
            otp_obj = EmailOTP.generate(email, EmailOTP.PURPOSE_RESET)
            send_otp_email(email, otp_obj.otp, 'reset')

        return Response({"message": "If this email exists, an OTP has been sent."}, status=status.HTTP_200_OK)


# ── Password Reset — Step 2: verify OTP ───────────────────────────────────────

class VerifyResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp   = request.data.get('otp')

        try:
            otp_obj = EmailOTP.objects.filter(
                email=email, purpose=EmailOTP.PURPOSE_RESET, is_used=False
            ).latest('created_at')
        except EmailOTP.DoesNotExist:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.is_expired():
            return Response({"error": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST)

        if otp_obj.otp != otp:
            return Response({"error": "Incorrect OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save()

        # Give a short-lived token to authorize the password reset
        user = CustomUser.objects.get(email=email)
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "OTP verified.",
            "reset_token": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


# ── Password Reset — Step 3: set new password ─────────────────────────────────

class PasswordResetSetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password         = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        if not password or password != confirm_password:
            return Response({"error": "Passwords do not match."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(password)
        request.user.save()
        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)