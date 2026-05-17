import django, os, time
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.chat.services.chroma_service import search_diseases
from apps.chat.services.clinical_rules import apply_clinical_rules
from apps.chat.services.scoring import apply_smart_scoring
from apps.chat.services.medical_validator import validate_diseases
from apps.chat.services.rag_service import translate_symptoms

# ══════════════════════════════════════════════════════════════
# TESTS CHROMA UNIQUEMENT — pas de Gemini, pas de quota
# (symptômes, maladie_attendue, langue, urgence_attendue)
# ══════════════════════════════════════════════════════════════
TESTS = [
    # Urgences
    ("douleur poitrine irradiant bras gauche sueurs",   "heart attack",    "fr", "urgent"),
    ("chest pain radiating left arm jaw sweating",      "heart attack",    "en", "urgent"),
    ("ألم في الصدر وضيق في التنفس",                    "heart attack",    "ar", "urgent"),
    ("maux de tête sévères raideur nuque fièvre",       "meningitis",      "fr", "urgent"),
    ("severe headache stiff neck fever rash",           "meningitis",      "en", "urgent"),

    # Respiratoire
    ("fièvre 39 toux sèche fatigue courbatures",        "influenza",       "fr", "modéré"),
    ("fièvre toux perte odorat goût fatigue",            "covid",           "fr", "modéré"),
    ("toux chronique sueurs nocturnes perte de poids",  "tuberculosis",    "fr", "modéré"),
    ("chronic cough night sweats weight loss",          "tuberculosis",    "en", "modéré"),
    ("سعال مزمن وتعرق ليلي وفقدان وزن",               "tuberculosis",    "ar", "modéré"),

    # Digestif
    ("douleur abdominale droite nausée fièvre",         "appendicitis",    "fr", "urgent"),
    ("diarrhée vomissements crampes abdominales",       "gastroenteritis", "fr", "modéré"),
    ("brûlures estomac reflux douleur après repas",     "gastritis",       "fr", "modéré"),
    ("ألم في البطن وغثيان وحمى على اليمين",            "appendicitis",    "ar", "urgent"),

    # Neurologique
    ("migraine pulsatile nausée sensibilité lumière",   "migraine",        "fr", "modéré"),
    ("tremblement mains raideur musculaire lenteur",    "parkinson",       "fr", "modéré"),
    ("صداع شديد وتيبس الرقبة وحساسية للضوء",          "meningitis",      "ar", "urgent"),

    # Métabolique
    ("soif excessive urination fréquente vision floue", "diabetes",        "fr", "modéré"),
    ("excessive thirst frequent urination fatigue",     "diabetes",        "en", "modéré"),
    ("عطش شديد وكثرة التبول والتعب",                   "diabetes",        "ar", "modéré"),
]

URGENCY_SCORES = {"urgent": 3, "modéré": 2, "faible": 1}

def compute_real_urgency(symptoms: str, diseases: list) -> str:
    URGENCY_10 = [
        "douleur poitrine", "bras gauche", "infarctus", "raideur nuque",
        "chest pain", "left arm", "heart attack", "stiff neck", "meningitis",
        "ألم صدري", "ألم في الصدر", "تيبس الرقبة",
    ]
    if any(kw in symptoms.lower() for kw in URGENCY_10):
        return "urgent"
    if not diseases:
        return "modéré"
    counts = {"urgent": 0, "modéré": 0, "faible": 0}
    for d in diseases:
        u = d.get("urgency", "modéré").lower()
        if u in counts:
            counts[u] += 1
    ALWAYS_MODERATE = ["tuberculosis", "parkinson", "alzheimer", "diabetes", "migraine", "depression", "anxiety", "chronic"]
    top_name = diseases[0].get("name_en", "").lower() if diseases else ""
    if any(m in top_name for m in ALWAYS_MODERATE):
        return "modéré"
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

    diseases = search_diseases(symptoms, k=5, lang=lang, query_en=symptoms_en)

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
            "heart attack":    ["myocardial infarction", "heart attack", "infarction", "cardiac"],
            "meningitis":      ["meningitis", "meningococcal", "meningeal", "encephalitis"],
            "parkinson":       ["parkinson", "tremor", "parkinsonian", "cerebellar"],
            "gastritis":       ["gastritis", "gastroduodenal", "peptic ulcer", "heartburn", "barrett"],
            "tuberculosis":    ["tuberculosis", "tuberculosis (tb)", "tb"],
            "covid":           ["covid", "covid-19", "coronavirus", "sars"],
            "influenza":       ["influenza", "flu", "grippe"],
            "appendicitis":    ["appendicitis", "appendix", "pancreatitis", "diverticulitis"],
            "gastroenteritis": ["gastroenteritis", "viral gastroenteritis", "infectious gastroenteritis"],
            "diabetes":        ["diabetes", "diabetes type 2", "diabetes mellitus", "diabetes "],
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