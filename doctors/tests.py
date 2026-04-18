from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from doctors.models import Doctor
from appointments.models import Appointment
from datetime import date, time

User = get_user_model()

class DoctorDashboardTests(APITestCase):
    def setUp(self):
        self.doc_user = User.objects.create_user(
            email='doctor@test.com', username='doctor', password='mdp', role='doctor',
            id_card_number='DOC123'
        )
        self.doctor = Doctor.objects.create(user=self.doc_user, specialty='general', order_number='ORDER123')

        self.pat_user = User.objects.create_user(
            email='patient@test.com', username='patient', password='mdp', role='patient',
            id_card_number='PAT123'
        )

    def test_doctor_dashboard_access(self):
        self.client.force_authenticate(user=self.doc_user)
        response = self.client.get('/api/doctors/dashboard/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('kpis', response.data)
        self.assertIn('todays_schedule', response.data)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=self.pat_user)
        response = self.client.get('/api/doctors/dashboard/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
