from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from django.db.models import Max, Count
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

    def create(self, request, *args, **kwargs):
        interlocutor_id = request.data.get('interlocutor_id')
        interlocutor = None

        if interlocutor_id:
            try:
                interlocutor = User.objects.get(id=interlocutor_id)
            except User.DoesNotExist:
                pass

        if interlocutor:
            if interlocutor.messages_disabled:
                raise PermissionDenied("MESSAGES_DISABLED")

            # Get-or-create: find existing 1-to-1 conversation between the two users
            existing = (
                Conversation.objects
                .filter(participants=request.user)
                .filter(participants=interlocutor)
                .annotate(pcount=Count('participants'))
                .filter(pcount=2)
                .first()
            )
            if existing:
                ctx = self.get_serializer_context()
                return Response(
                    ConversationSerializer(existing, context=ctx).data,
                    status=status.HTTP_200_OK,
                )

        return super().create(request, *args, **kwargs)

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
        ctx = {'request': request}
        if request.method == 'GET':
            msgs = Message.objects.filter(conversation=conversation, is_deleted=False)
            return Response(MessageSerializer(msgs, many=True, context=ctx).data)

        # POST — envoyer un message (texte et/ou fichier)
        # Bloquer si l'expéditeur a désactivé ses messages
        if request.user.messages_disabled:
            return Response({'detail': 'Vous avez désactivé les messages.'}, status=status.HTTP_403_FORBIDDEN)
        # Bloquer si un destinataire a désactivé ses messages
        if conversation.participants.exclude(id=request.user.id).filter(messages_disabled=True).exists():
            return Response({'detail': 'MESSAGES_DISABLED'}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content', '').strip()
        file = request.FILES.get('file')
        if not content and not file:
            return Response({'detail': 'Un contenu ou un fichier est requis.'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            file=file,
        )
        conversation.save()  # met à jour updated_at pour le tri
        return Response(MessageSerializer(msg, context=ctx).data, status=status.HTTP_201_CREATED)

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
        if self.request.user.messages_disabled:
            raise PermissionDenied("Vous avez désactivé les messages.")
        if conversation.participants.exclude(id=self.request.user.id).filter(messages_disabled=True).exists():
            raise PermissionDenied("MESSAGES_DISABLED")
        serializer.save(sender=self.request.user)
        conversation.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.sender != self.request.user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres messages.")
        serializer.save(edited_at=timezone.now())

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.sender != request.user:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres messages.")
        instance.is_deleted = True
        instance.content = ""
        instance.save()
        ctx = {'request': request}
        return Response(MessageSerializer(instance, context=ctx).data)


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
    """POST /api/chat/report/ — un utilisateur signale un autre user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta

        reported_user_id = request.data.get('reported_user_id')
        reason   = (request.data.get('reason') or '').strip()
        category = request.data.get('category') or 'other'

        if not reported_user_id or not reason:
            return Response(
                {'detail': 'reported_user_id et reason sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if category not in dict(UserReport.CATEGORY_CHOICES):
            category = 'other'

        try:
            reported = User.objects.get(id=reported_user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Anti auto-signalement
        if reported.id == request.user.id:
            return Response(
                {'detail': "Vous ne pouvez pas vous signaler vous-même."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Anti-doublon : pas de second signalement pending vers le même user
        # ni de signalement identique dans les dernières 24h.
        if UserReport.objects.filter(
            reporter=request.user, reported_user=reported, status='pending'
        ).exists():
            return Response(
                {'detail': "Vous avez déjà un signalement en cours contre cet utilisateur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recent = UserReport.objects.filter(
            reporter=request.user, reported_user=reported,
            created_at__gte=timezone.now() - timedelta(hours=24),
        ).exists()
        if recent:
            return Response(
                {'detail': "Vous avez déjà signalé cet utilisateur dans les dernières 24h."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = UserReport.objects.create(
            reporter=request.user,
            reported_user=reported,
            category=category,
            reason=reason,
        )

        # Notifier les admins qu'un nouveau signalement arrive
        try:
            from notifications.models import Notification
            from django.contrib.auth import get_user_model
            U = get_user_model()
            admins = U.objects.filter(role='admin', is_active=True)
            Notification.objects.bulk_create([
                Notification(
                    user=admin,
                    title="Nouveau signalement",
                    message=(
                        f"{request.user.get_full_name()} a signalé "
                        f"{reported.get_full_name()} ({reported.email}) — "
                        f"{dict(UserReport.CATEGORY_CHOICES).get(category, 'Autre')}."
                    ),
                    notification_type=Notification.NotificationType.SYSTEM,
                )
                for admin in admins
            ])
        except Exception:
            pass  # ne bloque pas la création du signalement

        return Response(UserReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """GET liste + détail (admin uniquement) + action de modération."""
    serializer_class = UserReportSerializer
    permission_classes = [IsAuthenticated]

    # Actions admin valides → comportement réel sur l'utilisateur signalé
    VALID_ACTIONS = {'warn', 'suspend', 'dismiss'}

    def _is_admin(self, user):
        return user.is_staff or getattr(user, 'role', None) == 'admin'

    def get_queryset(self):
        if not self._is_admin(self.request.user):
            return UserReport.objects.none()
        return UserReport.objects.select_related(
            'reporter', 'reported_user', 'resolved_by'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='action')
    def handle_action(self, request, pk=None):
        """
        POST /api/chat/reports/<id>/action/
        Body: { "action": "warn" | "suspend" | "dismiss", "notes": "…" }

        - warn    : avertit l'utilisateur signalé (notification in-app)
        - suspend : désactive le compte (is_active=False) + notif
        - dismiss : signalement classé sans suite

        Dans les 3 cas, l'auteur du signalement est aussi notifié pour qu'il
        sache que son report a bien été traité.
        """
        from django.utils import timezone
        from notifications.models import Notification

        if not self._is_admin(request.user):
            return Response({'detail': 'Accès admin requis.'}, status=status.HTTP_403_FORBIDDEN)

        report = self.get_object()
        if report.status != 'pending':
            return Response(
                {'detail': "Ce signalement a déjà été traité."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action_type = (request.data.get('action') or '').strip().lower()
        notes       = (request.data.get('notes') or '').strip()

        # Compatibilité historique : 'resolve' = avertissement (l'ancien front utilise 'resolve')
        if action_type == 'resolve':
            action_type = 'warn'

        if action_type not in self.VALID_ACTIONS:
            return Response(
                {'detail': f'Action invalide. Utilisez : {", ".join(sorted(self.VALID_ACTIONS))}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = report.reported_user

        # ── Exécution de l'action sur le user signalé ─────────────────────
        if action_type == 'warn':
            Notification.objects.create(
                user=target,
                title="Avertissement de la modération",
                message=(
                    f"Un signalement a été retenu à votre encontre. "
                    f"Catégorie : {report.get_category_display()}. "
                    + (f"Note de la modération : {notes}" if notes else "Veuillez respecter les règles de la plateforme.")
                ),
                notification_type=Notification.NotificationType.SYSTEM,
            )
            report.action_taken = 'warn'
            report.status       = 'resolved'

        elif action_type == 'suspend':
            target.is_active = False
            target.save(update_fields=['is_active'])
            Notification.objects.create(
                user=target,
                title="Compte suspendu",
                message=(
                    f"Votre compte a été suspendu suite à un signalement "
                    f"({report.get_category_display()}). "
                    + (f"Motif : {notes}" if notes else "Contactez le support pour plus d'informations.")
                ),
                notification_type=Notification.NotificationType.SYSTEM,
            )
            report.action_taken = 'suspend'
            report.status       = 'resolved'

        elif action_type == 'dismiss':
            report.action_taken = 'dismissed'
            report.status       = 'dismissed'

        # ── Métadonnées de traçabilité ─────────────────────────────────────
        report.admin_notes = notes
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        # ── Notification au signaleur ──────────────────────────────────────
        try:
            outcome_label = {
                'warn':    "un avertissement a été adressé à la personne signalée",
                'suspend': "le compte de la personne signalée a été suspendu",
                'dismiss': "aucune action n'a été retenue après examen",
            }[action_type]
            Notification.objects.create(
                user=report.reporter,
                title="Votre signalement a été traité",
                message=f"Suite à votre signalement, {outcome_label}. Merci de contribuer à la sécurité de la plateforme.",
                notification_type=Notification.NotificationType.SYSTEM,
            )
        except Exception:
            pass

        # ── Audit log applicatif ──────────────────────────────────────────
        try:
            from admin_panel.models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                level='warning' if action_type == 'suspend' else 'info',
                message=(
                    f"Signalement #{report.id} → {action_type} sur "
                    f"{target.email} (par {request.user.email})"
                )[:255],
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        return Response(UserReportSerializer(report).data)
