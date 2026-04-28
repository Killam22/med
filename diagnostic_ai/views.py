# diagnostic_ai/views.py

import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django.http import StreamingHttpResponse

from diagnostic_ai.serializers import (
    ChatRequestSerializer,
    FeedbackSerializer,
    InteractionSerializer,
    GeneticRunSerializer,
    TrainingDataSerializer,
)
from diagnostic_ai.models import (
    Interaction, TrainingData, GeneticRun,
    FileUpload, ConversationSession,
)
from diagnostic_ai.services.rag_service import process_chat, process_chat_stream
from diagnostic_ai.services.genetic.optimizer import GeneticOptimizer

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "image/gif", "application/pdf",
}
MAX_FILE_SIZE_MB = 10

URGENCY_10_KEYWORDS = [
    "douleur poitrine", "bras gauche", "infarctus", "arrêt cardiaque",
    "perte de conscience", "convulsion", "paralysie", "avc",
    "saignement abondant", "difficulté respirer", "méningite",
    "chest pain", "left arm", "heart attack", "loss of consciousness",
    "seizure", "paralysis", "stroke", "severe bleeding", "cannot breathe",
    "ألم صدري", "ألم في الصدر", "فقدان وعي", "تشنج", "شلل",
]

URGENCY_SCORES = {"urgent": 3, "modéré": 2, "faible": 1}


# ══════════════════════════════════════════════════════════════
# RATE LIMITING — 5 diagnostics/jour/patient
# ══════════════════════════════════════════════════════════════

class DiagnosisRateThrottle(UserRateThrottle):
    """
    Limite chaque utilisateur à 5 appels de diagnostic par jour.
    Protège le quota Gemini contre le spam.
    Configurer dans settings.py :
        DEFAULT_THROTTLE_RATES = { 'diagnosis': '5/day', ... }
    """
    scope = 'diagnosis'


# ══════════════════════════════════════════════════════════════
# HELPER — Contexte médical du patient
# ══════════════════════════════════════════════════════════════

def _get_patient_medical_context(patient, lang: str = "fr") -> str:
    """
    Construit un bloc de contexte médical personnalisé à injecter dans le prompt
    Gemini. Inclut allergies, antécédents actifs et traitements en cours.

    Retourne une chaîne vide si aucune donnée n'est disponible (sécurité, pas de crash).
    """
    if not patient:
        return ""

    try:
        lines = []

        # ── Allergies ──────────────────────────────────────────────────
        try:
            profile = getattr(patient, 'medical_profile', None)
            if profile:
                allergies = list(profile.allergies.all())
                if allergies:
                    allergy_list = ", ".join(
                        f"{a.substance} ({a.get_severity_display()})"
                        for a in allergies
                    )
                    if lang == "ar":
                        lines.append(f"الحساسية المعروفة: {allergy_list}")
                    elif lang == "en":
                        lines.append(f"Known allergies: {allergy_list}")
                    else:
                        lines.append(f"Allergies connues: {allergy_list}")
        except Exception:
            pass

        # ── Antécédents actifs ─────────────────────────────────────────
        try:
            antecedents = list(
                patient.antecedents.filter(status__in=['active', 'chronic'])
            )
            if antecedents:
                ant_list = ", ".join(
                    f"{a.name} ({a.get_type_display()}, {a.get_status_display()})"
                    for a in antecedents
                )
                if lang == "ar":
                    lines.append(f"السوابق الطبية الفعّالة: {ant_list}")
                elif lang == "en":
                    lines.append(f"Active medical history: {ant_list}")
                else:
                    lines.append(f"Antécédents actifs: {ant_list}")
        except Exception:
            pass

        # ── Traitements en cours ───────────────────────────────────────
        try:
            treatments = [t for t in patient.treatments.all() if t.is_active]
            if treatments:
                treat_list = ", ".join(
                    f"{t.medication_name} {t.dosage} ({t.get_frequency_display()})"
                    for t in treatments
                )
                if lang == "ar":
                    lines.append(f"العلاجات الجارية: {treat_list}")
                elif lang == "en":
                    lines.append(f"Current treatments: {treat_list}")
                else:
                    lines.append(f"Traitements en cours: {treat_list}")
        except Exception:
            pass

        if not lines:
            return ""

        if lang == "ar":
            header = "═══ المعلومات الطبية للمريض ═══"
            footer = "═══════════════════════════════"
            note   = "⚠️ يجب مراعاة هذه المعلومات أثناء التشخيص وتجنب التوصية بالأدوية المتعارضة مع علاجاته الحالية أو مسبباته الحساسية."
        elif lang == "en":
            header = "═══ PATIENT MEDICAL CONTEXT ═══"
            footer = "═══════════════════════════════"
            note   = "⚠️ Consider this information during diagnosis. Avoid recommending medications that conflict with current treatments or known allergies."
        else:
            header = "═══ CONTEXTE MÉDICAL DU PATIENT ═══"
            footer = "════════════════════════════════════"
            note   = "⚠️ Tiens compte de ces informations dans ton analyse. Évite de recommander des médicaments en conflit avec ses traitements actuels ou ses allergies connues."

        return "\n".join([header] + lines + [note, footer])

    except Exception as e:
        logger.warning("Impossible de récupérer le contexte médical: %s", e)
        return ""


def compute_real_urgency(symptoms: str, diseases: list) -> str:
    if any(kw in symptoms.lower() for kw in URGENCY_10_KEYWORDS):
        return "urgent"
    if not diseases:
        return "modéré"
    counts = {"urgent": 0, "modéré": 0, "faible": 0}
    for d in diseases:
        u = d.get("urgency", "modéré").lower()
        if u in counts:
            counts[u] += 1
    if counts["urgent"] >= 2:
        return "urgent"
    elif counts["modéré"] >= 1:
        return "modéré"
    return "faible"


def sort_diseases_by_danger(diseases: list) -> list:
    return sorted(diseases, key=lambda d: URGENCY_SCORES.get(
        d.get("urgency", "modéré").lower(), 2
    ))


def _get_patient(request):
    """Récupère le Patient depuis le JWT (request.user)."""
    try:
        return request.user.patient_profile
    except Exception:
        return None


def _save_session(patient, lang: str, user_msg: str, bot_response: str) -> None:
    try:
        session, created = ConversationSession.objects.get_or_create(
            patient   = patient,
            is_active = True,
            lang      = lang,
            defaults  = {"title": user_msg[:60], "history": []},
        )
        session.add_message(role="user",      content=user_msg)
        session.add_message(role="assistant", content=bot_response)
        if created:
            session.auto_title()
        logger.info("Session #%d mise à jour (%d messages)", session.id, session.message_count)
    except Exception as e:
        logger.warning("Session save error (non bloquant): %s", e)


# ══════════════════════════════════════════════════════════════
# CHAT NORMAL
# ══════════════════════════════════════════════════════════════

class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [DiagnosisRateThrottle]   # ← Rate limiting

    def post(self, request):
        if request.user.role != 'patient':
            return Response(
                {"error": "Seuls les patients peuvent utiliser le bot IA."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data    = serializer.validated_data
        patient = _get_patient(request)
        lang    = data["lang"]

        # ── Contexte médical personnalisé ─────────────────────────────
        medical_context = _get_patient_medical_context(patient, lang)
        if medical_context:
            logger.info("Contexte médical injecté pour patient #%s", getattr(patient, 'id', '?'))

        try:
            result = process_chat(
                symptoms        = data["symptoms"],
                lang            = lang,
                history         = data.get("history", []),
                patient         = patient,
                medical_context = medical_context,   # ← NOUVEAU
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Erreur pipeline RAG")
            return Response({"error": "Erreur interne du serveur"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        needs_more_details  = result.get("needs_more_details", False)
        diseases            = result.get("diseases", [])
        diseases_sorted     = sort_diseases_by_danger(diseases)
        real_urgency        = compute_real_urgency(data["symptoms"], diseases)
        recommended_doctors = result.get("recommended_doctors", [])

        top_doctor_id = recommended_doctors[0]["id"] if recommended_doctors else None
        top_doctor    = None
        if top_doctor_id:
            try:
                from doctors.models import Doctor
                top_doctor = Doctor.objects.get(id=top_doctor_id)
            except Exception:
                pass

        interaction = Interaction.objects.create(
            patient                = patient,
            symptoms               = data["symptoms"],
            response               = result["response"],
            lang                   = lang,
            urgency                = real_urgency,
            specialist             = result.get("specialist", {}).get("specialty_fr", ""),
            recommended_doctor     = top_doctor,
            pending_recommendation = None if needs_more_details else result.get("pending_recommendation", ""),
            recommendation_sent    = False,
            from_cache             = result.get("from_cache", False),
        )

        if not needs_more_details and patient:
            _save_session(
                patient      = patient,
                lang         = lang,
                user_msg     = data["symptoms"],
                bot_response = result["response"],
            )

        return Response({
            "interaction_id":      interaction.id,
            "response":            result["response"],
            "diseases":            diseases_sorted,
            "specialist":          result["specialist"],
            "urgency":             real_urgency,
            "ask_recommendation":  result.get("ask_recommendation", False) and not needs_more_details,
            "needs_more_details":  needs_more_details,
            "from_cache":          result.get("from_cache", False),
            "recommended_doctors": recommended_doctors,
        }, status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════════════
# CHAT STREAMING
# ══════════════════════════════════════════════════════════════

class ChatStreamView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes   = [DiagnosisRateThrottle]   # ← Rate limiting

    def post(self, request):
        if request.user.role != 'patient':
            return Response(
                {"error": "Seuls les patients peuvent utiliser le bot IA."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data    = serializer.validated_data
        patient = _get_patient(request)
        lang    = data["lang"]

        medical_context = _get_patient_medical_context(patient, lang)

        def event_stream():
            try:
                pending_reco        = None
                full_response       = ""
                diseases            = []
                specialist          = {}
                urgency             = "modéré"
                needs_details       = False
                ask_reco            = False
                recommended_doctors = []

                for event in process_chat_stream(
                    symptoms        = data["symptoms"],
                    lang            = lang,
                    history         = data.get("history", []),
                    patient         = patient,
                    medical_context = medical_context,   # ← NOUVEAU
                ):
                    if event.startswith("data: ") and event.strip() != "data: [DONE]":
                        try:
                            payload = json.loads(event[6:].strip())
                            if payload.get("type") == "meta":
                                diseases            = payload.get("diseases", [])
                                specialist          = payload.get("specialist", {})
                                urgency             = payload.get("urgency", "modéré")
                                needs_details       = payload.get("needs_more_details", False)
                                ask_reco            = payload.get("ask_recommendation", False)
                                pending_reco        = payload.get("pending_recommendation")
                                recommended_doctors = payload.get("recommended_doctors", [])

                                diseases_sorted = sort_diseases_by_danger(diseases)
                                real_urgency    = compute_real_urgency(data["symptoms"], diseases)

                                corrected_meta = {
                                    "type":                   "meta",
                                    "diseases":               diseases_sorted,
                                    "specialist":             specialist,
                                    "urgency":                real_urgency,
                                    "needs_more_details":     needs_details,
                                    "ask_recommendation":     ask_reco,
                                    "pending_recommendation": pending_reco,
                                    "recommended_doctors":    recommended_doctors,
                                }
                                yield f"data: {json.dumps(corrected_meta, ensure_ascii=False)}\n\n"
                                continue

                            elif payload.get("type") == "chunk":
                                full_response += payload.get("text", "")
                            elif payload.get("type") == "recommendation":
                                pending_reco = payload.get("text", "")

                        except Exception:
                            pass

                    yield event

                final_urgency = compute_real_urgency(data["symptoms"], diseases)

                top_doctor = None
                if recommended_doctors:
                    try:
                        from doctors.models import Doctor
                        top_doctor = Doctor.objects.get(id=recommended_doctors[0]["id"])
                    except Exception:
                        pass

                try:
                    interaction = Interaction.objects.create(
                        patient                = patient,
                        symptoms               = data["symptoms"],
                        response               = full_response,
                        lang                   = lang,
                        urgency                = final_urgency,
                        specialist             = specialist.get("specialty_fr", ""),
                        recommended_doctor     = top_doctor,
                        pending_recommendation = None if needs_details else pending_reco,
                        recommendation_sent    = False,
                        from_cache             = False,
                    )
                    yield f"data: {json.dumps({'type': 'interaction_id', 'id': interaction.id}, ensure_ascii=False)}\n\n"

                    if not needs_details and patient:
                        _save_session(
                            patient      = patient,
                            lang         = lang,
                            user_msg     = data["symptoms"],
                            bot_response = full_response,
                        )
                except Exception:
                    logger.exception("Erreur création interaction après stream")

            except Exception:
                logger.exception("Erreur stream pipeline RAG")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Erreur interne du serveur'})}\n\n"
                yield "data: [DONE]\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
        response["Cache-Control"]               = "no-cache"
        response["X-Accel-Buffering"]           = "no"
        response["Access-Control-Allow-Origin"] = "*"
        return response


# ══════════════════════════════════════════════════════════════
# ANALYSE FICHIERS MÉDICAUX
# ══════════════════════════════════════════════════════════════

class FileAnalysisStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "Aucun fichier envoyé."}, status=status.HTTP_400_BAD_REQUEST)

        if file.content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {"error": "Format non supporté. Acceptés : JPG, PNG, WEBP, GIF, PDF."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if file.size / (1024 * 1024) > MAX_FILE_SIZE_MB:
            return Response({"error": "Fichier trop grand (max 10 MB)."}, status=status.HTTP_400_BAD_REQUEST)

        patient    = _get_patient(request)
        message    = request.data.get("message", "").strip()
        lang       = request.data.get("lang", "fr")
        mime_type  = file.content_type
        file_bytes = file.read()

        history_raw = request.data.get("history", "[]")
        try:
            history = json.loads(history_raw) if isinstance(history_raw, str) else history_raw
        except Exception:
            history = []

        def event_stream():
            from diagnostic_ai.services.gemini_service import (
                generate_file_analysis_stream,
                detect_file_type,
                FILE_CLARIFICATION_QUESTIONS,
            )
            try:
                if not message:
                    clarification = FILE_CLARIFICATION_QUESTIONS.get(lang, FILE_CLARIFICATION_QUESTIONS["fr"])
                    yield f"data: {json.dumps({'type': 'clarification'}, ensure_ascii=False)}\n\n"
                    for char in clarification:
                        yield f"data: {json.dumps({'type': 'chunk', 'text': char}, ensure_ascii=False)}\n\n"
                    try:
                        interaction = Interaction.objects.create(
                            patient=patient, symptoms=f"[FICHIER: {file.name}]",
                            response=clarification, lang=lang, urgency="modéré",
                        )
                        yield f"data: {json.dumps({'type': 'interaction_id', 'id': interaction.id}, ensure_ascii=False)}\n\n"
                    except Exception:
                        logger.exception("Erreur interaction clarification")
                    yield "data: [DONE]\n\n"
                    return

                file_type = detect_file_type(message, mime_type)
                if file_type != "non_medical":
                    yield f"data: {json.dumps({'type': 'file_type', 'value': file_type}, ensure_ascii=False)}\n\n"

                full_response = ""
                for chunk_text in generate_file_analysis_stream(
                    file_bytes=file_bytes, mime_type=mime_type,
                    message=message, lang=lang, history=history,
                ):
                    full_response += chunk_text
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text}, ensure_ascii=False)}\n\n"

                try:
                    interaction = Interaction.objects.create(
                        patient=patient, symptoms=f"[FICHIER: {file.name}] {message}",
                        response=full_response, lang=lang, urgency="modéré",
                    )
                    yield f"data: {json.dumps({'type': 'interaction_id', 'id': interaction.id}, ensure_ascii=False)}\n\n"
                except Exception:
                    logger.exception("Erreur interaction analyse fichier")

                yield "data: [DONE]\n\n"

            except Exception:
                logger.exception("Erreur FileAnalysisStreamView")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Erreur interne'})}\n\n"
                yield "data: [DONE]\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream; charset=utf-8")
        response["Cache-Control"]     = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# ══════════════════════════════════════════════════════════════
# CONFIRM RECOMMENDATION
# ══════════════════════════════════════════════════════════════

class ConfirmRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        interaction_id = request.data.get("interaction_id")
        confirmed      = request.data.get("confirmed", False)

        if not interaction_id:
            return Response({"error": "interaction_id requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            interaction = Interaction.objects.get(id=interaction_id, patient=_get_patient(request))
        except Interaction.DoesNotExist:
            return Response({"error": "Interaction introuvable"}, status=status.HTTP_404_NOT_FOUND)

        if not confirmed:
            return Response({"message": "D'accord, n'hésitez pas si vous avez d'autres questions."})

        interaction.recommendation_sent = True
        interaction.save(update_fields=["recommendation_sent"])
        return Response({"recommendation": interaction.pending_recommendation})


# ══════════════════════════════════════════════════════════════
# FEEDBACK
# ══════════════════════════════════════════════════════════════

class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            interaction          = Interaction.objects.get(
                id=data["interaction_id"], patient=_get_patient(request)
            )
            interaction.feedback = data["feedback"]
            interaction.save(update_fields=["feedback"])

            if data["feedback"] == 1:
                TrainingData.objects.get_or_create(
                    symptoms=interaction.symptoms,
                    defaults={
                        "ideal_response": interaction.response,
                        "specialist":     interaction.specialist,
                        "urgency":        interaction.urgency,
                        "lang":           interaction.lang,
                        "quality_score":  1.0,
                        "diseases":       [],
                    }
                )
            return Response({"status": "success", "message": "Merci pour votre retour !"})

        except Interaction.DoesNotExist:
            return Response({"error": "Interaction introuvable"}, status=status.HTTP_404_NOT_FOUND)


# ══════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════

class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        patient = _get_patient(request)
        if not patient:
            return Response({"error": "Profil patient introuvable"}, status=status.HTTP_404_NOT_FOUND)

        limit        = int(request.query_params.get("limit", 20))
        interactions = Interaction.objects.filter(patient=patient)[:limit]
        serializer   = InteractionSerializer(interactions, many=True)
        return Response({
            "patient": request.user.get_full_name(),
            "count":   interactions.count(),
            "results": serializer.data,
        })


# ══════════════════════════════════════════════════════════════
# DOCTOR — voir les interactions IA de ses patients
# ══════════════════════════════════════════════════════════════

class DoctorPatientInteractionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'doctor':
            return Response(
                {"error": "Réservé aux médecins."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            doctor = request.user.doctor_profile
        except Exception:
            return Response({"error": "Profil médecin introuvable"}, status=status.HTTP_404_NOT_FOUND)

        qs = Interaction.objects.filter(recommended_doctor=doctor).select_related('patient__user')

        patient_id = request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient__id=patient_id)

        limit      = int(request.query_params.get("limit", 50))
        qs         = qs[:limit]
        serializer = InteractionSerializer(qs, many=True)

        return Response({
            "doctor":  f"Dr. {request.user.get_full_name()}",
            "count":   qs.count(),
            "results": serializer.data,
        })


# ══════════════════════════════════════════════════════════════
# SESSIONS
# ══════════════════════════════════════════════════════════════

class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        patient = _get_patient(request)
        if not patient:
            return Response({"error": "Profil patient introuvable"}, status=status.HTTP_404_NOT_FOUND)

        limit    = int(request.query_params.get("limit", 10))
        sessions = ConversationSession.objects.filter(
            patient=patient, is_active=True
        ).order_by("-updated_at")[:limit]

        data = [{
            "id":            s.id,
            "title":         s.title or "Nouvelle conversation",
            "lang":          s.lang,
            "message_count": s.message_count,
            "last_message":  s.last_message,
            "history":       s.get_gemini_history(),
            "created_at":    s.created_at.isoformat(),
            "updated_at":    s.updated_at.isoformat(),
        } for s in sessions]

        return Response({"count": len(data), "sessions": data})

    def delete(self, request):
        patient    = _get_patient(request)
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response({"error": "session_id requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session           = ConversationSession.objects.get(id=session_id, patient=patient)
            session.is_active = False
            session.save(update_fields=["is_active"])
            return Response({"status": "session fermée"})
        except ConversationSession.DoesNotExist:
            return Response({"error": "Session introuvable"}, status=status.HTTP_404_NOT_FOUND)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

class HealthView(APIView):
    permission_classes = []

    def get(self, request):
        try:
            from infrastructure.vector_db.chroma_client import get_collection_stats
            chroma = get_collection_stats()
        except Exception as e:
            chroma = {"status": "error", "error": str(e)}

        try:
            from diagnostic_ai.services.gemini_service import get_gemini
            get_gemini()
            gemini_status = "ok"
        except Exception:
            gemini_status = "error"

        return Response({
            "status":        "operational",
            "service":       "Diagnostic IA",
            "version":       "1.0.0",
            "chroma":        chroma,
            "gemini_status": gemini_status,
            "db": {
                "interactions":  Interaction.objects.count(),
                "training_data": TrainingData.objects.count(),
                "genetic_runs":  GeneticRun.objects.count(),
            }
        })


# ══════════════════════════════════════════════════════════════
# GENETIC OPTIMIZE
# ══════════════════════════════════════════════════════════════

class GeneticOptimizeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({"error": "Réservé aux admins."}, status=status.HTTP_403_FORBIDDEN)

        params = {
            "population_size": request.data.get("population_size", 10),
            "generations":     request.data.get("generations", 5),
            "mutation_rate":   request.data.get("mutation_rate", 0.15),
            "elite_count":     request.data.get("elite_count", 2),
        }
        try:
            optimizer = GeneticOptimizer(params=params)
            result    = optimizer.run()
            best      = result["best_chromosome"]
            run = GeneticRun.objects.create(
                generation      = result["generations_run"],
                best_fitness    = best["fitness_score"],
                best_chromosome = best,
                population_size = params["population_size"],
            )
            return Response({
                "status":          "optimization_complete",
                "run_id":          run.id,
                "best_params":     best,
                "generations_run": result["generations_run"],
                "history":         result["history"],
            })
        except Exception:
            logger.exception("Optimisation génétique échouée")
            return Response({"error": "Optimisation échouée"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        runs       = GeneticRun.objects.all()[:10]
        serializer = GeneticRunSerializer(runs, many=True)
        return Response({"count": runs.count(), "results": serializer.data})


# ══════════════════════════════════════════════════════════════
# TRAINING DATA
# ══════════════════════════════════════════════════════════════

class TrainingDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        training   = TrainingData.objects.all()[:50]
        serializer = TrainingDataSerializer(training, many=True)
        return Response({"count": TrainingData.objects.count(), "results": serializer.data})