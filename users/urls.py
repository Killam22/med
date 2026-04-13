from django.urls import path
from .views import (
    RegisterView, VerifyRegisterOTPView, ResendOTPView,
    LoginView, LogoutView,
    PasswordResetRequestView, VerifyResetOTPView, PasswordResetSetView,
)

urlpatterns = [
    path('register/',               RegisterView.as_view(),            name='register'),
    path('verify-register-otp/',    VerifyRegisterOTPView.as_view(),   name='verify_register_otp'),
    path('resend-otp/',             ResendOTPView.as_view(),           name='resend_otp'),
    path('login/',                  LoginView.as_view(),               name='login'),
    path('logout/',                 LogoutView.as_view(),              name='logout'),
    path('password-reset-request/', PasswordResetRequestView.as_view(),name='password_reset_request'),
    path('verify-reset-otp/',       VerifyResetOTPView.as_view(),     name='verify_reset_otp'),
    path('password-reset-set/',     PasswordResetSetView.as_view(),   name='password_reset_set'),
]