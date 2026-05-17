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
    "fatigue": "fatigue", "épuisement": "exhaustion", "epuisement": "exhaustion",
    "nausée": "nausea", "nausee": "nausea", "nausées": "nausea",
    "vomissement": "vomiting", "vomissements": "vomiting",
    "diarrhée": "diarrhea", "diarrhee": "diarrhea",
    "maux de tete": "headache", "mal de tete": "headache",
    "maux de tête": "headache", "mal de tête": "headache",
    # ── Tête / front / sinus ──────────────────────────────
    "mal au niveau du front": "frontal headache sinus pain sinusitis frontal pressure",
    "mal au front": "frontal headache sinus pain sinusitis",
    "douleur au front": "frontal headache frontal sinus pain sinusitis",
    "douleur front": "frontal headache sinusitis sinus",
    "pression front": "frontal pressure sinusitis sinus headache",
    "front qui fait mal": "frontal headache sinusitis sinus pain",
    "tête qui tourne": "dizziness vertigo lightheadedness",
    # ── Vertiges / étourdissements ────────────────────────
    "étourdissement": "dizziness vertigo lightheadedness",
    "etourdissement": "dizziness vertigo lightheadedness",
    "étourdissements": "dizziness vertigo lightheadedness",
    "etourdissements": "dizziness vertigo lightheadedness",
    # ── Respiration ───────────────────────────────────────
    "difficultés à respirer": "difficulty breathing dyspnea breathlessness",
    "difficulte a respirer": "difficulty breathing dyspnea",
    "difficultés respiratoires": "respiratory difficulty dyspnea shortness of breath",
    "gêne respiratoire": "breathing difficulty respiratory distress",
    "gene respiratoire": "breathing difficulty dyspnea",
    "souffle court": "shortness of breath dyspnea",
    "manque de souffle": "shortness of breath dyspnea",
    "oppression thoracique": "chest tightness pressure cardiac angina asthma",
    "sensation d'etouffement": "choking sensation dyspnea",
    # ── Gorge / déglutition ───────────────────────────────
    "gorge seche": "dry throat pharyngitis",
    "gorge irritée": "sore throat irritated throat pharyngitis",
    "gorge irritee": "sore throat pharyngitis",
    "mal à avaler": "difficulty swallowing odynophagia sore throat pharyngitis tonsillitis",
    "mal a avaler": "difficulty swallowing odynophagia sore throat tonsillitis",
    "difficultés à avaler": "difficulty swallowing odynophagia sore throat tonsillitis pharyngitis",
    "difficultés a avaler": "difficulty swallowing odynophagia sore throat tonsillitis pharyngitis",
    "difficulte a avaler": "difficulty swallowing odynophagia tonsillitis",
    "douleur en avalant": "painful swallowing odynophagia sore throat tonsillitis",
    "gêne à avaler": "dysphagia swallowing difficulty sore throat",
    "gene a avaler": "dysphagia swallowing difficulty sore throat",
    # ── Nez / ORL ─────────────────────────────────────────
    "ecoulement nasal": "nasal discharge rhinorrhea",
    "écoulement nasal": "nasal discharge rhinorrhea",
    "nez qui saigne": "nosebleed epistaxis",
    "saignement de nez": "nosebleed epistaxis",
    "saignement nez": "nosebleed epistaxis",
    # ── Douleurs diffuses ─────────────────────────────────
    "mal partout": "body aches myalgia diffuse pain generalized pain",
    "douleur partout": "body aches myalgia diffuse pain",
    "douleurs partout": "body aches myalgia diffuse pain generalized",
    "courbatures": "body aches muscle pain myalgia",
    "crampes": "cramps muscle spasm",
    "crampe": "cramp muscle spasm",
    "spasmes": "muscle spasms cramps",
    # ── Gonflement / oedème ───────────────────────────────
    "gonflement": "swelling edema inflammation",
    "gonflements": "swelling edema",
    "oedeme": "edema swelling",
    "œdème": "edema swelling",
    "enflure": "swelling edema",
    # ── Digestif complémentaire ───────────────────────────
    "constipation": "constipation bowel difficulty hard stool",
    "sang dans les selles": "blood in stool melena rectal bleeding hematochezia",
    "selles noires": "black stool melena gastrointestinal bleeding",
    "selles sanglantes": "bloody stool rectal bleeding",
    "mal à l'estomac": "stomach pain gastric pain gastritis",
    "mal a l'estomac": "stomach pain gastric pain",
    "douleur épigastrique": "epigastric pain gastritis peptic ulcer",
    "douleur epigastrique": "epigastric pain gastritis peptic ulcer",
    "nausée après repas": "nausea after eating postprandial nausea gastroparesis",
    "nausee apres repas": "nausea after eating gastroparesis",
    "urine foncée": "dark urine jaundice hepatitis",
    "urine fonce": "dark urine hepatitis",
    "brûlures en urinant": "dysuria burning urination urinary tract infection",
    "brulures en urinant": "dysuria burning urination",
    "douleur à la miction": "dysuria urinary pain urinary tract infection",
    "urine trouble": "cloudy urine urinary tract infection",
    # ── Transpiration ─────────────────────────────────────
    "transpiration": "sweating diaphoresis perspiration",
    "sueurs": "sweating night sweats diaphoresis",
    # ── Peau complémentaire ───────────────────────────────
    "cloques": "blisters vesicles herpes varicella",
    "croutes": "crusts skin lesion impetigo",
    "aphtes": "mouth ulcers canker sores stomatitis",
    "grosseur": "lump mass nodule tumor",
    "masse": "mass lump tumor nodule",
    # ── ORL / audition ────────────────────────────────────
    "bourdonnement": "tinnitus ringing ears",
    "bourdonnements": "tinnitus ringing ears",
    "acouphène": "tinnitus ringing in ears",
    "acouphenes": "tinnitus ringing ears",
    "surdite": "hearing loss deafness",
    "surdité": "hearing loss deafness",
    "perte audition": "hearing loss",
    "yeux qui brulent": "burning eyes conjunctivitis",
    "yeux qui brûlent": "burning eyes conjunctivitis",
    "mauvaise haleine": "bad breath halitosis",
    "haleine": "bad breath halitosis",
    "saignement gencives": "bleeding gums gingivitis",
    "saignement des gencives": "bleeding gums gingivitis periodontitis",
    # ── Gynécologique ─────────────────────────────────────
    "regles douloureuses": "dysmenorrhea painful periods menstrual cramps",
    "règles douloureuses": "dysmenorrhea painful periods menstrual cramps",
    "pertes blanches": "white vaginal discharge",
    "pertes": "discharge vaginal discharge",
    "douleur pelvienne": "pelvic pain gynecological",
    "douleurs pelviennes": "pelvic pain dysmenorrhea",
    "menopause": "menopause hot flashes",
    "ménopause": "menopause hot flashes hot flush",
    "mal aux dents": "toothache dental pain", "mal aux dent": "toothache dental pain",
    "douleur dentaire": "dental pain toothache", "douleur dent": "tooth pain",
    "dent qui fait mal": "toothache dental pain", "dents qui font mal": "toothache",
    "abcès dentaire": "dental abscess", "abces dentaire": "dental abscess",
    "carie": "dental caries cavity tooth decay", "caries": "dental caries cavity",
    "gencive": "gum gingivitis", "gencives": "gum disease gingivitis",
    "sensibilité dentaire": "dental sensitivity", "mâchoire": "jaw pain",
    "machoire": "jaw pain", "douleur mâchoire": "jaw pain mandible",
    "courbatures": "body aches muscle pain myalgia",
    "frissons": "chills shivering",
    "essoufflement": "shortness of breath dyspnea",
    # ── Traumatismes / Musculo-squelettique ───────────────────
    "entorse": "ankle sprain sprain ligament injury twisted",
    "entorse cheville": "ankle sprain twisted ankle ligament injury",
    "foulure": "sprain ankle sprain ligament strain",
    "cheville tordue": "twisted ankle ankle sprain",
    "cheville": "ankle",
    "traumatisme": "trauma injury traumatism",
    "traumatisme crânien": "traumatic brain injury head injury concussion",
    "commotion cérébrale": "concussion traumatic brain injury",
    "commotion cerebrale": "concussion traumatic brain injury",
    "commotion": "concussion head injury",
    "contusion": "contusion bruise injury",
    "fracture": "fracture bone break",
    "fracture cheville": "ankle fracture bone fracture",
    "luxation": "dislocation joint injury",
    "hématome": "hematoma bruise contusion",
    "hematome": "hematoma bruise contusion",
    "chute": "fall trauma injury",
    "je suis tombé": "fall trauma injury fell",
    "je suis tombée": "fall trauma injury fell",
    "je me suis tordu": "twisted sprain ligament injury",
    "tordu la cheville": "twisted ankle ankle sprain",
    "foulé": "sprained sprain ankle sprain",
    "foule": "sprained sprain ankle sprain",
    "genou gonflé": "knee swelling knee injury knee sprain",
    "poignet gonflé": "wrist swelling wrist injury sprain",
    "douleur cheville": "ankle pain ankle sprain ankle injury",
    "gonflement cheville": "ankle swelling ankle sprain injury",
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
    # ORL
    "mal à la gorge": "sore throat pharyngitis", "mal a la gorge": "sore throat pharyngitis",
    "gorge qui gratte": "sore throat", "gorge qui fait mal": "sore throat pharyngitis",
    "nez qui coule": "runny nose rhinorrhea", "nez bouche": "nasal congestion",
    "nez bouché": "nasal congestion stuffy nose",
    "éternuements": "sneezing rhinitis", "eternuements": "sneezing rhinitis",
    "mal aux oreilles": "earache otalgia otitis", "douleur oreille": "ear pain otitis",
    "maux d'oreilles": "earache otalgia", "oreille": "ear",
    "yeux rouges": "red eyes conjunctivitis", "yeux qui piquent": "itchy eyes conjunctivitis",
    "douleur oculaire": "eye pain",
    # Digestif
    "mal au ventre": "abdominal pain stomach ache", "douleur au ventre": "abdominal pain",
    "brûlures estomac": "heartburn acid reflux gastric burn",
    "brulures estomac": "heartburn acid reflux",
    "reflux": "acid reflux gastroesophageal reflux",
    "ballonnements": "bloating flatulence abdominal distension irritable bowel",
    "gonflement ventre": "abdominal bloating",
    "douleur abdominale gauche": "left abdominal pain irritable bowel syndrome colon spasm",
    "abdominale gauche": "left abdominal pain irritable bowel colon",
    # Musculo-squelettique
    "mal au dos": "back pain lumbar pain", "douleur dos": "back pain dorsalgia",
    "douleur lombaire": "lumbar pain back pain",
    "mal au genou": "knee pain", "mal aux jambes": "leg pain",
    # Urinaire
    "brûlures urinaires": "dysuria burning urination",
    "brulures urinaires": "dysuria burning urination",
    "envie d'uriner": "urinary urgency frequency polyuria",
    # Peau
    "peau qui gratte": "skin itching pruritus dermatitis",
    "taches sur la peau": "skin spots rash lesion",
    "boutons": "pimples acne rash skin lesion",
    "plaques rouges": "red plaques skin rash eczema dermatitis psoriasis",
    "plaques argentées": "silver plaques psoriasis scaly skin",
    "squames": "scales squamous psoriasis dandruff",
    "eruption cutanee": "skin rash eruption dermatitis",
    "éruption cutanée": "skin rash eruption dermatitis psoriasis",
    "psoriasis": "psoriasis scaly skin plaques",
    "eczema": "eczema atopic dermatitis itching skin",
    "eczéma": "eczema atopic dermatitis itching skin",
    # Yeux
    "yeux rouges": "red eyes conjunctivitis eye redness",
    "larmoiements": "tearing watery eyes conjunctivitis",
    "sécrétions yeux": "eye discharge conjunctivitis",
    "yeux qui coulent": "watery eyes conjunctivitis discharge",
    # Neuro
    "vertiges": "dizziness vertigo lightheadedness",
    "vertige": "dizziness vertigo",
    "mal à la tête": "headache cephalalgia",
    "paralysie visage": "facial paralysis bell palsy cranial nerve seventh",
    "paralysie faciale": "facial paralysis bell's palsy facial nerve",
    "paralysie côté visage": "bell palsy facial nerve palsy",
    "paralysie":   "paralysis palsy neurological weakness",
    "chute paupière": "ptosis eyelid droop bell palsy",
    # Oncologie / Os
    "douleur osseuse": "bone pain osteolysis myeloma bone cancer skeletal",
    "douleur os":      "bone pain skeletal osteosarcoma",
    "myélome":         "multiple myeloma plasma cell bone marrow",
    "myelome":         "multiple myeloma plasma cell bone marrow",
    "cancer os":       "bone cancer osteosarcoma myeloma",
    "amaigrissement":  "weight loss cachexia anorexia cancer",
    # Lymphome
    "ganglions gonflés": "swollen lymph nodes lymphadenopathy cervical adenopathy",
    "ganglions gonfles": "swollen lymph nodes lymphadenopathy cervical adenopathy",
    "ganglions":         "lymph nodes lymphadenopathy cervical",
    "boules cou":        "neck mass lymph nodes lymphadenopathy",
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
    "toothache":           ["toothache", "dental pain", "tooth pain", "odontalgia", "pulpitis", "dental abscess", "dental caries"],
    "sore throat":         ["sore throat", "pharyngitis", "tonsillitis", "throat pain", "odynophagia", "strep"],
    "runny nose":          ["runny nose", "rhinorrhea", "nasal discharge", "nasal congestion", "rhinitis"],
    "ear pain":            ["ear pain", "earache", "otalgia", "otitis", "tympanitis"],
    "abdominal pain":      ["abdominal pain", "stomach pain", "belly pain", "gastric pain", "cramping"],
    "heartburn":           ["heartburn", "acid reflux", "gastroesophageal reflux", "GERD", "pyrosis"],
    "back pain":           ["back pain", "lumbar pain", "dorsalgia", "spine pain", "lumbago"],
    "red eyes":            ["red eyes", "conjunctivitis", "eye redness", "ocular inflammation"],
    "itching":             ["itching", "pruritus", "skin itch", "dermatitis"],
    "bloating":            ["bloating", "flatulence", "abdominal distension", "meteorism", "irritable bowel syndrome", "IBS"],
    "ankle":               ["ankle sprain", "ankle fracture", "twisted ankle", "ligament injury", "ankle injury"],
    "sprain":              ["sprain", "ankle sprain", "ligament tear", "ligament injury", "musculoskeletal injury"],
    "fall":                ["fall injury", "trauma", "ankle sprain", "musculoskeletal trauma", "fracture"],
    "trauma":              ["trauma", "injury", "sprain", "fracture", "contusion", "musculoskeletal injury"],
    "fracture":            ["fracture", "bone fracture", "bone break", "bone injury"],
    "dizziness":           ["dizziness", "vertigo", "lightheadedness", "vestibular", "balance disorder"],
    "frontal headache":    ["frontal headache", "sinusitis", "sinus pain", "rhinosinusitis", "frontal sinus"],
    "frontal pain":        ["frontal pain", "sinusitis", "sinus pressure", "rhinosinusitis"],
    "sinus":               ["sinusitis", "rhinosinusitis", "sinus infection", "sinus pressure", "frontal sinusitis"],
    "sinusitis":           ["sinusitis", "rhinosinusitis", "sinus infection", "sinus inflammation", "paranasal sinus"],
    "nasal congestion":    ["nasal congestion", "sinusitis", "rhinitis", "rhinopharyngitis", "common cold", "nasal blockage"],
    "numbness":            ["numbness", "paresthesia", "tingling", "hypoesthesia"],
    "vision loss":         ["vision loss", "visual impairment", "blindness"],
    "seizure":             ["seizure", "convulsion", "epileptic attack"],
    "psoriasis":           ["psoriasis", "psoriasis vulgaris", "plaque psoriasis", "scaly skin plaques"],
    "scaly skin":          ["scaly skin", "psoriasis", "ichthyosis", "seborrhea"],
    "silver plaques":      ["psoriasis", "plaque psoriasis", "psoriasis vulgaris"],
    "scales":              ["psoriasis", "ichthyosis", "seborrheic dermatitis"],
    "bone pain":           ["bone pain", "multiple myeloma", "osteosarcoma", "bone cancer", "osteolysis"],
    "facial paralysis":    ["bell palsy", "facial nerve palsy", "facial weakness", "seventh nerve"],
    "bell palsy":          ["bell palsy", "facial paralysis", "seventh cranial nerve", "facial nerve"],
    "lymph nodes":         ["lymphadenopathy", "lymphoma", "lymph nodes swelling", "adenopathy"],
    "weight loss":         ["weight loss", "cachexia", "wasting", "cancer", "myeloma", "lymphoma"],
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
    en_version = symptoms
    if lang in ("fr", "ar"):
        en_version = translate_fr_to_en(symptoms)
        if en_version != symptoms.lower():
            queries.append(en_version)

    # Expansion des termes medicaux — cherche dans original ET traduit
    symptoms_lower = symptoms.lower()
    en_lower = en_version.lower()
    expanded_terms = []
    for term, expansions in SYMPTOM_EXPANSIONS.items():
        if term in symptoms_lower or term in en_lower:
            expanded_terms.extend(expansions[1:])  # saute le premier (deja present)

    if expanded_terms:
        expanded_query = symptoms + " " + " ".join(expanded_terms[:5])
        queries.append(expanded_query)

    # Requête séparée si symptômes multi-domaines conflictuels
    # Ex: douleur dentaire + paralysie visage → Bell's palsy noyé par dentaire
    _DENTAL_TERMS = ("dental", "tooth", "toothache", "gum", "caries", "abscess of tooth")
    _NEURO_FACIAL  = ("facial paralysis", "bell palsy", "facial nerve", "seventh nerve")
    _BONE_CANCER   = ("bone pain", "osteolysis", "myeloma", "bone cancer")
    _LYMPH_CANCER  = ("lymph nodes", "lymphadenopathy", "lymphoma")

    if any(t in en_lower for t in _DENTAL_TERMS) and any(t in en_lower for t in _NEURO_FACIAL):
        queries.append("bell palsy facial nerve paralysis facial weakness seventh cranial nerve")

    if any(t in en_lower for t in _BONE_CANCER):
        queries.append("multiple myeloma bone pain back pain plasma cell anemia weight loss")

    if any(t in en_lower for t in _LYMPH_CANCER) and ("fever" in en_lower or "fièvre" in symptoms_lower):
        queries.append("lymphoma hodgkin night sweats fever weight loss swollen lymph nodes")

    # ── Traumatisme musculo-squelettique aigu ─────────────────────────────────
    # Chute/coup + gonflement/douleur + membre → entorse/fracture EN PREMIER
    _TRAUMA_ACUTE = ("fall", "chute", "trauma", "trauma", "hit", "blow", "fell", "tombé",
                     "tomber", "accident", "twisted", "tordu", "entorse", "sprain", "foulé")
    _BODY_PART    = ("ankle", "cheville", "wrist", "poignet", "knee", "genou",
                     "shoulder", "épaule", "epaule", "foot", "pied", "hand", "main",
                     "arm", "bras", "leg", "jambe", "finger", "doigt", "toe")
    _SWELLING_PAIN = ("swelling", "gonflement", "gonflé", "swollen", "pain", "douleur",
                      "mal", "hurts", "ache")

    has_trauma = any(t in en_lower or t in symptoms_lower for t in _TRAUMA_ACUTE)
    has_part   = any(t in en_lower or t in symptoms_lower for t in _BODY_PART)
    has_swpain = any(t in en_lower or t in symptoms_lower for t in _SWELLING_PAIN)

    if has_trauma and (has_part or has_swpain):
        # Insérer en 2e position pour que ce soit la requête prioritaire après l'originale
        trauma_query = "ankle sprain fracture musculoskeletal trauma ligament injury sprained ankle twisted"
        if has_part:
            trauma_query += " " + " ".join(p for p in _BODY_PART if p in en_lower or p in symptoms_lower)
        queries.insert(1, trauma_query)

    # ── Combinaisons grippe / sinusite / rhinopharyngite ──────────────────────
    _NASAL   = ("nasal congestion", "stuffy nose", "runny nose", "rhinorrhea", "congestion nasale")
    _THROAT  = ("sore throat", "pharyngitis", "throat pain", "gorge")
    _FRONTAL = ("frontal", "sinus", "front qui", "niveau du front", "front headache")
    _FEVER   = ("fever", "fièvre", "fievre", "temperature")
    _DIZZY   = ("dizziness", "vertigo", "lightheadedness", "étourdissement", "etourdissement", "vertiges")
    _VOMIT   = ("vomiting", "nausea", "vomissement", "nausée", "nausee")
    _COUGH   = ("cough", "toux")

    # Sinusite : nez bouché + douleur frontale
    if any(t in en_lower or t in symptoms_lower for t in _NASAL) and \
       any(t in en_lower or t in symptoms_lower for t in _FRONTAL):
        queries.append("sinusitis sinus infection frontal headache nasal congestion rhinosinusitis facial pain")

    # Amygdalite / pharyngite : gorge + fièvre + ganglions gonfles
    # → les ganglions sont réactifs à l'infection ORL, pas primaires (lymphome)
    _LYMPH_NECK = ("lymph nodes", "lymphadenopathy", "lymphadenitis", "ganglions", "adenopathy", "sialoadenitis")
    if any(t in en_lower or t in symptoms_lower for t in _THROAT) and \
       any(t in en_lower or t in symptoms_lower for t in _FEVER) and \
       any(t in en_lower or t in symptoms_lower for t in _LYMPH_NECK):
        queries.append("tonsillitis pharyngitis sore throat fever swollen neck lymph nodes strep throat")

    # Dermatite / eczéma : boutons rouges démangeaisons généralisés
    _RASH_ITCH = ("rash", "itching", "pruritus", "demangeaisons", "démangeaisons", "pimples", "boutons")
    _GENERALIZED = ("whole body", "all over", "tout le corps", "partout", "generalized")
    if any(t in en_lower or t in symptoms_lower for t in _RASH_ITCH) and \
       any(t in en_lower or t in symptoms_lower for t in _GENERALIZED):
        queries.append("eczema atopic dermatitis urticaria hives generalized itching skin rash")

    # Grippe : fièvre/vomissement/étourdissement + gorge/nez
    flu_signals = sum([
        any(t in en_lower or t in symptoms_lower for t in _FEVER),
        any(t in en_lower or t in symptoms_lower for t in _VOMIT),
        any(t in en_lower or t in symptoms_lower for t in _DIZZY),
        any(t in en_lower or t in symptoms_lower for t in _COUGH),
    ])
    has_ent = any(t in en_lower or t in symptoms_lower for t in _NASAL) or \
              any(t in en_lower or t in symptoms_lower for t in _THROAT)
    if flu_signals >= 2 and has_ent:
        queries.append("influenza flu fever sore throat nasal congestion body aches dizziness vomiting")

    # Rhinopharyngite : gorge + nez + pas de frontal
    if has_ent and any(t in en_lower or t in symptoms_lower for t in _NASAL) and \
       any(t in en_lower or t in symptoms_lower for t in _THROAT) and flu_signals < 2:
        queries.append("rhinopharyngitis common cold nasopharyngitis sore throat nasal congestion")

    # ── Labyrintite / vertige isolé ───────────────────────────────────────────
    _BALANCE = ("dizziness", "vertigo", "lightheadedness")
    if any(t in en_lower for t in _BALANCE) and not any(t in en_lower for t in _FEVER):
        queries.append("labyrinthitis vertigo dizziness vestibular disorder inner ear")

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
    "psoriasis":           ["plaques", "scaly", "silver plaques", "scales", "itching skin", "psoriasis vulgaris"],
    "eczema":              ["itching", "atopic", "dry skin", "rash", "dermatitis"],
    "conjunctivitis":      ["red eyes", "eye redness", "discharge", "tearing", "crusting"],
    "bell palsy":          ["facial paralysis", "facial drooping", "eye closure", "mouth drooping", "weakness face"],
    "myeloma":             ["bone pain", "back pain", "weakness", "anemia", "weight loss", "elevated protein"],
    "lymphoma":            ["swollen lymph nodes", "night sweats", "weight loss", "fatigue", "fever"],
    "bell's palsy":        ["facial paralysis", "facial drooping", "seventh nerve", "facial weakness"],
    "dental":              ["toothache", "dental pain", "tooth pain", "jaw", "cavity"],
    "pulpitis":            ["toothache", "tooth pain", "sensitivity", "hot cold"],
    "dental abscess":      ["toothache", "swelling", "fever", "jaw", "pain"],
    "periodontitis":       ["gum", "gum pain", "bleeding gums", "loose teeth"],
    "gingivitis":          ["gum", "bleeding gums", "gum inflammation", "soreness"],
    "temporomandibular":   ["jaw", "jaw pain", "clicking jaw", "headache", "ear pain"],
    "trigeminal neuralgia":["facial pain", "jaw", "tooth pain", "shooting pain"],
    "sinusitis":           ["sinus pressure", "facial pain", "nasal congestion", "headache", "runny nose"],
    "otitis":              ["ear pain", "earache", "hearing loss", "fluid ear", "fever"],
    "pharyngitis":         ["sore throat", "throat pain", "swallowing pain", "fever"],
    "tonsillitis":         ["sore throat", "tonsils", "fever", "throat pain", "swallowing", "odynophagia", "strep", "cervical lymph", "swollen neck"],
    "rhinitis":            ["runny nose", "sneezing", "nasal congestion", "itchy nose"],
    "conjunctivitis":      ["red eyes", "eye discharge", "itchy eyes", "burning eyes"],
    "urinary tract":       ["burning urination", "frequency", "urgency", "dysuria", "cloudy urine"],
    "cystitis":            ["burning urination", "urgency", "frequency", "pelvic pain"],
    "gastroesophageal":    ["heartburn", "acid reflux", "chest burning", "regurgitation"],
    "irritable bowel":     ["abdominal pain", "bloating", "diarrhea", "constipation"],
    "hypothyroidism":      ["fatigue", "cold intolerance", "weight gain", "dry skin"],
    "hyperthyroidism":     ["weight loss", "palpitations", "heat intolerance", "anxiety"],
    "allergic rhinitis":   ["sneezing", "runny nose", "itchy eyes", "nasal congestion"],
    "eczema":              ["itching", "skin rash", "dry skin", "inflammation"],
    "anemia":              ["fatigue", "weakness", "pallor", "dizziness", "shortness of breath"],
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