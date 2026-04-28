# diagnostic_ai/services/cache_service.py

import hashlib
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD          = 0.75
QUESTION_SIMILARITY_THRESHOLD = 0.88


def compute_hash(text: str, lang: str) -> str:
    normalized = text.lower().strip()
    normalized = " ".join(sorted(normalized.split()))
    key = f"{normalized}_{lang}"
    return hashlib.sha256(key.encode()).hexdigest()


def similarity(text1: str, text2: str) -> float:
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


# ══════════════════════════════════════════════
# CACHE DIAGNOSTICS
# ══════════════════════════════════════════════

def get_from_cache(symptoms: str, lang: str) -> dict | None:
    return None # Désactivé temporairement pour test

    recent = DiagnosisCache.objects.filter(lang=lang).order_by("-hit_count")[:50]
    for cache in recent:
        sim = similarity(symptoms, cache.symptoms_text)
        if sim >= SIMILARITY_THRESHOLD:
            cache.hit_count += 1
            cache.save(update_fields=["hit_count"])
            logger.info("✅ Cache HIT similaire — sim: %.2f", sim)
            return _diagnosis_cache_to_result(cache)

    logger.info("❌ Cache MISS — '%s'", symptoms[:40])
    return None


def save_to_cache(symptoms, symptoms_en, lang, response, recommendation,
                  diseases, specialist, urgency):
    from diagnostic_ai.models import DiagnosisCache

    symptoms_hash = compute_hash(symptoms, lang)
    try:
        DiagnosisCache.objects.update_or_create(
            symptoms_hash=symptoms_hash,
            defaults={
                "symptoms_text":  symptoms,
                "symptoms_en":    symptoms_en,
                "lang":           lang,
                "response":       response,
                "recommendation": recommendation,
                "diseases":       diseases,
                "specialist":     specialist,
                "urgency":        urgency,
            }
        )
        logger.info("💾 Diagnostic sauvegardé en cache")
    except Exception as e:
        logger.error("Cache save error: %s", e)


def _diagnosis_cache_to_result(cache) -> dict:
    has_reco = bool(cache.recommendation and cache.recommendation.strip())
    return {
        "response":               cache.response,
        "diseases":               cache.diseases,
        "specialist":             cache.specialist,
        "urgency":                cache.urgency,
        "pending_recommendation": cache.recommendation if has_reco else None,
        "ask_recommendation":     has_reco,
        "needs_more_details":     False,
        "from_cache":             True,
    }


# ══════════════════════════════════════════════
# CACHE QUESTIONS
# ══════════════════════════════════════════════

def get_question_from_cache(question: str, lang: str) -> str | None:
    from diagnostic_ai.models import QuestionCache

    question_hash = compute_hash(question, lang)
    try:
        cache = QuestionCache.objects.get(question_hash=question_hash)
        cache.hit_count += 1
        cache.save(update_fields=["hit_count"])
        logger.info("✅ Question Cache HIT exact")
        return cache.response
    except QuestionCache.DoesNotExist:
        pass

    recent = QuestionCache.objects.filter(lang=lang).order_by("-hit_count")[:100]
    for cache in recent:
        sim = similarity(question, cache.question_text)
        if sim >= QUESTION_SIMILARITY_THRESHOLD:
            cache.hit_count += 1
            cache.save(update_fields=["hit_count"])
            logger.info("✅ Question Cache HIT similaire — sim: %.2f", sim)
            return cache.response

    return None


def save_question_to_cache(question, lang, response, intent="question"):
    from diagnostic_ai.models import QuestionCache

    question_hash = compute_hash(question, lang)
    try:
        QuestionCache.objects.update_or_create(
            question_hash=question_hash,
            defaults={
                "question_text": question,
                "lang":          lang,
                "response":      response,
                "intent":        intent,
            }
        )
    except Exception as e:
        logger.error("Question cache save error: %s", e)
