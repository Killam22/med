# diagnostic_ai/services/genetic/fitness.py

import logging
from diagnostic_ai.services.chroma_service import search_diseases
from diagnostic_ai.services.gemini_service import build_diagnosis_prompt, generate
from .chromosome import Chromosome

logger = logging.getLogger(__name__)

QUALITY_KEYWORDS = [
    "diagnostic", "symptôme", "maladie", "médecin", "urgence",
    "traitement", "consulter", "probabilité", "spécialiste",
    "disease", "symptom", "doctor", "specialist", "consult",
    "مرض", "طبيب", "أعراض", "تشخيص"
]

DISCLAIMER_KEYWORDS = [
    "diagnostic provisoire", "consultez", "médecin qualifié",
    "provisional", "consult", "تشخيص مبدئي", "استشر طبيباً"
]


def evaluate(chromosome: Chromosome, test_cases: list) -> float:
    if not test_cases:
        return 0.0

    scores = []
    for case in test_cases:
        symptoms = case.get("symptoms", "")
        lang     = case.get("lang", "fr")
        expected = case.get("expected_diseases", [])

        try:
            diseases = search_diseases(symptoms, k=chromosome.retrieval_k)

            disease_score = 0.0
            if expected and diseases:
                found = sum(
                    1 for exp in expected
                    if any(
                        exp.lower() in d.get("name_en", "").lower() or
                        exp.lower() in d.get("name_fr", "").lower()
                        for d in diseases[:3]
                    )
                )
                disease_score = found / len(expected)

            quality_score    = 0.5
            disclaimer_score = 0.5
            length_score     = 0.5

            if disease_score > 0.3 and diseases:
                prompt = build_diagnosis_prompt(
                    symptoms=symptoms, diseases=diseases, lang=lang,
                    history=[], prompt_style=chromosome.prompt_style,
                )
                response       = generate(prompt, temperature=chromosome.temperature, top_p=chromosome.top_p)
                response_lower = response.lower()

                keyword_hits     = sum(1 for kw in QUALITY_KEYWORDS if kw.lower() in response_lower)
                quality_score    = min(keyword_hits / max(len(QUALITY_KEYWORDS) * 0.4, 1), 1.0)
                disclaimer_score = float(any(kw.lower() in response_lower for kw in DISCLAIMER_KEYWORDS))
                word_count       = len(response.split())
                length_score     = 1.0 if 80 <= word_count <= 350 else 0.5

            final = (
                0.40 * disease_score    +
                0.30 * quality_score    +
                0.20 * disclaimer_score +
                0.10 * length_score
            )
            scores.append(round(final, 4))

        except Exception as e:
            logger.error("Fitness eval error: %s", e)
            scores.append(0.0)

    return round(sum(scores) / len(scores), 4) if scores else 0.0
