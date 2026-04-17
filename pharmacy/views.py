from django.db.models import Q
from rest_framework import generics, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Pharmacist, PharmacyOrder, PharmacyStock , Pharmacy
from .serializers import (
    PharmacistSerializer,
    PharmacyOrderSerializer, PharmacyOrderCreateSerializer,
    PharmacyOrderStatusSerializer,
    PharmacyStockSerializer, PharmacySerializer
)

class PharmacistListView(generics.ListAPIView):
    queryset = Pharmacist.objects.all()
    serializer_class = PharmacistSerializer
    permission_classes = [permissions.IsAuthenticated]

class PharmacyListView(generics.ListAPIView):
    queryset = Pharmacy.objects.all()
    serializer_class = PharmacySerializer
    permission_classes = [permissions.IsAuthenticated]


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

    def perform_create(self, serializer):
        order = serializer.save(patient=self.request.user)
        if order.pharmacist:
            from notifications.models import Notification
            Notification.objects.create(
                user=order.pharmacist,
                title="Nouvelle commande",
                message="Nouvelle commande en attente de préparation.",
                notification_type=Notification.NotificationType.PHARMACY
            )

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
        updated_order = serializer.save()

        from notifications.models import Notification
        if updated_order.status == 'preparing':
            Notification.objects.create(
                user=updated_order.patient,
                title="Commande en préparation",
                message="Votre commande a été acceptée et est en cours de préparation.",
                notification_type=Notification.NotificationType.PHARMACY
            )
        elif updated_order.status == 'ready':
            Notification.objects.create(
                user=updated_order.patient,
                title="Commande prête !",
                message="Votre commande est prête à être récupérée !",
                notification_type=Notification.NotificationType.PHARMACY
            )

        return Response(PharmacyOrderSerializer(updated_order).data)

class PharmacyStockViewSet(viewsets.ModelViewSet):
    """API pour les pharmaciens pour gérer leur inventaire personnel"""
    serializer_class = PharmacyStockSerializer

    def get_queryset(self):
        # Un pharmacien ne voit que son propre stock
        return PharmacyStock.objects.filter(pharmacist__user=self.request.user)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        if not hasattr(self.request.user, 'pharmacist_profile'):
            raise PermissionDenied("Vous devez être pharmacien pour gérer un stock.")
        stock = serializer.save(pharmacist=self.request.user.pharmacist_profile)
        self._check_low_stock(stock)

    def perform_update(self, serializer):
        stock = serializer.save()
        self._check_low_stock(stock)

    def _check_low_stock(self, stock):
        if stock.quantity < 10:
            from notifications.models import Notification
            # Nom du médicament (en supposant que stock.medication.name existe)
            med_name = getattr(stock.medication, 'name', 'ce médicament')
            Notification.objects.create(
                user=stock.pharmacist.user,
                title="Alerte Stock critique",
                message=f"Alerte : Le stock de {med_name} est critique.",
                notification_type=Notification.NotificationType.PHARMACY
            )

    @action(detail=False, methods=['get'], url_path='search-nearby')
    def search_nearby(self, request):
        """Recherche de médicaments en stock selon la position du patient"""
        medication_id = request.query_params.get('medication_id')
        lat = float(request.query_params.get('lat'))
        lon = float(request.query_params.get('lon'))

        # Logique de proximité (Haversine simplifiée dans l'ORM)
        # On filtre les pharmacies qui ont le médicament en stock > 0
        stocks = PharmacyStock.objects.filter(
            medication_id=medication_id,
            quantity__gt=0,
            pharmacist__latitude__isnull=False
        ).select_related('pharmacist')

        # Note : Pour une production réelle, utilisez PostGIS. 
        # Ici on retourne les officines filtrées.
        results = []
        for s in stocks:
            results.append({
                "pharmacy_name": s.pharmacist.pharmacy_name,
                "address": s.pharmacist.address,
                "distance_approx": "Calculée côté client ou via PostGIS",
                "stock_quantity": s.quantity,
                "price": s.selling_price or s.medication.price_dzd
            })
        
        return Response(results)        