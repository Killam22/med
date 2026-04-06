from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from caretaker.models import Caretaker, CareRequest, CareMessage

User = get_user_model()

class CaretakerAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # Création des utilisateurs
        cls.patient_user = User.objects.create_user(username='patient_test', email='patient@test.com', password='pw', role='patient')
        cls.pharma_user = User.objects.create_user(username='pharma', email='pharma@test.com', password='pw', role='pharmacist')
        
        cls.ct_user_1 = User.objects.create_user(username='caretaker_1', email='ct1@test.com', password='pw', role='caretaker')
        cls.ct_user_2 = User.objects.create_user(username='caretaker_2', email='ct2@test.com', password='pw', role='caretaker')
        cls.ct_user_unverified = User.objects.create_user(username='caretaker_unverified', email='ctu@test.com', password='pw', role='caretaker')

        # Création des profils Caretaker
        cls.caretaker_active = Caretaker.objects.create(
            user=cls.ct_user_1, 
            certification='Diplôme Infirmier', 
            is_verified=True, 
            is_available=True
        )
        
        cls.caretaker_inactive = Caretaker.objects.create(
            user=cls.ct_user_2, 
            certification='Aide Soignant', 
            is_verified=True, 
            is_available=False
        )

        cls.caretaker_unverified = Caretaker.objects.create(
            user=cls.ct_user_unverified,
            certification='En attente',
            is_verified=False,
            is_available=True
        )

    def test_search_caretaker_filters(self):
        """Un patient ne trouve que les gardes-malades vérifiés et disponibles."""
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get('/api/caretaker/search/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Gestion de la pagination éventuelle
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.caretaker_active.id)

    def test_create_care_request_success(self):
        """Un patient peut créer une demande pour un garde-malade disponible."""
        self.client.force_authenticate(user=self.patient_user)
        data = {
            'caretaker': self.caretaker_active.id,
            'start_date': '2026-05-01',
            'patient_message': 'J\'ai besoin d\'aide à domicile'
        }
        response = self.client.post('/api/caretaker/requests/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], CareRequest.Status.PENDING)
        self.assertEqual(response.data['patient'], self.patient_user.id) # Auto-assignation réussie
        self.assertEqual(response.data['patient_medical_dossier']['access_granted'], False)

    def test_create_care_request_inactive_caretaker_fails(self):
        """Une demande vers un garde-malade indisponible est refusée par la sécurité."""
        self.client.force_authenticate(user=self.patient_user)
        data = {
            'caretaker': self.caretaker_inactive.id,
            'start_date': '2026-05-01',
            'patient_message': 'Hello'
        }
        response = self.client.post('/api/caretaker/requests/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('caretaker', response.data)

    def test_respond_to_offer_security(self):
        """Validation des droits pour accepter une offre et accès au dossier médical."""
        # Setup Request
        care_request = CareRequest.objects.create(
            patient=self.patient_user,
            caretaker=self.caretaker_active,
            start_date='2026-05-01',
            patient_message='Besoin de vous'
        )

        # HACK: Le patient essaie d'accepter sa propre requête (doit échouer)
        self.client.force_authenticate(user=self.patient_user)
        response_hack = self.client.post(f'/api/caretaker/requests/{care_request.id}/respond_to_offer/', {'status': 'accepted'})
        self.assertEqual(response_hack.status_code, status.HTTP_403_FORBIDDEN)

        # GET: Le garde-malade lit la demande (avant d'accepter) -> Pas d'accès médical
        self.client.force_authenticate(user=self.ct_user_1)
        response_get_before = self.client.get(f'/api/caretaker/requests/{care_request.id}/')
        self.assertEqual(response_get_before.data['patient_medical_dossier']['access_granted'], False)

        # SUCCESS: Le vrai garde-malade accepte
        response_accept = self.client.post(f'/api/caretaker/requests/{care_request.id}/respond_to_offer/', {'status': 'accepted'})
        self.assertEqual(response_accept.status_code, status.HTTP_200_OK)

        # GET: Le garde-malade relit la demande (après avoir accepté) -> Accès Ok
        response_get_after = self.client.get(f'/api/caretaker/requests/{care_request.id}/')
        self.assertEqual(response_get_after.data['patient_medical_dossier']['access_granted'], True)

    def test_send_message_feature(self):
        """Test de la messagerie instantanée"""
        care_request = CareRequest.objects.create(
            patient=self.patient_user,
            caretaker=self.caretaker_active,
            start_date='2026-05-01'
        )
        
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(f'/api/caretaker/requests/{care_request.id}/send_message/', {'content': 'Bonjour!'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Bonjour!')
        self.assertEqual(response.data['sender'], self.patient_user.id)
