# diagnostic_ai/urls.py

from django.urls import path
from .views import (
    ChatView,
    ChatStreamView,
    FileAnalysisStreamView,
    FeedbackView,
    HistoryView,
    HealthView,
    GeneticOptimizeView,
    TrainingDataView,
    ConfirmRecommendationView,
    SessionListView,
    DoctorPatientInteractionsView,
)

urlpatterns = [
    # ── Bot IA (patients) ─────────────────────────────────────
    path("chat/",                        ChatView.as_view(),                  name="ai-chat"),
    path("chat/stream/",                 ChatStreamView.as_view(),            name="ai-chat-stream"),
    path("chat/analyze-file/",           FileAnalysisStreamView.as_view(),    name="ai-analyze-file"),
    path("chat/feedback/",               FeedbackView.as_view(),              name="ai-feedback"),
    path("chat/history/",                HistoryView.as_view(),               name="ai-history"),
    path("chat/confirm-recommendation/", ConfirmRecommendationView.as_view(), name="ai-confirm-reco"),
    path("chat/sessions/",               SessionListView.as_view(),           name="ai-sessions"),

    # ── Médecin — voir conversations IA ──────────────────────
    path("doctor/interactions/",         DoctorPatientInteractionsView.as_view(), name="ai-doctor-interactions"),

    # ── Monitoring & Admin ────────────────────────────────────
    path("health/",                      HealthView.as_view(),                name="ai-health"),
    path("genetic/optimize/",            GeneticOptimizeView.as_view(),       name="ai-genetic"),
    path("training/",                    TrainingDataView.as_view(),          name="ai-training"),
]
