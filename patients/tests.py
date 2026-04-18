from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from datetime import date, time
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class DoctorPatientsTests(APITestCase):
    def setUp(self):
        # Création des utilisateurs "doctor"
        self.doc_user1 = User.objects.create_user(
            email='doc1@test.com', username='doc1', password='mdp', role='doctor', 
            id_card_number='DOC_1_TEST'
        )
        self.doc_user2 = User.objects.create_user(
            email='doc2@test.com', username='doc2', password='mdp', role='doctor',
            id_card_number='DOC_2_TEST'
        )
        self.doctor1 = Doctor.objects.create(user=self.doc_user1, specialty='general', order_number='DOC001')
        self.doctor2 = Doctor.objects.create(user=self.doc_user2, specialty='general', order_number='DOC002')

        # Création des utilisateurs "patient"
        self.pat_userA = User.objects.create_user(
            email='patA@test.com', username='patA', password='mdp', role='patient',
            id_card_number='PAT_A_TEST'
        )
        self.pat_userB = User.objects.create_user(
            email='patB@test.com', username='patB', password='mdp', role='patient',
            id_card_number='PAT_B_TEST'
        )
        
        self.patientA = Patient.objects.create(user=self.pat_userA)
        self.patientB = Patient.objects.create(user=self.pat_userB)

        # Création des rendez-vous
        Appointment.objects.create(
            patient=self.patientA, doctor=self.doctor1, date=date.today(),
            start_time=time(10, 0), end_time=time(10, 30), status='completed'
        )
        Appointment.objects.create(
            patient=self.patientA, doctor=self.doctor1, date=date.today(),
            start_time=time(14, 0), end_time=time(14, 30), status='pending'
        )
        Appointment.objects.create(
            patient=self.patientB, doctor=self.doctor2, date=date.today(),
            start_time=time(11, 0), end_time=time(11, 30), status='confirmed'
        )

    def test_doctor_can_see_only_their_patients(self):
        self.client.force_authenticate(user=self.doc_user1)
        response = self.client.get('/api/patients/my-patients/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.patientA.id)

    def test_patient_cannot_access_list(self):
        self.client.force_authenticate(user=self.pat_userA)
        response = self.client.get('/api/patients/my-patients/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_dashboard(self):
        self.client.force_authenticate(user=self.pat_userA)
        response = self.client.get('/api/patients/dashboard/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('upcoming_appointments', response.data)
        self.assertIn('notifications', response.data)

    def test_update_medical_profile(self):
        self.client.force_authenticate(user=self.pat_userA)
        # Verify get_or_create works on GET
        response = self.client.get('/api/patients/medical-profile/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify PUT updates fields correctly
        data = {
            "blood_group": "A+",
            "weight": 70.0,
            "height": 175.0,
            "emergency_contact_name": "John Doe",
            "emergency_contact_phone": "123456789"
        }
        res_put = self.client.put('/api/patients/medical-profile/', data, format='json')
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.data['blood_group'], 'A+')
        self.assertIn('bmi', res_put.data)

    def test_create_allergy(self):
        self.client.force_authenticate(user=self.pat_userA)
        # Ensure MedicalProfile exists (should be auto-created in Allergy perform_create)
        data = {
            "substance": "Pollen",
            "severity": "mild",
            "reaction": "Eternuements"
        }
        response = self.client.post('/api/patients/allergies/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['substance'], "Pollen")

    def test_create_medical_document(self):
        self.client.force_authenticate(user=self.pat_userA)
        
        # Création d'un faux fichier
        file_content = b"Contenu de test pour analyse de sang."
        dummy_file = SimpleUploadedFile("analyse.pdf", file_content, content_type="application/pdf")
        
        data = {
            "name": "Analyse Sanguine Routine",
            "document_type": "lab_result",
            "date": "2023-10-18",
            "is_visible_to_patient": "true",
            "uploaded_files": dummy_file
        }
        
        # multipart/form-data est automatiquement défini lorsque l'on passe un dictionnaire avec des fichiers via le test client de DRF
        response = self.client.post('/api/patients/medical-documents/', data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Analyse Sanguine Routine")
        self.assertEqual(response.data['document_type'], "lab_result")
        self.assertEqual(response.data['uploaded_by'], self.pat_userA.id)
        
        # Vérifier que le fichier a bien été créé
        self.assertEqual(len(response.data['files']), 1)
        self.assertEqual(response.data['files'][0]['file_name'], "analyse.pdf")
        
    def test_create_treatment(self):
        self.client.force_authenticate(user=self.pat_userA)
        data = {
            "medication_name": "Doliprane",
            "dosage": "1000mg",
            "frequency": "as_needed",
            "start_date": "2023-10-01",
            "is_ongoing": True,
            "prescribed_by": self.doctor1.id
        }
        response = self.client.post('/api/patients/treatments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['medication_name'], "Doliprane")
        self.assertEqual(response.data['prescribed_by'], self.doctor1.id)
