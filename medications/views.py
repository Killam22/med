from django.shortcuts import render

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Medication
from .serializers import MedicationSerializer
from .permissions import IsAdminOrReadOnly

class MedicationViewSet(viewsets.ModelViewSet):
    """
    API pour consulter et gérer le registre global des médicaments.
    """
    queryset = Medication.objects.filter(is_active=True)
    serializer_class = MedicationSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    # Ajout des barres de recherche pour le frontend (Pharmacie en ligne / Medecin)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'requires_prescription', 'cnas_covered', 'is_shifa_compatible']
    search_fields = ['name', 'molecule', 'barcode']