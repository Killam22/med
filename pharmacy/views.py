from django.db.models import Q
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Pharmacist, PharmacyBranch, PharmacyOrder
from .serializers import (
    PharmacistSerializer, PharmacyBranchSerializer,
    PharmacyOrderSerializer, PharmacyOrderCreateSerializer,
    PharmacyOrderStatusSerializer
)

class PharmacyListView(generics.ListAPIView):
    queryset = Pharmacist.objects.all()
    serializer_class = PharmacistSerializer
    permission_classes = [permissions.IsAuthenticated]

class PharmacyBranchListView(generics.ListAPIView):
    queryset = PharmacyBranch.objects.all()
    serializer_class = PharmacyBranchSerializer
    permission_classes = [permissions.IsAuthenticated]

class PharmacyOrderViewSet(viewsets.ModelViewSet):
    """
    Gestion des commandes de pharmacie.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PharmacyOrderCreateSerializer
        if self.action in ['update_status', 'partial_update']:
            return PharmacyOrderStatusSerializer
        return PharmacyOrderSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)

        if role == 'patient':
            return PharmacyOrder.objects.filter(patient=user).select_related(
                'prescription', 'pharmacist'
            ).prefetch_related('prescription__items')

        if role == 'pharmacist':
            # Un pharmacien voit les commandes qui lui sont assignées ou qui sont libres (en attente)
            return PharmacyOrder.objects.filter(
                Q(pharmacist=user) | Q(pharmacist__isnull=True)
            ).select_related('prescription', 'patient').prefetch_related(
                'prescription__items'
            )

        if user.is_staff:
            return PharmacyOrder.objects.all()

        return PharmacyOrder.objects.none()

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status not in [PharmacyOrder.Status.PENDING]:
            return Response(
                {'error': 'Impossible d\'annuler une commande déjà en préparation.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = PharmacyOrder.Status.CANCELLED
        order.save()
        return Response({'detail': 'Commande annulée.'})

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request):
        """Commandes en attente pour les pharmaciens."""
        if getattr(request.user, 'role', None) != 'pharmacist':
            return Response({'error': 'Accès pharmacien requis.'}, status=403)

        orders = PharmacyOrder.objects.filter(
            status=PharmacyOrder.Status.PENDING
        ).select_related('patient', 'prescription').prefetch_related(
            'prescription__items'
        ).order_by('created_at')

        serializer = PharmacyOrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """Mise à jour du statut par le pharmacien."""
        if getattr(request.user, 'role', None) != 'pharmacist':
            return Response({'error': 'Accès pharmacien requis.'}, status=403)

        order = self.get_object()

        # Assigner le pharmacien au premier traitement
        if not order.pharmacist:
            order.pharmacist = request.user
            order.save(update_fields=['pharmacist'])

        serializer = PharmacyOrderStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(PharmacyOrderSerializer(order).data)
class PharmacyOrderViewSet(viewsets.ModelViewSet):
    """
    Patient:
      POST   /api/pharmacy-orders/                → envoyer ordonnance à pharmacie
      GET    /api/pharmacy-orders/                → mes commandes
      GET    /api/pharmacy-orders/<id>/           → détail
      DELETE /api/pharmacy-orders/<id>/           → annuler

    Pharmacien:
      GET    /api/pharmacy-orders/incoming/       → commandes reçues
      PATCH  /api/pharmacy-orders/<id>/status/    → mettre à jour le statut
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PharmacyOrderCreateSerializer
        if self.action == 'update_status':
            return PharmacyOrderStatusSerializer
        return PharmacyOrderSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)

        if role == 'patient':
            return PharmacyOrder.objects.filter(patient=user).select_related(
                'prescription', 'pharmacist'
            ).prefetch_related('prescription__items')

        if role == 'pharmacist':
            return PharmacyOrder.objects.filter(
                Q(pharmacist=user) | Q(pharmacist__isnull=True)
            ).select_related('prescription', 'patient').prefetch_related(
                'prescription__items'
            )

        if user.is_staff:
            return PharmacyOrder.objects.all()

        return PharmacyOrder.objects.none()

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status not in [PharmacyOrder.Status.PENDING]:
            return Response(
                {'error': 'Impossible d\'annuler une commande déjà en préparation.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = PharmacyOrder.Status.CANCELLED
        order.save()
        return Response({'detail': 'Commande annulée.'})

    @action(detail=False, methods=['get'], url_path='incoming')
    def incoming(self, request):
        """
        GET /api/pharmacy-orders/incoming/
        Pharmacien : commandes en attente à traiter.
        """
        if getattr(request.user, 'role', None) != 'pharmacist':
            return Response({'error': 'Accès pharmacien requis.'}, status=403)

        orders = PharmacyOrder.objects.filter(
            status=PharmacyOrder.Status.PENDING
        ).select_related('patient', 'prescription').prefetch_related(
            'prescription__items'
        ).order_by('created_at')

        serializer = PharmacyOrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """
        PATCH /api/pharmacy-orders/<id>/status/
        Pharmacien : mettre à jour le statut d'une commande.
        Body: { "status": "preparing", "pharmacist_note": "...", "estimated_ready": "..." }
        """
        if getattr(request.user, 'role', None) != 'pharmacist':
            return Response({'error': 'Accès pharmacien requis.'}, status=403)

        order = self.get_object()

        # Assigner le pharmacien si pas encore fait
        if not order.pharmacist:
            order.pharmacist = request.user
            order.save(update_fields=['pharmacist'])

        serializer = PharmacyOrderStatusSerializer(
            order, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(PharmacyOrderSerializer(order).data)