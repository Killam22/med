# diagnostic_ai/admin.py

from django.contrib import admin
from .models import (
    Interaction, FileUpload, ConversationSession,
    DiagnosisCache, QuestionCache, TrainingData, GeneticRun,
)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display    = ["id", "get_patient", "lang", "urgency", "specialist",
                       "recommended_doctor", "feedback", "from_cache", "created_at"]
    list_filter     = ["lang", "urgency", "feedback", "from_cache"]
    search_fields   = ["symptoms", "patient__user__first_name", "patient__user__last_name"]
    readonly_fields = ["created_at"]
    ordering        = ["-created_at"]
    list_per_page   = 50

    def get_patient(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "Anonyme"
    get_patient.short_description = "Patient"


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display    = ["id", "get_patient", "file_type", "original_name", "mime_type", "created_at"]
    list_filter     = ["file_type", "mime_type"]
    search_fields   = ["patient__user__first_name", "original_name"]
    readonly_fields = ["created_at"]
    list_per_page   = 50

    def get_patient(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "Anonyme"
    get_patient.short_description = "Patient"


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display    = ["id", "get_patient", "lang", "title", "message_count", "is_active", "updated_at"]
    list_filter     = ["lang", "is_active"]
    search_fields   = ["patient__user__first_name", "title"]
    readonly_fields = ["created_at", "updated_at"]
    ordering        = ["-updated_at"]
    list_per_page   = 50

    def get_patient(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "Anonyme"
    get_patient.short_description = "Patient"

    def message_count(self, obj):
        return obj.message_count
    message_count.short_description = "Messages"


@admin.register(DiagnosisCache)
class DiagnosisCacheAdmin(admin.ModelAdmin):
    list_display    = ["id", "symptoms_short", "lang", "urgency", "hit_count", "created_at"]
    list_filter     = ["lang", "urgency"]
    search_fields   = ["symptoms_text"]
    readonly_fields = ["symptoms_hash", "created_at", "updated_at"]
    ordering        = ["-hit_count"]
    list_per_page   = 50

    def symptoms_short(self, obj):
        return obj.symptoms_text[:60]
    symptoms_short.short_description = "Symptômes"


@admin.register(QuestionCache)
class QuestionCacheAdmin(admin.ModelAdmin):
    list_display    = ["id", "question_short", "lang", "intent", "hit_count", "created_at"]
    list_filter     = ["lang", "intent"]
    readonly_fields = ["question_hash", "created_at", "updated_at"]
    ordering        = ["-hit_count"]
    list_per_page   = 50

    def question_short(self, obj):
        return obj.question_text[:60]
    question_short.short_description = "Question"


@admin.register(TrainingData)
class TrainingDataAdmin(admin.ModelAdmin):
    list_display = ["id", "symptoms_short", "specialist", "urgency", "quality_score", "lang", "created_at"]
    list_filter  = ["urgency", "lang"]
    ordering     = ["-quality_score"]
    list_per_page = 50

    def symptoms_short(self, obj):
        return obj.symptoms[:60]
    symptoms_short.short_description = "Symptômes"


@admin.register(GeneticRun)
class GeneticRunAdmin(admin.ModelAdmin):
    list_display    = ["id", "generation", "best_fitness", "population_size", "created_at"]
    readonly_fields = ["created_at"]
    ordering        = ["-best_fitness"]
    list_per_page   = 20
