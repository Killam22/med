# apps/chat/services/chroma_service.py

import logging
from diagnostic_ai.infrastructure.vector_db.chroma_client import get_client
from diagnostic_ai.infrastructure.embeddings.encoder import encode

logger = logging.getLogger(__name__)

COLLECTION_COMMON    = "medical_common"
COLLECTION_RARE      = "medical_rare"
THRESHOLD_COMMON = 0.40
THRESHOLD_RARE   = 0.50
RARE_PRIORITY_MARGIN = 0.03

# ══════════════════════════════════════════════════════════
# MOTS CLÉS D'URGENCE
# ══════════════════════════════════════════════════════════
 
URGENT_KEYWORDS = [
    # FR
    "bras gauche","douleur poitrine intense","raideur nuque fièvre",
    "perte conscience","convulsions","paralysie","avc","sang urine",
    "douleur thoracique intense","sueurs froids","infarctus","méningite",
    # EN
    "left arm pain","chest pain radiating","stiff neck fever",
    "loss of consciousness","seizures","paralysis","stroke",
    "blood in urine","severe chest pain","cold sweats","heart attack","meningitis",
    # AR
    "ألم صدري شديد","تصلب رقبة","فقدان وعي","تشنجات","شلل",
]

# ══════════════════════════════════════════════════════════
# DICTIONNAIRE MÉDICAL FR/AR → EN (complet)
# ══════════════════════════════════════════════════════════

MEDICAL_TRANSLATIONS = {
    # ── Urgences ─────────────────────────────────────────
    "douleur thoracique intense bras gauche": "severe chest pain radiating left arm heart attack myocardial infarction",
    "bras gauche sueurs froids":    "left arm cold sweats heart attack cardiac emergency",
    "bras gauche":                  "left arm radiating pain cardiac",
    "douleur thoracique intense":   "severe chest pain heart attack cardiac emergency",
    "sueurs froids":                "cold sweats diaphoresis cardiac",
    "raideur nuque fièvre":         "stiff neck fever meningitis bacterial meningeal",
    "raideur nuque":                "stiff neck nuchal rigidity meningitis",

    # ── COVID / Respiratoire ──────────────────────────────
    "perte odorat perte goût":      "loss smell anosmia loss taste ageusia covid-19 coronavirus",
    "perte d'odorat perte de goût": "loss smell anosmia loss taste ageusia covid",
    "perte odorat":                 "loss of smell anosmia covid coronavirus",
    "perte goût":                   "loss of taste ageusia covid coronavirus",
    "perte d'odorat":               "loss of smell anosmia",
    "perte de goût":                "loss of taste ageusia",

    # ── Parkinson ─────────────────────────────────────────
    "tremblements rigidité lenteur":  "tremor rigidity bradykinesia parkinson disease",
    "tremblements repos":             "resting tremor parkinson",
    "lenteur mouvement":              "bradykinesia slow movement parkinson",
    "équilibre instable":             "balance problems gait disorder parkinson",

    # ── Rein ──────────────────────────────────────────────
    "sang urine douleur dos":       "blood urine hematuria flank pain kidney stones renal calculi",
    "sang urine":                   "blood in urine hematuria kidney stones",
    "douleur dos intense":          "severe flank pain kidney stones renal colic",
    "colique néphrétique":          "renal colic kidney stones severe flank pain",

    # ── Dermatologie ──────────────────────────────────────
    "squames épaisses":             "thick scales plaque psoriasis",
    "plaques squameuses":           "scaly plaques psoriasis chronic",
    "peau squameuse rouge":         "scaly red skin psoriasis eczema dermatitis",
    "démangeaisons chroniques":     "chronic itching pruritus psoriasis eczema",
    "phénomène raynaud":            "raynaud phenomenon scleroderma fingers cold",
    "peau dure doigts":             "skin hardening fingers scleroderma systemic sclerosis",

    # ── Maladies rares ────────────────────────────────────
    "faiblesse musculaire progressive": "progressive muscle weakness ALS amyotrophic lateral sclerosis",
    "fasciculations atrophie":      "fasciculations muscle atrophy ALS motor neuron",
    "fatigue musculaire double vision": "muscle weakness fatigue double vision myasthenia gravis",
    "sécheresse yeux bouche":       "dry eyes dry mouth sjogren syndrome",
    "papillon joues":               "butterfly rash malar lupus erythematosus",
    "rash papillon":                "butterfly rash lupus malar erythematosus",

    # ── Psychiatrique ─────────────────────────────────────
    "épisodes maniaques":           "manic episodes bipolar disorder mania",
    "pensées intrusives rituels":   "intrusive thoughts rituals compulsions OCD obsessive",
    "flashbacks cauchemars":        "flashbacks nightmares PTSD post traumatic stress",
    "humeur instable manie":        "mood swings mania bipolar disorder",
    "trouble obsessionnel":         "obsessive compulsive disorder OCD rituals",
    "stress post traumatique":      "post traumatic stress disorder PTSD flashbacks",
    "trouble bipolaire":            "bipolar disorder manic depression mood swings",
    "déficit attention":            "attention deficit hyperactivity ADHD",
    "phobie panique":               "phobia panic disorder anxiety attacks",

    # ── Symptômes courants FR ─────────────────────────────
    "fièvre":        "fever", "toux sèche":    "dry cough", "toux grasse":   "productive cough",
    "toux":          "cough", "fatigue":       "fatigue",   "maux de tête":  "headache",
    "mal de tête":   "headache", "nausées":    "nausea",    "nausée":        "nausea",
    "vomissements":  "vomiting", "vomissement":"vomiting",  "diarrhée":      "diarrhea",
    "constipation":  "constipation", "frissons":"chills",   "sueurs nocturnes":"night sweats",
    "sueurs":        "sweating","essoufflement":"shortness of breath",
    "vertiges":      "dizziness","vertige":    "dizziness", "faiblesse":     "weakness",
    "gonflement":    "swelling","démangeaisons":"itching",  "démangeaison":  "itching",
    "saignements":   "bleeding","saignement":  "bleeding",  "brûlures":      "burning",
    "brûlure":       "burning", "raideur":     "stiffness", "engourdissement":"numbness",
    "palpitations":  "palpitations","tremblements":"tremor","convulsions":   "seizures epilepsy",
    "crampes":       "cramps",  "jaunisse":    "jaundice",  "tristesse":     "sadness",
    "désespoir":     "hopelessness","squames":  "scaly skin","sang":          "blood",
    "thoracique":    "chest",   "poitrine":    "chest",     "abdominale":    "abdominal",
    "ventre":        "abdomen", "gorge":       "throat",    "nuque":         "stiff neck",
    "dos":           "back",    "articulaire": "joint",     "articulation":  "joint",
    "musculaire":    "muscle",  "peau":        "skin",      "droite":        "right",
    "gauche":        "left",    "sévère":      "severe",    "chronique":     "chronic",
    "persistant":    "persistent","soudain":   "sudden",    "cyclique":      "cyclic",
    "intense":       "intense severe","léger":  "mild",      "fréquent":      "frequent",
    "perte de poids":"weight loss","perte d'appétit":"loss of appetite",
    "perte d'intérêt":"loss of interest","perte de mémoire":"memory loss cognitive",
    "mal de gorge":  "sore throat","douleur thoracique":"chest pain",
    "douleur abdominale":"abdominal pain","douleur articulaire":"joint pain arthralgia",
    "miction fréquente":"frequent urination","brûlure miction":"burning urination dysuria",
    "urine trouble": "cloudy urine","urine foncée":"dark urine jaundice",
    "vision floue":  "blurred vision","sensibilité lumière":"photophobia light sensitivity",
    "raideur matinale":"morning stiffness arthritis","plaques rouges":"red patches psoriasis",
    "peau rouge":    "red skin rash",

    # ── Maladies FR ───────────────────────────────────────
    "paludisme":     "malaria plasmodium fever chills",
    "grippe":        "influenza flu fever cough body aches",
    "rhume":         "common cold rhinovirus runny nose",
    "bronchite":     "bronchitis cough mucus airway",
    "pneumonie":     "pneumonia lung infection fever",
    "appendicite":   "appendicitis right abdominal pain",
    "gastrite":      "gastritis stomach burning nausea",
    "hépatite":      "hepatitis liver jaundice fatigue",
    "diabète":       "diabetes mellitus hyperglycemia thirst urination",
    "hypertension":  "high blood pressure headache dizziness",
    "dépression":    "depression sadness hopelessness fatigue",
    "anxiété":       "anxiety worry panic fear heart racing",
    "épilepsie":     "epilepsy seizures convulsions",
    "méningite":     "meningitis stiff neck fever headache",
    "tuberculose":   "tuberculosis lung cough blood weight loss",
    "asthme":        "asthma wheezing shortness breath",
    "arthrite":      "arthritis joint pain swelling stiffness",
    "psoriasis":     "psoriasis scaly red skin plaques itching",
    "eczéma":        "eczema atopic dermatitis itching dry skin",
    "lupus":         "lupus erythematosus butterfly rash joint pain",
    "sclérodermie":  "scleroderma skin hardening raynaud fibrosis",
    "fibromyalgie":  "fibromyalgia chronic pain fatigue tender points",
    "infarctus":     "myocardial infarction heart attack chest pain",
    "avc":           "stroke brain cerebrovascular accident",

    # ── Arabe enrichi ─────────────────────────────────────
    "حمى":           "fever high temperature",
    "سعال":          "cough respiratory",
    "ألم":           "pain ache",
    "تعب":           "fatigue weakness tiredness",
    "غثيان":         "nausea vomiting",
    "قيء":           "vomiting nausea",
    "إسهال":         "diarrhea loose stool",
    "صداع":          "headache head pain",
    "دوخة":          "dizziness vertigo",
    "تورم":          "swelling edema",
    "حكة":           "itching pruritus skin",
    "نزيف":          "bleeding hemorrhage",
    "ضعف":           "weakness fatigue",
    "رعشة":          "tremor shaking parkinson",
    "تشنج":          "seizure epilepsy convulsion",
    "يرقان":         "jaundice yellow skin hepatitis",
    "عطش":           "thirst excessive diabetes",
    "تعرق":          "sweating perspiration",
    "قشعريرة":       "chills fever shivering",
    "ضيق تنفس":      "shortness of breath dyspnea respiratory",
    "ألم صدري":      "chest pain cardiac heart",
    "فقدان وزن":     "weight loss cachexia",
    "تصلب رقبة":     "stiff neck meningitis nuchal rigidity",
    "فقدان شم":      "loss of smell anosmia covid coronavirus",
    "فقدان تذوق":    "loss of taste ageusia covid",
    "كثرة التبول":   "frequent urination polyuria diabetes",
    "عطش مفرط":      "excessive thirst polydipsia diabetes",
    "ضبابية الرؤية": "blurred vision visual disturbance diabetes",
    "حزن مستمر":     "persistent sadness depression mood disorder",
    "فقدان اهتمام":  "loss of interest anhedonia depression",
    "اضطراب نوم":    "sleep disorder insomnia depression anxiety",
    "قلق مفرط":      "excessive anxiety worry panic disorder",
    "حمى دورية":     "cyclic fever malaria plasmodium",
    "تعرق ليلي":     "night sweats tuberculosis fever",
    "سعال دموي":     "bloody cough hemoptysis tuberculosis",
    "تصلب":          "stiffness rigidity parkinson arthritis",
    "بطء حركة":      "bradykinesia slow movement parkinson",
    "صعوبة توازن":   "balance difficulty gait parkinson",
    "جفاف عيون":     "dry eyes sjogren syndrome",
    "جفاف فم":       "dry mouth sjogren syndrome",
    "طفح فراشة":     "butterfly rash lupus malar",
    "تساقط شعر":     "hair loss alopecia lupus",
    "تصلب جلد":      "skin hardening scleroderma",
    "أصابع رينو":    "raynaud fingers scleroderma cold",
    "حزن":           "sadness depression",
    "يأس":           "hopelessness depression",
    "خوف":           "fear anxiety phobia",
    "ذعر":           "panic disorder anxiety attack",
    "وسواس":         "obsessive compulsive OCD rituals",
    "كوابيس":        "nightmares PTSD trauma",
    "ذكريات مؤلمة":  "flashbacks PTSD post traumatic",
    "نوبات هوس":     "manic episodes bipolar disorder",
    "مزاج متقلب":    "mood swings bipolar disorder",
    # ── AR Infarctus / Urgences cardiaques ────────────────
    "ألم في الصدر":          "chest pain heart attack myocardial infarction cardiac",
    "ألم صدري بالذراع":      "chest pain left arm heart attack myocardial infarction",
    "الذراع الأيسر":         "left arm radiating pain cardiac heart attack",
    "ألم في الذراع الأيسر":  "left arm pain heart attack myocardial infarction",
    "تعرق وألم صدري":        "sweating chest pain heart attack cardiac emergency",
    "ضيق صدر":               "chest tightness cardiac angina heart attack",
    # ── AR Grippe ──────────────────────────────────────────
    "حمى وسعال وتعب":        "fever cough fatigue influenza flu",
    "آلام الجسم":             "body aches myalgia influenza flu",
    "آلام العضلات":           "muscle pain myalgia influenza body aches",
    "صداع وحمى":             "headache fever influenza flu",
    "حمى شديدة وسعال":       "high fever cough influenza flu respiratory",
    "سعال جاف":              "dry cough influenza covid respiratory",
    "أعاني من حمى":          "fever high temperature influenza flu",
}


def is_urgent(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in URGENT_KEYWORDS)


def translate_medical_local(text: str) -> str:
    result = text.lower()
    for fr_term, en_term in sorted(MEDICAL_TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        result = result.replace(fr_term.lower(), en_term)
    return result.strip()


def translate_to_english(text: str, lang: str) -> str:
    if lang == "en":
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        if translated and translated.lower() != text.lower():
            return translated
    except Exception as e:
        logger.warning("deep_translator échoué: %s", e)
    return translate_medical_local(text)


def get_col_common():
    return get_client().get_collection(COLLECTION_COMMON)


def get_col_rare():
    return get_client().get_collection(COLLECTION_RARE)


def _query(collection, embedding, k: int, threshold: float) -> list:
    try:
        results = collection.query(
            query_embeddings = embedding,
            n_results        = k,
            include          = ["documents", "metadatas", "distances"]
        )
        diseases = []
        for i, doc in enumerate(results["documents"][0]):
            meta       = results["metadatas"][0][i]
            distance   = results["distances"][0][i]
            # multilingual-e5-large avec espace ip retourne des scores [0,1]
            # (inner product avec normalize=True = cosine similarity)
            confidence = round(max(0.0, 1.0 - (distance / 2.0)), 3)
            if confidence < threshold:
                continue
            diseases.append({
                "document":     doc,
                "name_fr":      meta.get("name_fr", ""),
                "name_en":      meta.get("name_en", ""),
                "name_ar":      meta.get("name_ar", ""),
                "specialist":   meta.get("specialist", ""),
                "category":     meta.get("category", ""),
                "urgency":      meta.get("urgency", "modéré"),
                "icd10":        meta.get("icd10", ""),
                "severity":     meta.get("severity", "0"),
                "confidence":   confidence,
                "key_symptoms": meta.get("key_symptoms", ""),
                "is_rare":      meta.get("is_rare", "false") == "true",
            })
        return diseases
    except Exception as e:
        logger.error("Erreur query: %s", e)
        return []


def _smart_merge(common: list, rare: list, max_results: int = 5) -> list:
    if not common and not rare:
        return []
    best_common    = max((d["confidence"] for d in common), default=0)
    rare_priority  = [d for d in rare if d["confidence"] >= best_common + RARE_PRIORITY_MARGIN]
    rare_secondary = [d for d in rare if d["confidence"] <  best_common + RARE_PRIORITY_MARGIN]
    for d in rare_priority:
        logger.info("🔬 Rare prioritaire: '%s' (%.3f)", d["name_en"], d["confidence"])
    ordered = rare_priority + common + rare_secondary
    seen, merged = set(), []
    for d in ordered:
        name = d.get("name_en", "").lower()
        if name not in seen:
            seen.add(name)
            merged.append(d)
    merged.sort(key=lambda x: -x["confidence"])
    return merged[:max_results]


def search_diseases(
    query:    str,
    k:        int  = 5,
    lang:     str  = "fr",
    query_en: str  = None,
) -> list:
    """
    Recherche intelligente dans 2 collections Chroma.
    Traduit FR/AR → EN via Google Translate + dictionnaire local enrichi.
    Détecte les urgences et baisse le seuil automatiquement.
    """
    try:
        if not query_en:
            query_en = translate_to_english(query, lang)

        if lang in ["fr", "ar"]:
            local    = translate_medical_local(query)
            combined = " ".join(dict.fromkeys(f"{query_en} {local}".split()))
        else:
            combined = query_en

        embedding = encode([combined])

        urgent      = is_urgent(query) or is_urgent(combined)
        threshold_c = 0.62 if urgent else THRESHOLD_COMMON
        threshold_r = 0.78 if urgent else THRESHOLD_RARE
        if urgent:
            logger.info("🚨 Urgence détectée — seuil baissé à %.2f", threshold_c)

        try:
            results_common = _query(get_col_common(), embedding, k, threshold_c)
        except Exception as e:
            logger.warning("Collection commune indisponible: %s", e)
            results_common = []

        try:
            results_rare = _query(get_col_rare(), embedding, k, threshold_r)
        except Exception as e:
            logger.warning("Collection rare indisponible: %s", e)
            results_rare = []

        merged = _smart_merge(results_common, results_rare, max_results=k)

        logger.info(
            "Search '%s' urgent=%s → common:%d rare:%d merged:%d",
            combined[:40], urgent, len(results_common), len(results_rare), len(merged)
        )

        return merged

    except Exception as e:
        logger.error("Chroma search failed: %s", e)
        return []