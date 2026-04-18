from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time, timedelta
import uuid
from doctors.models import Doctor
from patients.models import Patient
from consultations.models import Consultation
from prescriptions.models import Prescription, PrescriptionItem, QRToken
from medications.models import Medication

User = get_user_model()

class PrescriptionAPITests(APITestCase):
    def setUp(self):
        # 1. Setup Users
        self.doc_user = User.objects.create_user(
            email='doc_rx@test.com', username='doc_rx', password='pw', role='doctor',
            id_card_number='DOC_RX_ID', first_name='John', last_name='Doe', sex='male'
        )
        self.doctor = Doctor.objects.create(user=self.doc_user, specialty='general', order_number='DOC_RX_ORD')

        self.pat_user = User.objects.create_user(
            email='pat_rx@test.com', username='pat_rx', password='pw', role='patient',
            id_card_number='PAT_RX_ID', first_name='Jane', last_name='Smith', sex='female'
        )
        self.patient = Patient.objects.create(user=self.pat_user)

        self.pharma_user = User.objects.create_user(
            email='pharma_rx@test.com', username='pharma_rx', password='pw', role='pharmacist',
            id_card_number='PHARMA_RX_ID', first_name='Paul', last_name='Pharma', sex='male'
        )

        # 2. Setup Consultation
        self.consultation = Consultation.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            chief_complaint="Grosse fatigue",
            consulted_at=timezone.now()
        )

        # 3. Setup Medication
        self.med = Medication.objects.create(name='Vitamin C', molecule='Ascorbic Acid', price_dzd=500)

    def test_doctor_can_create_prescription(self):
        self.client.force_authenticate(user=self.doc_user)
        valid_until = (date.today() + timedelta(days=30)).isoformat()
        data = {
            "consultation": self.consultation.id,
            "notes": "Prendre matin et soir",
            "valid_until": valid_until,
            "items": [
                {
                    "medication": self.med.id,
                    "drug_name": "Vitamin C",
                    "dosage": "1g",
                    "frequency": "2x_day",
                    "duration": "10 days",
                    "quantity": 2
                }
            ]
        }
        response = self.client.post('/api/prescriptions/prescriptions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify QR Token automatic creation (assuming signals or serialiser logic)
        prescription = Prescription.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(prescription, 'qr_token'))

    def test_patient_can_view_own_prescription(self):
        # Manually create a prescription
        rx = Prescription.objects.create(
            consultation=self.consultation,
            valid_until=date.today() + timedelta(days=30)
        )
        
        self.client.force_authenticate(user=self.pat_user)
        response = self.client.get(f'/api/prescriptions/prescriptions/{rx.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['patient_name'], f"{self.pat_user.first_name} {self.pat_user.last_name}")

    def test_pharmacist_can_scan_qr(self):
        # Create prescription
        rx = Prescription.objects.create(
            consultation=self.consultation,
            valid_until=date.today() + timedelta(days=30)
        )
        # QR token was automatically created by signal
        qr = rx.qr_token

        self.client.force_authenticate(user=self.pharma_user)
        data = {"token": qr.token}
        response = self.client.post('/api/prescriptions/prescriptions/scan/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['prescription']['id'], str(rx.id))

    def test_unauthorized_scan(self):
        self.client.force_authenticate(user=self.pat_user)
        response = self.client.post('/api/prescriptions/prescriptions/scan/', {"token": "dummy"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
