from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

class NotificationTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123', first_name='User', last_name='One')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123', first_name='User', last_name='Two')
        
        # User 1 Notifications
        self.notif1 = Notification.objects.create(
            user=self.user1,
            title='Test 1',
            message='Message 1',
            notification_type=Notification.NotificationType.SYSTEM
        )
        self.notif2 = Notification.objects.create(
            user=self.user1,
            title='Test 2',
            message='Message 2',
            notification_type=Notification.NotificationType.SYSTEM
        )
        
        # User 2 Notification
        self.notif_user2 = Notification.objects.create(
            user=self.user2,
            title='Test User 2',
            message='Message User 2',
            notification_type=Notification.NotificationType.SYSTEM
        )

    def test_list_notifications_isolated(self):
        """Les utilisateurs ne doivent voir que leurs propres notifications."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/notifications/', format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination or flat list
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)
        
        # S'assurer que la notification de l'user 2 n'est pas présente
        notif_ids = [n['id'] for n in results]
        self.assertNotIn(self.notif_user2.id, notif_ids)

    def test_mark_as_read(self):
        """Tester le marquage d'une notification individuelle comme lue."""
        self.client.force_authenticate(user=self.user1)
        self.assertFalse(self.notif1.is_read)
        
        response = self.client.post(f'/api/notifications/{self.notif1.id}/mark_as_read/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_mark_all_as_read(self):
        """Tester le marquage de toutes les notifications comme lues."""
        self.client.force_authenticate(user=self.user1)
        self.assertFalse(self.notif1.is_read)
        self.assertFalse(self.notif2.is_read)
        
        response = self.client.post('/api/notifications/mark_all_as_read/', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.notif1.refresh_from_db()
        self.notif2.refresh_from_db()
        self.assertTrue(self.notif1.is_read)
        self.assertTrue(self.notif2.is_read)

    def test_security_cannot_mark_others_notification(self):
        """Un utilisateur ne peut pas modifier la notification d'un autre."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(f'/api/notifications/{self.notif_user2.id}/mark_as_read/', format='json')
        # DRF renvoie 404 car le get_queryset la masque complètement
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
