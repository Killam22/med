from rest_framework import serializers
from .models import Pharmacist, PharmacyBranch, PharmacyOrder
from prescriptions.serializers import PrescriptionSerializer, PrescriptionItemSerializer
from prescriptions.models import Prescription

class PharmacistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacist
        fields = '__all__'

class PharmacyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacyBranch
        fields = '__all__'

class PharmacyOrderSerializer(serializers.ModelSerializer):
    prescription_ref = serializers.SerializerMethodField()
    patient_name     = serializers.CharField(source='patient.get_full_name', read_only=True)
    pharmacist_name  = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    status_display   = serializers.CharField(source='get_status_display', read_only=True)
    items            = serializers.SerializerMethodField()

    class Meta:
        model  = PharmacyOrder
        fields = [
            'id', 'prescription', 'prescription_ref',
            'patient', 'patient_name',
            'pharmacist', 'pharmacist_name',
            'status', 'status_display',
            'patient_message', 'pharmacist_note',
            'estimated_ready', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at', 'updated_at']

    def get_prescription_ref(self, obj):
        return f"RX-{str(obj.prescription.id)[:8].upper()}"

    def get_items(self, obj):
        return PrescriptionItemSerializer(
            obj.prescription.items.all(), many=True
        ).data

class PharmacyOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PharmacyOrder
        fields = ['prescription', 'patient_message']

    def validate_prescription(self, value):
        user = self.context['request'].user
        # Si le patient est lié à l'utilisateur, on vérifie
        if hasattr(user, 'patient_profile'):
             if value.patient != user:
                raise serializers.ValidationError("Cette ordonnance ne vous appartient pas.")
        if value.status != Prescription.Status.ACTIVE:
            raise serializers.ValidationError("L'ordonnance n'est pas active.")
        return value

    def create(self, validated_data):
        return PharmacyOrder.objects.create(
            patient=self.context['request'].user,
            **validated_data
        )

class PharmacyOrderStatusSerializer(serializers.ModelSerializer):
    """Pour que le pharmacien mette à jour le statut."""
    class Meta:
        model  = PharmacyOrder
        fields = ['status', 'pharmacist_note', 'estimated_ready']