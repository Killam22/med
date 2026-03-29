from rest_framework import generics, permissions
from .models import Caretaker, CaretakerService
from .serializers import CaretakerSerializer, CaretakerServiceSerializer

class CaretakerListView(generics.ListAPIView):
    queryset = Caretaker.objects.all()
    serializer_class = CaretakerSerializer
    permission_classes = [permissions.IsAuthenticated]

class CaretakerServiceListView(generics.ListAPIView):
    queryset = CaretakerService.objects.all()
    serializer_class = CaretakerServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
