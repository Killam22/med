# apps/chat/services/scoring.py
# VERSION 3 — coefficient medical FR corrige
#   - Ajout mots medicaux FR manquants (convulsions, morsure, conscience...)
#   - Normalisation probabilites (font 100%)
#   - Filtre complications
#   - Logique medicale

import logging
logger = logging.getLogger(__name__)

MIN_CONFIDENCE_THRESHOLD = 0.30

MEDICAL_KEYWORDS = {
    # EN
    "fever","cough","pain","fatigue","nausea","vomiting","diarrhea",
    "headache","dizziness","weakness","swelling","rash","itching",
    "bleeding","shortness","breath","chest","throat","muscle","joint",
    "back","abdomen","stomach","skin","weight","appetite","sleep",
    "vision","hearing","urine","blood","heart","lung","liver","kidney",
    "tremor","seizure","confusion","memory","anxiety","mood","sweating",
    "chills","thirst","burning","stiffness","numbness","palpitation",
    "cramp","discharge","sore","tender","swollen","pale","yellow","dark",
    "frequent","chronic","acute","sudden","severe","mild","persistent",
    "convulsion","consciousness","unconscious","paralysis","tongue",
    "bite","twitching","spasm","rigidity","syncope","fainting",
    # FR
    "fièvre","fievre","toux","douleur","mal","fatigue","nausée","nausee",
    "vomissement","diarrhée","diarrhee","vertiges","faiblesse","gonflement",
    "démangeaison","saignement","essoufflement","gorge","poitrine","ventre",
    "peau","poids","urine","sang","frisson","sueur","brûlure","raideur",
    "engourdissement","convulsions","convulsion","morsure","conscience",
    "paralysie","fourmillements","palpitations","bouffees","tremblements",
    "nuque","crampe","gonfle","douleurs","symptome","symptomes",
    "fievre","tete","oeil","oreille","nez","gorge","ventre","dos",
    "jambe","bras","pied","main","doigt","genou","epaule","hanche",
    "respiration","souffle","coeur","poumon","foie","rein","estomac",
    "intestin","cerveau","nerf","muscle","os","articulation","peau",
    # AR — enrichi (était trop limité → coefficient 0.40 pour tous les arabophones)
    "حمى","تعب","سعال","ألم","غثيان","قيء","إسهال","صداع","دوخة",
    "ضعف","تورم","طفح","حكة","نزيف","ضيق","صدر","حلق","عضلة",
    "مفصل","ظهر","بطن","معدة","جلد","وزن","نوم","رؤية","سمع",
    "بول","دم","قلب","رئة","كبد","كلية","رعشة","تشنج","ارتباك",
    # AR supplémentaires manquants
    "ألم","مرض","أعراض","عرض","أعاني","أشعر","وجع","صداع","دوار",
    "إمساك","انتفاخ","حرقة","بلع","صوت","سمع","بصر","عين","أذن",
    "أنف","فم","لسان","أسنان","رقبة","كتف","ذراع","يد","إصبع",
    "ركبة","قدم","ساق","ورك","صدر","قلب","رئة","كبد","كلى","معدة",
    "أمعاء","جلد","شعر","عظم","مفصل","عصب","دم","بول","براز",
    "حرارة","برودة","عرق","قشعريرة","تعرق","رجفة","خدر","وخز",
    "تورم","احمرار","طفح","حكة","جرح","كدمة","حرق","نزيف","قيح",
    "سعال","بلغم","ضيق","لهاث","أزيز","بحة","التهاب","عدوى",
    "حساسية","سكر","ضغط","كوليسترول","أنيميا","فقر دم",
    "اكتئاب","قلق","توتر","أرق","نسيان","صرع","شلل","إغماء",
    "إسهال","غثيان","قيء","مغص","انتفاخ","حموضة","نزلة","أنفلونزا",
    "كورونا","تشنج","خفقان","دوخة","إعياء","هزال","شهية",
}

# Mots courts medicaux
SHORT_MEDICAL = {
    # EN
    "flu","ear","eye","gut","arm","leg","rib","jaw","dry","wet","hot","red",
    "fit","tic",
    # FR
    "mal","dos","nez","sang","toux","oeil","pus","gel","feu",
    # AR
    "حمى","تعب","ألم","قيء",
}

# Termes medicaux FR specifiques pas detectes par MEDICAL_KEYWORDS
MEDICAL_KEYWORDS_FR_EXTRA = {
    "convulsions","convulsion","morsure","conscience","perte",
    "paralysie","paralysis","fourmillements","bouffees","tremblements",
    "raideur","nuque","crampes","gonfle","douleurs","symptomes",
    "saignements","brulures","demangeaisons","vertiges","malaise",
    "etourdissements","essoufflement","palpitations","sueurs",
    "frissons","fievre","nausees","vomissements","diarrhee",
    "constipation","ballonnements","reflux","brulure","ulcere",
    "eruption","plaques","demangeaison","gonflement","oedeme",
    "fatigue","asthenie","insomnie","anorexie","amaigrissement",
    "grossesse","menstruation","regles","menopause","impuissance",
    "dysurie","hematurie","pollakiurie","anurie","polyurie",
    "dysphagie","odynophagie","aphonie","dysphonie","toux",
    "hemoptysie","epistaxis","otorrhee","otalgies","acouphenes",
    "diplopie","photophobie","phonophobie","photopsie","scotome",
    "ataxie","dysarthrie","dysphasie","aphasie","amnesia",
    "syncope","lipothymie","vertige","cephalee","migraine",
}


def is_medical_message(symptoms_en: str, symptoms_fr: str = "") -> float:
    """
    Detecte si le message contient des termes medicaux.
    Retourne un coefficient entre 0.0 et 1.0.
    """
    combined = (symptoms_en + " " + symptoms_fr).lower()
    words    = set(combined.split())

    # Compte mots medicaux principaux
    count = sum(1 for w in words if any(kw in w or w in kw for kw in MEDICAL_KEYWORDS))

    # Bonus pour termes medicaux FR specifiques
    fr_bonus = sum(1 for w in words if w in MEDICAL_KEYWORDS_FR_EXTRA)
    count += fr_bonus

    if count >= 3:   return 1.0
    elif count == 2: return 0.85
    elif count == 1: return 0.65
    else:            return 0.40


def _symptom_overlap(symptoms_en: str, key_symptoms: str) -> float:
    if not key_symptoms or not symptoms_en:
        return 0.0
    patient = {w for w in symptoms_en.lower().split() if len(w) >= 2}
    disease = {w for w in key_symptoms.lower().replace(",", " ").split() if len(w) >= 2}
    patient |= {w for w in symptoms_en.lower().split() if w in SHORT_MEDICAL}
    disease |= {w for w in key_symptoms.lower().split() if w in SHORT_MEDICAL}
    if not disease:
        return 0.0
    common  = patient & disease
    union   = patient | disease
    jaccard = len(common) / len(union) if union else 0
    overlap = len(common) / len(disease)
    return min(jaccard * 0.4 + overlap * 0.6, 1.0)


def _urgency_score(urgency: str, severity: float) -> float:
    base = {"urgent": 1.0, "modéré": 0.6, "modere": 0.6, "faible": 0.3}.get(urgency, 0.5)
    if severity > 5:
        base = min(base + 0.2, 1.0)
    return base


def _medical_logic_score(disease: dict, symptoms_en: str) -> float:
    """
    Score base sur la logique medicale :
    +  symptome cle present    → +poids
    -  symptome cle absent     → -1.5
    -  symptome exclu present  → -3.0
    +  symptome optionnel      → +0.5
    """
    syms         = symptoms_en.lower()
    key_syms     = disease.get("key_symptoms_list", [])
    optional_syms= disease.get("optional_symptoms", [])
    exclude_syms = disease.get("exclude_symptoms", [])
    weights      = disease.get("symptom_weights", {})
    score        = 0.0

    for ks in key_syms:
        if any(word in syms for word in ks.lower().split()):
            score += weights.get(ks, 2)
        else:
            score -= 1.5

    for es in exclude_syms:
        if any(word in syms for word in es.lower().split()):
            score -= 3.0

    for os_ in optional_syms:
        if any(word in syms for word in os_.lower().split()):
            score += 0.5

    max_possible = sum(weights.get(k, 2) for k in key_syms) + len(optional_syms) * 0.5
    if max_possible > 0:
        score = score / max_possible
    return max(-1.0, min(1.0, score))


def compute_smart_score(
    disease:      dict,
    symptoms_en:  str,
    vector_score: float,
    nih_valid:    bool,
    medical_coef: float = 1.0,
) -> float:
    if medical_coef == 0.0:
        return 0.0

    score_vector   = vector_score * 0.30
    key_symptoms   = disease.get("key_symptoms", "")
    score_symptoms = _symptom_overlap(symptoms_en, key_symptoms) * 0.25
    score_nih      = (1.0 if nih_valid else 0.0) * 0.15
    urgency        = disease.get("urgency", "modéré").lower()
    severity       = float(disease.get("severity", "0") or 0)
    score_urgency  = _urgency_score(urgency, severity) * 0.10
    logic_score    = _medical_logic_score(disease, symptoms_en)
    score_logic    = ((logic_score + 1) / 2) * 0.20

    raw   = score_vector + score_symptoms + score_nih + score_urgency + score_logic
    final = round(raw * medical_coef, 3)

    logger.debug(
        "Score '%s': vec=%.2f symp=%.2f nih=%.2f urg=%.2f logic=%.2f coef=%.2f → %.3f",
        disease.get("name_en", ""),
        score_vector, score_symptoms, score_nih, score_urgency, score_logic,
        medical_coef, final
    )

    return min(final, 1.0)


def apply_smart_scoring(
    diseases:     list,
    symptoms_en:  str,
    nih_results:  dict = None,
    symptoms_fr:  str  = "",
) -> list:
    nih_results  = nih_results or {}
    medical_coef = is_medical_message(symptoms_en, symptoms_fr)
    logger.info("Coefficient medical: %.2f pour '%s'", medical_coef, symptoms_en[:50])

    # ── Filtre complications et symptomes ─────────────────
    diseases_only = []
    for d in diseases:
        dtype = d.get("type", "disease")
        if dtype == "complication":
            logger.debug("Filtre complication '%s'", d.get("name_en", ""))
            continue
        if dtype == "symptom":
            logger.debug("Filtre symptome '%s'", d.get("name_en", ""))
            continue
        diseases_only.append(d)

    if not diseases_only:
        diseases_only = diseases

    # ── Scoring ───────────────────────────────────────────
    scored = []
    for disease in diseases_only:
        name_en      = disease.get("name_en", "")
        vector_score = disease.get("confidence", 0)
        nih_valid    = nih_results.get(name_en, False)

        disease["raw_score"] = compute_smart_score(
            disease      = disease,
            symptoms_en  = symptoms_en,
            vector_score = vector_score,
            nih_valid    = nih_valid,
            medical_coef = medical_coef,
        )

        if disease["raw_score"] >= MIN_CONFIDENCE_THRESHOLD:
            scored.append(disease)
        else:
            logger.debug("Filtre '%s' — score %.3f < seuil %.2f",
                name_en, disease["raw_score"], MIN_CONFIDENCE_THRESHOLD)

    scored.sort(key=lambda d: d.get("raw_score", 0), reverse=True)

    # ── Normalisation probabilites (font 100%) ────────────
    total = sum(d.get("raw_score", 0) for d in scored)
    for d in scored:
        if total > 0:
            d["confidence"]  = d["raw_score"]
            d["probability"] = round((d["raw_score"] / total) * 100, 1)
        else:
            d["confidence"]  = 0
            d["probability"] = 0

    logger.info("%d/%d maladies conservees (seuil=%.2f)",
        len(scored), len(diseases), MIN_CONFIDENCE_THRESHOLD)

    for d in scored[:3]:
        logger.info("  → %s : %.1f%%", d.get("name_en", ""), d.get("probability", 0))

    return scored