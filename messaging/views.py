from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db.models import Max
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """On ne récupère que les conversations de l'utilisateur connecté, triées par le message le plus récent"""
        return Conversation.objects.prefetch_related('participants').filter(participants=self.request.user).annotate(
            last_msg_time=Max('messages__created_at')
        ).order_by('-last_msg_time')

    def perform_create(self, serializer):
        """Créer une nouvelle conversation (Nécessite de passer une liste de 'participant_ids' dans le JSON)"""
        conversation = serializer.save()
        # On ajoute automatiquement le créateur
        conversation.participants.add(self.request.user)
        # On ajoute les autres participants envoyés dans la requête
        participant_ids = self.request.data.get('participant_ids', [])
        for p_id in participant_ids:
            conversation.participants.add(p_id)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """On ne voit que les messages des conversations auxquelles on participe"""
        conversation_id = self.request.query_params.get('conversation_id')
        queryset = Message.objects.filter(conversation__participants=self.request.user)
        
        # Filtre optionnel pour ne charger que les messages d'un chat précis : ?conversation_id=X
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        return queryset

    def perform_create(self, serializer):
        """On force l'expéditeur à être l'utilisateur connecté"""
        conversation = serializer.validated_data['conversation']
        if not conversation.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Vous ne participez pas à cette conversation.")
        
        serializer.save(sender=self.request.user)
        
        # Astuce : Mettre à jour la date de la conversation pour qu'elle remonte en haut de la liste
        conversation.save()