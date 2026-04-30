from rest_framework import viewsets, status, filters, generics, permissions
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Caretaker, CareRequest, CareMessage, CaretakerCertificate, CaretakerTask
from .serializers import CaretakerProfileSerializer, CareRequestSerializer, CareMessageSerializer, CaretakerCertificateSerializer, CaretakerTaskSerializer

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


class CaretakerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        if getattr(request.user, 'role', None) != 'caretaker':
            return Response({"error": "Accès refusé"}, status=status.HTTP_403_FORBIDDEN)

        user = request.user
        my_requests = CareRequest.objects.filter(caretaker__user=user, status='accepted')

        data = {
            "my_patients": [
                {
                    "name": r.patient.get_full_name(),
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                }
                for r in my_requests
            ],
            "pending_requests": CareRequest.objects.filter(
                caretaker__user=user, status='pending'
            ).count(),
        }
        return Response(data)
