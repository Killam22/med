from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Caretaker, CareRequest, CareMessage
from .serializers import CaretakerProfileSerializer, CareRequestSerializer, CareMessageSerializer

class CaretakerViewSet(viewsets.ReadOnlyModelViewSet):
    """API pour les patients : Rechercher et filtrer les gardes-malades"""
    queryset = Caretaker.objects.filter(is_verified=True, is_available=True)
    serializer_class = CaretakerProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filtres exacts
    filterset_fields = ['availability_area', 'experience_years']
    # Recherche textuelle (ex: chercher une spécialité dans la bio)
    search_fields = ['bio', 'certification', 'user__first_name', 'user__last_name']

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