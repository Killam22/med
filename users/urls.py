# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register,    name='register'),
    path('login/',    views.user_login,  name='user_login'),
    path('logout/',   views.user_logout, name='user_logout'),
   path('password_reset_request/', views.password_reset_request, name='password_reset_request'),
   path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
   path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('verify-register-otp/', views.verify_register_otp, name='verify_register_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('set-new-password/', views.password_reset_set, name='password_reset_set'),
]