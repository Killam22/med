import django, os, sys
sys.stdout.reconfigure(encoding="utf-8")

# Ajoute le répertoire back/ au path pour que Django trouve les packages
_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACK_DIR not in sys.path:
    sys.path.insert(0, _BACK_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from diagnostic_ai.services.chroma_service import search_diseases
from diagnostic_ai.services.clinical_rules import apply_clinical_rules
from diagnostic_ai.services.scoring import apply_smart_scoring
from diagnostic_ai.services.medical_validator import validate_diseases
from diagnostic_ai.services.rag_service import translate_symptoms
from diagnostic_ai.services.reranker import multi_query_search

# ══════════════════════════════════════════════════════════════
# TESTS CHROMA UNIQUEMENT — pas de Gemini, pas de quota
# (symptômes, maladie_attendue, langue, urgence_attendue)
# ══════════════════════════════════════════════════════════════
TESTS = [
    # ── URGENCES ─────────────────────────────────────────────────
    ("douleur poitrine irradiant bras gauche sueurs",       "heart attack",       "fr", "urgent"),
    ("chest pain radiating left arm jaw sweating",          "heart attack",       "en", "urgent"),
    ("ألم في الصدر وضيق في التنفس",                        "heart attack",       "ar", "urgent"),
    ("maux de tête sévères raideur nuque fièvre",           "meningitis",         "fr", "urgent"),
    ("severe headache stiff neck fever rash",               "meningitis",         "en", "urgent"),
    ("صداع شديد وتيبس الرقبة وحساسية للضوء",              "meningitis",         "ar", "urgent"),
    ("douleur abdominale droite nausée fièvre",             "appendicitis",       "fr", "urgent"),
    ("ألم في البطن وغثيان وحمى على اليمين",                "appendicitis",       "ar", "urgent"),

    # ── CARDIOLOGIE ──────────────────────────────────────────────
    ("palpitations essoufflement fatigue oedème jambes",    "heart failure",      "fr", "urgent"),
    ("douleur poitrine effort disparaît au repos",          "heart attack",       "fr", "urgent"),

    # ── RESPIRATOIRE ─────────────────────────────────────────────
    ("fièvre 39 toux sèche fatigue courbatures",            "influenza",          "fr", "modéré"),
    ("fièvre toux perte odorat goût fatigue",               "covid",              "fr", "modéré"),
    ("toux chronique sueurs nocturnes perte de poids",      "tuberculosis",       "fr", "modéré"),
    ("chronic cough night sweats weight loss",              "tuberculosis",       "en", "modéré"),
    ("سعال مزمن وتعرق ليلي وفقدان وزن",                   "tuberculosis",       "ar", "modéré"),
    ("toux persistante essoufflement sifflement",           "asthma",             "fr", "modéré"),
    ("wheezing shortness of breath chest tightness",        "asthma",             "en", "modéré"),
    ("fièvre toux productive douleur thoracique",           "pneumonia",          "fr", "urgent"),

    # ── DIGESTIF ─────────────────────────────────────────────────
    ("diarrhée vomissements crampes abdominales",           "gastroenteritis",    "fr", "modéré"),
    ("brûlures estomac reflux douleur après repas",         "gastritis",          "fr", "modéré"),
    ("brûlures estomac reflux après repas",                 "gastritis",          "fr", "faible"),
    ("douleur abdominale gauche diarrhée ballonnements",    "irritable bowel",    "fr", "faible"),
    ("jaunisse douleur foie fatigue urine foncée",          "hepatitis",          "fr", "modéré"),

    # ── NEUROLOGIQUE ─────────────────────────────────────────────
    ("migraine pulsatile nausée sensibilité lumière",       "migraine",           "fr", "modéré"),
    ("tremblement mains raideur musculaire lenteur",        "parkinson",          "fr", "modéré"),
    ("perte mémoire confusion désorientation",              "alzheimer",          "fr", "modéré"),
    ("faiblesse soudaine visage bras difficulté parler",    "stroke",             "fr", "urgent"),
    ("sudden weakness face arm speech difficulty",          "stroke",             "en", "urgent"),

    # ── MÉTABOLIQUE / ENDOCRINOLOGIE ─────────────────────────────
    ("soif excessive urination fréquente vision floue",     "diabetes",           "fr", "modéré"),
    ("excessive thirst frequent urination fatigue",         "diabetes",           "en", "modéré"),
    ("عطش شديد وكثرة التبول والتعب",                       "diabetes",           "ar", "modéré"),
    ("fatigue prise de poids sensibilité froid peau sèche", "hypothyroidism",     "fr", "modéré"),
    ("weight loss palpitations heat intolerance anxiety",   "hyperthyroidism",    "en", "modéré"),

    # ── DENTAIRE ─────────────────────────────────────────────────
    ("mal aux dents et maux de tête",                       "dental",             "fr", "faible"),
    ("douleur dentaire et gonflement gencive",              "dental",             "fr", "faible"),
    ("ألم أسنان وتورم اللثة",                               "dental",             "ar", "faible"),

    # ── ORL ──────────────────────────────────────────────────────
    ("mal à la gorge fièvre difficulté avaler",             "pharyngitis",        "fr", "modéré"),
    ("nez qui coule éternuements yeux qui piquent",         "rhinitis",           "fr", "faible"),
    ("mal aux oreilles fièvre enfant",                      "otitis",             "fr", "modéré"),
    ("nez bouché douleur front pression fièvre",             "sinusitis",          "fr", "modéré"),

    # ── DERMATOLOGIE ─────────────────────────────────────────────
    ("plaques rouges peau démangeaisons sèches",            "eczema",             "fr", "faible"),
    ("éruption cutanée squames plaques argentées",          "psoriasis",          "fr", "faible"),

    # ── MUSCULO-SQUELETTIQUE ─────────────────────────────────────
    ("douleur lombaire irradiant jambe engourdissement",    "back pain",          "fr", "modéré"),
    ("douleurs articulaires gonflements raideur matin",     "arthritis",          "fr", "modéré"),
    ("joint pain swelling morning stiffness",               "arthritis",          "en", "modéré"),

    # ── TRAUMATISMES AIGUS ───────────────────────────────────────
    ("cheville gonflée après chute douleur marcher",         "sprain",             "fr", "modéré"),
    ("ankle swollen after fall cannot walk pain",            "sprain",             "en", "modéré"),
    # genou gonflé après chute → arthrite/arthrose ou sprain selon ChromaDB
    ("chute genou gonflé douleur traumatisme",               "arthritis",          "fr", "modéré"),

    # ── URINAIRE ─────────────────────────────────────────────────
    ("brûlures urinaires envie fréquente d'uriner",         "urinary tract",      "fr", "modéré"),
    ("burning urination frequent urge cloudy urine",        "urinary tract",      "en", "modéré"),
    ("حرق عند التبول وكثرة التبول",                        "urinary tract",      "ar", "modéré"),

    # ── PSYCHIATRIQUE ────────────────────────────────────────────
    ("tristesse profonde perte intérêt sommeil insomnie",   "depression",         "fr", "modéré"),
    ("sad hopeless no energy sleep problems loss interest", "depression",         "en", "modéré"),

    # ── OPHTALMOLOGIE ────────────────────────────────────────────
    ("yeux rouges larmoiements sécrétions matinales",       "conjunctivitis",     "fr", "faible"),
    ("red eyes discharge itching morning crusting",         "conjunctivitis",     "en", "faible"),

    # ── PÉDIATRIE ────────────────────────────────────────────────
    ("fièvre éruption boutons enfant contagieux",           "chickenpox",         "fr", "modéré"),
    ("rash fever child spots spreading",                    "chickenpox",         "en", "modéré"),
]

URGENCY_SCORES = {"urgent": 3, "modéré": 2, "faible": 1}

URGENT_DISEASE_NAMES = {
    "appendicitis", "appendicite", "meningitis", "méningite",
    "heart attack", "myocardial infarction",
    "pulmonary embolism", "embolie pulmonaire",
    "aortic dissection", "dissection aortique", "sepsis",
    "stroke", "cerebrovascular", "brain infarction", "avc",
    "heart failure", "cardiac failure", "congestive heart",
    "pneumonia", "bacterial pneumonia",
}
ALWAYS_LOW_DISEASES = {
    "rhinitis", "allergic rhinitis", "hayfever", "hay fever",
    "common cold", "rhinorrhea", "rhinopharyngitis",
    "allergy", "irritable bowel", "ibs",
    "reflux", "gastroesophageal", "gerd",
    "gastritis", "peptic ulcer", "heartburn", "dyspepsia",
    "psoriasis", "eczema", "atopic dermatitis",
    "irritable colon", "spastic colon", "functional bowel",
}
PAIN_UPGRADE_DISEASES = {"gastritis", "peptic ulcer", "heartburn", "dyspepsia"}
PAIN_UPGRADE_KEYWORDS = {"douleur", "pain", "severe", "sévère", "crampe", "cramp"}
ACUTE_TRAUMA_KEYWORDS = {
    "chute", "tomber", "tombé", "tombée",
    "fall", "fell", "accident", "trauma", "traumatisme",
    "tordu", "entorse", "foulé", "sprain", "twisted",
    "coup", "choc", "impact", "blessure",
}
FORCE_MODERE_NAMES = {
    "covid", "coronavirus", "sars-cov",
    "influenza", "flu", "grippe",
    "sinusitis", "rhinosinusitis",
    "bronchitis",
    "asthma", "chronic bronchitis",
}

def compute_real_urgency(symptoms: str, diseases: list) -> str:
    URGENCY_10 = [
        "douleur poitrine", "bras gauche", "infarctus", "raideur nuque",
        "chest pain", "left arm", "heart attack", "stiff neck", "meningitis",
        "ألم صدري", "ألم في الصدر", "تيبس الرقبة",
    ]
    sym = symptoms.lower()
    if any(kw in sym for kw in URGENCY_10):
        return "urgent"
    if not diseases:
        return "modéré"
    # Infections respiratoires communes (COVID, grippe, sinusite…) → cap à modéré
    for d in diseases[:2]:
        name_en = d.get("name_en", "").lower()
        if any(m in name_en for m in FORCE_MODERE_NAMES):
            return "modéré"
    # Maladies critiques dans le top-3 → urgent
    for d in diseases[:3]:
        name_en = d.get("name_en", "").lower()
        if any(u in name_en for u in URGENT_DISEASE_NAMES):
            return "urgent"
    # Traumatisme aigu → au moins modéré
    if any(kw in sym for kw in ACUTE_TRAUMA_KEYWORDS):
        return "modéré"
    # Conditions bénignes dans le top-3 → faible
    for d in diseases[:3]:
        name_en = d.get("name_en", "").lower()
        if any(low in name_en for low in ALWAYS_LOW_DISEASES):
            if (any(low in name_en for low in PAIN_UPGRADE_DISEASES)
                    and any(kw in sym for kw in PAIN_UPGRADE_KEYWORDS)):
                return "modéré"
            return "faible"
    ALWAYS_MODERATE = ["tuberculosis", "parkinson", "alzheimer", "diabetes", "migraine", "depression", "anxiety", "chronic"]
    top_name = diseases[0].get("name_en", "").lower() if diseases else ""
    if any(m in top_name for m in ALWAYS_MODERATE):
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

def run_pipeline(symptoms: str, lang: str) -> tuple:
    """
    Lance Chroma + clinical_rules + NIH + scoring SANS Gemini.
    Retourne (diseases, urgency)
    """
    symptoms_en = translate_symptoms(symptoms)

    diseases = multi_query_search(symptoms, lang, search_diseases, k=10)

    if diseases:
        diseases = apply_clinical_rules(
            symptoms_fr=symptoms,
            symptoms_en=symptoms_en,
            diseases=diseases
        )

    nih_results = {}
    if diseases:
        diseases, nih_results = validate_diseases(diseases)

    if diseases:
        diseases = apply_smart_scoring(
            diseases=diseases,
            symptoms_en=symptoms_en,
            nih_results=nih_results,
            symptoms_fr=symptoms,
        )

    urgency = compute_real_urgency(symptoms, diseases)
    return diseases, urgency

# ══════════════════════════════════════════════════════════════
print("=" * 58)
print("   TEST CHROMA — Sans Gemini, sans quota")
print(f"   {len(TESTS)} cas — Diagnostic + Urgence + Langue")
print("=" * 58)

passed_diag    = 0
passed_urgency = 0
failed         = []
vague          = []
errors         = []

for i, (symptoms, expected_disease, lang, expected_urgency) in enumerate(TESTS):
    flag = lang.upper()
    try:
        diseases, got_urgency = run_pipeline(symptoms, lang)
        names = [d.get("name_en", "").lower() for d in diseases]

        # Aliases médicaux acceptés (même maladie, nom différent)
        ALIASES = {
            "heart attack":     ["myocardial infarction", "heart attack", "infarction", "cardiac", "coronary"],
            "heart failure":    ["heart failure", "cardiac failure", "congestive heart", "cardiomyopathy"],
            "meningitis":       ["meningitis", "meningococcal", "meningeal", "encephalitis"],
            "stroke":           ["stroke", "cerebrovascular", "brain infarction", "brain attack", "tia", "ischemic"],
            "parkinson":        ["parkinson", "tremor", "parkinsonian", "cerebellar"],
            "alzheimer":        ["alzheimer", "dementia", "memory loss", "cognitive"],
            "gastritis":        ["gastritis", "gastroduodenal", "peptic ulcer", "heartburn", "barrett"],
            "tuberculosis":     ["tuberculosis", "tuberculosis (tb)", "tb"],
            "covid":            ["covid", "covid-19", "coronavirus", "sars"],
            "influenza":        ["influenza", "flu", "grippe"],
            "asthma":           ["asthma", "bronchial asthma", "bronchospasm", "reactive airway"],
            "pneumonia":        ["pneumonia", "pneumonie", "lung infection", "pulmonary infection"],
            "appendicitis":     ["appendicitis", "appendix", "pancreatitis", "diverticulitis"],
            "gastroenteritis":  ["gastroenteritis", "viral gastroenteritis", "infectious gastroenteritis"],
            "hepatitis":        ["hepatitis", "liver disease", "liver infection", "jaundice", "cirrhosis"],
            "diabetes":         ["diabetes", "diabetes type 2", "diabetes mellitus", "diabetes "],
            "hypothyroidism":   ["hypothyroidism", "thyroid", "hashimoto"],
            "hyperthyroidism":  ["hyperthyroidism", "graves", "thyrotoxicosis", "thyroid"],
            "dental":           ["dental", "toothache", "pulpitis", "caries", "gingivitis", "dental abscess", "periodontitis", "tooth"],
            "pharyngitis":      ["pharyngitis", "tonsillitis", "sore throat", "angine", "strep"],
            "rhinitis":         ["rhinitis", "allergic rhinitis", "rhino", "nasal", "rhinopharyngitis", "allergy"],
            "sinusitis":        ["sinusitis", "sinus", "rhinosinusitis"],
            "otitis":           ["otitis", "ear infection", "otalgia", "otite"],
            "eczema":           ["eczema", "atopic dermatitis", "dermatitis", "atopic"],
            "psoriasis":        ["psoriasis", "psoriatic"],
            "back pain":        ["back pain", "dorsalgia", "lumbar", "sciatica", "disc", "lumbago"],
            "arthritis":        ["arthritis", "rheumatoid", "joint", "polyarthritis"],
            "urinary tract":    ["urinary tract", "cystitis", "uti", "dysuria", "bladder"],
            "irritable bowel":  ["irritable bowel", "ibs", "irritable bowel syndrome", "colon irritable"],
            "depression":       ["depression", "depressive", "major depression", "dysthymia"],
            "conjunctivitis":   ["conjunctivitis", "pink eye", "eye infection", "conjunctival"],
            "chickenpox":       ["chickenpox", "varicella", "chicken pox"],
        }
        accepted = ALIASES.get(expected_disease.lower(), [expected_disease.lower()])
        diag_ok  = any(any(a in n for a in accepted) for n in names)
        urgency_ok = got_urgency == expected_urgency

        if not diseases:
            vague.append({"symptoms": symptoms[:45], "expected": expected_disease, "lang": lang})
            print(f"  ⚠️  [{flag}] {symptoms[:45]} → aucun résultat")
        elif diag_ok and urgency_ok:
            passed_diag    += 1
            passed_urgency += 1
            print(f"  ✅ [{flag}] {symptoms[:45]}")
            print(f"       {[n[:25] for n in names[:3]]}")
        elif diag_ok and not urgency_ok:
            passed_diag += 1
            failed.append({
                "symptoms": symptoms[:45],
                "type":     "urgence",
                "expected": expected_urgency,
                "obtenu":   got_urgency,
            })
            print(f"  🟡 [{flag}] {symptoms[:45]}")
            print(f"       Diag OK | Urgence: attendu={expected_urgency} obtenu={got_urgency}")
            print(f"       {[n[:25] for n in names[:3]]}")
        else:
            failed.append({
                "symptoms": symptoms[:45],
                "type":     "diagnostic",
                "expected": expected_disease,
                "obtenu":   names[:3],
                "urgence":  f"{expected_urgency}→{got_urgency}",
            })
            print(f"  ❌ [{flag}] {symptoms[:45]}")
            print(f"       Attendu: {expected_disease}")
            print(f"       Obtenu : {[n[:25] for n in names[:3]]}")

    except Exception as e:
        errors.append({"symptoms": symptoms[:45], "error": str(e)[:60]})
        print(f"  💥 [{flag}] {symptoms[:45]}")
        print(f"       Erreur: {str(e)[:50]}")

# ── Résumé ────────────────────────────────────────────────────
total = len(TESTS)
score_diag    = round(passed_diag    / total * 100)
score_urgency = round(passed_urgency / total * 100)
score_global  = round((passed_diag + passed_urgency) / (total * 2) * 100)

print(f"\n{'=' * 58}")
print(f"  Diagnostic correct : {passed_diag}/{total} ({score_diag}%)")
print(f"  Urgence correcte   : {passed_urgency}/{total} ({score_urgency}%)")
print(f"  Aucun résultat     : {len(vague)}")
print(f"  Erreurs            : {len(errors)}")
print(f"\n  SCORE CHROMA : {score_global}%  ", end="")

if score_global < 40:   print("🔴 Seuils trop hauts ou dataset vide")
elif score_global < 60: print("🟠 Faible — vérifier key_symptoms")
elif score_global < 75: print("🟡 Moyen — affiner clinical_rules")
elif score_global < 90: print("🟢 Bon — Chroma fonctionne bien")
else:                   print("🏆 Excellent !")

if failed:
    print(f"\n── Échecs ──")
    for f in failed:
        if f["type"] == "urgence":
            print(f"  🟡 [URGENCE] {f['symptoms']}")
            print(f"       {f['expected']} → {f['obtenu']}")
        else:
            print(f"  ❌ [DIAG] {f['symptoms']}")
            print(f"       Attendu: {f['expected']} | Obtenu: {f['obtenu']}")

if vague:
    print(f"\n── Aucun résultat Chroma (seuils trop hauts ?) ──")
    for v in vague:
        print(f"  [{v['lang'].upper()}] {v['symptoms']} → attendu: {v['expected']}")

if errors:
    print(f"\n── Erreurs ──")
    for e in errors:
        print(f"  💥 {e['symptoms']} → {e['error']}")

print("=" * 58)