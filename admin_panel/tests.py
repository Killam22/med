from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from admin_panel.models import AuditLog
from notifications.models import Notification
from doctors.models import Doctor, DoctorQualification
from pharmacy.models import Pharmacist, PharmacistQualification
from caretaker.models import Caretaker, CaretakerCertificate

User = get_user_model()

class AdminPanelTests(APITestCase):
    def setUp(self):
        # Création d'un admin
        self.admin_user = User.objects.create_superuser(
            email='admin@medsmart.com',
            username='admin',
            password='password123',
            role='admin'
        )
        
        # Création d'un utilisateur normal
        self.normal_user = User.objects.create_user(
            email='user@test.com',
            username='user',
            password='password123',
            role='patient'
        )
        
        # Création d'un médecin à valider
        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            username='doctor',
            password='password123',
            role='doctor',
            is_active=True
        )
        self.doctor_profile = Doctor.objects.create(
            user=self.doctor_user,
            license_number='DOC123',
            practice_authorization=SimpleUploadedFile('auth.pdf', b'content', content_type='application/pdf')
        )
        DoctorQualification.objects.create(
            doctor=self.doctor_profile,
            title='Doctorat',
            institution='Faculté',
            graduation_year=2020,
            degree_type='Etat',
            scan=SimpleUploadedFile('diploma.pdf', b'content', content_type='application/pdf')
        )

    def test_admin_permission_required(self):
        """Vérifie que seuls les admins accèdent au panel"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_serializer_submitted_documents(self):
        """Vérifie que le sérialiseur extrait bien les documents du médecin"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/admin/users/{self.doctor_user.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        docs = response.data['submitted_documents']
        
        # 1 autorisation + 1 diplôme
        self.assertEqual(len(docs), 2)
        titles = [d['title'] for d in docs]
        self.assertIn("Autorisation d'exercer", titles)
        self.assertTrue(any("Diplôme" in t for t in titles))

    def test_verify_professional_action(self):
        """Vérifie le bouton 'Approuver'"""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/admin/users/{self.doctor_user.id}/verify_professional/'
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Vérification BDD
        self.doctor_user.refresh_from_db()
        self.doctor_profile.refresh_from_db()
        self.assertEqual(self.doctor_user.verification_status, 'verified')
        self.assertTrue(self.doctor_profile.is_verified)
        
        # Vérification Notification
        self.assertTrue(Notification.objects.filter(user=self.doctor_user, title="Compte approuvé !").exists())
        
        # Vérification AuditLog
        self.assertTrue(AuditLog.objects.filter(level='success', message__icontains='approuvé').exists())

    def test_reject_professional_action(self):
        """Vérifie le bouton 'Rejeter' avec un motif personnalisé"""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/admin/users/{self.doctor_user.id}/reject_professional/'
        data = {'reason': 'Diplôme flou'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.doctor_user.refresh_from_db()
        self.assertEqual(self.doctor_user.verification_status, 'rejected')
        
        notification = Notification.objects.filter(user=self.doctor_user).first()
        self.assertIn('Diplôme flou', notification.message)
        
        self.assertTrue(AuditLog.objects.filter(level='warning', message__icontains='rejetée').exists())

    def test_toggle_suspend_security(self):
        """Vérifie qu'un admin ne peut pas se suspendre lui-même"""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/admin/users/{self.admin_user.id}/toggle_suspend/'
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('propre compte', response.data['error'])

    def test_toggle_suspend_logic(self):
        """Vérifie la suspension d'un utilisateur tiers"""
        self.client.force_authenticate(user=self.admin_user)
        url = f'/api/admin/users/{self.doctor_user.id}/toggle_suspend/'
        
        # Actif -> Suspendre
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertFalse(self.doctor_user.is_active)
        self.assertTrue(Notification.objects.filter(user=self.doctor_user, title="Compte suspendu").exists())
        
        # Suspendu -> Réactiver
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.is_active)
