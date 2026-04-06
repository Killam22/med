from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, timedelta

from appointments.models import Appointment
from patients.models import Patient
from doctors.models import Doctor
from pharmacy.models import Pharmacist, PharmacyOrder, PharmacyStock
from caretaker.models import Caretaker, CareRequest
from notifications.models import Notification
from consultations.models import Consultation

User = get_user_model()

class DashboardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pwd = 'password123'
        
        # Patient
        self.patient_user = User.objects.create_user(
            email='patient@test.com', username='patient', password=self.pwd, role='patient'
        )
        self.patient_profile = Patient.objects.create(user=self.patient_user, blood_group='O+')
        
        # Doctor
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com', username='doctor', password=self.pwd, role='doctor', 
            verification_status='verified'
        )
        self.doctor_profile = Doctor.objects.create(
            user=self.doctor_user, specialty='Généraliste', license_number='DOC123'
        )
        
        self.other_doctor_user = User.objects.create_user(
            email='otherdoc@test.com', username='otherdoc', password=self.pwd, role='doctor'
        )
        self.other_doctor_profile = Doctor.objects.create(
            user=self.other_doctor_user, specialty='Chirurgien', license_number='DOC456'
        )
        
        # Pharmacist
        self.pharmacist_user = User.objects.create_user(
            email='pharma@test.com', username='pharma', password=self.pwd, role='pharmacist'
        )
        self.pharma_profile = Pharmacist.objects.create(
            user=self.pharmacist_user, pharmacy_name='Ma Pharmacie', license_number='PH123', address='Test Address'
        )
        
        # Admin
        self.admin_user = User.objects.create_user(
            email='admin@test.com', username='admin', password=self.pwd, role='admin', is_staff=True
        )

    def test_unauthenticated_access_denied(self):
        endpoints = [
            '/api/dashboard/patient/',
            '/api/dashboard/doctor/',
            '/api/dashboard/pharmacist/',
            '/api/dashboard/caretaker/',
            '/api/dashboard/admin/',
        ]
        for url in endpoints:
            response = self.client.get(url, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_isolation(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get('/api/dashboard/doctor/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_dashboard_kpis(self):
        today = timezone.now().date()
        Appointment.objects.create(
            patient=self.patient_profile, doctor=self.doctor_profile, 
            date=today, start_time=time(9,0), end_time=time(9,30), status='confirmed'
        )
        Appointment.objects.create(
            patient=self.patient_profile, doctor=self.doctor_profile, 
            date=today, start_time=time(10,0), end_time=time(10,30), status='completed'
        )
        Appointment.objects.create(
            patient=self.patient_profile, doctor=self.doctor_profile, 
            date=today + timedelta(days=1), start_time=time(11,0), end_time=time(11,30), status='pending'
        )

        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get('/api/dashboard/doctor/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['kpis']['today_consultations'], 2)
        self.assertEqual(response.data['kpis']['pending_requests'], 1)

    def test_pharmacist_dashboard_revenue(self):
        today = timezone.now().date()
        PharmacyOrder.objects.create(
            patient=self.patient_user, pharmacist=self.pharmacist_user, 
            status='delivered', total_price=150.50
        )
        PharmacyOrder.objects.create(
            patient=self.patient_user, pharmacist=self.pharmacist_user, 
            status='delivered', total_price=49.50
        )

        self.client.force_authenticate(user=self.pharmacist_user)
        response = self.client.get('/api/dashboard/pharmacist/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Revenue should be 200.0
        self.assertEqual(float(response.data['kpis']['today_revenue']), 200.0)
