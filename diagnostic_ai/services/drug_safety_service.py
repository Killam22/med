"""
Service de sécurité médicamenteuse.
Vérifie les interactions médicament-médicament et médicament-allergie
à partir du profil patient avant de générer la réponse Gemini.
"""
import logging
logger = logging.getLogger(__name__)

# ── Réactions croisées allergie → classe médicamenteuse ────────────────────────
# Si le patient est allergique à X, éviter Y (même classe ou réaction croisée)
ALLERGY_CROSS_REACTIONS: dict[str, dict] = {
    "aspirine": {
        "avoid_class": "AINS / anti-inflammatoires non stéroïdiens",
        "avoid_drugs": ["ibuprofène", "ibuprofen", "naproxène", "naproxen",
                        "diclofénac", "diclofenac", "kétoprofène", "ketoprofen",
                        "indométacine", "celecoxib", "celebrex", "piroxicam"],
        "severity": "critique",
        "reason": "Réaction croisée AINS : risque de choc anaphylactique",
    },
    "aspirin": {
        "avoid_class": "NSAIDs",
        "avoid_drugs": ["ibuprofen", "naproxen", "diclofenac", "ketoprofen",
                        "indomethacin", "celecoxib", "piroxicam", "meloxicam"],
        "severity": "critique",
        "reason": "NSAID cross-reaction: risk of anaphylaxis",
    },
    "pénicilline": {
        "avoid_class": "Bêta-lactamines",
        "avoid_drugs": ["amoxicilline", "amoxicillin", "ampicilline", "ampicillin",
                        "oxacilline", "cloxacilline", "pipéracilline",
                        "céfalexine", "cefalexin", "ceftriaxone", "cefazoline",
                        "imipénème", "méropénème"],
        "severity": "élevée",
        "reason": "Réaction croisée bêta-lactamine (~10%) : allergie pénicilline",
    },
    "penicillin": {
        "avoid_class": "Beta-lactams",
        "avoid_drugs": ["amoxicillin", "ampicillin", "oxacillin", "cloxacillin",
                        "piperacillin", "cefalexin", "ceftriaxone", "cefazolin",
                        "imipenem", "meropenem"],
        "severity": "high",
        "reason": "Beta-lactam cross-reaction (~10%): penicillin allergy",
    },
    "sulfonamide": {
        "avoid_class": "Sulfamides",
        "avoid_drugs": ["sulfaméthoxazole", "sulfamethoxazole", "cotrimoxazole",
                        "triméthoprime", "trimethoprim", "bactrim", "septra"],
        "severity": "élevée",
        "reason": "Réaction croisée sulfamides",
    },
    "codéine": {
        "avoid_class": "Opioïdes",
        "avoid_drugs": ["morphine", "tramadol", "oxycodone", "hydrocodone",
                        "fentanyl", "dihydrocodéine"],
        "severity": "modérée",
        "reason": "Métabolisme CYP2D6 partagé, risque de réaction croisée opioïde",
    },
    "latex": {
        "avoid_class": "Certains fruits / aliments (réaction croisée latex-fruit)",
        "avoid_drugs": ["kiwi", "banane", "avocat", "châtaigne"],
        "severity": "modérée",
        "reason": "Syndrome latex-fruit : réaction croisée possible",
    },
    "iode": {
        "avoid_class": "Produits de contraste iodés",
        "avoid_drugs": ["produit de contraste", "contrast medium", "iohexol",
                        "iopamidol", "amiodarone"],
        "severity": "élevée",
        "reason": "Allergie iode : contre-indication produits de contraste",
    },
}

# ── Interactions médicament–médicament critiques ───────────────────────────────
# Format : (drug_a_keywords, drug_b_keywords, severity, description)
DRUG_DRUG_INTERACTIONS: list[tuple] = [
    # Anticoagulants
    (
        ["warfarine", "warfarin", "sintrom", "coumadine"],
        ["ibuprofène", "ibuprofen", "naproxène", "naproxen", "aspirine", "aspirin",
         "diclofénac", "diclofenac", "kétoprofène"],
        "critique",
        "Warfarine + AINS : risque hémorragique majeur (INR imprévisible)",
    ),
    (
        ["warfarine", "warfarin", "sintrom"],
        ["amiodarone", "fluconazole", "métronidazole", "metronidazole",
         "ciprofloxacine", "ciprofloxacin"],
        "critique",
        "Warfarine + inhibiteur CYP2C9 : potentialisation anticoagulation → hémorragie",
    ),
    # IMAO
    (
        ["imao", "maoi", "phénelzine", "phenelzine", "tranylcypromine",
         "sélégiline", "selegiline", "rasagiline"],
        ["ssri", "isrs", "fluoxétine", "fluoxetine", "sertraline", "paroxétine",
         "paroxetine", "escitalopram", "citalopram", "venlafaxine",
         "tramadol", "triptans", "triptan", "sumatriptan", "dextromethorphan",
         "méperidine", "meperidine", "pethidine"],
        "critique",
        "IMAO + sérotoninergique : risque de SYNDROME SÉROTONINERGIQUE (potentiellement mortel)",
    ),
    # Statines
    (
        ["simvastatine", "simvastatin", "atorvastatine", "atorvastatin",
         "rosuvastatine", "rosuvastatine"],
        ["clarithromycine", "clarithromycin", "érythromycine", "erythromycin",
         "itraconazole", "kétoconazole", "ketoconazole", "ciclosporine", "cyclosporin"],
        "élevée",
        "Statine + inhibiteur CYP3A4 : risque de rhabdomyolyse",
    ),
    # Metformine
    (
        ["metformine", "metformin", "glucophage"],
        ["produit de contraste", "contrast", "iohexol", "iopamidol"],
        "élevée",
        "Metformine + produit de contraste iodé : risque d'acidose lactique → arrêter 48h avant",
    ),
    # IEC / ARAII + Potassium
    (
        ["lisinopril", "ramipril", "perindopril", "enalapril",
         "losartan", "valsartan", "irbesartan", "telmisartan",
         "iec", "ace inhibitor", "arb", "sartan"],
        ["spironolactone", "éplérénone", "eplerenone", "amiloride",
         "triamtérène", "triamterene", "suppléments potassium", "potassium supplements"],
        "élevée",
        "IEC/ARA2 + diurétique épargneur potassium : risque d'HYPERKALIÉMIE (arythmie cardiaque)",
    ),
    # Digoxine
    (
        ["digoxine", "digoxin", "digitale"],
        ["amiodarone", "vérapamil", "verapamil", "diltiazem",
         "clarithromycine", "clarithromycin", "érythromycine", "erythromycin"],
        "critique",
        "Digoxine + inhibiteur P-gp : toxicité digitalique (troubles du rythme)",
    ),
    # Antidiabétiques oraux
    (
        ["glibenclamide", "gliclazide", "glipizide", "sulfonylurée",
         "répaglinide", "repaglinide"],
        ["fluconazole", "clarithromycine", "clarithromycin", "gemfibrozil"],
        "élevée",
        "Sulfonylurée + inhibiteur CYP2C9 : hypoglycémie sévère",
    ),
    # Lithium
    (
        ["lithium", "lithicarb", "téralithe", "priadel"],
        ["ibuprofène", "ibuprofen", "naproxène", "naproxen", "diclofénac",
         "diclofenac", "iec", "lisinopril", "ramipril"],
        "élevée",
        "Lithium + AINS/IEC : surdosage lithium (neurologique)",
    ),
    # QT prolongation
    (
        ["amiodarone", "sotalol", "dofétilide"],
        ["azithromycine", "azithromycin", "clarithromycine", "clarithromycin",
         "ciprofloxacine", "ciprofloxacin", "haloperidol", "halopéridol",
         "méthadone", "methadone"],
        "critique",
        "Anti-arythmique + médicament allongeant le QT : risque de TORSADES DE POINTES",
    ),
    # Contraceptifs oraux
    (
        ["pilule", "contraceptif oral", "oral contraceptive",
         "ethinylestradiol", "lévonorgestrel", "levonorgestrel"],
        ["rifampicine", "rifampin", "rifampicin",
         "carbamazépine", "carbamazepine", "phénytoïne", "phenytoin",
         "phénobarbital", "phenobarbital", "topiramate", "oxcarbazépine"],
        "élevée",
        "Contraceptif oral + inducteur enzymatique : efficacité contraceptive réduite → grossesse non désirée",
    ),
]


def _normalize(name: str) -> str:
    return name.lower().strip()


def check_allergy_conflicts(
    allergies: list[str],
    medications_to_check: list[str] | None = None,
) -> list[dict]:
    """
    Vérifie si les allergies connues du patient créent des contre-indications
    avec une liste de médicaments (ou retourne les classes à éviter globalement).

    `allergies` : substances auxquelles le patient est allergique
    `medications_to_check` : médicaments suggérés (ex: proposés par Gemini)
    """
    warnings = []
    for allergy in allergies:
        key = _normalize(allergy)
        for allergy_key, rule in ALLERGY_CROSS_REACTIONS.items():
            if allergy_key in key or key in allergy_key:
                if medications_to_check:
                    for med in medications_to_check:
                        med_low = _normalize(med)
                        if any(d in med_low for d in rule["avoid_drugs"]):
                            warnings.append({
                                "type": "allergie_croisée",
                                "allergie": allergy,
                                "médicament_conflict": med,
                                "classe": rule["avoid_class"],
                                "severity": rule["severity"],
                                "reason": rule["reason"],
                            })
                else:
                    warnings.append({
                        "type": "allergie_croisée",
                        "allergie": allergy,
                        "classe_à_éviter": rule["avoid_class"],
                        "médicaments_à_éviter": ", ".join(rule["avoid_drugs"][:5]),
                        "severity": rule["severity"],
                        "reason": rule["reason"],
                    })
    return warnings


def check_drug_interactions(current_medications: list[str]) -> list[dict]:
    """
    Vérifie les interactions dangereuses entre les médicaments en cours du patient.
    """
    if len(current_medications) < 2:
        return []

    warnings = []
    meds_low = [_normalize(m) for m in current_medications]

    for drug_a_kws, drug_b_kws, severity, description in DRUG_DRUG_INTERACTIONS:
        has_a = any(any(kw in m for kw in drug_a_kws) for m in meds_low)
        has_b = any(any(kw in m for kw in drug_b_kws) for m in meds_low)
        if has_a and has_b:
            # Identifier les médicaments spécifiques impliqués
            drugs_a = [m for m in current_medications
                       if any(kw in _normalize(m) for kw in drug_a_kws)]
            drugs_b = [m for m in current_medications
                       if any(kw in _normalize(m) for kw in drug_b_kws)]
            warnings.append({
                "type": "interaction_médicamenteuse",
                "médicament_a": drugs_a[0] if drugs_a else drug_a_kws[0],
                "médicament_b": drugs_b[0] if drugs_b else drug_b_kws[0],
                "severity": severity,
                "description": description,
            })

    return warnings


def build_safety_context(patient, lang: str = "fr") -> str:
    """
    Construit un bloc de mise en garde médicamenteuse à injecter dans le prompt.
    Appeler depuis _get_patient_medical_context() dans views.py.

    Retourne une chaîne vide si aucun problème détecté.
    """
    if not patient:
        return ""

    try:
        # Récupérer allergies
        allergies = []
        profile = getattr(patient, 'medical_profile', None)
        if profile:
            allergies = [a.substance for a in profile.allergies.all()]

        # Récupérer médicaments actifs
        treatments = [t for t in patient.treatments.all() if t.is_active]
        medication_names = [t.medication_name for t in treatments]

        # Vérifications
        allergy_warnings  = check_allergy_conflicts(allergies)
        drug_warnings     = check_drug_interactions(medication_names)

        all_warnings = allergy_warnings + drug_warnings
        if not all_warnings:
            return ""

        lines = []

        for w in all_warnings:
            sev = w.get("severity", "")
            icon = "🔴" if sev in ("critique", "critical") else "🟠"

            if w["type"] == "allergie_croisée":
                if lang == "ar":
                    lines.append(
                        f"{icon} تحذير حساسية: المريض حساس من {w['allergie']} — "
                        f"تجنب {w.get('classe_à_éviter','')}: {w['reason']}"
                    )
                elif lang == "en":
                    avoid = w.get("classe_à_éviter") or w.get("classe", "")
                    lines.append(
                        f"{icon} ALLERGY WARNING: Patient is allergic to {w['allergie']} — "
                        f"Avoid {avoid}. {w['reason']}"
                    )
                else:
                    avoid = w.get("classe_à_éviter") or w.get("classe", "")
                    lines.append(
                        f"{icon} ALERTE ALLERGIE: Patient allergique à {w['allergie']} — "
                        f"Éviter {avoid}. {w['reason']}"
                    )

            elif w["type"] == "interaction_médicamenteuse":
                if lang == "ar":
                    lines.append(
                        f"{icon} تفاعل دوائي: {w['médicament_a']} + {w['médicament_b']} — "
                        f"{w['description']}"
                    )
                elif lang == "en":
                    lines.append(
                        f"{icon} DRUG INTERACTION DETECTED: {w['médicament_a']} + "
                        f"{w['médicament_b']} — {w['description']}"
                    )
                else:
                    lines.append(
                        f"{icon} INTERACTION DÉTECTÉE: {w['médicament_a']} + "
                        f"{w['médicament_b']} — {w['description']}"
                    )

        if not lines:
            return ""

        if lang == "ar":
            header = "⚠️ تحذيرات السلامة الدوائية ⚠️"
        elif lang == "en":
            header = "⚠️ DRUG SAFETY WARNINGS ⚠️"
        else:
            header = "⚠️ ALERTES SÉCURITÉ MÉDICAMENTEUSE ⚠️"

        note_map = {
            "fr": "Ces alertes DOIVENT être mentionnées dans ta réponse avant toute recommandation.",
            "en": "These alerts MUST be mentioned in your response before any recommendation.",
            "ar": "يجب ذكر هذه التحذيرات في إجابتك قبل أي توصية.",
        }

        return "\n".join([header] + lines + [note_map.get(lang, note_map["fr"])])

    except Exception as e:
        logger.warning("drug_safety_service error: %s", e)
        return ""
