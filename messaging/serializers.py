from rest_framework import serializers
from .models import Conversation, Message, UserReport
from django.contrib.auth import get_user_model

User = get_user_model()


class ParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'role']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'content',
                  'is_read', 'is_deleted', 'edited_at', 'created_at', 'is_mine']
        read_only_fields = ['sender', 'is_read', 'is_deleted', 'edited_at', 'is_mine']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return obj.sender_id == request.user.id


class ConversationSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'other_participant', 'created_at', 'updated_at',
                  'last_message', 'unread_count']

    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).last()
        if last_msg:
            return {
                "content": last_msg.content,
                "sender_id": last_msg.sender.id,
                "created_at": last_msg.created_at,
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        return obj.messages.filter(is_read=False, is_deleted=False).exclude(sender=request.user).count()

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return {'id': other.id, 'full_name': other.get_full_name(), 'role': other.role}
        return None


class UserReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    reported_name = serializers.CharField(source='reported_user.get_full_name', read_only=True)

    class Meta:
        model = UserReport
        fields = ['id', 'reporter', 'reporter_name', 'reported_user', 'reported_name',
                  'reason', 'status', 'created_at']
        read_only_fields = ['reporter', 'status']
