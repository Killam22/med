# apps/chat/services/medical_validator.py

import logging
import requests
import concurrent.futures
from django.core.cache import cache as django_cache

logger = logging.getLogger(__name__)

NIH_API_URL    = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
NIH_CACHE_TTL  = 60 * 60 * 24  # 24h — les codes ICD-10 ne changent pas souvent

# Noms alternatifs pour les maladies que NIH ne reconnaît pas sous leur nom courant
NIH_ALIASES = {
    "heart attack":               "myocardial infarction",
    "heart failure":              "cardiac failure",
    "flu":                        "influenza",
    "covid":                      "coronavirus disease",
    "covid-19":                   "coronavirus disease",
    "chickenpox":                 "varicella",
    "stroke":                     "cerebrovascular accident",
    "food poisoning":             "foodborne illness",
    "blood poisoning":            "septicemia",
    "mono":                       "infectious mononucleosis",
    "mononucleosis":              "infectious mononucleosis",
    "cold":                       "common cold",
    "pink eye":                   "conjunctivitis",
    "heartburn":                  "gastroesophageal reflux",
    "gastro":                     "gastroenteritis",
    "back pain":                  "dorsalgia",
    "kidney stones":              "urolithiasis",
    "kidney":                     "renal disease",
    "urinary tract":              "urinary tract infection",
    "alzheimer":                  "alzheimer disease",
    "parkinson":                  "parkinson disease",
    "vertigo":                    "vestibular vertigo",
    "arrhythmia":                 "cardiac arrhythmia",
    "allergy":                    "allergic reaction",
    "eczema":                     "atopic dermatitis",
    "hypothyroidism":             "hypothyroidism",
    "hyperthyroidism":            "hyperthyroidism",
    "appendicitis":               "acute appendicitis",
    "hepatitis":                  "viral hepatitis",
    "pancreatitis":               "acute pancreatitis",
    "migraine":                   "migraine disorder",
    "anxiety":                    "anxiety disorder",
    "depression":                 "major depressive disorder",
    "psoriasis":                  "psoriasis vulgaris",
    "arthritis":                  "rheumatoid arthritis",
    "meningitis":                 "bacterial meningitis",
    "pneumonia":                  "bacterial pneumonia",
    "bronchitis":                 "acute bronchitis",
    "asthma":                     "bronchial asthma",
    "tuberculosis":               "pulmonary tuberculosis",
    "malaria":                    "plasmodium malaria",
    "diabetes":                   "diabetes mellitus",
    "hypertension":               "essential hypertension",
    "heart block":                "atrioventricular block",
    "anemia":                     "iron deficiency anemia",
}


def validate_disease_nih(disease_name: str) -> dict:
    """
    Valide une maladie via l'API NIH.
    Résultat mis en cache Django (partagé entre tous les workers Gunicorn).
    TTL : 24h (les codes ICD-10 sont stables).
    """
    cache_key = f"nih_validation_{disease_name.lower().replace(' ', '_')}"
    cached = django_cache.get(cache_key)
    if cached is not None:
        return cached

    # Chercher d'abord avec le nom original, puis avec l'alias si pas trouvé
    search_names = [disease_name]
    alias = NIH_ALIASES.get(disease_name.lower())
    if alias:
        search_names.append(alias)

    for name in search_names:
        result = _query_nih(disease_name, name)
        if result["valid"]:
            django_cache.set(cache_key, result, NIH_CACHE_TTL)
            return result

    result = _not_found(disease_name)
    django_cache.set(cache_key, result, NIH_CACHE_TTL)
    return result


def _query_nih(original_name: str, search_name: str) -> dict:
    try:
        params = {
            "sf":      "code,name",
            "terms":   search_name,
            "maxList": 3,
        }

        response = requests.get(
            NIH_API_URL,
            params  = params,
            timeout = 3,
        )

        if response.status_code != 200:
            return _not_found(original_name)

        data = response.json()

        if not data or len(data) < 4 or data[0] == 0:
            logger.debug("NIH: '%s' non trouvée", search_name)
            return _not_found(original_name)

        codes = data[1]
        names = data[3]
        result = {
            "valid":         True,
            "icd10_code":    codes[0] if codes else "",
            "official_name": names[0][1] if names and len(names[0]) > 1 else original_name,
            "score":         1.0,
        }
        logger.debug(
            "NIH: '%s' → '%s' (%s)",
            original_name,
            result["official_name"],
            result["icd10_code"]
        )
        return result

    except requests.Timeout:
        logger.warning("NIH API timeout pour: '%s'", search_name)
        return _not_found(original_name)
    except Exception as e:
        logger.error("NIH API erreur: %s", e)
        return _not_found(original_name)


def _not_found(disease_name: str) -> dict:
    return {
        "valid":         False,
        "icd10_code":    "",
        "official_name": disease_name,
        "score":         0.5,
    }


def validate_diseases(diseases: list) -> tuple:
    """
    Valide toutes les maladies EN PARALLÈLE via l'API NIH.
    Utilise les alias NIH pour les maladies au nom courant non reconnu.
    """
    enriched    = []
    nih_results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_disease = {
            executor.submit(validate_disease_nih, d.get("name_en", "")): d
            for d in diseases
        }

        for future, disease in future_to_disease.items():
            name_en    = disease.get("name_en", "")
            confidence = disease.get("confidence", 0)

            try:
                validation = future.result()
            except Exception as e:
                logger.error("NIH validation error for '%s': %s", name_en, e)
                validation = _not_found(name_en)

            nih_results[name_en] = validation["valid"]

            if validation["valid"]:
                disease["confidence"]    = round(min(confidence * 1.1, 1.0), 2)
                disease["icd10_code"]    = validation["icd10_code"] or disease.get("icd10", "")
                disease["official_name"] = validation["official_name"]
                logger.debug(
                    "✅ NIH validée '%s' → %s (conf: %.2f → %.2f)",
                    name_en, validation["icd10_code"],
                    confidence, disease["confidence"]
                )
            else:
                disease["confidence"] = round(confidence * 0.9, 2)
                logger.debug(
                    "⚠️ NIH non trouvée '%s' (conf: %.2f → %.2f)",
                    name_en, confidence, disease["confidence"]
                )

            enriched.append(disease)

    enriched.sort(key=lambda d: d.get("confidence", 0), reverse=True)
    return enriched, nih_results