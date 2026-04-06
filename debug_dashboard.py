import os
import django
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from dashboard.views import DoctorDashboardView
from doctors.models import Doctor

User = get_user_model()

def run_debug():
    factory = APIRequestFactory()
    user = User.objects.get(email='doctor@test.com') # Assuming it exists from previous fails or create one
    if not user:
        user = User.objects.create_user(email='doctor@test.com', username='doctor_dbg', password='password123', role='doctor')
        Doctor.objects.get_or_create(user=user, license_number='DBG123')

    view = DoctorDashboardView.as_view()
    request = factory.get('/api/dashboard/doctor/')
    force_authenticate(request, user=user)
    
    try:
        response = view(request)
        print(f"Status: {response.status_code}")
        print(f"Data: {response.data}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()
