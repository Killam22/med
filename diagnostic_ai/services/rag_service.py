# diagnostic_ai/services/rag_service.py
# MODIFICATION : process_chat() et process_chat_stream() acceptent medical_context
# qui est injecté dans build_diagnosis_prompt()

import json
import os
import logging
import concurrent.futures
from django.conf import settings
from diagnostic_ai.services.reranker import multi_query_search, rerank
from diagnostic_ai.services.chroma_service import search_diseases
from diagnostic_ai.services.gemini_service import (
    build_diagnosis_prompt,
    build_recommendation_prompt,
    generate,
    generate_stream,
    generate_conversational,
    generate_conversational_stream,
    generate_diagnosis_stream,
    generate_recommendation_stream,
    LANG_INSTRUCTIONS,
)
from diagnostic_ai.services.genetic.optimizer import get_best_params
from diagnostic_ai.services.clinical_rules import apply_clinical_rules
from diagnostic_ai.services.medical_validator import validate_diseases
from diagnostic_ai.services.scoring import apply_smart_scoring
from diagnostic_ai.services.cache_service import get_from_cache, save_to_cache

logger = logging.getLogger(__name__)

_specialists = None

MIN_SYMPTOMS_WORDS      = 2
MIN_SYMPTOMS_CHARS      = 5
MIN_DISEASES_CONFIDENCE = 0.40

DETAIL_MESSAGES = {
    "fr": (
        "Pourriez-vous me donner plus de détails sur vos symptômes ? "
        "Par exemple : depuis combien de temps, à quelle fréquence, "
        "d'autres symptômes associés (fièvre, douleurs, fatigue...) ? "
        "Plus vous êtes précis, mieux je peux vous aider. 🩺"
    ),
    "ar": (
        "هل يمكنك إعطائي مزيدًا من التفاصيل حول أعراضك؟ "
        "مثلاً: منذ متى وأنت تعاني من هذا، هل توجد أعراض أخرى "
        "(حمى، آلام، تعب...)؟ كلما كنت أكثر دقة، كان بإمكاني مساعدتك أفضل. 🩺"
    ),
    "en": (
        "Could you give me more details about your symptoms? "
        "For example: how long have you had them, how often, "
        "any other symptoms (fever, pain, fatigue...)? "
        "The more precise you are, the better I can help you. 🩺"
    ),
}

FOLLOWUP_KEYWORDS = [
    "explique", "explication", "clarifier", "précise", "détaille", "développe",
    "c'est quoi", "qu'est ce que", "que veut dire", "signifie",
    "comprends pas", "pas clair", "plus clair", "elaborate",
    "autre", "autres", "encore", "suite", "continuer", "continue",
    "plus", "davantage", "ensuite", "après", "apres",
    "alternative", "alternatives", "option", "options",
    "solution", "solutions", "possibilité", "possibilités",
    "quoi d'autre", "autre chose", "et aussi", "en plus",
    "recommandation", "recommandations", "conseil", "conseils",
    "traitement", "remède", "médicament", "medicament",
    "que faire", "quoi faire", "comment faire", "comment traiter",
    "symptome", "symptôme", "symptomes", "symptômes", "signe",
    "diagnostic", "pronostic", "risque", "danger", "grave",
    "contagieux", "contagion", "transmission", "chronique", "aigu",
    "déjà", "deja", "dit", "dis", "mentionné",
    "ok", "okay", "oui", "non", "d'accord", "compris",
    "merci", "super", "bien", "parfait",
    "comment", "pourquoi", "quand", "combien", "quel", "quelle",
    "est ce que", "est-ce que", "peux tu", "pouvez vous",
    "explain", "other", "more", "continue", "next", "elaborate",
    "alternative", "option", "solution", "advice", "prevent",
    "ok", "yes", "no", "thanks", "thank you", "understood",
    "what", "why", "how", "when", "which", "where",
]

OUT_OF_SCOPE_KEYWORDS = [
    "bonne nuit", "bonne journée", "bonne soirée",
    "qui es tu", "tu es quoi", "ton nom", "comment tu t appelles",
    "quelle heure", "quel jour", "quel mois", "quelle année",
    "météo", "weather", "il fait chaud", "il fait froid",
    "code", "coder", "programmer", "développer",
    "python", "javascript", "java", "html", "css", "sql",
    "argent", "money", "bourse", "investissement", "crypto", "bitcoin",
    "politique", "election", "president", "gouvernement",
    "film", "movie", "serie", "jeu", "game", "musique", "music",
    "football", "cuisine", "recette", "recipe", "voyage",
    "religion", "dieu", "philosophie",
    "blague", "joke", "humour",
]

MEDICAL_PROTECTION_KEYWORDS = [
    "douleur", "fièvre", "toux", "fatigue", "nausée", "vomissement",
    "diarrhée", "saignement", "poitrine", "gorge", "vertige", "faiblesse",
    "gonflement", "brûlure", "démangeaison", "frisson", "crampe",
    "paralysie", "convulsion", "essoufflement", "palpitation",
    "symptôme", "symptomes", "maladie", "médecin", "docteur", "urgence",
    "traitement", "médicament", "ordonnance", "allergie", "infection",
    "j'ai mal", "je souffre",
    "pain", "fever", "cough", "fatigue", "nausea", "vomiting", "diarrhea",
    "bleeding", "chest", "throat", "dizzy", "weakness", "swelling",
    "burning", "itching", "chills", "sweating", "cramp", "seizure",
    "symptom", "disease", "emergency", "medicine", "allergy",
    "infection", "i have", "i feel", "hurts",
    "ألم", "حمى", "سعال", "تعب", "غثيان", "قيء", "إسهال", "نزيف",
    "صدر", "حلق", "دوخة", "ضعف", "تورم", "حرق", "حكة", "رعشة",
    "تشنج", "مرض", "طبيب", "أعاني", "أشعر",
]

OUT_OF_SCOPE_RESPONSE = {
    "fr": (
        "Je suis un assistant médical spécialisé. 🩺\n\n"
        "Je peux uniquement vous aider avec :\n"
        "• Vos symptômes et ce qu'ils peuvent signifier\n"
        "• Les maladies possibles\n"
        "• Les conseils médicaux pratiques\n\n"
        "Décrivez-moi vos symptômes et je ferai de mon mieux pour vous aider."
    ),
    "ar": (
        "أنا مساعد طبي متخصص. 🩺\n\n"
        "يمكنني فقط مساعدتك في:\n"
        "• أعراضك وما قد تعنيه\n"
        "• الأمراض المحتملة\n"
        "• النصائح الطبية العملية\n\n"
        "صف لي أعراضك وسأبذل قصارى جهدي لمساعدتك."
    ),
    "en": (
        "I am a specialized medical assistant. 🩺\n\n"
        "I can only help you with:\n"
        "• Your symptoms and what they may mean\n"
        "• Possible diseases\n"
        "• Practical medical advice\n\n"
        "Describe your symptoms and I will do my best to help you."
    ),
}

LOCATION_RESPONSE = {
    "fr": (
        "Je suis un assistant médical IA, je ne peux pas localiser "
        "des médecins ou cliniques près de chez vous directement. 📍\n\n"
        "Mais ne vous inquiétez pas — après votre diagnostic, "
        "je vous recommanderai automatiquement des médecins "
        "disponibles sur notre plateforme près de chez vous ! 🩺"
    ),
    "ar": (
        "أنا مساعد طبي ذكاء اصطناعي. 📍\n\n"
        "بعد تشخيصك، سأوصي تلقائياً بأطباء متاحين على منصتنا بالقرب منك! 🩺"
    ),
    "en": (
        "I am an AI medical assistant. 📍\n\n"
        "After your diagnosis, I will automatically recommend "
        "available doctors on our platform near you! 🩺"
    ),
}

LOCATION_KEYWORDS = [
    "près de chez moi", "autour de moi", "dans ma ville",
    "trouver un médecin", "donne moi un médecin", "chercher un médecin",
    "trouver un docteur", "clinique près", "hôpital près",
    "médecin près", "docteur près", "spécialiste près",
    "rendez-vous médecin", "prendre rendez-vous",
    "find a doctor", "doctor near", "clinic near", "hospital near",
    "أين أجد طبيب", "طبيب قريب", "عيادة قريبة",
]

GENERAL_QUESTION_PATTERNS = [
    "c'est quoi", "c est quoi", "qu'est-ce que", "qu'est ce que",
    "définition de", "definition de", "expliquer", "explique moi",
    "donne moi des informations sur", "informations sur",
    "comment fonctionne", "comment se développe", "comment se transmet",
    "quels sont les symptômes de", "quelles sont les causes de",
    "comment se soigne", "comment traiter", "quel est le traitement de",
    "quelle est la différence entre", "différence entre",
    "c'est dangereux", "est-ce grave", "comment prévenir",
    "what is", "what are", "what's", "how does", "how do",
    "explain", "tell me about", "information about",
    "definition of", "what causes", "how is it treated",
    "symptoms of", "signs of", "causes of", "treatment for",
    "difference between", "is it dangerous", "how to prevent",
    "ما هو", "ما هي", "ما هي أعراض", "كيف يعمل",
    "اشرح لي", "أخبرني عن", "معلومات عن",
]


def is_general_medical_question(symptoms: str) -> bool:
    text = symptoms.lower().strip()
    return any(pattern in text for pattern in GENERAL_QUESTION_PATTERNS)


def get_specialists() -> list:
    global _specialists
    if _specialists is None:
        path = os.path.join(settings.DATASET_PATH, "specialists.json")
        with open(path, "r", encoding="utf-8") as f:
            _specialists = json.load(f)
        logger.info("Spécialistes chargés: %d", len(_specialists))
    return _specialists


def find_specialist(key: str) -> dict:
    for s in get_specialists():
        if key.lower() in s.get("specialty_en", "").lower():
            return s
        if key.lower() in s.get("specialty_fr", "").lower():
            return s
    return {"specialty_fr": key, "specialty_ar": key, "specialty_en": key}


def is_location_request(symptoms: str) -> bool:
    return any(kw in symptoms.lower() for kw in LOCATION_KEYWORDS)


def is_out_of_scope(symptoms: str) -> bool:
    symptoms_lower = symptoms.lower()
    if any(kw in symptoms_lower for kw in MEDICAL_PROTECTION_KEYWORDS):
        return False
    return any(kw in symptoms_lower for kw in OUT_OF_SCOPE_KEYWORDS)


def is_followup_message(symptoms: str, history: list) -> bool:
    if not history:
        return False
    symptoms_lower = symptoms.lower().strip()
    if len(symptoms_lower.split()) <= 5:
        if any(kw in symptoms_lower for kw in FOLLOWUP_KEYWORDS):
            return True
    return False


def handle_followup(symptoms: str, lang: str, history: list) -> dict:
    from diagnostic_ai.services.cache_service import get_question_from_cache, save_question_to_cache
    from diagnostic_ai.services.gemini_service import detect_intent

    cached_response = get_question_from_cache(symptoms, lang)
    if cached_response:
        return {
            "response": cached_response, "diseases": [], "specialist": {},
            "urgency": "modéré", "lang": lang, "params_used": {},
            "pending_recommendation": None, "ask_recommendation": False,
            "needs_more_details": False, "from_cache": True,
            "recommended_doctors": [],
        }

    intent   = detect_intent(symptoms, history)
    response = generate_conversational(symptoms, lang, history)
    save_question_to_cache(question=symptoms, lang=lang, response=response, intent=intent)

    return {
        "response": response, "diseases": [], "specialist": {},
        "urgency": "modéré", "lang": lang, "params_used": {},
        "pending_recommendation": None, "ask_recommendation": False,
        "needs_more_details": False, "from_cache": False,
        "recommended_doctors": [],
    }


def handle_followup_stream(symptoms: str, lang: str, history: list):
    from diagnostic_ai.services.cache_service import get_question_from_cache, save_question_to_cache
    from diagnostic_ai.services.gemini_service import detect_intent
    import json as _json

    cached_response = get_question_from_cache(symptoms, lang)
    if cached_response:
        meta = {
            "type": "meta", "diseases": [], "specialist": {},
            "urgency": "modéré", "ask_recommendation": False,
            "needs_more_details": False, "from_cache": True,
            "recommended_doctors": [],
        }
        yield f"data: {_json.dumps(meta, ensure_ascii=False)}\n\n"
        for char in cached_response:
            yield f"data: {_json.dumps({'type': 'chunk', 'text': char}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    intent = detect_intent(symptoms, history)
    meta = {
        "type": "meta", "diseases": [], "specialist": {},
        "urgency": "modéré", "ask_recommendation": False,
        "needs_more_details": False, "from_cache": False,
        "recommended_doctors": [],
    }
    yield f"data: {_json.dumps(meta, ensure_ascii=False)}\n\n"

    full_response = ""
    for chunk in generate_conversational_stream(symptoms, lang, history):
        full_response += chunk
        yield f"data: {_json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"
    save_question_to_cache(question=symptoms, lang=lang, response=full_response, intent=intent)


def extract_cumulative_symptoms(symptoms: str, history: list) -> str:
    if not history:
        return symptoms
    previous_user_msgs = [
        m["content"] for m in history
        if m["role"] == "user" and m["content"].strip()
    ]
    if not previous_user_msgs:
        return symptoms
    all_symptoms = " ".join(previous_user_msgs + [symptoms])
    seen, unique_words = set(), []
    for word in all_symptoms.split():
        w = word.lower().strip(".,;:!?")
        if w and w not in seen:
            seen.add(w)
            unique_words.append(word)
    return " ".join(unique_words)


def is_symptoms_too_vague(symptoms: str, diseases: list) -> bool:
    words = symptoms.strip().split()
    if len(words) < MIN_SYMPTOMS_WORDS:
        return True
    if len(symptoms.strip()) < MIN_SYMPTOMS_CHARS:
        return True
    
    # Si on n'a pas de maladies dans la DB, on laisse quand même Gemini répondre
    # au lieu de bloquer avec un message générique.
    if not diseases:
        return False
        
    best_confidence = max(d.get("confidence", 0) for d in diseases)
    if best_confidence < MIN_DISEASES_CONFIDENCE:
        # Même si la confiance est faible, on laisse Gemini tenter une analyse
        return False
    return False



def translate_symptoms(symptoms: str) -> str:
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(symptoms)
        if translated and translated.strip():
            return translated
        return symptoms
    except Exception as e:
        logger.warning("Traduction échouée: %s", e)
        return symptoms


def _make_static_response(response: str, lang: str) -> dict:
    return {
        "response": response, "diseases": [], "specialist": {},
        "urgency": "modéré", "lang": lang, "params_used": {},
        "pending_recommendation": None, "ask_recommendation": False,
        "needs_more_details": False, "from_cache": False,
        "recommended_doctors": [],
    }


def _stream_static_response(response: str, lang: str):
    import json as _json
    meta = {
        "type": "meta", "diseases": [], "specialist": {},
        "urgency": "modéré", "ask_recommendation": False,
        "needs_more_details": False, "from_cache": False,
        "recommended_doctors": [],
    }
    yield f"data: {_json.dumps(meta, ensure_ascii=False)}\n\n"
    for char in response:
        yield f"data: {_json.dumps({'type': 'chunk', 'text': char}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def _run_rag_pipeline(symptoms: str, lang: str, symptoms_en: str, k: int = 15) -> list:
    diseases = multi_query_search(symptoms, lang, search_diseases, k=k)
    diseases = rerank(diseases, symptoms_en, symptoms)
    if diseases:
        diseases = apply_clinical_rules(
            symptoms_fr=symptoms, symptoms_en=symptoms_en, diseases=diseases,
        )
    nih_results = {}
    if diseases:
        diseases, nih_results = validate_diseases(diseases)
    if diseases:
        diseases = apply_smart_scoring(
            diseases=diseases, symptoms_en=symptoms_en,
            nih_results=nih_results, symptoms_fr=symptoms,
        )
    return diseases


# ══════════════════════════════════════════════════════════════
# PIPELINE NORMAL
# ══════════════════════════════════════════════════════════════

def process_chat(
    symptoms:        str,
    lang:            str  = "fr",
    history:         list = None,
    patient=None,
    medical_context: str  = "",   # ← NOUVEAU : contexte médical personnalisé
) -> dict:

    if not symptoms or not symptoms.strip():
        raise ValueError("Les symptômes ne peuvent pas être vides")

    history  = history or []
    symptoms = extract_cumulative_symptoms(symptoms, history)

    if is_location_request(symptoms):
        return _make_static_response(LOCATION_RESPONSE.get(lang, LOCATION_RESPONSE["fr"]), lang)

    if is_out_of_scope(symptoms):
        return _make_static_response(OUT_OF_SCOPE_RESPONSE.get(lang, OUT_OF_SCOPE_RESPONSE["fr"]), lang)

    if is_general_medical_question(symptoms):
        return handle_followup(symptoms, lang, history)

    if is_followup_message(symptoms, history):
        return handle_followup(symptoms, lang, history)

    cached = get_from_cache(symptoms, lang)
    if cached:
        logger.info("✅ Depuis cache (contexte médical non appliqué sur réponse cachée)")
        cached["lang"]                = lang
        cached["params_used"]         = {}
        cached["recommended_doctors"] = _get_recommended_doctors(
            cached.get("specialist", {}), patient
        )
        return cached

    params      = get_best_params()
    symptoms_en = translate_symptoms(symptoms)
    diseases    = _run_rag_pipeline(symptoms, lang, symptoms_en, k=15)

    if is_symptoms_too_vague(symptoms, diseases):
        return _make_static_response(
            DETAIL_MESSAGES.get(lang, DETAIL_MESSAGES["fr"]), lang
        ) | {"needs_more_details": True, "params_used": params}

    truncated_history = history[-params.get("history_len", 4):]

    # ── Injecte le contexte médical dans le prompt de diagnostic ──────────────
    diagnosis_prompt = build_diagnosis_prompt(
        symptoms        = symptoms,
        diseases        = diseases,
        lang            = lang,
        history         = truncated_history,
        prompt_style    = params.get("prompt_style", 2),
        medical_context = medical_context,   # ← NOUVEAU
    )
    recommendation_prompt = build_recommendation_prompt(
        symptoms=symptoms, diseases=diseases, lang=lang,
    )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        diag_future = executor.submit(generate, diagnosis_prompt,
                                      params.get("temperature", 0.7), params.get("top_p", 0.9))
        reco_future = executor.submit(generate, recommendation_prompt,
                                      params.get("temperature", 0.7), params.get("top_p", 0.9))
        response     = diag_future.result()
        pending_reco = reco_future.result()

    top_disease = diseases[0] if diseases else {}
    specialist  = find_specialist(top_disease.get("specialist", "médecin_généraliste"))
    recommended_doctors = _get_recommended_doctors(specialist, patient)

    save_to_cache(
        symptoms=symptoms, symptoms_en=symptoms_en, lang=lang,
        response=response, recommendation=pending_reco,
        diseases=diseases[:3], specialist=specialist,
        urgency=top_disease.get("urgency", "modéré"),
    )

    return {
        "response":               response,
        "diseases":               diseases[:3],
        "specialist":             specialist,
        "urgency":                top_disease.get("urgency", "modéré"),
        "lang":                   lang,
        "params_used":            params,
        "pending_recommendation": pending_reco,
        "ask_recommendation":     True,
        "needs_more_details":     False,
        "from_cache":             False,
        "recommended_doctors":    recommended_doctors,
    }


def _get_recommended_doctors(specialist: dict, patient) -> list:
    try:
        from diagnostic_ai.services.doctor_recommender import (
            find_doctors_near_patient,
            get_patient_location,
        )
        specialist_key = specialist.get("specialty_en", "general")
        location       = get_patient_location(patient)
        return find_doctors_near_patient(
            specialist_key  = specialist_key,
            patient_city    = location["city"],
            patient_wilaya  = location["wilaya"],
            limit           = 3,
        )
    except Exception as e:
        logger.warning("Recommandation médecin échouée: %s", e)
        return []


# ══════════════════════════════════════════════════════════════
# PIPELINE STREAMING
# ══════════════════════════════════════════════════════════════

def process_chat_stream(
    symptoms:        str,
    lang:            str  = "fr",
    history:         list = None,
    patient=None,
    medical_context: str  = "",   # ← NOUVEAU
):
    import json as _json

    if not symptoms or not symptoms.strip():
        yield f"data: {_json.dumps({'type': 'error', 'message': 'Les symptômes ne peuvent pas être vides'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    history  = history or []
    symptoms = extract_cumulative_symptoms(symptoms, history)

    if is_location_request(symptoms):
        yield from _stream_static_response(LOCATION_RESPONSE.get(lang, LOCATION_RESPONSE["fr"]), lang)
        return

    if is_out_of_scope(symptoms):
        yield from _stream_static_response(OUT_OF_SCOPE_RESPONSE.get(lang, OUT_OF_SCOPE_RESPONSE["fr"]), lang)
        return

    if is_general_medical_question(symptoms):
        yield from handle_followup_stream(symptoms, lang, history)
        return

    if is_followup_message(symptoms, history):
        yield from handle_followup_stream(symptoms, lang, history)
        return

    cached = get_from_cache(symptoms, lang)
    if cached:
        logger.info("✅ Stream depuis cache")
        recommended_doctors = _get_recommended_doctors(cached.get("specialist", {}), patient)
        meta = {
            "type":                   "meta",
            "diseases":               cached.get("diseases", []),
            "specialist":             cached.get("specialist", {}),
            "urgency":                cached.get("urgency", "modéré"),
            "ask_recommendation":     cached.get("ask_recommendation", False),
            "pending_recommendation": cached.get("pending_recommendation"),
            "needs_more_details":     False,
            "from_cache":             True,
            "recommended_doctors":    recommended_doctors,
        }
        yield f"data: {_json.dumps(meta, ensure_ascii=False)}\n\n"
        for char in cached.get("response", ""):
            yield f"data: {_json.dumps({'type': 'chunk', 'text': char}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        return

    params      = get_best_params()
    symptoms_en = translate_symptoms(symptoms)
    diseases    = _run_rag_pipeline(symptoms, lang, symptoms_en, k=15)

    if is_symptoms_too_vague(symptoms, diseases):
        yield from _stream_static_response(DETAIL_MESSAGES.get(lang, DETAIL_MESSAGES["fr"]), lang)
        return

    top_disease           = diseases[0] if diseases else {}
    specialist            = find_specialist(top_disease.get("specialist", "médecin_généraliste"))
    truncated_history     = history[-params.get("history_len", 4):]
    recommendation_prompt = build_recommendation_prompt(symptoms=symptoms, diseases=diseases, lang=lang)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        reco_future    = executor.submit(generate, recommendation_prompt,
                                         params.get("temperature", 0.7), params.get("top_p", 0.9))
        doctors_future = executor.submit(_get_recommended_doctors, specialist, patient)

        recommended_doctors = doctors_future.result()

        meta = {
            "type":                "meta",
            "diseases":            diseases[:3],
            "specialist":          specialist,
            "urgency":             top_disease.get("urgency", "modéré"),
            "ask_recommendation":  True,
            "needs_more_details":  False,
            "from_cache":          False,
            "recommended_doctors": recommended_doctors,
        }
        yield f"data: {_json.dumps(meta, ensure_ascii=False)}\n\n"

        full_response = ""
        for chunk in generate_diagnosis_stream(
            symptoms        = symptoms,
            diseases        = diseases,
            lang            = lang,
            history         = truncated_history,
            prompt_style    = params.get("prompt_style", 2),
            medical_context = medical_context,   # ← NOUVEAU
        ):
            full_response += chunk
            yield f"data: {_json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

        pending_reco = reco_future.result()

    yield f"data: {_json.dumps({'type': 'recommendation', 'text': pending_reco}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"

    save_to_cache(
        symptoms=symptoms, symptoms_en=symptoms_en, lang=lang,
        response=full_response, recommendation=pending_reco,
        diseases=diseases[:3], specialist=specialist,
        urgency=top_disease.get("urgency", "modéré"),
    )