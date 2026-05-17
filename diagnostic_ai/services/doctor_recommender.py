# diagnostic_ai/services/doctor_recommender.py
#
# Après le diagnostic IA, cherche un médecin RÉEL sur la plateforme
# filtré par spécialité + GPS (Haversine) ou ville/wilaya du patient.

import logging
import math
from doctors.models import Doctor, Exercice

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km entre deux points GPS (formule de Haversine)."""
    R = 6371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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
    "médecin_généraliste":  "general",
    "médecin généraliste":  "general",
    "general practitioner": "general",
    "generaliste":          "general",
    "general":              "general",
    "généraliste":          "general",
    "pneumologue":          "pulmonology",
    "pulmonologist":        "pulmonology",
    "pulmonology":          "pulmonology",
    "gastro-entérologue":   "gastroenterology",
    "gastroenterologist":   "gastroenterology",
    "gastroenterology":     "gastroenterology",
    "endocrinologue":       "endocrinology",
    "endocrinologist":      "endocrinology",
    "endocrinology":        "endocrinology",
    "rhumatologue":         "rheumatology",
    "rheumatologist":       "rheumatology",
    "rheumatology":         "rheumatology",
    "infectiologue":        "infectious_disease",
    "hématologue":          "hematology",
    "hematologist":         "hematology",
}


def get_specialty_code(specialist_key: str) -> str:
    """Convertit la clé spécialiste du bot en code Doctor model."""
    key = specialist_key.lower().strip()
    return SPECIALTY_MAP.get(key, "general")


def get_patient_location(patient) -> dict:
    """
    Extrait ville, wilaya et coordonnées GPS depuis le profil patient.
    Retourne {"city": ..., "wilaya": ..., "lat": float|None, "lon": float|None}
    """
    if patient and hasattr(patient, 'user'):
        return {
            "city":   getattr(patient.user, 'city', '') or '',
            "wilaya": getattr(patient.user, 'wilaya', '') or '',
            "lat":    float(patient.user.latitude)  if getattr(patient.user, 'latitude', None)  else None,
            "lon":    float(patient.user.longitude) if getattr(patient.user, 'longitude', None) else None,
        }
    return {"city": "", "wilaya": "", "lat": None, "lon": None}


def find_doctors_near_patient(
    specialist_key: str,
    patient_city:   str   = None,
    patient_wilaya: str   = None,
    patient_lat:    float = None,
    patient_lon:    float = None,
    limit:          int   = 3,
) -> list:
    """
    Cherche des médecins vérifiés sur la plateforme.

    Priorité de recherche :
    1. GPS Haversine (si coordonnées patient disponibles) → triés par distance km
    2. Même ville (fallback texte)
    3. Même wilaya (fallback texte)
    4. National (fallback final)
    """
    specialty_code = get_specialty_code(specialist_key)
    logger.info(
        "Recherche médecin: spécialité='%s' → code='%s', gps=(%s,%s), ville='%s'",
        specialist_key, specialty_code, patient_lat, patient_lon, patient_city,
    )

    base_qs = Doctor.objects.filter(
        specialty       = specialty_code,
        is_verified     = True,
        user__is_active = True,
    ).select_related('user').prefetch_related('exercises')

    doctors  = []
    seen_ids = set()

    # ── 1. GPS Haversine ──────────────────────────────────────
    if patient_lat is not None and patient_lon is not None:
        candidates = []
        for doc in base_qs:
            ex = doc.exercises.filter(is_main_location=True).first() or doc.exercises.first()
            if ex and ex.latitude and ex.longitude:
                dist = _haversine_km(patient_lat, patient_lon, float(ex.latitude), float(ex.longitude))
                candidates.append((dist, doc))

        candidates.sort(key=lambda x: x[0])
        for dist, doc in candidates:
            if doc.id not in seen_ids and len(doctors) < limit:
                entry = _serialize_doctor(doc)
                entry["distance_km"] = round(dist, 1)
                doctors.append(entry)
                seen_ids.add(doc.id)
                logger.info("GPS: Dr.%s — %.1f km", doc.user.last_name, dist)

    # ── 2. Même ville (fallback texte) ────────────────────────
    if len(doctors) < limit and patient_city:
        city_ids = Exercice.objects.filter(
            est_city__icontains=patient_city
        ).values_list('doctor_id', flat=True)
        for doc in base_qs.filter(id__in=city_ids).order_by('-rating', '-experience_years'):
            if doc.id not in seen_ids and len(doctors) < limit:
                doctors.append(_serialize_doctor(doc))
                seen_ids.add(doc.id)

    # ── 3. Même wilaya (fallback texte) ───────────────────────
    if len(doctors) < limit and patient_wilaya:
        wilaya_ids = Exercice.objects.filter(
            est_address__icontains=patient_wilaya
        ).values_list('doctor_id', flat=True)
        for doc in base_qs.filter(id__in=wilaya_ids).order_by('-rating', '-experience_years'):
            if doc.id not in seen_ids and len(doctors) < limit:
                doctors.append(_serialize_doctor(doc))
                seen_ids.add(doc.id)

    # ── 4. National (fallback final) ──────────────────────────
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

    result = {
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
        "distance_km":      None,
    }
    if main_ex and main_ex.latitude and main_ex.longitude:
        result["latitude"]  = float(main_ex.latitude)
        result["longitude"] = float(main_ex.longitude)
    return result
