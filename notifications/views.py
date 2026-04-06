from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # Sécurité : on ne renvoie que les notifications de l'utilisateur connecté
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marque une notification spécifique comme lue"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Notification marquée comme lue'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Le fameux bouton 'Tout marquer comme lu'"""
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'Toutes les notifications ont été marquées comme lues'})
