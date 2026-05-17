from rest_framework import viewsets, status, filters, generics, permissions
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Caretaker, CareRequest, CareMessage, CaretakerCertificate, CaretakerTask, MedicationSchedule
from .serializers import CaretakerProfileSerializer, CareRequestSerializer, CareMessageSerializer, CaretakerCertificateSerializer, CaretakerTaskSerializer, MedicationScheduleSerializer

class CaretakerViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour les patients : Rechercher et filtrer les gardes-malades"""
    queryset = Caretaker.objects.filter(is_verified=True, is_available=True)
    serializer_class = CaretakerProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filtres exacts
    filterset_fields = ['availability_area', 'experience_years']
    # Recherche textuelle (ex: chercher une spécialité dans la bio)
    search_fields = ['bio', 'certification', 'user__first_name', 'user__last_name']

class AddCertificateView(generics.CreateAPIView):
    queryset = CaretakerCertificate.objects.all()
    serializer_class = CaretakerCertificateSerializer
    # C'est cette ligne qui permet à Django de lire les fichiers Form-Data
    parser_classes = (MultiPartParser, FormParser)    
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(caretaker=self.request.user.caretaker_profile)

class CareRequestViewSet(viewsets.ModelViewSet):
    """API pour gérer les offres d'emploi et les contrats"""
    serializer_class = CareRequestSerializer

    def get_queryset(self):
        user = self.request.user
        # Un patient voit ses demandes envoyées, un garde-malade voit celles reçues
        if user.role == 'patient':
            return CareRequest.objects.filter(patient=user)
        elif user.role == 'caretaker':
            return CareRequest.objects.filter(caretaker__user=user)
        return CareRequest.objects.none()

    def perform_create(self, serializer):
        # Le patient qui fait la requête est automatiquement défini comme le demandeur
        care_request = serializer.save(patient=self.request.user)
        from notifications.models import Notification
        Notification.objects.create(
            user=care_request.caretaker.user,
            title="Nouvelle demande de soins",
            message=f"Nouvelle demande de prise en charge reçue de {care_request.patient.get_full_name()}.",
            notification_type=Notification.NotificationType.CARETAKER
        )

    @action(detail=True, methods=['post'])
    def respond_to_offer(self, request, pk=None):
        """Action exclusive au garde-malade : Accepter ou Refuser"""
        care_request = self.get_object()
        
        # Vérification de sécurité
        if request.user != care_request.caretaker.user:
            return Response({"error": "Non autorisé"}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status not in [CareRequest.Status.ACCEPTED, CareRequest.Status.REJECTED]:
            return Response({"error": "Statut invalide"}, status=status.HTTP_400_BAD_REQUEST)

        care_request.status = new_status
        care_request.save()

        from notifications.models import Notification
        status_text = "accepté" if new_status == 'accepted' else "refusé"
        Notification.objects.create(
            user=care_request.patient,
            title=f"Demande {status_text}",
            message=f"Le garde-malade {care_request.caretaker.user.get_full_name()} a {status_text} votre demande.",
            notification_type=Notification.NotificationType.CARETAKER
        )

        msg = "Félicitations, vous avez accès au dossier médical de ce patient." if new_status == 'accepted' else "Demande refusée."
        return Response({"status": f"Demande {new_status}", "details": msg})

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Envoyer un message de chat dans le cadre d'une demande"""
        care_request = self.get_object()
        content = request.data.get('content')
        
        message = CareMessage.objects.create(
            request=care_request,
            sender=request.user,
            content=content
        )

        from notifications.models import Notification
        receiver = care_request.caretaker.user if request.user == care_request.patient else care_request.patient
        Notification.objects.create(
            user=receiver,
            title="Nouveau message",
            message=f"Nouveau message de {request.user.get_full_name()} concernant votre contrat.",
            notification_type=Notification.NotificationType.CARETAKER
        )

        return Response(CareMessageSerializer(message).data, status=status.HTTP_201_CREATED)

class CaretakerTaskViewSet(viewsets.ModelViewSet):
    """
    Garde-malade : gestion des tâches pour ses patients assignés.
    POST   /api/caretaker/tasks/             → créer une tâche
    GET    /api/caretaker/tasks/             → liste ses tâches
    PATCH  /api/caretaker/tasks/{id}/        → mettre à jour (marquer effectuée)
    DELETE /api/caretaker/tasks/{id}/        → supprimer

    Le patient associé peut aussi voir les tâches qui le concernent.
    """
    serializer_class = CaretakerTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'caretaker':
            return CaretakerTask.objects.filter(care_request__caretaker__user=user)
        if user.role == 'patient':
            return CaretakerTask.objects.filter(care_request__patient=user)
        return CaretakerTask.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != 'caretaker':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Seul un garde-malade peut créer des tâches.")
        task = serializer.save()
        from notifications.models import Notification
        Notification.objects.create(
            user=task.care_request.patient,
            title="Nouvelle tâche planifiée",
            message=f"Votre garde-malade a planifié une nouvelle tâche : {task.title}.",
            notification_type=Notification.NotificationType.CARETAKER,
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        if task.status == CaretakerTask.Status.DONE:
            from notifications.models import Notification
            Notification.objects.create(
                user=task.care_request.patient,
                title="Tâche effectuée",
                message=f"La tâche « {task.title} » a été marquée comme effectuée.",
                notification_type=Notification.NotificationType.CARETAKER,
            )
        return Response(serializer.data)


class MedicationScheduleViewSet(viewsets.ModelViewSet):
    """
    Garde-malade : plan médicamenteux (matin/après-midi/soir) pour ses patients.
    GET    /api/caretaker/medication-schedules/       → liste
    POST   /api/caretaker/medication-schedules/       → créer
    PATCH  /api/caretaker/medication-schedules/{id}/  → modifier les médicaments
    DELETE /api/caretaker/medication-schedules/{id}/  → supprimer
    """
    serializer_class   = MedicationScheduleSerializer
    permission_classes = [IsAuthenticated]
    http_method_names  = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        if self.request.user.role != 'caretaker':
            return MedicationSchedule.objects.none()
        return MedicationSchedule.objects.filter(
            care_request__caretaker__user=self.request.user
        ).select_related('care_request__patient')

    def perform_create(self, serializer):
        if self.request.user.role != 'caretaker':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Réservé aux gardes-malades.")
        care_request = serializer.validated_data['care_request']
        if care_request.caretaker.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cette demande ne vous appartient pas.")
        if care_request.status != CareRequest.Status.ACCEPTED:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("La demande doit être acceptée avant de créer un plan.")
        medications = self.request.data.get('medications', {'morning': [], 'afternoon': [], 'evening': []})
        serializer.save(medications=medications)


class CaretakerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'caretaker':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        my_requests = CareRequest.objects.filter(
            caretaker__user=user, status='accepted'
        ).select_related('patient', 'patient__patient_profile')

        def build_patient(r):
            u = r.patient  # CustomUser
            from datetime import date
            age = None
            if u.date_of_birth:
                today = date.today()
                age = today.year - u.date_of_birth.year - (
                    (today.month, today.day) < (u.date_of_birth.month, u.date_of_birth.day)
                )
            try:
                patient_profile = u.patient_profile
                conditions = list(
                    patient_profile.antecedents
                    .filter(status__in=['active', 'chronic'])
                    .values_list('name', flat=True)[:5]
                )
                patient_id = patient_profile.id
                try:
                    mp = patient_profile.medical_profile
                    emergency_contact = mp.emergency_contact_name or ""
                    emergency_phone = mp.emergency_contact_phone or ""
                except Exception:
                    emergency_contact = ""
                    emergency_phone = ""
            except Exception:
                conditions = []
                patient_id = u.id
                emergency_contact = ""
                emergency_phone = ""
            name = u.get_full_name()
            initials = "".join(w[0] for w in name.split() if w).upper()[:2] or "?"
            return {
                "id": patient_id,
                "user_id": u.id,
                "care_request_id": str(r.id),
                "name": name,
                "initials": initials,
                "age": age,
                "gender": getattr(u, 'sex', None),
                "city": getattr(u, 'city', ""),
                "address": getattr(u, 'address', "") or "",
                "phone": getattr(u, 'phone', "") or "",
                "emergencyContact": emergency_contact,
                "emergencyPhone": emergency_phone,
                "conditions": conditions,
                "condition": conditions[0] if conditions else "",
                "start_date": r.start_date,
                "end_date": r.end_date,
            }

        data = {
            "my_patients": [build_patient(r) for r in my_requests],
            "pending_requests": CareRequest.objects.filter(
                caretaker__user=user, status='pending'
            ).count(),
        }
        return Response(data)
