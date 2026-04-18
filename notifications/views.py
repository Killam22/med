from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer, NotificationSummarySerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Sécurité : on ne renvoie que les notifications de l'utilisateur connecté.
        Filtres optionnels :
          ?type=appointment|pharmacy|caretaker|system
          ?unread=true
        """
        qs = Notification.objects.filter(user=self.request.user)

        notif_type = self.request.query_params.get('type')
        if notif_type:
            qs = qs.filter(notification_type=notif_type)

        unread_only = self.request.query_params.get('unread')
        if unread_only and unread_only.lower() == 'true':
            qs = qs.filter(is_read=False)

        return qs

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """POST /notifications/{id}/mark_as_read/"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Notification marquée comme lue.'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """POST /notifications/mark_all_as_read/"""
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': f'{updated} notifications marquées comme lues.'})

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """DELETE /notifications/clear_all/"""
        deleted_count, _ = self.get_queryset().delete()
        return Response({'status': f'{deleted_count} notifications supprimées.'})


class NotificationSummaryView(APIView):
    """
    GET /notifications/summary/
    Retourne le nombre de notifications non lues par type.
    Respecte les préférences de notifications de l'utilisateur (settings_app).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs   = Notification.objects.filter(user=user, is_read=False)

        try:
            prefs = user.notification_preferences
        except Exception:
            prefs = None

        def count_type(notif_type, pref_field):
            if prefs and not getattr(prefs, pref_field, True):
                return 0
            return qs.filter(notification_type=notif_type).count()

        data = {
            'total_unread':        qs.count(),
            'unread_appointment':  count_type('appointment', 'notify_appointment'),
            'unread_pharmacy':     count_type('pharmacy',    'notify_pharmacy'),
            'unread_caretaker':    count_type('caretaker',   'notify_caretaker'),
            'unread_system':       count_type('system',      'notify_system'),
        }

        serializer = NotificationSummarySerializer(data)
        return Response(serializer.data)