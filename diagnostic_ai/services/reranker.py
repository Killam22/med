# apps/chat/services/reranker.py
# Reranker leger + Multi-query
# Pas de modele lourd — utilise la logique medicale directement
#
# Usage dans chroma_service.py ou pipeline :
#   from apps.chat.services.reranker import rerank, expand_query

import logging
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# MULTI-QUERY EXPANSION
# Transforme une query simple en plusieurs requetes
# pour ameliorer le recall (surtout pour le francais)
# ──────────────────────────────────────────────────────────

FR_TO_EN_MEDICAL = {
    # ── Symptômes de base ──────────────────────────────────
    "fièvre": "fever", "fievre": "fever",
    "toux": "cough", "toux seche": "dry cough", "toux grasse": "productive cough",
    "douleur": "pain", "douleurs": "pain",
    "fatigue": "fatigue", "épuisement": "exhaustion",
    "nausée": "nausea", "nausee": "nausea", "nausées": "nausea",
    "vomissement": "vomiting", "vomissements": "vomiting",
    "diarrhée": "diarrhea", "diarrhee": "diarrhea",
    "maux de tete": "headache", "mal de tete": "headache",
    "maux de tête": "headache", "mal de tête": "headache",
    "courbatures": "body aches muscle pain myalgia",
    "frissons": "chills shivering",
    "essoufflement": "shortness of breath dyspnea",
    "raideur nuque": "stiff neck nuchal rigidity meningitis",
    "nuque": "neck stiffness",
    "sueurs nocturnes": "night sweats",
    "perte poids": "weight loss", "perte de poids": "weight loss",
    "perte odorat": "loss of smell anosmia", "perte gout": "loss of taste ageusia",
    "brulure miction": "burning urination dysuria",
    "sang urine": "blood in urine hematuria",
    "poitrine": "chest", "bras gauche": "left arm radiating cardiac",
    "tremblements": "tremor", "raideur": "stiffness",
    "soif excessive": "excessive thirst polydipsia",
    "urination frequente": "frequent urination polyuria",
    "vision floue": "blurred vision",
    "engourdissement": "numbness", "fourmillements": "tingling paresthesia",
    "palpitations": "palpitations heart racing tachycardia",
    "sueurs froides": "cold sweats diaphoresis",
    "eruption cutanee": "skin rash", "éruption cutanée": "skin rash",
    "demangeaisons": "itching pruritus", "démangeaisons": "itching pruritus",
    "jaunisse": "jaundice",
    "ganglions": "lymph nodes swollen lymphadenopathy",
    # ── Infarctus / Cardiaque (critique) ──────────────────
    "douleur poitrine bras gauche": "chest pain radiating left arm heart attack myocardial infarction",
    "douleur thoracique bras gauche": "chest pain left arm heart attack myocardial infarction cardiac",
    "douleur poitrine": "chest pain heart attack angina cardiac",
    "douleur thoracique": "chest pain thoracic cardiac heart attack",
    "infarctus": "myocardial infarction heart attack cardiac",
    "crise cardiaque": "heart attack myocardial infarction cardiac emergency",
    # ── Grippe / Respiratoire ─────────────────────────────
    "grippe": "influenza flu fever cough body aches",
    "rhume": "common cold rhinovirus runny nose",
    "angine": "tonsillitis sore throat streptococcal",
    "bronchite": "bronchitis cough mucus airway",
    "pneumonie": "pneumonia lung infection fever",
    # ── AR → EN (maladies courantes en arabe) ─────────────
    "حمى سعال تعب": "fever cough fatigue influenza flu",
    "حمى": "fever", "سعال": "cough", "تعب": "fatigue weakness",
    "ألم صدري": "chest pain cardiac heart attack",
    "ذراع أيسر": "left arm radiating cardiac",
    "تعرق": "sweating diaphoresis",
    "ضيق تنفس": "shortness of breath dyspnea",
    "صداع": "headache", "دوخة": "dizziness vertigo",
    "غثيان": "nausea", "قيء": "vomiting",
    "إسهال": "diarrhea", "إمساك": "constipation",
    "تورم": "swelling edema", "حكة": "itching pruritus",
    "نزيف": "bleeding hemorrhage", "ضعف": "weakness fatigue",
    "رعشة": "tremor shaking", "تشنج": "seizure convulsion",
    "يرقان": "jaundice hepatitis",
    "عطش": "thirst excessive diabetes polydipsia",
    "كثرة التبول": "frequent urination polyuria diabetes",
    "فقدان شم": "loss of smell anosmia covid",
    "فقدان تذوق": "loss of taste ageusia covid",
    "آلام الجسم": "body aches myalgia influenza flu",
}

SYMPTOM_EXPANSIONS = {
    "chest pain":          ["chest pain", "chest pressure", "thoracic pain", "cardiac pain", "myocardial infarction", "heart attack", "angina"],
    "heart attack":        ["heart attack", "myocardial infarction", "cardiac infarction", "MI", "acute coronary syndrome"],
    "myocardial":          ["myocardial infarction", "heart attack", "cardiac arrest", "coronary"],
    "left arm":            ["left arm pain", "left arm radiating", "heart attack", "myocardial infarction"],
    "influenza":           ["influenza", "flu", "grippe", "seasonal flu", "influenza virus"],
    "flu":                 ["flu", "influenza", "seasonal influenza", "fever cough body aches"],
    "headache":            ["headache", "cephalgia", "head pain", "cephalalgia"],
    "fever":               ["fever", "pyrexia", "high temperature", "febrile"],
    "cough":               ["cough", "coughing", "tussis"],
    "shortness of breath": ["shortness of breath", "dyspnea", "breathlessness"],
    "diarrhea":            ["diarrhea", "loose stool", "diarrhoea"],
    "nausea":              ["nausea", "nauseous", "queasiness"],
    "fatigue":             ["fatigue", "tiredness", "exhaustion", "weakness"],
    "stiff neck":          ["stiff neck", "neck stiffness", "nuchal rigidity", "meningismus"],
    "rash":                ["rash", "skin eruption", "exanthem", "dermatitis"],
    "tremor":              ["tremor", "trembling", "shaking", "resting tremor"],
    "loss of smell":       ["loss of smell", "anosmia", "hyposmia"],
    "loss of taste":       ["loss of taste", "ageusia", "dysgeusia"],
    "night sweats":        ["night sweats", "nocturnal hyperhidrosis", "diaphoresis"],
    "weight loss":         ["weight loss", "cachexia", "wasting"],
    "joint pain":          ["joint pain", "arthralgia", "arthritis"],
    "back pain":           ["back pain", "lumbar pain", "dorsalgia"],
    "abdominal pain":      ["abdominal pain", "stomach pain", "belly pain", "abdomen pain"],
    "burning urination":   ["burning urination", "dysuria", "painful urination"],
    "swollen lymph nodes": ["swollen lymph nodes", "lymphadenopathy", "adenopathy"],
    "jaundice":            ["jaundice", "icterus", "yellow skin"],
    "palpitations":        ["palpitations", "rapid heartbeat", "tachycardia"],
    "dizziness":           ["dizziness", "vertigo", "lightheadedness"],
    "numbness":            ["numbness", "paresthesia", "tingling", "hypoesthesia"],
    "vision loss":         ["vision loss", "visual impairment", "blindness"],
    "seizure":             ["seizure", "convulsion", "epileptic attack"],
}


def translate_fr_to_en(text: str) -> str:
    result = text.lower()
    for fr, en in sorted(FR_TO_EN_MEDICAL.items(), key=lambda x: -len(x[0])):
        result = result.replace(fr, en)
    return result


def expand_query(symptoms: str, lang: str = "en") -> list[str]:
    """
    Genere plusieurs variantes de la query pour ameliorer le recall.
    Retourne une liste de 3-5 queries.
    Gère FR, AR et EN.
    """
    queries = [symptoms]

    # Traduction si francais ou arabe
    if lang in ("fr", "ar"):
        en_version = translate_fr_to_en(symptoms)
        if en_version != symptoms.lower():
            queries.append(en_version)

    # Expansion des termes medicaux
    symptoms_lower = symptoms.lower()
    expanded_terms = []
    for term, expansions in SYMPTOM_EXPANSIONS.items():
        if term in symptoms_lower:
            expanded_terms.extend(expansions[1:])  # saute le premier (deja present)

    if expanded_terms:
        expanded_query = symptoms + " " + " ".join(expanded_terms[:5])
        queries.append(expanded_query)

    # Version clinique (ajoute termes medicaux)
    clinical_query = symptoms + " symptoms causes diagnosis"
    queries.append(clinical_query)

    return list(dict.fromkeys(queries))  # deduplique en gardant l'ordre


# ──────────────────────────────────────────────────────────
# RERANKER
# Reordonne les resultats Chroma avec logique medicale
# ──────────────────────────────────────────────────────────

DISEASE_KEY_SYMPTOMS = {
    "gastroenteritis":     ["diarrhea", "vomiting", "nausea", "cramps"],
    "appendicitis":        ["right abdominal pain", "right lower quadrant", "rebound"],
    "heart attack":        ["chest pain", "left arm", "sweating", "jaw", "radiating", "myocardial"],
    "myocardial":          ["chest pain", "left arm", "sweating", "jaw", "radiating"],
    "influenza":           ["fever", "cough", "body aches", "fatigue", "headache", "chills"],
    "flu":                 ["fever", "cough", "body aches", "fatigue", "headache", "chills"],
    "meningitis":          ["stiff neck", "neck stiffness", "photophobia", "rash"],
    "diabetes":            ["thirst", "urination", "blurred vision", "fatigue"],
    "tuberculosis":        ["night sweats", "weight loss", "chronic cough", "hemoptysis"],
    "covid":               ["loss of smell", "loss of taste", "anosmia", "ageusia"],
    "migraine":            ["throbbing", "photophobia", "nausea", "aura"],
    "pneumonia":           ["fever", "productive cough", "chest pain", "sputum"],
    "stroke":              ["sudden weakness", "facial droop", "speech", "arm weakness"],
    "parkinson":           ["resting tremor", "rigidity", "bradykinesia", "shuffling"],
    "epilepsy":            ["seizure", "convulsion", "loss of consciousness"],
    "glaucoma":            ["eye pain", "vision loss", "intraocular", "halos"],
    "cholecystitis":       ["right upper quadrant", "fatty food", "gallbladder"],
    "urinary tract":       ["burning urination", "dysuria", "cloudy urine", "frequency"],
    "kidney stones":       ["flank pain", "blood urine", "colicky", "renal"],
    "hepatitis":           ["jaundice", "dark urine", "pale stools", "liver"],
    "pancreatitis":        ["severe abdominal", "epigastric", "radiating back"],
    "rheumatoid arthritis":["morning stiffness", "symmetric", "hands", "feet joints"],
    "hypothyroidism":      ["cold intolerance", "weight gain", "dry skin", "constipation"],
    "hyperthyroidism":     ["heat intolerance", "weight loss", "palpitations", "anxiety"],
    "depression":          ["persistent sadness", "loss interest", "anhedonia"],
    "anxiety":             ["worry", "panic", "palpitations", "restlessness"],
    "asthma":              ["wheezing", "bronchospasm", "chest tightness", "inhaler"],
    "malaria":             ["cyclic fever", "chills", "tropical", "mosquito"],
    "lupus":               ["butterfly rash", "malar rash", "photosensitivity"],
    "multiple sclerosis":  ["relapsing", "optic neuritis", "demyelinating", "numbness tingling"],
}

COMPLICATIONS_LIST = {
    "hypovolemia", "dehydration", "shock", "septic shock",
    "respiratory failure", "organ failure", "cardiac arrest",
    "hypoxia", "acidosis", "coagulopathy", "hyponatremia",
    "hypokalemia", "hypocalcemia", "pulmonary edema", "cerebral edema",
    "ascites", "hepatic encephalopathy", "renal failure",
    "diabetic ketoacidosis", "hypertensive crisis", "withdrawal",
}


def _is_complication(name_en: str) -> bool:
    name = name_en.lower()
    return any(comp in name for comp in COMPLICATIONS_LIST)


def _key_symptom_match(disease_name: str, symptoms: str) -> float:
    name  = disease_name.lower()
    syms  = symptoms.lower()
    score = 0.0
    for key, key_syms in DISEASE_KEY_SYMPTOMS.items():
        if key in name:
            matched = sum(1 for ks in key_syms if ks in syms)
            score   = matched / len(key_syms)
            break
    return score


def rerank(diseases: list, symptoms_en: str, symptoms_fr: str = "") -> list:
    """
    Reordonne les resultats Chroma avec logique medicale.
    Appeler APRES search_diseases(), AVANT apply_smart_scoring().
    """
    combined = (symptoms_en + " " + symptoms_fr).lower()
    results  = []

    for d in diseases:
        name = d.get("name_en", "")

        # Exclure complications
        if _is_complication(name):
            logger.debug("Reranker: exclut complication '%s'", name)
            continue

        # Score de correspondance symptomes cles
        match_score = _key_symptom_match(name, combined)

        # Score final = confiance Chroma + bonus matching
        d["rerank_score"] = d.get("confidence", 0) + (match_score * 0.3)
        results.append(d)

    results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

    logger.info("Reranker: %d → %d maladies (complications filtrees)", len(diseases), len(results))
    return results


def multi_query_search(symptoms: str, lang: str, search_fn, k: int = 10) -> list:
    """
    Lance plusieurs recherches Chroma avec des queries expandees.
    Fusionne et deduplique les resultats.
    Remplace l'appel simple a search_diseases().

    Usage dans ton pipeline :
        from apps.chat.services.reranker import multi_query_search
        from apps.chat.services.chroma_service import search_diseases

        diseases = multi_query_search(
            symptoms  = symptoms,
            lang      = lang,
            search_fn = search_diseases,
            k         = 10,
        )
    """
    queries = expand_query(symptoms, lang)
    logger.info("Multi-query: %d queries generees", len(queries))

    seen     = {}
    for query in queries:
        try:
            results = search_fn(query, k=k, lang=lang)
            for d in results:
                name = d.get("name_en", "").lower()
                if name not in seen or d.get("confidence", 0) > seen[name].get("confidence", 0):
                    seen[name] = d
        except Exception as e:
            logger.warning("Multi-query echec pour '%s': %s", query[:40], e)

    merged = list(seen.values())
    merged.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    logger.info("Multi-query: %d resultats fusionnes", len(merged))
    return merged[:k]