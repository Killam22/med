from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, time
from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from consultations.models import Consultation

User = get_user_model()

class ConsultationAPITests(APITestCase):
    def setUp(self):
        # 1. Setup Users & Profiles
        self.doc_user = User.objects.create_user(
            email='doc_consult@test.com', username='doc_consult', password='pw', role='doctor',
            id_card_number='DOC_CONSULT_ID', first_name='John', last_name='Doe', sex='male'
        )
        self.doctor = Doctor.objects.create(user=self.doc_user, specialty='general', order_number='DOC_CONSULT_ORD')

        self.pat_user = User.objects.create_user(
            email='pat_consult@test.com', username='pat_consult', password='pw', role='patient',
            id_card_number='PAT_CONSULT_ID', first_name='Jane', last_name='Smith', sex='female'
        )
        self.patient = Patient.objects.create(user=self.pat_user)

        self.other_pat_user = User.objects.create_user(
            email='other_pat@test.com', username='other_pat', password='pw', role='patient',
            id_card_number='PAT_OTHER_ID', first_name='Other', last_name='Patient', sex='male'
        )
        self.other_patient = Patient.objects.create(user=self.other_pat_user)

        # 2. Setup Appointment
        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(10, 30),
            status='confirmed',
            motif='Checkup'
        )

    def test_doctor_can_create_consultation(self):
        self.client.force_authenticate(user=self.doc_user)
        data = {
            "doctor": self.doctor.id,
            "patient": self.patient.id,
            "appointment": self.appointment.id,
            "chief_complaint": "Mal de tête persistant",
            "diagnosis": "Stress",
            "treatment_plan": "Repos",
            "consulted_at": timezone.now().isoformat()
        }
        response = self.client.post('/api/consultations/consultations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify appointment status update
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'completed')
        
        # Verify object creation
        self.assertEqual(Consultation.objects.count(), 1)

    def test_patient_cannot_create_consultation(self):
        self.client.force_authenticate(user=self.pat_user)
        data = {
            "doctor": self.doctor.id,
            "patient": self.patient.id,
            "chief_complaint": "Tentative frauduleuse"
        }
        response = self.client.post('/api/consultations/consultations/', data)
        # IsDoctor permission should block this
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consultation_list_filtering(self):
        # Create a consultation
        Consultation.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            chief_complaint="C1",
            consulted_at=timezone.now()
        )
        # Create another for other patient
        Consultation.objects.create(
            doctor=self.doctor,
            patient=self.other_patient,
            chief_complaint="C2",
            consulted_at=timezone.now()
        )

        # Doctor sees both
        self.client.force_authenticate(user=self.doc_user)
        response = self.client.get('/api/consultations/consultations/')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

        # Patient A sees only C1
        self.client.force_authenticate(user=self.pat_user)
        response = self.client.get('/api/consultations/consultations/')
        if isinstance(response.data, dict) and 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
            
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['chief_complaint'], "C1")
