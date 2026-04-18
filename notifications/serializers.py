from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'created_at']
 
 
class NotificationSummarySerializer(serializers.Serializer):
    """
    Returned by GET /notifications/summary/
    Gives unread counts per type — useful for badge counters in the frontend.
    """
    total_unread      = serializers.IntegerField()
    unread_appointment = serializers.IntegerField()
    unread_pharmacy    = serializers.IntegerField()
    unread_caretaker   = serializers.IntegerField()
    unread_system      = serializers.IntegerField()
 
