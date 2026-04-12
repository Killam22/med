from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views  # 🔥 IMPORTANT

urlpatterns = [
    path('', lambda request: redirect('user_login')),
    path('admin/', admin.site.urls),

    path('users/',    include('users.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/',  include('doctors.urls')),
     path('api/settings/', include('settings.urls'))
    
]