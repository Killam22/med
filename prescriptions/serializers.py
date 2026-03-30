from rest_framework import serializers
from .models import Prescription, PrescriptionItem, Medication, QRToken

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class MedicationAutocompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ['id', 'name', 'molecule', 'dosage_forms']

class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ['id', 'drug_name', 'molecule', 'dosage', 'frequency', 'duration', 'instructions', 'quantity']

class QRTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = QRToken
        fields = ['token', 'expires_at', 'is_used']

class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    doctor_name = serializers.ReadOnlyField(source='doctor.user.get_full_name')
    patient_name = serializers.ReadOnlyField(source='patient.user.get_full_name')
    qr_token = QRTokenSerializer(read_only=True)

    class Meta:
        model = Prescription
        fields = [
            'id', 'status', 'notes', 'valid_until',
            'created_at', 'updated_at', 'items', 'qr_token',
            'doctor_name', 'patient_name'
        ]

class PrescriptionCreateSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True)

    class Meta:
        model = Prescription
        fields = ['consultation', 'notes', 'valid_until', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        prescription = Prescription.objects.create(**validated_data)
        for item_data in items_data:
            PrescriptionItem.objects.create(prescription=prescription, **item_data)
        return prescription
