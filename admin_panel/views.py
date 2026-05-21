from rest_framework import viewsets, status, filters, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Count


class IsAdminRole(BasePermission):
    """Accorde l'accès aux utilisateurs avec role='admin' ou is_superuser=True."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser)
        )

from .models import AuditLog
from .serializers import AdminUserSerializer, AuditLogSerializer
from notifications.models import Notification # Toujours lié à tes supers notifications
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer

User = get_user_model()


class SystemStatusView(APIView):
    """
    GET /api/admin/system-status/
    Retourne l'état des dépendances critiques de la plateforme.
    Aucune valeur hardcodée : tout est calculé en live.
    """
    permission_classes = [IsAdminRole]
    renderer_classes   = [JSONRenderer]

    def get(self, request):
        import django
        from django.conf import settings as dj_settings
        from django.db import connection

        # Version PostgreSQL réelle
        db_version = None
        db_status  = 'ok'
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                if row:
                    raw = row[0]
                    # "PostgreSQL 16.2 on x86_64-..." → "PostgreSQL 16.2"
                    parts = raw.split(' on ')
                    db_version = parts[0] if parts else raw
        except Exception as e:
            db_status  = 'error'
            db_version = str(e)[:80]

        # Email : on vérifie juste que la config est présente (pas d'envoi)
        email_status = 'ok' if (
            getattr(dj_settings, 'EMAIL_HOST_USER', '') and
            getattr(dj_settings, 'EMAIL_HOST_PASSWORD', '')
        ) else 'unconfigured'

        # Compteurs
        try:
            users_total  = User.objects.count()
            users_active = User.objects.filter(is_active=True).count()
            users_pending = User.objects.filter(verification_status='pending').count()
        except Exception:
            users_total = users_active = users_pending = 0

        return Response({
            'backend': {
                'status':  'ok',
                'django':  django.get_version(),
                'debug':   bool(dj_settings.DEBUG),
            },
            'database': {
                'status':  db_status,
                'version': db_version,
            },
            'email': {
                'status': email_status,
                'host':   getattr(dj_settings, 'EMAIL_HOST', ''),
            },
            'users': {
                'total':   users_total,
                'active':  users_active,
                'pending': users_pending,
            },
        })

def create_audit_log(message, level, request):
    ip = request.META.get('REMOTE_ADDR')
    actor = request.user if request.user.is_authenticated else None
    AuditLog.objects.create(message=message, level=level, actor=actor, ip_address=ip)

class AdminUserManagementViewSet(viewsets.ModelViewSet):
    """Endpoints pour 'Validation des inscriptions' et 'Gestion Utilisateurs'"""
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None  # filtrage côté client dans l'admin

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['role', 'verification_status', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']

    @action(detail=True, methods=['post'])
    def verify_professional(self, request, pk=None):
        """Bouton 'Approuver' sur la liste d'attente"""
        user = self.get_object()
        user.verification_status = 'verified'
        user.is_active = True
        user.save()

        # Synchronisation du booléen sur le profil spécifique pour la visibilité
        if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
            user.doctor_profile.is_verified = True
            user.doctor_profile.save()
        elif user.role == 'pharmacist' and hasattr(user, 'pharmacist_profile'):
            user.pharmacist_profile.is_verified = True
            user.pharmacist_profile.save()
        elif user.role == 'caretaker' and hasattr(user, 'caretaker_profile'):
            user.caretaker_profile.is_verified = True
            user.caretaker_profile.save()

        # Email de bienvenue (tous rôles)
        from users.utils import send_welcome_email
        send_welcome_email(user)

        # Notification à l'utilisateur
        Notification.objects.create(
            user=user,
            title="Compte approuvé !",
            message="Votre dossier a été validé par l'administration. Vous pouvez maintenant vous connecter sur Healy.",
            notification_type=Notification.NotificationType.SYSTEM
        )

        # Trace de l'action dans le journal d'audit
        create_audit_log(f"Compte {user.role} approuvé : {user.email}", AuditLog.Level.SUCCESS, request)

        return Response({"status": "Utilisateur vérifié avec succès."})

    @action(detail=True, methods=['post'])
    def reject_professional(self, request, pk=None):
        """Bouton 'Rejeter' sur la liste d'attente"""
        user = self.get_object()
        reason = request.data.get('reason', 'Dossier incomplet ou non valide.')
        user.verification_status = 'rejected'
        user.save()

        # Désynchronisation du booléen sur le profil
        if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
            user.doctor_profile.is_verified = False
            user.doctor_profile.save()
        elif user.role == 'pharmacist' and hasattr(user, 'pharmacist_profile'):
            user.pharmacist_profile.is_verified = False
            user.pharmacist_profile.save()
        elif user.role == 'caretaker' and hasattr(user, 'caretaker_profile'):
            user.caretaker_profile.is_verified = False
            user.caretaker_profile.save()

        Notification.objects.create(
            user=user,
            title="Validation refusée",
            message=f"Votre inscription n'a pas pu être validée. Motif : {reason}",
            notification_type=Notification.NotificationType.SYSTEM
        )
        create_audit_log(f"Inscription rejetée pour {user.email}", AuditLog.Level.WARNING, request)

        return Response({"status": "Utilisateur rejeté. Notification envoyée."})

    @action(detail=True, methods=['post'])
    def toggle_suspend(self, request, pk=None):
        """Bouton cadenas pour Suspendre / Réactiver un utilisateur"""
        user = self.get_object()

        # Empêcher l'admin de se suspendre lui-même
        if user == request.user:
            return Response({"error": "Vous ne pouvez pas suspendre votre propre compte admin."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = not user.is_active
        user.save()

        action_text = "réactivé" if user.is_active else "suspendu"
        log_level = AuditLog.Level.SUCCESS if user.is_active else AuditLog.Level.ERROR

        create_audit_log(f"Utilisateur {user.email} {action_text}", log_level, request)

        if not user.is_active:
             Notification.objects.create(
                user=user,
                title="Compte suspendu",
                message="Votre compte a été suspendu par l'administration. Veuillez nous contacter.",
                notification_type=Notification.NotificationType.SYSTEM
            )

        return Response({"status": f"Utilisateur {action_text} avec succès."})

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpoint pour l'écran 'Journal d'Audit'"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['level']


class AdminAppointmentListView(generics.ListAPIView):
    """GET /api/admin/appointments/ — liste tous les RDV (admin uniquement)"""
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        qs = Appointment.objects.all().select_related(
            'patient__user', 'doctor__user'
        ).order_by('date', 'start_time')
        if status := self.request.query_params.get('status'):
            qs = qs.filter(status=status)
        if date := self.request.query_params.get('date'):
            qs = qs.filter(date=date)
        return qs

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                "id": a.id,
                "patient": a.patient.user.get_full_name() if a.patient and a.patient.user else "—",
                "patient_id": a.patient.user.id if a.patient and a.patient.user else None,
                "doctor": a.doctor.user.get_full_name() if a.doctor and a.doctor.user else "—",
                "doctor_id": a.doctor.user.id if a.doctor and a.doctor.user else None,
                "specialty": getattr(a.doctor, 'specialty', '') or '',
                "date": str(a.date),
                "start_time": str(a.start_time),
                "duration_minutes": getattr(a, 'duration_minutes', 30) or 30,
                "motif": a.motif or '—',
                "status": a.status,
            }
            for a in qs
        ]
        return Response(data)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'admin' and not request.user.is_superuser:
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        users = User.objects.all()
        role_counts = users.values('role').annotate(count=Count('id'))
        distribution = {item['role']: item['count'] for item in role_counts}

        from appointments.models import Appointment
        from django.utils import timezone

        today = timezone.now().date()

        data = {
            "kpis": {
                "total_users": users.count(),
                "total_patients": users.filter(role='patient').count(),
                "total_doctors": users.filter(role='doctor').count(),
                "total_pharmacists": users.filter(role='pharmacist').count(),
                "total_caretakers": users.filter(role='caretaker').count(),
                "verified_doctors": users.filter(role='doctor', verification_status='verified').count(),
                "active_pharmacies": users.filter(role='pharmacist').count(),
                "pending_validations": users.filter(
                    verification_status='pending'
                ).count(),
                "total_appointments": Appointment.objects.count(),
                "appointments_today": Appointment.objects.filter(date=today).count(),
            },
            "role_distribution": distribution,
            "recent_registrations": [
                {
                    "name": u.get_full_name() or u.username or u.email,
                    "role": u.role,
                    "date": u.date_joined.date(),
                }
                for u in users.order_by('-date_joined')[:5]
            ],
        }
        return Response(data)


from users.models import ProfileUpdateRequest
from users.serializers import ProfileUpdateRequestSerializer
from django.utils import timezone

class AdminProfileUpdateListView(generics.ListAPIView):
    """
    (Admin) Liste toutes les demandes de changement de profil.
    """
    queryset = ProfileUpdateRequest.objects.all()
    serializer_class = ProfileUpdateRequestSerializer
    permission_classes = [IsAdminRole] # Utilise la classe locale IsAdminRole
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

class AdminProfileUpdateActionView(APIView):
    """
    (Admin) Approuve ou refuse une demande de changement de profil.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        action = request.data.get('action') # 'approve' ou 'reject'
        notes = request.data.get('admin_notes', '')

        try:
            req = ProfileUpdateRequest.objects.get(pk=pk)
        except ProfileUpdateRequest.DoesNotExist:
            return Response({'error': 'Demande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if req.status != 'pending':
            return Response({'error': 'Cette demande a déjà été traitée.'}, status=status.HTTP_400_BAD_REQUEST)

        req.reviewed_at = timezone.now()
        req.reviewed_by = request.user
        req.admin_notes = notes

        if action == 'approve':
            req.status = 'approved'
            # Appliquer les changements à l'utilisateur
            user = req.user
            user.first_name = req.new_first_name
            user.last_name = req.new_last_name
            user.save(update_fields=['first_name', 'last_name'])
            
            # Notification au patient
            Notification.objects.create(
                user=user,
                title="Changement de nom approuvé",
                message=f"Votre demande de changement de nom a été acceptée. Votre profil affiche désormais : {user.get_full_name()}.",
                notification_type=Notification.NotificationType.SYSTEM
            )
        elif action == 'reject':
            req.status = 'rejected'
            # Notification au patient
            Notification.objects.create(
                user=req.user,
                title="Changement de nom refusé",
                message=f"Votre demande de changement de nom a été refusée par l'administration. Motif : {notes or 'Non spécifié'}",
                notification_type=Notification.NotificationType.SYSTEM
            )
        else:
            return Response({'error': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        req.save()
        return Response({'message': f'Demande {req.status}.'}, status=status.HTTP_200_OK)

