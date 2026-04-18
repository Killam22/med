from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from caretaker.models import Caretaker

User = get_user_model()

class CaretakerDashboardTests(APITestCase):
    def setUp(self):
        self.caretaker_user = User.objects.create_user(
            email='caretaker@test.com', username='caretaker', password='mdp', role='caretaker',
            id_card_number='CT123'
        )
        self.caretaker = Caretaker.objects.create(user=self.caretaker_user, availability_area='Alger')

        self.pat_user = User.objects.create_user(
            email='patient@test.com', username='patient', password='mdp', role='patient',
            id_card_number='PAT456'
        )

    def test_caretaker_dashboard_access(self):
        self.client.force_authenticate(user=self.caretaker_user)
        response = self.client.get('/api/caretaker/dashboard/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('my_patients', response.data)
        self.assertIn('pending_requests', response.data)

    def test_unauthorized_access(self):
        self.client.force_authenticate(user=self.pat_user)
        response = self.client.get('/api/caretaker/dashboard/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
