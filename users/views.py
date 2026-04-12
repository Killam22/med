from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from .serializers import (
    CustomTokenObtainPairSerializer, 
    RegisterPatientSerializer, 
    RegisterDoctorSerializer,
    UserSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

class RegisterPatientView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterPatientSerializer
    permission_classes = [permissions.AllowAny]

class RegisterDoctorView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterDoctorSerializer
    permission_classes = [permissions.AllowAny]

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
