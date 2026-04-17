from rest_framework import serializers
from .models import Pharmacist, Pharmacy, PharmacyOrder, PharmacyStock, PharmacistQualification
from medications.serializers import MedicationSerializer
from prescriptions.serializers import PrescriptionSerializer, PrescriptionItemSerializer
from prescriptions.models import Prescription

class PharmacistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacist
        fields = [
            'id', 'user', 'order_registration_number', 'is_verified', 
        ]

class PharmacySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy    
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
        if not obj.prescription:
            return None
        return f"RX-{str(obj.prescription.id)[:8].upper()}"

    def get_items(self, obj):
        if not obj.prescription:
            return []
        return PrescriptionItemSerializer(
            obj.prescription.items.all(), many=True
        ).data

class PharmacyOrderCreateSerializer(serializers.ModelSerializer):
    prescription = serializers.PrimaryKeyRelatedField(
        queryset=Prescription.objects.all(), required=False, allow_null=True
    )
    
    class Meta:
        model  = PharmacyOrder
        fields = [
            'prescription', 'patient_message', 'order_type', 
            'withdrawal_method', 'caretaker'
        ]

    def validate(self, data):
        order_type = data.get('order_type', PharmacyOrder.OrderType.PRESCRIPTION)
        prescription = data.get('prescription')

        if order_type == PharmacyOrder.OrderType.PRESCRIPTION:
            if not prescription:
                raise serializers.ValidationError({"prescription": "Une ordonnance est requise pour ce type de commande."})
                
            user = self.context['request'].user
            # Vérifier si l'ordonnance appartient au patient
            if hasattr(user, 'patient_profile'):
                 if getattr(prescription, 'patient', None) != user:
                    raise serializers.ValidationError({"prescription": "Cette ordonnance ne vous appartient pas."})
                    
            if getattr(prescription, 'status', None) != Prescription.Status.ACTIVE:
                raise serializers.ValidationError({"prescription": "L'ordonnance n'est pas active."})
                
        elif order_type == PharmacyOrder.OrderType.DIRECT:
            if prescription:
                raise serializers.ValidationError({"prescription": "Une commande d'achat direct ne doit pas inclure d'ordonnance."})

        return data

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

class PharmacyStockSerializer(serializers.ModelSerializer):
    # Pour l'affichage frontend (lecture seule)
    medication_details = MedicationSerializer(source='medication', read_only=True)
    
    class Meta:
        model = PharmacyStock
        fields = [
            'id', 'pharmacist', 'medication', 'medication_details', 
            'quantity', 'selling_price', 'expiry_date', 
            'last_updated'
        ]
        read_only_fields = ['pharmacist']
        
    def validate(self, data):
        """Validation personnalisée : un stock négatif n'est pas permis"""
        if data.get('quantity', 0) < 0:
            raise serializers.ValidationError({"quantity": "La quantité ne peut pas être négative."})
        return data

class PharmacistQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacistQualification   
        fields = '__all__'