from datetime import timedelta, date, time
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from doctors.models import Doctor, WeeklySchedule, DayOff
from patients.models import Patient
from .models import Appointment

User = get_user_model()

class AppointmentAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # 1. Création du Patient
        cls.patient_user = User.objects.create_user(
            username='patient1', 
            email='patient1@test.com', 
            password='pw', 
            role='patient',
            id_card_number='PAT123456'
        )
        cls.patient = Patient.objects.create(user=cls.patient_user)

        # 2. Création du Médecin
        cls.doctor_user = User.objects.create_user(
            username='doctor1', 
            email='doctor1@test.com', 
            password='pw', 
            role='doctor',
            id_card_number='DOC123456'
        )
        cls.doctor = Doctor.objects.create(
            user=cls.doctor_user, specialty='general', order_number='DOC001'
        )

        # 3. Création du Planning (WeeklySchedule)
        # On crée un planning valide pour demain
        cls.tomorrow = timezone.now().date() + timedelta(days=1)
        cls.weekday = cls.tomorrow.weekday()
        
        WeeklySchedule.objects.create(
            doctor=cls.doctor,
            day_of_week=cls.weekday,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration=30, # Créneaux de 30 min: 09:00-09:30, 09:30-10:00, etc.
            is_active=True
        )

        # 4. Création d'un rdv existant (pour tester annuler / confirmer)
        cls.existing_appt = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=cls.tomorrow,
            start_time=time(9, 0),
            end_time=time(9, 30),
            motif='Consultation de base'
        )

    # ── Tests Patient ────────────────────────────────────────────────────────

    def test_patient_can_book_appointment(self):
        self.client.force_authenticate(user=self.patient_user)
        # 09:30 à 10:00 est libre (le premier créneau de 9:00 est pris par setup)
        data = {
            'doctor_id': self.doctor.id,
            'date': self.tomorrow.isoformat(),
            'start_time': '09:30:00',
            'end_time': '10:00:00',
            'motif': 'Mal de gorge'
        }
        response = self.client.post('/api/appointments/appointments/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 2)

    def test_booking_conflict_returns_400(self):
        self.client.force_authenticate(user=self.patient_user)
        # Le créneau 09:00 à 09:30 est déjà pris par 'existing_appt'
        data = {
            'doctor_id': self.doctor.id,
            'date': self.tomorrow.isoformat(),
            'start_time': '09:00:00',
            'end_time': '09:30:00',
            'motif': 'Test de conflit'
        }
        response = self.client.post('/api/appointments/appointments/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check if the error message is present (usually in non_field_errors for DRF validation raises)
        # We just check the 400 occurred which means my custom validation rule in the serializer worked.
        self.assertTrue(len(response.data) > 0)

    def test_patient_can_cancel_appointment(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.post(f'/api/appointments/appointments/{self.existing_appt.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Vérif en BDD
        self.existing_appt.refresh_from_db()
        self.assertEqual(self.existing_appt.status, 'cancelled')

    def test_patient_list_appointments(self):
        self.client.force_authenticate(user=self.patient_user)
        response = self.client.get('/api/appointments/appointments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Tests Doctor ─────────────────────────────────────────────────────────

    def test_doctor_can_confirm_appointment(self):
        self.client.force_authenticate(user=self.doctor_user)
        self.assertEqual(self.existing_appt.status, 'pending')
        
        response = self.client.post(f'/api/appointments/doctor/appointments/{self.existing_appt.id}/confirm/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.existing_appt.refresh_from_db()
        self.assertEqual(self.existing_appt.status, 'confirmed')

    def test_doctor_can_refuse_appointment(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(f'/api/appointments/doctor/appointments/{self.existing_appt.id}/refuse/', {
            'reason': 'Pas disponible ce moment'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.existing_appt.refresh_from_db()
        self.assertEqual(self.existing_appt.status, 'refused')
        self.assertEqual(self.existing_appt.refusal_reason, 'Pas disponible ce moment')

    def test_doctor_list_pending_appointments(self):
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get('/api/appointments/doctor/appointments/pending/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ── Tests Utilitaires / Disponibilité ────────────────────────────────────
    
    def test_availability_endpoint(self):
        """Vérifier que l'endpoint GET public ressort les créneaux libres."""
        
        response = self.client.get(f'/api/appointments/doctors/{self.doctor.id}/availability/?date={self.tomorrow.isoformat()}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        slots = response.data['slots']
        # Il y a 6 créneaux theoriques entre 9h-12h. Le 1er est retiré. Donc 5 slots attendus.
        self.assertEqual(len(slots), 5)
        # Check either string or time object depending on serializer behavior
        self.assertEqual(str(slots[0]['start_time']), '09:30:00')
