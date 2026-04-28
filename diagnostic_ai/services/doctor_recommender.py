# diagnostic_ai/services/doctor_recommender.py
#
# Après le diagnostic IA, cherche un médecin RÉEL sur la plateforme
# filtré par spécialité + ville/wilaya du patient.

import logging
from doctors.models import Doctor, Exercice

logger = logging.getLogger(__name__)

# ── Mapping spécialité bot → code Doctor model ────────────────
SPECIALTY_MAP = {
    "cardiologue":         "cardiology",
    "cardiology":          "cardiology",
    "dermatologue":        "dermatology",
    "dermatology":         "dermatology",
    "gynécologue":         "gynecology",
    "gynecology":          "gynecology",
    "pédiatre":            "pediatrics",
    "pediatrics":          "pediatrics",
    "ophtalmologue":       "ophthalmology",
    "ophthalmology":       "ophthalmology",
    "orl":                 "ent",
    "ent":                 "ent",
    "orthopédiste":        "orthopedics",
    "orthopedics":         "orthopedics",
    "neurologue":          "neurology",
    "neurology":           "neurology",
    "psychiatre":          "psychiatry",
    "psychiatry":          "psychiatry",
    "dentiste":            "dentistry",
    "dentistry":           "dentistry",
    "urologue":            "urology",
    "urology":             "urology",
    "oncologue":           "oncology",
    "oncology":            "oncology",
    "médecin_généraliste": "general",
    "generaliste":         "general",
    "general":             "general",
    "généraliste":         "general",
}


def get_specialty_code(specialist_key: str) -> str:
    """Convertit la clé spécialiste du bot en code Doctor model."""
    key = specialist_key.lower().strip()
    return SPECIALTY_MAP.get(key, "general")


def get_patient_location(patient) -> dict:
    """
    Extrait la ville et wilaya depuis le CustomUser du patient.
    Retourne {"city": ..., "wilaya": ...}
    """
    if patient and hasattr(patient, 'user'):
        return {
            "city":   getattr(patient.user, 'city', '') or '',
            "wilaya": getattr(patient.user, 'wilaya', '') or '',
        }
    return {"city": "", "wilaya": ""}


def find_doctors_near_patient(
    specialist_key: str,
    patient_city:   str = None,
    patient_wilaya: str = None,
    limit:          int = 3,
) -> list:
    """
    Cherche des médecins vérifiés sur la plateforme.

    Priorité de recherche :
    1. Même ville + bonne spécialité
    2. Même wilaya + bonne spécialité
    3. N'importe où + bonne spécialité (fallback national)

    Retourne une liste de dicts sérialisables JSON.
    """
    specialty_code = get_specialty_code(specialist_key)
    logger.info(
        "Recherche médecin: spécialité='%s' → code='%s', ville='%s', wilaya='%s'",
        specialist_key, specialty_code, patient_city, patient_wilaya
    )

    # Base queryset : médecins vérifiés actifs avec la bonne spécialité
    base_qs = Doctor.objects.filter(
        specialty          = specialty_code,
        is_verified        = True,
        user__is_active    = True,
    ).select_related('user').prefetch_related('exercises')

    doctors        = []
    seen_ids       = set()

    # ── 1. Même ville ─────────────────────────────────────────
    if patient_city:
        city_ids = Exercice.objects.filter(
            est_city__icontains=patient_city
        ).values_list('doctor_id', flat=True)

        for doc in base_qs.filter(id__in=city_ids).order_by('-rating', '-experience_years'):
            if doc.id not in seen_ids and len(doctors) < limit:
                doctors.append(_serialize_doctor(doc))
                seen_ids.add(doc.id)

    # ── 2. Même wilaya (fallback) ─────────────────────────────
    if len(doctors) < limit and patient_wilaya:
        wilaya_ids = Exercice.objects.filter(
            est_address__icontains=patient_wilaya
        ).values_list('doctor_id', flat=True)

        for doc in base_qs.filter(id__in=wilaya_ids).order_by('-rating', '-experience_years'):
            if doc.id not in seen_ids and len(doctors) < limit:
                doctors.append(_serialize_doctor(doc))
                seen_ids.add(doc.id)

    # ── 3. National (fallback) ────────────────────────────────
    if len(doctors) < limit:
        for doc in base_qs.order_by('-rating', '-experience_years'):
            if doc.id not in seen_ids and len(doctors) < limit:
                doctors.append(_serialize_doctor(doc))
                seen_ids.add(doc.id)

    logger.info("Médecins trouvés: %d", len(doctors))
    return doctors


def _serialize_doctor(doc: Doctor) -> dict:
    """Sérialise un médecin en dict léger pour la réponse API."""
    main_ex = doc.exercises.filter(is_main_location=True).first()
    if not main_ex:
        main_ex = doc.exercises.first()

    return {
        "id":               doc.id,
        "full_name":        f"Dr. {doc.user.get_full_name()}",
        "specialty":        doc.get_specialty_display(),
        "specialty_code":   doc.specialty,
        "clinic_name":      doc.clinic_name or "",
        "city":             main_ex.est_city    if main_ex else "",
        "address":          main_ex.est_address if main_ex else "",
        "phone":            main_ex.pro_phone   if main_ex else "",
        "consultation_fee": float(doc.consultation_fee),
        "rating":           float(doc.rating),
        "experience_years": doc.experience_years,
        "cnas_coverage":    doc.cnas_coverage,
        "languages":        doc.languages or "",
    }
