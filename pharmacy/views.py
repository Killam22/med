from rest_framework import generics, permissions
from .models import Pharmacist, PharmacyBranch
from .serializers import PharmacistSerializer, PharmacyBranchSerializer

class PharmacyListView(generics.ListAPIView):
    queryset = Pharmacist.objects.all()
    serializer_class = PharmacistSerializer
    permission_classes = [permissions.IsAuthenticated]

class PharmacyBranchListView(generics.ListAPIView):
    queryset = PharmacyBranch.objects.all()
    serializer_class = PharmacyBranchSerializer
    permission_classes = [permissions.IsAuthenticated]
