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
    "toothache","dental","tooth","gum","cavity","abscess","caries",
    "earache","sore throat","runny nose","stuffy","congestion","sneeze",
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
    "dent","gencive","carie","abces","oreille","gorge","nez",
    "yeux","oeil","larmes","vision","peau","rash",
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
    "larmoiements","sécrétions","secretions","ecoulement","yeux","larmes",
    "demangeaisons","ecoulements","conjonctivite","ophtalmique",
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
    # key_symptoms_list is rarely set in ChromaDB — parse key_symptoms string as fallback
    key_syms     = disease.get("key_symptoms_list") or []
    if not key_syms:
        raw = disease.get("key_symptoms", "") or ""
        key_syms = [s.strip() for s in raw.replace(",", " ").split() if s.strip()]
    optional_syms= disease.get("optional_symptoms") or []
    exclude_syms_raw = disease.get("exclude_symptoms") or []
    if isinstance(exclude_syms_raw, str):
        exclude_syms_raw = [s.strip() for s in exclude_syms_raw.replace(",", " ").split() if s.strip()]
    exclude_syms = exclude_syms_raw
    weights      = disease.get("symptom_weights") or {}
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


# Prévalence relative des maladies (source : données CDC/HAS/OMS).
# Valeur entre 0.7 (très rare) et 1.15 (très fréquente).
# Appliqué comme multiplicateur léger pour départager à score égal.
_PREVALENCE_BOOST: dict[str, float] = {
    # Très fréquentes
    "influenza":              1.15,
    "flu":                    1.15,
    "common cold":            1.15,
    "covid":                  1.12,
    "covid-19":               1.12,
    "hypertension":           1.12,
    "diabetes":               1.10,
    "gastroenteritis":        1.10,
    "urinary tract infection": 1.10,
    "anxiety":                1.08,
    "depression":             1.08,
    "back pain":              1.08,
    "migraine":               1.07,
    "allergic rhinitis":      1.07,
    "sinusitis":              1.07,
    "bronchitis":             1.06,
    "otitis media":           1.06,
    "tonsillitis":            1.05,
    "asthma":                 1.05,
    "pneumonia":              1.05,
    "conjunctivitis":         1.05,
    "eczema":                 1.04,
    "psoriasis":              1.03,
    "hypothyroidism":         1.03,
    "anemia":                 1.03,
    "rheumatoid arthritis":   1.02,
    "osteoarthritis":         1.02,
    "insomnia":               1.02,
    # Reflux / digestif — plus commun que ses complications
    "heartburn":              1.08,
    "gastritis":              1.06,
    "peptic ulcer":           1.04,
    "gerd":                   1.08,
    "gastroesophageal reflux": 1.08,
    # Rares → légère pénalité (pas forte pour ne pas exclure)
    "rabies":                 0.75,
    "ebola":                  0.72,
    "plague":                 0.72,
    "cholera":                0.75,
    "yellow fever":           0.77,
    "leprosy":                0.75,
    "tetanus":                0.80,
    "tularemia":              0.80,
    "mollaret meningitis":    0.80,
    "porphyria":              0.80,
    # Traumatismes musculo-squelettiques — très fréquents après chutes/chocs
    "ankle sprain":           1.15,
    "sprain":                 1.12,
    "fracture":               1.05,
    "contusion":              1.05,
    "ligament":               1.08,
    "musculoskeletal injury": 1.08,
    # Complications / pathologies nécessitant investigation spécialisée
    "barrett esophagus":      0.78,
    "tracheobronchomalacia":  0.72,
    "swyer-james":            0.70,
    "parsonage turner":       0.73,
    "gastroparesis":          0.82,
    "silicosis":              0.78,
    "idiopathic pulmonary":   0.78,
}


def _prevalence_factor(name_en: str) -> float:
    name = name_en.lower()
    for key, factor in _PREVALENCE_BOOST.items():
        if key in name:
            return factor
    return 1.0


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

    raw        = score_vector + score_symptoms + score_nih + score_urgency + score_logic
    prevalence = _prevalence_factor(disease.get("name_en", ""))
    final      = round(raw * medical_coef * prevalence, 3)

    logger.debug(
        "Score '%s': vec=%.2f symp=%.2f nih=%.2f urg=%.2f logic=%.2f coef=%.2f prev=%.2f → %.3f",
        disease.get("name_en", ""),
        score_vector, score_symptoms, score_nih, score_urgency, score_logic,
        medical_coef, prevalence, final
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

    # Noms qui sont des symptômes/non-maladies, jamais des diagnostics
    SYMPTOM_NAMES = {
        "fever", "headache", "pain", "fatigue", "nausea", "cough",
        "dizziness", "vomiting", "diarrhea", "rash", "itching",
        "weakness", "swelling", "bleeding", "shortness of breath",
        "flu shot", "vaccination", "cold and cough medicines",
        "chest pain", "chest injuries and disorders",
        "vital signs", "personal health records",
        "children's page", "health checkup", "healthy living",
        "dental health", "child dental health", "mental health",
        "health topics", "medical terms", "first aid",
        "orthodontia", "cosmetic dentistry",
        "oral hygiene", "preventive dentistry",
        "diet and nutrition", "exercise and fitness",
        # Pages génériques NIH (catégories, pas des maladies)
        "tooth disorders", "tooth disorder", "dental disorders", "throat disorders",
        "swallowing disorders", "mouth disorders", "nose injuries and disorders",
        "skin disorders", "eye disorders", "ear disorders", "bone disorders",
        "heart disorders", "lung disorders", "kidney disorders",
        "liver disorders", "stomach disorders", "bowel disorders",
        "joint disorders", "muscle disorders", "nerve disorders",
        "blood disorders", "immune disorders", "hormone disorders",
        "understanding medical research", "pinkeye",
        "jaw injuries and disorders", "nose injuries and disorders",
        "children's health",
        # Pages NIH pour tranches d'âge / populations
        "teen health", "teens", "teen page", "teenagers",
        "children's page", "kids page", "baby health",
        "men's health", "women's health", "senior health",
        "page pour adolescents", "santé des adolescents",
        # Pages info génériques
        "about", "overview", "introduction", "basics",
        # Pages contextuelles NIH non-pathologiques
        "family history", "international health", "homeless health concerns",
        "child care", "toddler health", "parenting",
        "sexually transmitted diseases",
        "mental disorders",
        "coping with disasters", "coping with chronic illness",
        # Catégories trop larges
        "health care", "healthcare", "medical care",
        "emergency care", "urgent care",
        # Symptômes / termes génériques capturés comme maladies
        "memory", "gas", "gas in the digestive tract",
        "short stature", "growth problems",
        "pain management",
        # Pages symptômes / situations génériques pas des maladies
        "falls", "fall prevention", "fall risk",
        # Pages aidants / support NIH
        "alzheimer's caregivers", "caregivers", "caregiver support",
        "cancer care", "palliative care",
    }
    # Préfixes génériques (pages d'aide, guides, catégories)
    GENERIC_PREFIXES = (
        "coping with", "living with chronic", "what i need to know",
        "understanding ", "guide to ", "managing your ",
        "short stature",
        "colonic diseases", "colonic disease",
        "digestive diseases", "gastrointestinal diseases",
    )
    # Filtrer aussi les noms se terminant par des suffixes génériques NIH
    GENERIC_SUFFIXES = (
        " injuries and disorders", " injuries",
        " health topics", " problems",
        "'s page", " page",
        " caregivers", " caregiver",
        " information", " resources",
    )

    # Maladies nécessitant un contexte spécifique absent du message
    CONTEXT_REQUIRED = {
        # maladie : mots qui doivent être présents dans les symptômes
        "endometriosis":                {"menstrual","period","règle","pelvic","pelv","gynéco","utérus","uterus","menstruation","ovaire","ovary"},
        "neuroleptic malignant syndrome":{"antipsychotic","neuroleptic","drug","médicament","traitement","halopéridol","rispéridone","clozapine","olanzapine"},
        "dengue fever":                 {"tropical","dengue","mosquito","moustique","voyage","travel"},
        "malaria":                      {"tropical","malaria","paludisme","mosquito","moustique","voyage","travel","africa","afrique"},
        "lymphatic filariasis":         {"lymphedema","elephantiasis","tropical","filaria","swelling limb"},
        "parasites - lymphatic filariasis": {"lymphedema","elephantiasis","tropical","filaria"},
        "bird flu":                     {"bird","poultry","volaille","avian","poulet"},
        # Encéphalites / maladies neurologiques graves — requièrent signes neuro
        "herpes simplex encephalitis":  {"confusion","encephalitis","encéphalite","alteration","altered","consciousness","conscience","seizure","convulsion","focal","neurological","agitation","bizarre","hallucin","rigidity","nuchal","stiff neck"},
        "encephalitis":                 {"confusion","encephalitis","encéphalite","altered","consciousness","conscience","seizure","convulsion","focal","neurological","agitation"},
        "viral encephalitis":           {"confusion","encephalitis","encéphalite","altered","consciousness","seizure","convulsion","focal","neurological"},
        "bacterial meningitis":         {"stiff","nuchal","rigidity","photophobia","phonophobia","nuque","raideur","méningisme","meningism","meningit"},
        "meningitis":                   {"stiff","nuchal","rigidity","photophobia","phonophobia","nuque","raideur","méningisme","meningism","meningit"},
        "rabies":                       {"bite","morsure","animal","chien","dog","cat","chat","hydrophobie","hydrophobia","aerophobia"},
        "tetanus":                      {"wound","plaie","blessure","cut","coupure","soil","terre","trismus","jaw","lockjaw","spasm","rigidity"},
        "botulism":                     {"food","aliment","conserve","canned","paralysis","descending","diplopia","dysphagia"},
        "leptospirosis":                {"water","eau","flood","inondation","rat","rodent","rongeur","jaundice","ictere","ictère","river","rivière"},
        "typhoid fever":                {"travel","voyage","contaminated","contaminé","water","eau","typhoid","typhoïde","enteric","abdomen rose"},
        "brucellosis":                  {"animal","livestock","bétail","cattle","sheep","mouton","goat","chèvre","unpasteurized","non pasteurisé","zoonose"},
        # Maladies thoraciques — requièrent symptômes chest/rib/sternum
        "tietze syndrome":              {"chest","rib","sternum","poitrine","côte","cote","thorax","costal","costochondral","sternal"},
        "syndrome de tietze":           {"chest","rib","sternum","poitrine","côte","cote","thorax","costal","costochondral","sternal"},
        "tietze's syndrome":            {"chest","rib","sternum","poitrine","côte","cote","thorax","costal","costochondral","sternal"},
        "costochondritis":              {"chest","rib","sternum","poitrine","côte","cote","thorax","costal"},
        "costochondrite":               {"chest","rib","sternum","poitrine","côte","cote","thorax","costal"},
        "pleuritis":                    {"chest","pleurisy","poitrine","thorax","breathing","respiration"},
        "pericarditis":                 {"chest","heart","palpitations","poitrine","coeur","thorax"},
        # Cancers/malignités — requièrent signaux d'alarme spécifiques
        "adenocarcinoma":               {"blood","bleeding","rectal","rectal bleeding","hematochezia","melena","weight loss","perte de poids","anorexia","anorexie","night sweats","sueurs nocturnes","mass","tumour","tumor"},
        "adenocarcinoma of the appendix": {"blood","bleeding","rectal","weight loss","perte de poids","anorexia","mass","tumour","tumor","appendix","appendice"},
        "colorectal cancer":            {"blood","bleeding","rectal","weight loss","perte de poids","anorexia","anorexie","occult","iron deficiency"},
        "colon cancer":                 {"blood","bleeding","rectal","weight loss","perte de poids","anorexia","mass","tumour","tumor"},
        # Maladies chroniques musculo-squelettiques — requièrent douleurs musculaires diffuses
        "fibromyalgia":                 {"muscle","musculaire","fibro","widespread pain","douleur diffuse","tender point","fatigue chronique","chronic fatigue","sleep","sommeil","douleurs multiples"},
        "fibromyalgie":                 {"muscle","musculaire","fibro","widespread pain","douleur diffuse","tender point","fatigue chronique","chronic fatigue","sleep","sommeil","douleurs multiples"},
        # Maladies psychiatriques — requièrent contexte psychologique explicite
        "depression":                   {"sad","tristesse","dépression","depressed","hopeless","désespoir","mood","humeur","suicide","anxiety","angoisse"},
        "anxiety disorder":             {"anxiety","angoisse","anxiété","panic","panique","worry","inquiétude","peur","fear","stress chronique"},
        "bipolar":                      {"bipolar","manic","manie","mood swing","humeur","psychose","psychosis","épisode","episode"},
        # Complications digestives — requièrent signes spécifiques de complication
        "barrett esophagus":            {"chronic","years","barrett","complication","endoscopy","biopsy","adenocarcinoma","long-standing","longstanding","dysplasia"},
        "esophageal cancer":            {"barrett","dysphagia","weight loss","chronic","bleeding","hematemesis","perte de poids"},
        "gastroparesis":                {"vomit","nausea after","delayed","fullness","diabet","post-surgery","post-op","bloating after eating","postprandial"},
        # Syndromes rares — requièrent terminologie spécifique
        "tracheobronchomalacia":        {"trachea","bronch","trachéo","collaps","stridor","strideur","tube","airway","voie aérienne"},
        "swyer-james syndrome":         {"xray","x-ray","radio","radiograph","lucency","hyperlucent","unilateral","lobe"},
        "parsonage turner syndrome":    {"shoulder","brachial","nerve","plexus","épaule","bras","arm pain sudden","after surgery","post-vaccine"},
        "short stature, hyperextensibility": {"growth","pediatric","genetic","chromosome","child","enfant","height","taille"},
        # Traumatismes — requièrent antécédent de choc/chute
        "concussion":           {"trauma","traumatism","hit","blow","fall","chute","coup","accident","head injury","blessure tête","collision","impact"},
        "traumatic brain injury":{"trauma","hit","blow","fall","chute","coup","accident","head injury","tbi","impact"},
        "subdural hematoma":    {"trauma","hit","blow","fall","chute","coup","accident","head injury","elderly","anticoagulant"},
        # Diverticulose/diverticulite — requiert signes spécifiques
        "diverticulosis and diverticulitis": {"diverticul","diverticulite","diverticulose","rectal bleed","blood stool","sang selles","colon left","left colon","colonoscopy","coloscopie","fever left","fièvre gauche"},
        "diverticulitis":                   {"diverticul","diverticulite","rectal bleed","blood stool","sang selles","fever","fièvre","rigidity","défense"},
        "diverticulosis":                   {"diverticul","diverticulose","colonoscopy","coloscopie","rectal bleed","blood stool","sang selles"},
        # Occlusion intestinale — requiert signes d'obstruction
        "intestinal obstruction":           {"obstruction","occlusion","bowel obstruction","blocked","no stool","pas de selles","cannot pass","absent bowel","distension","distended","vomit fecal","feculent","hernia","adherence","adhesion"},
        "small bowel obstruction":          {"obstruction","occlusion","blocked","no stool","cannot pass","absent bowel","distension","distended","vomit fecal","hernia","adhesion"},
        "large bowel obstruction":          {"obstruction","occlusion","blocked","no stool","cannot pass","absent bowel","distension","distended","vomit fecal","hernia","adhesion"},
        "bowel obstruction":                {"obstruction","occlusion","blocked","no stool","cannot pass","absent bowel","distension","distended","vomit fecal","hernia","adhesion"},
        # Insuffisance cardiaque — gonflement bilatéral chronique, pas un oedème aigu unilatéral
        # Un gonflement d'une cheville après une chute ≠ insuffisance cardiaque
        "heart failure":                    {"bilateral","both legs","both ankles","bilatéral","les deux","orthopnea","orthopnée","exertion","effort","essoufflement","dyspnea","dyspnée","chronic","weeks","months","mois","semaines","persistant","nuit","nocturn","paroxysmal","jugular","jugulaire","oedème","oedeme","jambes","jambe","legs","leg","palpitations","fatigue","gonflement"},
        "congestive heart failure":         {"bilateral","both legs","orthopnea","exertion","dyspnea","essoufflement","chronic","weeks","months","mois","semaines","jugular","oedème","oedeme","jambes"},
        "heart failure with reduced":       {"bilateral","both legs","orthopnea","exertion","chronic","weeks","months","oedème","jambes"},
        "heart failure with preserved":     {"bilateral","both legs","orthopnea","exertion","chronic","weeks","months","oedème","jambes"},
        # Myélome multiple — ne se présente pas avec un trauma aigu
        "multiple myeloma":                 {"bone pain","douleur osseuse","back pain","anemia","anémie","weakness","weight loss","perte de poids","myeloma","myélome","calcium","protein","protéine","fatigue chronique","chronic fatigue","plasma"},
        # Maladies osseuses rares — requièrent imagerie/chronique, pas un trauma aigu
        "kienbock's disease":               {"wrist","poignet","carpal","lunate","mri","irm","imaging","chronic","avascular","necrosis","osteonecrosis"},
        "kienbock disease":                 {"wrist","poignet","carpal","lunate","mri","irm","chronic","avascular","necrosis"},
        "avascular necrosis":               {"mri","irm","imaging","chronic","avascular","necrosis","osteonecrosis","hip","hanche","femoral"},
        "osteonecrosis":                    {"mri","irm","imaging","chronic","avascular","necrosis","steroid","corticoid","hip","hanche"},
    }

    combined_symptoms = (symptoms_en + " " + symptoms_fr).lower()

    # ── Filtre complications et symptomes ─────────────────
    diseases_only = []
    for d in diseases:
        dtype = d.get("type", "disease")
        name_lower = d.get("name_en", "").lower().strip()
        if dtype in ("complication", "symptom", "other"):
            logger.debug("Filtre '%s' (type=%s)", d.get("name_en", ""), dtype)
            continue
        if (name_lower in SYMPTOM_NAMES
                or any(name_lower.endswith(s) for s in GENERIC_SUFFIXES)
                or any(name_lower.startswith(p) for p in GENERIC_PREFIXES)):
            logger.debug("Filtre symptome-nom '%s'", d.get("name_en", ""))
            continue
        # Filtre contexte requis : exclure si aucun mot-clé déclencheur n'est présent
        required_ctx = CONTEXT_REQUIRED.get(name_lower)
        if required_ctx and not any(kw in combined_symptoms for kw in required_ctx):
            logger.debug("Filtre contexte-manquant '%s'", d.get("name_en", ""))
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

    # ── Déduplication — supprime quasi-doublons (même racine de nom) ──
    import re as _re

    # Synonymes médicaux canoniques (forme normalisée → clé unique)
    _CANONICAL = {
        "tooth decay":       "dental caries",
        "caries":            "dental caries",
        "tooth caries":      "dental caries",
        "dental decay":      "dental caries",
        "tooth abscess":     "dental abscess",
        "periapical abscess":"dental abscess",
        "tooth disorder":    "dental disorder",
        "dental disorder":   "dental disorder",
        "allergic rhinitis": "rhinitis",
        "hay fever":         "rhinitis",
        "hayfever":          "rhinitis",
        "viral rhinitis":    "rhinitis",
        "tonsillitis":       "pharyngitis",
        "strep throat":      "pharyngitis",
        "sore throat":       "pharyngitis",
        "urinary tract infection": "cystitis",
        "uti":               "cystitis",
        "bladder infection": "cystitis",
    }

    # Mots non-discriminants retirés avant comparaison
    _NOISE_PREFIXES = r"^(acute|chronic|viral|bacterial|primary|secondary|dental|tooth|oral|gum|pediatric|childhood|adult)\s+"
    _NOISE_SUFFIXES = r"\s+(disorder|disease|condition|syndrome|infection|injury|disorders|diseases|conditions|injuries|health|pain)s?$"
    _PLURAL_NORM    = [
        (r"ies$", "y"),          # caries → cary
        (r"(?<![cs])es$", "e"),  # abscesses → abscess (skip -ces, -ses)
        (r"(?<![aeious])s$", ""),# troubles → trouble (skip -ss, -us, -is)
    ]

    def _root(name: str) -> str:
        n = name.lower().strip()
        if n in _CANONICAL:
            return _CANONICAL[n]
        n = _re.sub(_NOISE_SUFFIXES, "", n)
        n = _re.sub(_NOISE_PREFIXES, "", n)
        if n in _CANONICAL:
            return _CANONICAL[n]
        for pat, repl in _PLURAL_NORM:
            n = _re.sub(pat, repl, n)
        return n.strip()

    def _is_dup(root_a: str, root_b: str) -> bool:
        if root_a == root_b:
            return True
        # Un root est contenu dans l'autre (ex: "cary" ⊆ "dental cary")
        words_a = set(root_a.split())
        words_b = set(root_b.split())
        if words_a and words_b:
            if words_a <= words_b or words_b <= words_a:
                return True
        return False

    seen_roots: list = []
    deduped = []
    for d in scored:
        root = _root(d.get("name_en", ""))
        if not any(_is_dup(root, r) for r in seen_roots):
            seen_roots.append(root)
            deduped.append(d)
        else:
            logger.debug("Dédoublonnage '%s' (racine '%s')", d.get("name_en", ""), root)
    scored = deduped

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

    # ── Correcteur d'urgence pour traumatismes musculo-squelettiques ──
    # ChromaDB stocke parfois "low" pour entorse/fracture ; on corrige en "modéré"
    _TRAUMA_MODERATE = {
        "sprain", "ankle sprain", "ligament sprain", "ligament injury",
        "fracture", "bone fracture", "stress fracture",
        "contusion", "bruise",
        "dislocation",
        "musculoskeletal injury", "musculoskeletal trauma",
        "strain", "strains", "sprains", "sprains and strains",
        "ankle injury", "wrist sprain", "knee sprain",
    }
    for d in scored:
        name_lower = d.get("name_en", "").lower().strip()
        current_urg = (d.get("urgency") or "").lower()
        if current_urg in ("low", "faible", "") and any(t in name_lower for t in _TRAUMA_MODERATE):
            d["urgency"] = "modéré"
            logger.debug("Urgence corrigée low→modéré pour '%s'", d.get("name_en", ""))

    return scored