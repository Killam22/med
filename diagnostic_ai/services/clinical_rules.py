# apps/chat/services/clinical_rules.py

import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🔴 NOUVEAU : Système 3 niveaux d'alerte symptômes
# ============================================================

CRITICAL_SYMPTOMS = {
    # Cardiovasculaire
    "chest pain", "douleur poitrine", "douleur thoracique",
    "left arm pain", "douleur bras gauche", "jaw pain", "douleur machoire",
    "cardiac arrest", "arrêt cardiaque",
    "aortic dissection", "dissection aortique",

    # Neurologique urgent
    "loss of consciousness", "perte de conscience", "unconscious", "inconscient",
    "sudden severe headache", "céphalée brutale", "thunderclap headache",
    "facial drooping", "paralysie faciale", "arm weakness sudden", "speech difficulty sudden",
    "seizure", "convulsion",
    "neck stiffness fever", "raideur nuque fièvre",

    # Respiratoire
    "severe shortness of breath", "détresse respiratoire", "cannot breathe", "ne peut pas respirer",
    "choking", "étouffement",
    "pulmonary embolism", "embolie pulmonaire",

    # Autre
    "severe bleeding", "saignement abondant", "hemorrhage", "hémorragie",
    "anaphylaxis", "anaphylaxie", "severe allergic reaction", "réaction allergique sévère",
    "suicidal", "suicidaire", "self harm", "automutilation",
}

MODERATE_SYMPTOMS = {
    # Fièvre
    "high fever", "fièvre élevée", "fever 39", "fièvre 39", "fever 40", "fièvre 40",

    # Douleurs importantes
    "severe abdominal pain", "douleur abdominale sévère",
    "severe headache", "migraine sévère",
    "ear pain severe", "douleur oreille forte",

    # Infectieux
    "difficulty swallowing", "difficulté à avaler",
    "vomiting blood", "vomissement sang", "blood in stool", "sang dans selles",
    "urinary pain severe", "douleur urinaire forte",
    "wound infected", "plaie infectée",

    # Chronique en aggravation
    "uncontrolled diabetes", "diabète non contrôlé",
    "blood pressure very high", "tension très élevée",
    "asthma attack", "crise d'asthme",
    "appendicitis", "appendicite",
}

ALERT_MESSAGES = {
    "critical": {
        "fr": "🚨 URGENCE MÉDICALE — Appelez le 15 (SAMU) ou le 112, ou rendez-vous AUX URGENCES IMMÉDIATEMENT. N'attendez pas.",
        "en": "🚨 MEDICAL EMERGENCY — Call emergency services immediately or go to the ER. Do not wait.",
        "icon": "🔴",
        "color": "red",
    },
    "moderate": {
        "fr": "⚠️ Consultez un médecin dans les 24 à 48 heures. Si vos symptômes s'aggravent, allez aux urgences.",
        "en": "⚠️ See a doctor within 24–48 hours. If symptoms worsen, go to the ER.",
        "icon": "🟠",
        "color": "orange",
    },
    "low": {
        "fr": "ℹ️ Vous pouvez surveiller vos symptômes à domicile. Consultez un médecin si ça ne s'améliore pas sous 3–5 jours.",
        "en": "ℹ️ You can monitor your symptoms at home. See a doctor if no improvement within 3–5 days.",
        "icon": "🟢",
        "color": "green",
    },
}


def check_symptom_alert(symptoms_fr: str, symptoms_en: str) -> dict:
    """
    Analyse les symptômes bruts et retourne le niveau d'alerte + message.
    À appeler AVANT le pipeline RAG/IA.

    Retourne:
    {
        "level": "critical" | "moderate" | "low",
        "message_fr": str,
        "message_en": str,
        "icon": str,
        "color": str,
        "matched_symptoms": list[str],   # symptômes déclencheurs trouvés
        "block_ai": False,               # l'IA répond toujours, mais avec alerte
    }
    """
    symptoms_combined = (symptoms_fr + " " + symptoms_en).lower()

    # 🔴 Vérifier symptômes critiques
    matched_critical = [s for s in CRITICAL_SYMPTOMS if s in symptoms_combined]
    if matched_critical:
        logger.warning("Symptômes critiques détectés: %s", matched_critical)
        return {
            "level": "critical",
            "message_fr": ALERT_MESSAGES["critical"]["fr"],
            "message_en": ALERT_MESSAGES["critical"]["en"],
            "icon": ALERT_MESSAGES["critical"]["icon"],
            "color": ALERT_MESSAGES["critical"]["color"],
            "matched_symptoms": matched_critical,
            "block_ai": False,  # L'IA analyse quand même, mais alerte en tête
        }

    # 🟠 Vérifier symptômes modérés
    matched_moderate = [s for s in MODERATE_SYMPTOMS if s in symptoms_combined]
    if matched_moderate:
        logger.info("Symptômes modérés détectés: %s", matched_moderate)
        return {
            "level": "moderate",
            "message_fr": ALERT_MESSAGES["moderate"]["fr"],
            "message_en": ALERT_MESSAGES["moderate"]["en"],
            "icon": ALERT_MESSAGES["moderate"]["icon"],
            "color": ALERT_MESSAGES["moderate"]["color"],
            "matched_symptoms": matched_moderate,
            "block_ai": False,
        }

    # 🟢 Bénin
    return {
        "level": "low",
        "message_fr": ALERT_MESSAGES["low"]["fr"],
        "message_en": ALERT_MESSAGES["low"]["en"],
        "icon": ALERT_MESSAGES["low"]["icon"],
        "color": ALERT_MESSAGES["low"]["color"],
        "matched_symptoms": [],
        "block_ai": False,
    }


def format_alert_for_response(alert: dict, lang: str = "fr") -> str:
    """
    Formate le message d'alerte à injecter EN TÊTE de la réponse de l'IA.

    Usage dans ton view/service :
        alert = check_symptom_alert(symptoms_fr, symptoms_en)
        prefix = format_alert_for_response(alert, lang="fr")
        final_response = prefix + "\\n\\n" + ai_response
    """
    msg = alert["message_fr"] if lang == "fr" else alert["message_en"]
    level = alert["level"]

    if level == "critical":
        separator = "=" * 50
        return f"{separator}\\n{msg}\\n{separator}"
    elif level == "moderate":
        return f"{msg}"
    else:
        return f"{msg}"


# ============================================================
# Code existant — inchangé
# ============================================================

STRICT_DISEASES = {
    "cholera":            ["watery diarrhea", "rice water stool", "severe dehydration"],
    "plague":             ["buboes", "swollen lymph", "rodent"],
    "rabies":             ["animal bite", "hydrophobia", "paralysis"],
    "ebola":              ["hemorrhage", "bleeding", "ebola"],
    "typhoid":            ["rose spots", "sustained fever", "contaminated water"],
    "malaria":            ["cyclical fever", "chills", "mosquito", "tropical"],
    "yellow fever":       ["jaundice", "hemorrhage", "tropical travel"],
    "hiv":                ["immunodeficiency", "opportunistic infection", "chronic weight loss"],
    "aids":               ["immunodeficiency", "opportunistic infection", "chronic weight loss"],
    "tuberculosis":       ["chronic cough", "night sweats", "weight loss"],
    "leprosy":            ["skin lesion numb", "nerve damage"],
    "syphilis":           ["chancre", "sexually transmitted"],
    "meningitis":         [
        "neck stiffness", "stiff neck", "nuchal rigidity",
        "nuque", "raideur nuque", "photophobia",
        "severe headache", "meningococcal", "meningitis",
        "neck stiff", "sensitivity light", "light sensitivity",
        "headache fever rash", "rash fever",
        "rash", "petechial", "purpura",
    ],
    "encephalitis":       ["confusion", "seizure", "altered consciousness"],
    "tetanus":            ["muscle spasm", "lockjaw", "trismus"],
    "leukemia":           ["bone marrow", "abnormal blood"],
    "lymphoma":           ["lymph node swelling chronic", "night sweats weight loss"],
    "brain tumor":        ["progressive headache", "vision loss", "seizure"],
    "heart attack":       [
        "chest pain", "chest pain radiating", "arm pain", "jaw pain",
        "myocardial", "infarction", "douleur poitrine", "thoracique",
        "shortness of breath", "left arm", "bras gauche",
    ],
    "infarction":         [
        "chest pain radiating", "arm pain", "myocardial",
        "heart attack", "chest pain", "left arm",
    ],
    "lupus":              ["butterfly rash", "photosensitivity"],
    "multiple sclerosis": ["vision loss", "numbness progressive", "weakness progressive"],
    "schizophrenia":      ["hallucination", "delusion", "psychosis"],
    "bipolar":            ["mania", "extreme mood", "psychosis"],
    "tourette":           ["tic", "vocal tic", "motor tic"],
    "cystic fibrosis":    ["chronic lung infection", "digestive enzyme", "genetic"],
}

STRICT_CONTEXT_BOOSTS = {
    "meningitis": {
        "rash":       0.15,
        "petechial":  0.20,
        "purpura":    0.20,
        "photophobia": 0.10,
        "neck stiff": 0.10,
        "raideur":    0.10,
    },
}

COMMON_DISEASES = [
    "influenza", "grippe", "flu",
    "cold", "rhume", "rhinopharyngitis",
    "bronchitis", "bronchite",
    "pneumonia", "pneumonie",
    "covid", "coronavirus",
    "gastroenteritis", "gastro",
    "sinusitis", "sinusite",
    "tonsillitis", "angine", "pharyngitis",
    "otitis", "otite",
    "urinary tract", "cystitis",
    "migraine", "headache",
    "hypertension",
    "diabetes",
    "anemia", "anemie",
    "anxiety", "anxiete",
    "depression",
    "dermatitis", "eczema", "psoriasis",
    "allergy", "allergie",
    "asthma", "asthme",
    "gastritis", "gastrite",
    "conjunctivitis",
    "herpes", "chickenpox", "varicelle",
    "measles", "rougeole",
    "fungal", "candida",
    "hypothyroidism", "hyperthyroidism",
    "arthritis", "back pain",
    "insomnia", "fatigue",
    "vitamin deficiency", "iron deficiency",
    "appendicitis", "appendicite",
    "parkinson", "alzheimer",
    "epilepsy", "epilepsie",
    "hepatitis", "hepatite",
    "pancreatitis",
    "kidney stones", "calculs",
]

DISEASE_URGENCY_TIER = {
    "parkinson":              "low",
    "tremor":                 "low",
    "alzheimer":              "low",
    "multiple sclerosis":     "moderate",
    "epilepsy":               "moderate",
    "heart attack":           "critical",
    "infarction":             "critical",
    "myocardial infarction":  "critical",
    "sudden cardiac arrest":  "critical",
    "pulmonary embolism":     "critical",
    "aortic dissection":      "critical",
    "meningitis":             "critical",
    "encephalitis":           "critical",
    "sepsis":                 "critical",
    "ebola":                  "critical",
    "rabies":                 "critical",
    "tuberculosis":           "moderate",
    "pneumonia":              "moderate",
    "appendicitis":           "high",
    "cholecystitis":          "moderate",
    "gastroparesis":          "low",
    "gastroenteritis":        "moderate",
    "pancreatitis":           "high",
    "migraine":               "low",
    "diabetes":               "low",
    "hypertension":           "low",
    "anxiety":                "low",
    "depression":             "low",
    "asthma":                 "moderate",
    "back pain":              "low",
    "insomnia":               "low",
    "arthritis":              "low",
    "celiac disease":         "low",
    "irritable bowel":        "low",
}


def get_urgency_tier(name_en: str, name_fr: str = "") -> str | None:
    name = (name_en + " " + name_fr).lower()
    for key, tier in DISEASE_URGENCY_TIER.items():
        if key in name:
            return tier
    return None


def is_common_disease(name_en: str, name_fr: str) -> bool:
    name = (name_en + " " + name_fr).lower()
    return any(common in name for common in COMMON_DISEASES)


def get_strict_rule(name_en: str, name_fr: str) -> list:
    name = (name_en + " " + name_fr).lower()
    for key, required in STRICT_DISEASES.items():
        if key in name:
            return required
    return []


def get_strict_key(name_en: str, name_fr: str) -> str | None:
    name = (name_en + " " + name_fr).lower()
    for key in STRICT_DISEASES:
        if key in name:
            return key
    return None


def symptom_match_score(symptoms: str, key_symptoms: str) -> float:
    if not key_symptoms:
        return 0.5
    patient_words = set(symptoms.lower().split())
    disease_words = set(key_symptoms.lower().replace(",", " ").split())
    if not disease_words:
        return 0.5
    common = patient_words.intersection(disease_words)
    return min(len(common) / len(disease_words), 1.0)


def _apply_context_boost(disease_key: str, symptoms: str, confidence: float) -> float:
    boosts = STRICT_CONTEXT_BOOSTS.get(disease_key, {})
    total_boost = 0.0
    for trigger, boost in boosts.items():
        if trigger in symptoms:
            total_boost += boost
    return min(round(confidence + total_boost, 2), 0.99)


def apply_clinical_rules(symptoms_fr: str, symptoms_en: str, diseases: list) -> list:
    symptoms_combined = (symptoms_fr + " " + symptoms_en).lower()
    filtered = []

    for disease in diseases:
        name_en      = disease.get("name_en", "")
        name_fr      = disease.get("name_fr", "")
        key_symptoms = disease.get("key_symptoms", "")
        confidence   = disease.get("confidence", 0)

        if is_common_disease(name_en, name_fr):
            match_score = symptom_match_score(symptoms_combined, key_symptoms)
            disease["confidence"] = round((confidence * 0.6) + (match_score * 0.4), 2)
            filtered.append(disease)
            logger.debug("Commune '%s' — conf: %.2f", name_en, disease["confidence"])
            continue

        strict_required = get_strict_rule(name_en, name_fr)
        if strict_required:
            has_required = any(req in symptoms_combined for req in strict_required)
            if has_required:
                strict_key = get_strict_key(name_en, name_fr)
                if strict_key:
                    disease["confidence"] = _apply_context_boost(
                        strict_key, symptoms_combined, confidence
                    )
                filtered.append(disease)
                logger.info("Stricte '%s' acceptee", name_en)
            else:
                logger.info("Stricte '%s' rejetee", name_en)
            continue

        match_score = symptom_match_score(symptoms_combined, key_symptoms)
        if match_score > 0.1 or confidence > 0.75:
            disease["confidence"] = round((confidence * 0.5) + (match_score * 0.5), 2)
            filtered.append(disease)
            logger.debug("Autre '%s' — conf: %.2f", name_en, disease["confidence"])
        else:
            logger.info("Autre '%s' rejetee — match faible: %.2f", name_en, match_score)

    filtered.sort(key=lambda d: d.get("confidence", 0), reverse=True)

    if not filtered and diseases:
        logger.warning("Toutes filtrees — garde top 3: %s", diseases[0].get("name_en", ""))
        filtered = diseases[:3]

    return filtered