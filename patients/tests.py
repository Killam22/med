from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from datetime import date, time

User = get_user_model()

class DoctorPatientsTests(APITestCase):
    def setUp(self):
        # Création des utilisateurs "doctor"
        self.doc_user1 = User.objects.create_user(email='doc1@test.com', username='doc1', password='mdp', role='doctor')
        self.doc_user2 = User.objects.create_user(email='doc2@test.com', username='doc2', password='mdp', role='doctor')
        self.doctor1 = Doctor.objects.create(user=self.doc_user1, specialty='Cardio', license_number='1234')
        self.doctor2 = Doctor.objects.create(user=self.doc_user2, specialty='Neuro', license_number='5678')

        # Création des utilisateurs "patient"
        self.pat_userA = User.objects.create_user(email='patA@test.com', username='patA', password='mdp', role='patient')
        self.pat_userB = User.objects.create_user(email='patB@test.com', username='patB', password='mdp', role='patient')
        
        self.patientA = Patient.objects.create(
            user=self.pat_userA, blood_group='O+'
        )
        self.patientB = Patient.objects.create(
            user=self.pat_userB, blood_group='A-'
        )

        # Création des rendez-vous
        # Patient A a un rdv avec Doctor 1
        Appointment.objects.create(
            patient=self.patientA, doctor=self.doctor1, date=date.today(),
            start_time=time(10, 0), end_time=time(10, 30), status='completed'
        )
        # Patient A a UN AUTRE rdv avec Doctor 1 (pour tester le .distinct())
        Appointment.objects.create(
            patient=self.patientA, doctor=self.doctor1, date=date.today(),
            start_time=time(14, 0), end_time=time(14, 30), status='pending'
        )
        
        # Patient B a un rdv avec Doctor 2
        Appointment.objects.create(
            patient=self.patientB, doctor=self.doctor2, date=date.today(),
            start_time=time(11, 0), end_time=time(11, 30), status='confirmed'
        )

    def test_doctor_can_see_only_their_patients(self):
        """Le médecin 1 doit voir le patient A, mais pas B. Et A ne doit apparaître qu'une seule fois !"""
        self.client.force_authenticate(user=self.doc_user1)
        response = self.client.get('/api/patients/my-patients/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Selon la pagination de DRF, results est présent ou non
        results = response.data.get('results', response.data)
        
        # Doit contenir exactement 1 élément (Patient A est unique)
        self.assertEqual(len(results), 1)
        
        self.assertEqual(results[0]['id'], self.patientA.id)
        # Le patient B ne doit pas y être
        patient_ids = [p['id'] for p in results]
        self.assertNotIn(self.patientB.id, patient_ids)

    def test_patient_cannot_access_list(self):
        """Un patient ne peut pas accéder à cette vue."""
        self.client.force_authenticate(user=self.pat_userA)
        response = self.client.get('/api/patients/my-patients/', format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
