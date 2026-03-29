from rest_framework import serializers
from .models import Caretaker, CaretakerService

class CaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caretaker
        fields = '__all__'

class CaretakerServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaretakerService
        fields = '__all__'
