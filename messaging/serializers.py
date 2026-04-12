from rest_framework import serializers
from .models import Conversation, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class ParticipantSerializer(serializers.ModelSerializer):
    """Mini-sérialiseur pour afficher avec qui on parle"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role'] # Ajoute la photo de profil ici plus tard !

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'content', 'is_read', 'created_at']
        read_only_fields = ['sender', 'is_read'] # Sécurité : on ne peut pas falsifier l'expéditeur

class ConversationSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'updated_at', 'last_message']

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                "content": last_msg.content,
                "sender_id": last_msg.sender.id,
                "created_at": last_msg.created_at
            }
        return None