import django, os, sys
sys.stdout.reconfigure(encoding="utf-8")

_BACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACK_DIR not in sys.path:
    sys.path.insert(0, _BACK_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

import logging
logging.disable(logging.CRITICAL)

from diagnostic_ai.services.chroma_service import search_diseases
from diagnostic_ai.services.clinical_rules import apply_clinical_rules
from diagnostic_ai.services.scoring import apply_smart_scoring
from diagnostic_ai.services.medical_validator import validate_diseases
from diagnostic_ai.services.rag_service import translate_symptoms
from diagnostic_ai.services.reranker import multi_query_search
from training.test_reliability import compute_real_urgency

def run_pipeline(symptoms: str, lang: str) -> tuple:
    symptoms_en = translate_symptoms(symptoms)
    diseases = multi_query_search(symptoms, lang, search_diseases, k=10)
    if diseases:
        diseases = apply_clinical_rules(symptoms_fr=symptoms, symptoms_en=symptoms_en, diseases=diseases)
    nih_results = {}
    if diseases:
        diseases, nih_results = validate_diseases(diseases)
    if diseases:
        diseases = apply_smart_scoring(diseases=diseases, symptoms_en=symptoms_en,
                                       nih_results=nih_results, symptoms_fr=symptoms)
    urgency = compute_real_urgency(symptoms, diseases)
    return diseases, urgency

# ══════════════════════════════════════════════════════════════
# CAS LIMITES — symptômes vagues, rares, mixtes
# ══════════════════════════════════════════════════════════════
EDGE_CASES = [
    # Vagues / court
    ("je me sens mal",                           "fr", "vague"),
    ("fatigue",                                  "fr", "vague"),
    ("I feel sick",                              "en", "vague"),
    ("j'ai mal",                                 "fr", "vague"),

    # Maladies rares
    ("douleur osseuse nocturne amaigrissement",  "fr", "myélome/cancer os"),
    ("boules dans le cou ganglions fièvre",      "fr", "lymphome"),
    ("soif excessive urination excessive vision floue", "en", "diabète"),

    # Psychiatrie subtile
    ("je pense que les gens me suivent partout", "fr", "paranoïa"),
    ("tristesse + perte poids insomnies",        "fr", "dépression"),
    ("manque de sommeil irritabilité energie",   "fr", "dépression/anxiété"),

    # Combos inhabituels
    ("douleur dent paralysie visage gauche",     "fr", "Bell's palsy?"),
    ("vertiges debout rapidement",               "fr", "hypotension orthostatique"),
    ("crampes nocturnes jambes",                 "fr", "syndrome jambes sans repos"),

    # Arabe vague
    ("تعب عام وفقدان شهية",                    "ar", "fatigue/anorexie"),
    ("ألم في الرأس",                            "ar", "céphalée"),

    # Mixte symptômes communs
    ("fièvre + toux + essoufflement",            "fr", "pneumonie/grippe"),
    ("nausées matinales femme",                  "fr", "grossesse"),
    ("brûlures en urinant femme",               "fr", "cystite"),
]

print("=" * 65)
print("   TEST CAS LIMITES — Robustesse")
print(f"   {len(EDGE_CASES)} cas")
print("=" * 65)

ok = 0
no_result = 0
for symptoms, lang, expected_hint in EDGE_CASES:
    diseases, urgency = run_pipeline(symptoms, lang)
    names = [d.get("name_en", "")[:22] for d in diseases[:3]]
    if diseases:
        ok += 1
        flag = "✅"
    else:
        no_result += 1
        flag = "❌"
    print(f"{flag} [{lang.upper()}] {symptoms[:38]:<38}")
    print(f"       Attendu hint : {expected_hint}")
    print(f"       Résultats    : {names} | urgence={urgency}")

print()
print("=" * 65)
print(f"  Résultats trouvés : {ok}/{len(EDGE_CASES)}")
print(f"  Aucun résultat    : {no_result}/{len(EDGE_CASES)}")
print("=" * 65)
