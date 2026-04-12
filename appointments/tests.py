from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Patient, Doctor, Appointment

User = get_user_model()

class AppointmentModelsTest(TestCase):

    def setUp(self):
        """
        Cette méthode s'exécute avant chaque test.
        Elle sert à préparer des fausses données dans la base de données de test.
        """
        # 1. Créer un faux utilisateur et un profil Patient
        self.user_patient = User.objects.create_user(
            username='jean_dupont',
            email='patient@test.com',
            password='password123',
            first_name='Jean',
            last_name='Dupont',
            date_of_birth=timezone.datetime(1990, 1, 1).date(),
            phone='0600000000'
        )
        self.patient = Patient.objects.create(
            user=self.user_patient
        )

        # 2. Créer un faux utilisateur et un profil Docteur
        self.user_doctor = User.objects.create_user(
            username='greg_house',
            email='doctor@test.com',
            password='password123',
            first_name='Gregory',
            last_name='House'
        )
        self.doctor = Doctor.objects.create(
            user=self.user_doctor,
            specialty='general',
            license_number='DOC12345'
        )

        # 3. Créer un rendez-vous (en se basant sur les champs date, start_time, end_time au lieu de slot)
        tomorrow = timezone.now().date() + timedelta(days=1)
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=tomorrow,
            start_time='10:00:00',
            end_time='10:30:00',
            motif='Consultation de routine',
            status='pending'
        )

    def test_patient_age_calculation(self):
        """
        Test 1 : Vérifier que la propriété 'age' du patient calcule correctement l'âge.
        """
        # Né le 1er Janvier 1990
        self.assertEqual(self.patient.age, timezone.now().year - 1990)

    def test_appointment_confirm(self):
        """
        Test 2 : Vérifier que app.confirm() passe le statut à 'confirmed'
        """
        self.appointment.confirm()
        self.assertEqual(self.appointment.status, 'confirmed')

    def test_appointment_cancel(self):
        """
        Test 3 : Vérifier que app.cancel() annule le rdv
        """
        self.appointment.cancel()

        # On vérifie le changement de statut
        self.assertEqual(self.appointment.status, 'cancelled')

    def test_appointment_refuse(self):
        """
        Test 4 : Vérifier que app.refuse() refuse le rdv, enregistre la raison
        """
        raison = "Je suis en vacances."
        self.appointment.refuse(reason=raison)

        self.assertEqual(self.appointment.status, 'refused')
        self.assertEqual(self.appointment.refusal_reason, raison)

    def test_appointment_string_representation(self):
        """
        Test 5 : S'assurer que le '__str__' (l'affichage texte de l'objet) ne plante pas
        """
        representation = str(self.appointment)
        self.assertIn("RDV", representation)
        self.assertIn("House", representation)
