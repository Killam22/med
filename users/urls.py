from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    RegisterPatientView,
    RegisterDoctorView,
    UserProfileView
)

urlpatterns = [
    # Auth
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Registration
    path('register/patient/', RegisterPatientView.as_view(), name='register_patient'),
    path('register/doctor/', RegisterDoctorView.as_view(), name='register_doctor'),
    
    # User Profile
    path('me/', UserProfileView.as_view(), name='user_profile'),
]
