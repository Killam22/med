from rest_framework import serializers
from .models import Pharmacist, PharmacyBranch

class PharmacistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacist
        fields = '__all__'

class PharmacyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyBranch
        fields = '__all__'
