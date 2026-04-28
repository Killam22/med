# diagnostic_ai/serializers.py

from rest_framework import serializers
from .models import Interaction, TrainingData, GeneticRun, ConversationSession


class ChatRequestSerializer(serializers.Serializer):
    symptoms = serializers.CharField(
        min_length=3, max_length=2000,
        error_messages={
            "min_length": "Décrivez vos symptômes en au moins 3 caractères.",
            "max_length": "Description trop longue (max 2000 caractères).",
            "required":   "Les symptômes sont obligatoires.",
        }
    )
    lang    = serializers.ChoiceField(choices=["fr", "ar", "en"], default="fr")
    history = serializers.ListField(
        child=serializers.DictField(), required=False, default=list, max_length=20,
    )


class RecommendedDoctorSerializer(serializers.Serializer):
    """Médecin recommandé par le bot après diagnostic."""
    id               = serializers.IntegerField()
    full_name        = serializers.CharField()
    specialty        = serializers.CharField()
    specialty_code   = serializers.CharField()
    clinic_name      = serializers.CharField()
    city             = serializers.CharField()
    address          = serializers.CharField()
    phone            = serializers.CharField()
    consultation_fee = serializers.FloatField()
    rating           = serializers.FloatField()
    experience_years = serializers.IntegerField()
    cnas_coverage    = serializers.BooleanField()
    languages        = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    interaction_id      = serializers.IntegerField()
    response            = serializers.CharField()
    diseases            = serializers.ListField(child=serializers.DictField())
    specialist          = serializers.DictField()
    urgency             = serializers.CharField()
    recommended_doctors = RecommendedDoctorSerializer(many=True)  # ✅ NOUVEAU


class FeedbackSerializer(serializers.Serializer):
    interaction_id = serializers.IntegerField()
    feedback       = serializers.IntegerField(
        min_value=0, max_value=1,
        error_messages={
            "min_value": "Feedback doit être 0 ou 1.",
            "max_value": "Feedback doit être 0 ou 1.",
        }
    )


class InteractionSerializer(serializers.ModelSerializer):
    patient_name        = serializers.SerializerMethodField()
    recommended_doctors = serializers.SerializerMethodField()

    class Meta:
        model  = Interaction
        fields = [
            "id", "patient_name", "symptoms", "response", "lang",
            "urgency", "specialist", "recommended_doctors",
            "feedback", "from_cache", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "Anonyme"

    def get_recommended_doctors(self, obj):
        if obj.recommended_doctor:
            from diagnostic_ai.services.doctor_recommender import _serialize_doctor
            return [_serialize_doctor(obj.recommended_doctor)]
        return []


class ConversationSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message  = serializers.SerializerMethodField()
    history       = serializers.SerializerMethodField()
    patient_name  = serializers.SerializerMethodField()

    class Meta:
        model  = ConversationSession
        fields = [
            "id", "patient_name", "lang", "title",
            "message_count", "last_message", "history",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_message_count(self, obj):
        return obj.message_count

    def get_last_message(self, obj):
        return obj.last_message

    def get_history(self, obj):
        return obj.get_gemini_history()

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "Anonyme"


class GeneticRunSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GeneticRun
        fields = ["id", "generation", "best_fitness", "best_chromosome",
                  "population_size", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class TrainingDataSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TrainingData
        fields = ["id", "symptoms", "specialist", "urgency",
                  "quality_score", "lang", "created_at"]
        read_only_fields = ["id", "created_at"]
