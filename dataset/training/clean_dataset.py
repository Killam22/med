# dataset/training/clean_dataset.py
# Nettoie diseases.json et supprime les maladies mal indexées
# Lance : python clean_dataset.py

import json
import re
import os

INPUT_PATH  = r"C:\Users\HP\Desktop\ai_bot\dataset\processed\diseases.json"
OUTPUT_PATH = r"C:\Users\HP\Desktop\ai_bot\dataset\processed\diseases.json"
BACKUP_PATH = r"C:\Users\HP\Desktop\ai_bot\dataset\processed\diseases_backup.json"

print("=" * 65)
print("   DATA CLEANING — Medical Smart App")
print("=" * 65)

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    diseases = json.load(f)

# Backup
with open(BACKUP_PATH, "w", encoding="utf-8") as f:
    json.dump(diseases, f, ensure_ascii=False, indent=2)
print(f"\n💾 Backup sauvegardé : diseases_backup.json")
print(f"📦 {len(diseases)} maladies au départ\n")

# ══════════════════════════════════════════════════════════
# RÈGLES DE NETTOYAGE
# ══════════════════════════════════════════════════════════

# Mots qui indiquent un titre d'article NIH (pas une maladie)
ARTICLE_PATTERNS = [
    r"^am i at risk",
    r"^taking steps",
    r"^what is ",
    r"^how to ",
    r"^living with",
    r"^questions and",
    r"^fact sheet",
    r"^overview of",
    r"^understanding ",
    r"^managing ",
    r"^coping with",
    r"^prevention of",
    r"^treatment of",
    r"^caring for",
    r"\?$",                    # finit par ?
    r"^x.?ray",
    r"^mri$",
    r"^ct scan",
    r"^blood test",
    r"^laboratory",
    r"^screening",
    r"^diagnosis of",
    r"^causes of",
    r"^symptoms of",
    r"^types of",
]

# Maladies rares à garder même sans beaucoup de symptômes
RARE_WHITELIST = {
    "lupus", "scleroderma", "sclerodermie", "multiple sclerosis",
    "sclerose", "amyotrophic lateral sclerosis", "huntington",
    "cystic fibrosis", "mucoviscidose", "sickle cell", "thalassemia",
    "hemophilia", "wilson disease", "marfan", "ehlers-danlos",
    "celiac disease", "crohn", "ulcerative colitis",
    "myasthenia gravis", "guillain-barre", "tourette",
    "phenylketonuria", "gaucher", "fabry", "pompe",
}

# Symptômes trop génériques (si une maladie n'a QUE ces symptômes → supprimer)
GENERIC_SYMPTOMS = {
    "fatigue", "pain", "weakness", "fever", "nausea", "vomiting",
    "headache", "dizziness", "loss of appetite", "weight loss",
    "shortness of breath", "cough", "sweating", "chills",
}


def is_article_title(name: str) -> bool:
    """Retourne True si le nom ressemble à un titre d'article."""
    name_lower = name.lower().strip()
    for pattern in ARTICLE_PATTERNS:
        if re.search(pattern, name_lower):
            return True
    if len(name) > 80:
        return True
    return False


def has_specific_symptoms(disease: dict) -> bool:
    """
    Retourne True si la maladie a des symptômes spécifiques.
    Une maladie avec seulement des symptômes génériques est suspecte.
    """
    syms = set(s.lower().strip() for s in disease.get("symptoms_en", []))

    if len(syms) < 3:
        return False

    # Compter les symptômes NON génériques
    specific = syms - GENERIC_SYMPTOMS
    if len(specific) >= 2:
        return True

    # A une description médicale
    if disease.get("description_en") and len(disease["description_en"]) > 50:
        return True

    # A des symptômes clés définis
    if disease.get("key_symptoms") and len(disease["key_symptoms"]) > 20:
        return True

    return False


def is_rare_with_generic_symptoms(disease: dict) -> bool:
    """
    Retourne True si c'est une maladie rare avec des symptômes trop génériques
    → à supprimer car elle va créer des faux positifs.
    """
    name   = disease.get("name_en", "").lower()
    source = disease.get("source", "")

    # Toujours garder le dataset manuel
    if source == "manual":
        return False

    # Garder les maladies rares importantes
    for w in RARE_WHITELIST:
        if w in name:
            return False

    # Garder si a des symptômes spécifiques
    if has_specific_symptoms(disease):
        return False

    # Vérifier si c'est une maladie rare (nom complexe)
    rare_indicators = [
        "syndrome", "dysplasia", "dystrophy", "type 1", "type 2",
        "autosomal", "hereditary", "congenital", "x-linked",
        "deficiency", "ataxia", "palsy", "sclerosis", "myopathy",
        "neuropathy", "encephalopathy", "lipofuscinosis",
    ]
    rare_count = sum(1 for kw in rare_indicators if kw in name)

    if rare_count >= 2 and not has_specific_symptoms(disease):
        return True

    return False


# ══════════════════════════════════════════════════════════
# PIPELINE DE NETTOYAGE
# ══════════════════════════════════════════════════════════

stats = {
    "removed_article_title":    0,
    "removed_no_symptoms":      0,
    "removed_rare_generic":     0,
    "removed_duplicate":        0,
    "kept":                     0,
}

clean    = []
seen_names = set()

for d in diseases:
    name   = d.get("name_en", "").strip()
    source = d.get("source", "")

    # ── 1. Toujours garder le dataset manuel ───────────────
    if source == "manual":
        clean.append(d)
        seen_names.add(name.lower())
        stats["kept"] += 1
        continue

    # ── 2. Supprimer les titres d'articles NIH ─────────────
    if is_article_title(name):
        stats["removed_article_title"] += 1
        continue

    # ── 3. Supprimer si nom vide ou trop court ─────────────
    if not name or len(name) < 3:
        stats["removed_no_symptoms"] += 1
        continue

    # ── 4. Supprimer les doublons ──────────────────────────
    if name.lower() in seen_names:
        stats["removed_duplicate"] += 1
        continue

    # ── 5. Supprimer maladies rares sans symptômes précis ──
    if is_rare_with_generic_symptoms(d):
        stats["removed_rare_generic"] += 1
        continue

    # ── 6. Supprimer si moins de 3 symptômes ──────────────
    if len(d.get("symptoms_en", [])) < 3:
        stats["removed_no_symptoms"] += 1
        continue

    clean.append(d)
    seen_names.add(name.lower())
    stats["kept"] += 1

# ── Réassigner les IDs ─────────────────────────────────────
for i, d in enumerate(clean):
    d["id"] = f"D{i+1:04d}"

# ══════════════════════════════════════════════════════════
# RÉSULTATS
# ══════════════════════════════════════════════════════════

print("📊 Résultats du nettoyage :")
print(f"  Titres d'articles NIH supprimés : {stats['removed_article_title']}")
print(f"  Sans symptômes supprimées       : {stats['removed_no_symptoms']}")
print(f"  Maladies rares génériques       : {stats['removed_rare_generic']}")
print(f"  Doublons supprimés              : {stats['removed_duplicate']}")
print(f"  ─────────────────────────────────")
print(f"  Total supprimé  : {len(diseases) - len(clean)}")
print(f"  Total conservé  : {len(clean)}")

# Vérifier que les maladies importantes sont présentes
important = [
    "Influenza", "COVID-19", "Pneumonia", "Asthma", "Heart Attack",
    "Migraine", "Diabetes Type 2", "Depression", "Malaria", "Tuberculosis",
    "Appendicitis", "Hepatitis B", "Psoriasis", "Urinary Tract Infection",
]

print(f"\n✅ Vérification maladies importantes :")
clean_names = {d["name_en"].lower() for d in clean}
for name in important:
    found = any(name.lower() in n for n in clean_names)
    status = "✅" if found else "❌ MANQUANT"
    print(f"  {status} {name}")

# Sauvegarder
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(clean, f, ensure_ascii=False, indent=2)

print(f"\n✅ diseases.json mis à jour : {len(clean)} maladies")
print(f"💾 Backup disponible : diseases_backup.json")
print("\n" + "=" * 65)
print("✅ NETTOYAGE TERMINÉ")
print("   Prochaine étape : python ingest_to_chroma.py")
print("=" * 65)