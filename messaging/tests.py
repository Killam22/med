from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from .models import Conversation, Message
import time

User = get_user_model()

class MessagingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Création de nos utilisateurs mocks
        self.patient = User.objects.create_user(
            username='patient1',
            email='patient@test.com',
            password='password123',
            role='patient',
            first_name='Jean',
            last_name='Dupont',
            phone='0600000001'
        )
        
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@test.com',
            password='password123',
            role='doctor',
            first_name='Gregory',
            last_name='House',
            phone='0600000002'
        )
        
        self.intruder = User.objects.create_user(
            username='intruder1',
            email='intruder@test.com',
            password='password123',
            role='pharmacist',
            first_name='Bad',
            last_name='Guy',
            phone='0600000003'
        )

        # Création directe d'une conversation pour gagner du temps
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.patient, self.doctor)

    def test_create_conversation(self):
        """Test API: Création d'une conversation entre deux utilisateurs"""
        self.client.force_authenticate(user=self.patient)
        url = reverse('conversation-list') # Assurez-vous que l'URL name correspond au DefaultRouter
        
        response = self.client.post(url, {
            'participant_ids': [self.doctor.id]
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Conversation.objects.count(), 2) # Il y en a 1 dans le setUp, donc ça fait 2

    def test_send_message_updates_conversation_updated_at(self):
        """Test API: Envoi d'un message met à jour le updated_at de la conversation"""
        self.client.force_authenticate(user=self.doctor)
        url = reverse('message-list')
        
        # On sauvegarde le temps initial
        old_updated_at = self.conversation.updated_at
        
        # Pause artificielle pour s'assurer que updated_at va vraiment changer
        time.sleep(0.1)

        response = self.client.post(url, {
            'conversation': self.conversation.id,
            'content': "Bonjour Jean, comment allez-vous ?"
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)
        
        # Vérification du updated_at
        self.conversation.refresh_from_db()
        self.assertGreater(self.conversation.updated_at, old_updated_at)

    def test_security_unauthorized_user_cannot_read_messages(self):
        """Test API: Un utilisateur externe ne peut pas lire les messages (Doit retourner 404/vide)"""
        # On ajoute d'abord un message privé
        Message.objects.create(
            conversation=self.conversation,
            sender=self.patient,
            content="J'ai mal au ventre."
        )

        # L'intrus se connecte
        self.client.force_authenticate(user=self.intruder)
        
        # 1. Peut-il voir la conversation dans sa liste ?
        conv_list_url = reverse('conversation-list')
        response_list = self.client.get(conv_list_url)
        self.assertEqual(len(response_list.data.get('results', response_list.data)), 0, "L'intrus ne doit voir aucune conversation")

        # 2. Peut-il forcer l'accès s'il devine l'ID de la conversation ?
        conv_detail_url = reverse('conversation-detail', kwargs={'pk': self.conversation.id})
        response_detail = self.client.get(conv_detail_url)
        self.assertEqual(response_detail.status_code, status.HTTP_404_NOT_FOUND, "L'intrus doit recevoir une 404")

        # 3. Peut-il récupérer les messages bruts de la conversation ?
        msg_list_url = f"{reverse('message-list')}?conversation_id={self.conversation.id}"
        response_msgs = self.client.get(msg_list_url)
        self.assertEqual(len(response_msgs.data.get('results', response_msgs.data)), 0, "L'intrus ne doit pas voir les messages du GET filtré")

    def test_security_unauthorized_user_cannot_send_message(self):
        """Test API: Un utilisateur externe ne peut pas envoyer dans un chat privé (Doit générer 403/Forbidden)"""
        self.client.force_authenticate(user=self.intruder)
        url = reverse('message-list')
        
        response = self.client.post(url, {
            'conversation': self.conversation.id,
            'content': "Je m'incruste dans votre rdv !"
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
