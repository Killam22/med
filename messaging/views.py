from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from django.db.models import Max
from django.contrib.auth import get_user_model

from .models import Conversation, Message, BlockedUser, UserReport
from .serializers import ConversationSerializer, MessageSerializer, UserReportSerializer

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def get_queryset(self):
        return (
            Conversation.objects
            .prefetch_related('participants')
            .filter(participants=self.request.user)
            .annotate(last_msg_time=Max('messages__created_at'))
            .order_by('-last_msg_time')
        )

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)
        # Support interlocutor_id (frontend) ou participant_ids (legacy)
        interlocutor_id = self.request.data.get('interlocutor_id')
        if interlocutor_id:
            try:
                conversation.participants.add(User.objects.get(id=interlocutor_id))
            except User.DoesNotExist:
                pass
        for p_id in self.request.data.get('participant_ids', []):
            try:
                conversation.participants.add(User.objects.get(id=p_id))
            except User.DoesNotExist:
                pass

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.method == 'GET':
            msgs = Message.objects.filter(conversation=conversation, is_deleted=False)
            return Response(MessageSerializer(msgs, many=True).data)

        # POST — envoyer un message
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'detail': 'Le contenu est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
        )
        conversation.save()  # met à jour updated_at pour le tri
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        Message.objects.filter(
            conversation=conversation,
            is_read=False,
            is_deleted=False,
        ).exclude(sender=request.user).update(is_read=True)
        return Response({'detail': 'Messages marqués comme lus.'})


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        conversation_id = self.request.query_params.get('conversation_id')
        qs = Message.objects.filter(
            conversation__participants=self.request.user,
            is_deleted=False,
        )
        if conversation_id:
            qs = qs.filter(conversation_id=conversation_id)
        return qs

    def perform_create(self, serializer):
        conversation = serializer.validated_data['conversation']
        if not conversation.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Vous ne participez pas à cette conversation.")
        serializer.save(sender=self.request.user)
        conversation.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.sender != self.request.user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres messages.")
        serializer.save(edited_at=timezone.now())

    def perform_destroy(self, instance):
        if instance.sender != self.request.user:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres messages.")
        instance.is_deleted = True
        instance.content = "Message supprimé"
        instance.save()


class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            blocked = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if blocked == request.user:
            return Response({'detail': 'Vous ne pouvez pas vous bloquer vous-même.'}, status=status.HTTP_400_BAD_REQUEST)
        BlockedUser.objects.get_or_create(blocker=request.user, blocked=blocked)
        return Response({'detail': f'{blocked.get_full_name()} a été bloqué.'})

    def delete(self, request, user_id):
        BlockedUser.objects.filter(blocker=request.user, blocked_id=user_id).delete()
        return Response({'detail': 'Utilisateur débloqué.'})


class ReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reported_user_id = request.data.get('reported_user_id')
        reason = request.data.get('reason', '')
        if not reported_user_id or not reason:
            return Response(
                {'detail': 'reported_user_id et reason sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            reported = User.objects.get(id=reported_user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        report = UserReport.objects.create(reporter=request.user, reported_user=reported, reason=reason)
        return Response(UserReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_staff:
            return UserReport.objects.none()
        return UserReport.objects.all().order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='action')
    def handle_action(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Accès admin requis.'}, status=status.HTTP_403_FORBIDDEN)
        report = self.get_object()
        action_type = request.data.get('action')
        if action_type == 'resolve':
            report.status = 'resolved'
        elif action_type == 'dismiss':
            report.status = 'dismissed'
        else:
            return Response(
                {'detail': 'Action invalide. Utilisez "resolve" ou "dismiss".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        report.save()
        return Response(UserReportSerializer(report).data)
