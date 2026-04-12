from rest_framework import serializers
from .models import Prescription, PrescriptionItem, QRToken
from medications.models import Medication

class PrescriptionItemSerializer(serializers.ModelSerializer):
    medication = serializers.PrimaryKeyRelatedField(
        queryset=Medication.objects.all(), required=False, allow_null=True
    )
    
    class Meta:
        model = PrescriptionItem
        fields = ['id', 'medication', 'drug_name', 'molecule', 'dosage', 'frequency', 'duration', 'instructions', 'quantity']

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


class QRScanSerializer(serializers.Serializer):
    """Serializer pour le formulaire de scan QR dans l'interface DRF."""
    token = serializers.CharField(
        max_length=200,
        help_text="Collez ici le token QR récupéré depuis GET /api/prescriptions/{id}/qr/"
    )
