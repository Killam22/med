from rest_framework.test import APITestCase
import uuid
from django.contrib.auth import get_user_model
from pharmacy.models import Pharmacist, PharmacyStock, PharmacyOrder
from pharmacy.serializers import PharmacyOrderCreateSerializer
from medications.models import Medication
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class PharmacySerializerTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.patient_user = User.objects.create_user(username='patient_test', password='pw')
        cls.med = Medication.objects.create(name='TestMed', price_dzd=100)

    def test_direct_purchase_order_creation_success(self):
        """Un achat direct ne demande pas d'ordonnance et doit passer la validation."""
        data = {
            'order_type': PharmacyOrder.OrderType.DIRECT,
            'withdrawal_method': PharmacyOrder.WithdrawalMethod.PATIENT,
            'patient_message': 'Vite svp'
        }
        
        # Simuler un contexte de requête
        class MockRequest:
            def __init__(self, user):
                self.user = user

        serializer = PharmacyOrderCreateSerializer(data=data, context={'request': MockRequest(self.patient_user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['order_type'], PharmacyOrder.OrderType.DIRECT)

    def test_direct_purchase_with_prescription_fails(self):
        """Un achat direct ne doit pas inclure un ID d'ordonnance."""
        data = {
            'prescription': uuid.uuid4(), # Fake ID
            'order_type': PharmacyOrder.OrderType.DIRECT,
        }
        class MockRequest:
            def __init__(self, user):
                self.user = user

        serializer = PharmacyOrderCreateSerializer(data=data, context={'request': MockRequest(self.patient_user)})
        self.assertFalse(serializer.is_valid())
        self.assertIn('prescription', serializer.errors)

    def test_prescription_purchase_without_prescription_fails(self):
        """Une commande d'ordonnance doit inclure l'ID de la prescription."""
        data = {
            'order_type': PharmacyOrder.OrderType.PRESCRIPTION,
            # manquante
        }
        class MockRequest:
            def __init__(self, user):
                self.user = user
                
        serializer = PharmacyOrderCreateSerializer(data=data, context={'request': MockRequest(self.patient_user)})
        self.assertFalse(serializer.is_valid())
        self.assertIn('prescription', serializer.errors)


class PharmacyStockAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pharma_user = User.objects.create_user(username='pharma1', password='pw')
        cls.pharmacist = Pharmacist.objects.create(
            user=cls.pharma_user,
            license_number='LIC-1234',
            pharmacy_name='Pharma Test',
            address='Rue 1',
            city='Alger',
            latitude=36.0,
            longitude=3.0
        )
        cls.med = Medication.objects.create(name='Paracetamol', price_dzd=50)

    def test_create_stock_auto_assigns_pharmacist(self):
        """Créer un stock doit auto-assigner le profil pharmacien de l'utilisateur."""
        self.client.force_authenticate(user=self.pharma_user)
        
        data = {
            'medication': self.med.id,
            'quantity': 50,
            'selling_price': 60.00
        }
        res = self.client.post('/api/pharmacy/stock/', data)
        self.assertEqual(res.status_code, 201)
        
        stock = PharmacyStock.objects.get(id=res.data['id'])
        self.assertEqual(stock.pharmacist, self.pharmacist)

    def test_create_negative_stock_fails(self):
        self.client.force_authenticate(user=self.pharma_user)
        data = {
            'medication': self.med.id,
            'quantity': -5,
            'selling_price': 60.00
        }
        res = self.client.post('/api/pharmacy/stock/', data)
        self.assertEqual(res.status_code, 400)
        self.assertIn('quantity', res.data)

    def test_search_nearby_endpoint(self):
        """Teste la recherche géographique (simulée via latitude non nulle)"""
        # Créer le stock
        PharmacyStock.objects.create(
            pharmacist=self.pharmacist,
            medication=self.med,
            quantity=10,
            selling_price=55.0
        )
        
        self.client.force_authenticate(user=self.pharma_user)
        
        # Test recherche (mock basique attendu par l'API)
        res = self.client.get(f'/api/pharmacy/stock/search-nearby/?medication_id={self.med.id}&lat=36.0&lon=3.0')
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['pharmacy_name'], 'Pharma Test')
        self.assertEqual(data[0]['stock_quantity'], 10)
        self.assertEqual(data[0]['price'], 55.0)

