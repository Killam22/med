# diagnostic_ai/services/gemini_service.py

import time
import base64
import logging
from google import genai
from google.genai import types
from django.conf import settings

from diagnostic_ai.services.clinical_rules import check_symptom_alert, format_alert_for_response

logger = logging.getLogger(__name__)
_client = None

PROMPT_STYLES = {
1: """
Tu es un assistant médical IA qui parle directement avec le patient de manière naturelle.

Instructions :
- Réponds en phrases complètes, comme si tu discutais avec le patient.
- Explique chaque maladie possible associée aux symptômes.
- Ne fais jamais de diagnostic définitif.
- Termine chaque réponse par une recommandation de consulter un médecin.
""",
2: """
Tu es un assistant médical IA interactif.

Instructions :
- Parle directement au patient, comme dans une conversation.
- Pour chaque symptôme, explique clairement ce qu'il peut signifier.
- Décris les maladies possibles, leurs symptômes associés et le niveau d'urgence.
- Toujours finir par: "Ces informations sont générales, consultez un médecin pour confirmation."
"""
}

LANG_INSTRUCTIONS = {
"fr": """
Réponds uniquement en français.
Contraintes :
- Utilise un langage médical clair et professionnel.
- N'utilise aucune autre langue.
- Les explications doivent être compréhensibles mais scientifiquement correctes.
""",
"ar": """
أجب باللغة العربية فقط.
تعليمات صارمة:
- استخدم لغة طبية دقيقة وواضحة.
- لا تستخدم أي لغة أخرى.
""",
"en": """
Reply strictly in English.
Constraints:
- Use clear and professional medical language.
- Do not use any other language.
- All explanations must be medically accurate and evidence-based.
"""
}

CONVERSATIONAL_SYSTEM_PROMPT = """
Tu es MedSmart, un assistant médical IA professionnel et bienveillant.

Tu as les capacités suivantes :
1. DIAGNOSTIC — Analyser les symptômes et proposer des maladies possibles
2. QUESTIONS MÉDICALES — Répondre à toute question de santé générale
3. CONSEILS SANTÉ — Donner des conseils de prévention et d'hygiène de vie
4. MÉDICAMENTS — Expliquer les médicaments (usage, effets, précautions) SANS prescrire
5. ANALYSES — Expliquer des résultats d'analyses médicales
6. FICHIERS MÉDICAUX — Lire et expliquer ordonnances, comptes rendus, radios, analyses
7. SUIVI — Mémoriser le contexte de la conversation pour des réponses cohérentes

Règles absolues :
- Tu ne prescris JAMAIS de médicaments — tu informes uniquement
- Tu ne remplaces JAMAIS un médecin — tu orientes
- Tu ne donnes JAMAIS de diagnostic définitif
- Tu restes TOUJOURS dans le domaine médical et de santé
- Si question hors médical → rediriger poliment vers les symptômes
- Termine TOUJOURS par encourager à consulter un médecin

Ton style :
- Naturel et chaleureux comme un ami médecin
- Précis et scientifiquement correct
- Empathique avec le patient
- Concis mais complet
"""

# ══════════════════════════════════════════════
# PROMPTS ANALYSE FICHIERS MÉDICAUX
# ══════════════════════════════════════════════

FILE_ANALYSIS_PROMPTS = {
    "ordonnance": """
Tu analyses une ordonnance médicale. Tu dois :
- Lister chaque médicament prescrit avec son nom
- Expliquer à quoi sert chaque médicament (en langage simple)
- Mentionner les précautions importantes pour chaque médicament
- Expliquer la posologie prescrite (sans la modifier)
- Rappeler que seul le médecin prescripteur peut modifier l'ordonnance
- Encourager à poser des questions au pharmacien
""",
    "analyse": """
Tu analyses des résultats d'analyses médicales (sang, urine, etc.). Tu dois :
- Identifier chaque paramètre analysé
- Expliquer ce que mesure chaque paramètre en langage clair
- Indiquer si les valeurs sont dans les normes habituelles
- Expliquer ce que signifie une valeur anormale (sans alarmer)
- Rappeler que l'interprétation définitive appartient au médecin
- Conseiller de discuter des résultats avec le médecin traitant
""",
    "radio": """
Tu analyses une image médicale (radio, IRM, scanner, échographie). Tu dois :
- Décrire ce que tu observes de manière générale
- Expliquer ce que montre ce type d'examen normalement
- Si des anomalies sont visibles, les décrire sans diagnostic définitif
- Rappeler que seul un radiologue peut interpréter officiellement ces images
- Encourager à consulter le médecin pour une interprétation complète
- Ne jamais affirmer un diagnostic basé uniquement sur l'image
""",
    "medicament": """
Tu analyses une photo de médicament. Tu dois :
- Identifier le médicament (nom, forme, dosage si visible)
- Expliquer la classe thérapeutique et l'usage général
- Mentionner les effets secondaires courants
- Donner les précautions d'emploi importantes
- Rappeler de ne jamais prendre un médicament sans prescription médicale
- Orienter vers un pharmacien ou médecin pour plus de détails
""",
    "compte_rendu": """
Tu analyses un compte rendu médical. Tu dois :
- Résumer les points principaux en langage clair et accessible
- Expliquer les termes médicaux complexes
- Mettre en évidence les conclusions importantes
- Expliquer les recommandations mentionnées
- Rappeler que seul le médecin peut interpréter ce document dans son contexte
- Encourager à poser des questions au médecin lors de la prochaine consultation
""",
    "general": """
Tu analyses un document ou une image médicale. Tu dois :
- Identifier le type de document ou d'image
- Extraire et expliquer les informations médicales importantes
- Utiliser un langage clair et accessible pour le patient
- Mentionner les points qui nécessitent l'attention d'un médecin
- Rappeler que tes explications sont informatives, pas diagnostiques
- Encourager à consulter un professionnel de santé
"""
}

NON_MEDICAL_RESPONSE = {
    "fr": (
        "Ce document ne semble pas être un document médical. 🚫\n\n"
        "Je suis spécialisé uniquement dans l'analyse de documents de santé :\n"
        "• Ordonnances médicales\n"
        "• Résultats d'analyses (sang, urine...)\n"
        "• Radios, IRM, scanners\n"
        "• Comptes rendus médicaux\n"
        "• Photos de médicaments\n\n"
        "Envoyez-moi un document médical et je ferai de mon mieux pour vous aider. 🩺"
    ),
    "ar": (
        "هذا المستند لا يبدو وثيقة طبية. 🚫\n\n"
        "أنا متخصص فقط في تحليل وثائق الصحة :\n"
        "• الوصفات الطبية\n"
        "• نتائج التحاليل\n"
        "• صور الأشعة\n"
        "• التقارير الطبية\n"
        "• صور الأدوية\n\n"
        "أرسل لي وثيقة طبية وسأساعدك. 🩺"
    ),
    "en": (
        "This document does not appear to be a medical document. 🚫\n\n"
        "I am specialized only in analyzing health documents:\n"
        "• Medical prescriptions\n"
        "• Lab results (blood, urine...)\n"
        "• X-rays, MRI, CT scans\n"
        "• Medical reports\n"
        "• Medication photos\n\n"
        "Send me a medical document and I will do my best to help you. 🩺"
    ),
}

FILE_CLARIFICATION_QUESTIONS = {
    "fr": (
        "J'ai bien reçu votre fichier médical. 📄\n\n"
        "Pour vous aider au mieux, que souhaitez-vous que j'analyse ?\n\n"
        "• **Expliquer** le contenu en langage simple\n"
        "• **Résumer** les points importants\n"
        "• **Interpréter** les valeurs ou résultats\n"
        "• **Identifier** les médicaments ou traitements\n"
        "• **Autre** — précisez votre question\n\n"
        "Dites-moi ce que vous voulez savoir ! 🩺"
    ),
    "ar": (
        "لقد استلمت ملفك الطبي. 📄\n\n"
        "لمساعدتك بشكل أفضل، ماذا تريد مني أن أحلل؟\n\n"
        "• **شرح** المحتوى بلغة بسيطة\n"
        "• **تلخيص** النقاط المهمة\n"
        "• **تفسير** القيم أو النتائج\n"
        "• **تحديد** الأدوية أو العلاجات\n"
        "• **أخرى** — حدد سؤالك\n\n"
        "أخبرني ما تريد معرفته! 🩺"
    ),
    "en": (
        "I have received your medical file. 📄\n\n"
        "To help you better, what would you like me to analyze?\n\n"
        "• **Explain** the content in simple language\n"
        "• **Summarize** the important points\n"
        "• **Interpret** the values or results\n"
        "• **Identify** medications or treatments\n"
        "• **Other** — specify your question\n\n"
        "Tell me what you want to know! 🩺"
    ),
}


def get_gemini():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini client initialise")
    return _client


def detect_intent(message: str, history: list) -> str:
    msg = message.lower()

    symptom_keywords = [
        "j'ai", "je souffre", "je ressens", "douleur", "mal", "fièvre",
        "toux", "fatigue", "nausée", "vomissement", "froid", "chaud",
        "brûlure", "démangeaison", "gonflement", "saignement", "vertige",
        "essoufflement", "palpitation", "i have", "i feel", "pain", "fever",
        "أعاني", "ألم", "حمى", "تعب"
    ]
    question_keywords = [
        "qu'est ce que", "c'est quoi", "comment", "pourquoi", "expliquer",
        "what is", "how", "why", "explain", "ما هو", "كيف", "لماذا"
    ]
    medication_keywords = [
        "médicament", "comprimé", "pilule", "doliprane", "ibuprofène",
        "paracétamol", "antibiotique", "dose", "posologie", "effets",
        "medication", "pill", "tablet", "drug", "دواء", "حبة", "علاج"
    ]
    prevention_keywords = [
        "prévenir", "éviter", "protéger", "vaccin", "alimentation",
        "régime", "sport", "sommeil", "stress", "hygiène",
        "prevent", "avoid", "vaccine", "diet", "وقاية", "تغذية"
    ]

    if any(kw in msg for kw in medication_keywords):
        return 'medication'
    if any(kw in msg for kw in prevention_keywords):
        return 'prevention'
    if any(kw in msg for kw in symptom_keywords):
        return 'symptom'
    if any(kw in msg for kw in question_keywords):
        return 'question'
    if history:
        return 'followup'
    return 'question'


def detect_file_type(message: str, mime_type: str) -> str:
    msg = message.lower() if message else ""

    non_medical_keywords = [
        "classement", "promotion", "étudiant", "étudiants", "bulletin",
        "notes", "relevé de notes", "moyenne", "faculté", "université",
        "facture", "contrat", "salaire", "relevé bancaire", "bancaire",
        "score", "rang", "ranking", "inscription", "diplôme", "cursus",
        "invoice", "receipt", "bank", "student", "grade", "transcript",
    ]
    if any(kw in msg for kw in non_medical_keywords):
        return "non_medical"

    if any(kw in msg for kw in ["ordonnance", "prescription", "prescrit", "prescribed", "وصفة"]):
        return "ordonnance"
    if any(kw in msg for kw in ["analyse", "bilan", "prise de sang", "urine", "blood test", "تحليل", "نتائج"]):
        return "analyse"
    if any(kw in msg for kw in ["radio", "irm", "scanner", "échographie", "rx", "xray", "x-ray", "scan", "أشعة"]):
        return "radio"
    if any(kw in msg for kw in ["médicament", "comprimé", "pilule", "boite", "medication", "pill", "دواء"]):
        return "medicament"
    if any(kw in msg for kw in ["compte rendu", "rapport", "report", "résultat", "result", "تقرير"]):
        return "compte_rendu"

    if mime_type and "image" in mime_type:
        return "general"
    if mime_type and "pdf" in mime_type:
        return "compte_rendu"

    return "general"


def build_file_analysis_prompt(message, lang, file_type, history):
    lang_instr = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["fr"])
    file_instr = FILE_ANALYSIS_PROMPTS.get(file_type, FILE_ANALYSIS_PROMPTS["general"])

    history_text = ""
    for msg in history[-6:]:
        role = "Patient" if msg["role"] == "user" else "MedSmart"
        history_text += f"{role}: {msg['content'][:200]}\n"
    if not history_text:
        history_text = "Début de conversation."

    user_question = (
        f'Question du patient : "{message}"'
        if message
        else "Le patient n'a pas précisé de question — analyse le document de manière générale."
    )

    return f"""
{CONVERSATIONAL_SYSTEM_PROMPT}

{lang_instr}

══════════════════════════════════════════════
⚠️ VÉRIFICATION OBLIGATOIRE — À FAIRE EN PREMIER
══════════════════════════════════════════════
Avant toute analyse, examine le contenu du fichier et vérifie qu'il s'agit
bien d'un document MÉDICAL ou de SANTÉ.

Documents médicaux ACCEPTÉS :
- Ordonnances, prescriptions médicales
- Résultats d'analyses (sang, urine, biologie)
- Radios, IRM, scanners, échographies
- Comptes rendus médicaux, rapports de consultation
- Photos de médicaments, boites de médicaments
- Bilans de santé, carnets de vaccination

Documents NON MÉDICAUX — À REJETER :
- Bulletins scolaires, relevés de notes, classements
- Factures, contrats, documents bancaires
- Documents administratifs, formulaires
- Tout document sans rapport avec la santé

SI le document N'EST PAS médical → réponds UNIQUEMENT et EXACTEMENT :
"Ce document ne semble pas être un document médical. Je suis spécialisé
uniquement dans l'analyse de documents de santé (ordonnances, analyses,
radios, comptes rendus médicaux). Envoyez-moi un document médical
et je ferai de mon mieux pour vous aider. 🩺"

SI le document EST médical → continue avec les instructions ci-dessous.
══════════════════════════════════════════════

{file_instr}

Historique de la conversation :
{history_text}

{user_question}

Analyse maintenant le fichier joint et réponds de manière claire, bienveillante et professionnelle.
Utilise des titres et des listes pour structurer ta réponse.
Termine toujours par encourager le patient à consulter son médecin.
"""


def build_conversational_prompt(message, lang, history, intent):
    lang_instr = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["fr"])

    history_text = ""
    for msg in history[-8:]:
        role = "Patient" if msg["role"] == "user" else "MedSmart"
        history_text += f"{role}: {msg['content'][:300]}\n"
    if not history_text:
        history_text = "Début de conversation."

    intent_instructions = {
        'symptom': """
Le patient décrit des symptômes. Tu dois :
- Écouter attentivement et poser 1-2 questions de clarification si nécessaire
- Expliquer ce que ces symptômes peuvent signifier
- Mentionner les causes possibles les plus probables
- Indiquer le niveau d'urgence
- Conseiller de consulter un médecin
""",
        'question': """
Le patient pose une question médicale générale. Tu dois :
- Répondre de manière claire, précise et pédagogique
- Utiliser des exemples concrets si utile
- Rester factuel et scientifiquement correct
- Terminer par un conseil pratique
""",
        'medication': """
Le patient pose une question sur un médicament. Tu dois :
- Expliquer le médicament (classe, usage général)
- Mentionner les précautions importantes
- Rappeler que la posologie doit être prescrite par un médecin
- Ne JAMAIS recommander une dose spécifique sans prescription
""",
        'prevention': """
Le patient cherche des conseils de prévention ou d'hygiène de vie. Tu dois :
- Donner des conseils pratiques et concrets
- Baser les conseils sur des recommandations médicales reconnues
- Adapter les conseils au contexte de la conversation
- Encourager un mode de vie sain
""",
        'followup': """
C'est une suite de conversation. Tu dois :
- Tenir compte de tout l'historique pour répondre
- Être cohérent avec les réponses précédentes
- Approfondir ou clarifier selon la demande
- Garder le fil médical de la conversation
""",
    }

    instruction = intent_instructions.get(intent, intent_instructions['question'])

    return f"""
{CONVERSATIONAL_SYSTEM_PROMPT}

{lang_instr}

Historique de la conversation :
{history_text}

Message actuel du patient : "{message}"

Type de demande détecté : {intent}

Instructions spécifiques :
{instruction}

Réponds maintenant de manière naturelle, professionnelle et bienveillante.
Termine par encourager à consulter un médecin si pertinent.
"""


# ✅ MODIFIÉ — accepte medical_context pour personnaliser le diagnostic
def build_diagnosis_prompt(symptoms, diseases, lang, history, prompt_style=2,
                           medical_context: str = ""):
    lang_instr  = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["fr"])
    style_instr = PROMPT_STYLES.get(prompt_style, PROMPT_STYLES[2])

    context = "\n".join([
        f"- {d['name_fr'] or d['name_en']} "
        f"(Spécialiste: {d['specialist']}, "
        f"Urgence: {d['urgency']}, "
        f"ICD-10: {d['icd10']})"
        for d in diseases[:3]
    ])

    history_text = ""
    for msg in history:
        role = "Patient" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"
    if not history_text:
        history_text = "Première interaction."

    # ── Bloc contexte médical personnalisé (allergies, antécédents, traitements) ──
    medical_context_block = ""
    if medical_context and medical_context.strip():
        medical_context_block = f"""
{medical_context}

⚠️ IMPORTANT — Utilise ces informations pour personnaliser ton analyse :
- Mentionne si un symptôme peut être lié à un antécédent connu du patient.
- Signale si une maladie probable est incompatible avec un traitement en cours.
- Mets en garde si une allergie connue est pertinente pour les recommandations.

"""

    return f"""
{CONVERSATIONAL_SYSTEM_PROMPT}

{lang_instr}
{style_instr}
{medical_context_block}
Symptômes du patient : {symptoms}

Maladies possibles identifiées par analyse médicale :
{context}

Historique de la conversation :
{history_text}

Explique chaque maladie possible en phrases complètes et naturelles.
Ne donne PAS encore les médecins recommandés ni les conseils pratiques.
Sois précis mais accessible — évite le jargon trop technique.
Termine par : "Diagnostic provisoire - Consultez un médecin."
"""


def build_recommendation_prompt(symptoms, diseases, lang):
    lang_instr = LANG_INSTRUCTIONS.get(lang, LANG_INSTRUCTIONS["fr"])

    context = "\n".join([
        f"- {d['name_fr'] or d['name_en']} "
        f"(Spécialiste: {d['specialist']}, "
        f"Urgence: {d['urgency']})"
        for d in diseases[:3]
    ])

    return f"""
{CONVERSATIONAL_SYSTEM_PROMPT}

{lang_instr}

Patient a les symptômes : {symptoms}
Maladies probables : {context}

Donne de manière claire et bienveillante :
1. Le spécialiste recommandé et pourquoi (1-2 phrases)
2. Les actions immédiates à faire (3-4 points concrets)
3. Les signes d'alarme qui nécessitent une urgence

Sois pratique et rassurant.
"""


def generate(prompt, temperature=0.7, top_p=0.9, max_retries=3):
    for attempt in range(max_retries):
        try:
            client  = get_gemini()
            config  = types.GenerateContentConfig(
                temperature       = temperature,
                top_p             = top_p,
                max_output_tokens = 8192,
            )
            response = client.models.generate_content(
                model    = settings.GEMINI_MODEL,
                contents = prompt,
                config   = config,
            )
            return response.text

        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    wait = 60 * (attempt + 1)
                    logger.warning("Quota Gemini dépassé — attente %ds", wait)
                    time.sleep(wait)
                else:
                    raise ValueError("Le service IA est temporairement indisponible. Veuillez réessayer dans quelques minutes.")
            elif "UNAVAILABLE" in error_str or "503" in error_str:
                if attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    logger.warning("Gemini surchargé — retry dans %ds", wait)
                    time.sleep(wait)
                else:
                    raise ValueError("Le service IA est actuellement surchargé. Veuillez réessayer dans quelques instants.")
            else:
                logger.error("Gemini error: %s", e)
                raise

    raise ValueError("Impossible de contacter le service IA.")


def generate_stream(prompt, temperature=0.7, top_p=0.9, max_retries=3):
    for attempt in range(max_retries):
        try:
            client = get_gemini()
            config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                max_output_tokens=8192,
            )
            response = client.models.generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
            return

        except Exception as e:
            error_str = str(e)
            if "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries - 1:
                    wait = 60 * (attempt + 1)
                    logger.warning("Quota Gemini stream dépassé — attente %ds", wait)
                    time.sleep(wait)
                    continue
                else:
                    yield "\n⚠️ Service temporairement indisponible. Réessayez dans quelques minutes."
                    return
            elif "UNAVAILABLE" in error_str or "503" in error_str:
                if attempt < max_retries - 1:
                    wait = 3 * (attempt + 1)
                    logger.warning("Gemini stream surchargé — retry dans %ds", wait)
                    time.sleep(wait)
                    continue
                else:
                    yield "\n⚠️ Service surchargé. Réessayez dans quelques instants."
                    return
            else:
                logger.error("Gemini stream error: %s", e)
                yield "\n⚠️ Une erreur est survenue."
                return


# ══════════════════════════════════════════════
# FONCTIONS STREAM — avec alerte médicale
# ══════════════════════════════════════════════

def generate_conversational_stream(message: str, lang: str, history: list):
    alert = check_symptom_alert(symptoms_fr=message, symptoms_en=message)
    if alert["level"] in ("critical", "moderate"):
        yield format_alert_for_response(alert, lang=lang) + "\n\n"
    intent = detect_intent(message, history)
    logger.info("Stream intent: '%s' pour: '%s'", intent, message[:40])
    prompt = build_conversational_prompt(message, lang, history, intent)
    yield from generate_stream(prompt, temperature=0.75, top_p=0.92)


# ✅ MODIFIÉ — accepte medical_context et le transmet à build_diagnosis_prompt
def generate_diagnosis_stream(symptoms: str, diseases: list, lang: str, history: list,
                               prompt_style: int = 2, medical_context: str = ""):
    alert = check_symptom_alert(symptoms_fr=symptoms, symptoms_en=symptoms)
    if alert["level"] in ("critical", "moderate"):
        yield format_alert_for_response(alert, lang=lang) + "\n\n"
    prompt = build_diagnosis_prompt(
        symptoms, diseases, lang, history, prompt_style,
        medical_context=medical_context,
    )
    yield from generate_stream(prompt)


def generate_recommendation_stream(symptoms: str, diseases: list, lang: str):
    prompt = build_recommendation_prompt(symptoms, diseases, lang)
    yield from generate_stream(prompt)


def generate_conversational(message: str, lang: str, history: list) -> str:
    intent = detect_intent(message, history)
    logger.info("Intent détecté: '%s' pour: '%s'", intent, message[:40])
    prompt = build_conversational_prompt(message, lang, history, intent)
    return generate(prompt, temperature=0.75, top_p=0.92)


# ══════════════════════════════════════════════
# ANALYSE FICHIERS MÉDICAUX
# ══════════════════════════════════════════════

def generate_file_analysis_stream(
    file_bytes: bytes,
    mime_type:  str,
    message:    str,
    lang:       str,
    history:    list,
):
    try:
        file_type = detect_file_type(message, mime_type)
        logger.info("Analyse fichier — type: '%s', mime: '%s'", file_type, mime_type)

        if file_type == "non_medical":
            yield NON_MEDICAL_RESPONSE.get(lang, NON_MEDICAL_RESPONSE["fr"])
            return

        prompt_text = build_file_analysis_prompt(
            message=message, lang=lang,
            file_type=file_type, history=history,
        )

        contents = [
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            types.Part.from_text(text=prompt_text),
        ]

        client = get_gemini()
        config = types.GenerateContentConfig(
            temperature=0.7, top_p=0.9, max_output_tokens=8192,
        )
        response = client.models.generate_content_stream(
            model=settings.GEMINI_MODEL, contents=contents, config=config,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        error_str = str(e)
        logger.error("Erreur analyse fichier: %s", e)
        if "RESOURCE_EXHAUSTED" in error_str:
            yield "\n⚠️ Service temporairement indisponible. Réessayez dans quelques minutes."
        elif "UNAVAILABLE" in error_str or "503" in error_str:
            yield "\n⚠️ Service surchargé. Réessayez dans quelques instants."
        elif "invalid" in error_str.lower() or "unsupported" in error_str.lower():
            yield "\n⚠️ Format de fichier non supporté. Envoyez une image (JPG, PNG) ou un PDF."
        else:
            yield "\n⚠️ Une erreur est survenue lors de l'analyse du fichier."