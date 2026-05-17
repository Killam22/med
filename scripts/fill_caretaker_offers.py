"""
Ajoute des Offres de Missions et Plans de Traitement pour Fatima Hadj.
Lancer : python manage.py shell -c "exec(open('scripts/fill_caretaker_offers.py', encoding='utf-8').read())"
"""
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

from caretaker.models import Caretaker, CareRequest, MedicationSchedule
from notifications.models import Notification
from patients.models import Patient, MedicalProfile, Antecedent

TODAY    = date.today()
PASSWORD = "Demo@2025"

print("=" * 60)
print("OFFRES & PLANS — Fatima Hadj")
print("=" * 60)

# ─── Fatima Hadj ──────────────────────────────────────────────
try:
    u_hadj = User.objects.get(email='fatima.hadj@demo.com')
    caretaker = u_hadj.caretaker_profile
except Exception as e:
    print(f"❌ {e} — lancez d'abord fill_caretaker_data.py")
    raise SystemExit


# ─── Helpers ──────────────────────────────────────────────────
def make_patient(email, first, last, sex, dob, phone, card,
                 address, postal, city, wilaya,
                 emg_name="", emg_phone="",
                 blood="", weight=None, height=None):
    if User.objects.filter(email=email).exists():
        return User.objects.get(email=email)
    u = User(
        username=email, email=email, role='patient',
        first_name=first, last_name=last, sex=sex,
        date_of_birth=dob, phone=phone, id_card_number=card,
        address=address, postal_code=postal, city=city, wilaya=wilaya,
        verification_status='verified', is_active=True,
    )
    u.set_password(PASSWORD)
    u.save()
    p = Patient.objects.create(user=u)
    MedicalProfile.objects.create(
        patient=p,
        emergency_contact_name=emg_name,
        emergency_contact_phone=emg_phone,
        blood_group=blood, weight=weight, height=height,
    )
    print(f"  ✅ Patient créé : {first} {last}")
    return u


def add_antecedents(user_obj, entries):
    try:
        prof = user_obj.patient_profile
    except Exception:
        return
    for name, atype, status in entries:
        Antecedent.objects.get_or_create(
            patient=prof, name=name,
            defaults={'type': atype, 'status': status}
        )


def make_offer(patient_user, start_offset, end_offset, message):
    if CareRequest.objects.filter(patient=patient_user, caretaker=caretaker, status='pending').exists():
        print(f"  ⏭️  Offre existe : {patient_user.get_full_name()}")
        return None
    try:
        req = CareRequest.objects.create(
            patient=patient_user,
            caretaker=caretaker,
            status='pending',
            start_date=TODAY + timedelta(days=start_offset),
            end_date=TODAY + timedelta(days=end_offset) if end_offset else None,
            patient_message=message,
        )
        print(f"  ✅ Offre : {patient_user.get_full_name():<28} [en attente]")
        Notification.objects.get_or_create(
            user=u_hadj,
            title=f"Nouvelle demande — {patient_user.get_full_name()}",
            defaults={'message': message[:120], 'notification_type': 'caretaker'},
        )
        return req
    except Exception as e:
        print(f"  ❌ {patient_user.get_full_name()} : {e}")
        return None


def make_schedule(care_request, condition, morning, afternoon, evening):
    if care_request is None:
        return
    if MedicationSchedule.objects.filter(care_request=care_request).exists():
        print(f"  ⏭️  Plan existe : {care_request.patient.get_full_name()}")
        return
    try:
        MedicationSchedule.objects.create(
            care_request=care_request,
            condition=condition,
            medications={'morning': morning, 'afternoon': afternoon, 'evening': evening},
        )
        print(f"  ✅ Plan : {care_request.patient.get_full_name()}")
    except Exception as e:
        print(f"  ❌ Plan : {e}")


# ═══════════════════════════════════════════════════════════════
# 1. NOUVELLES OFFRES DE MISSION (6 patients)
# ═══════════════════════════════════════════════════════════════
print("\n--- Nouveaux patients / Offres de mission ---")

u_amina = make_patient(
    'amina.chentouf@demo.com', 'Amina', 'Chentouf', 'female',
    date(1942, 3, 18), '0770234567', 'DEMO-OFF1-2026-030',
    '22 Rue Didouche Mourad', '16000', 'Alger Centre', 'Alger',
    emg_name='Omar Chentouf (fils)', emg_phone='0555234568',
    blood='A+', weight=55, height=153,
)
add_antecedents(u_amina, [
    ('Diabète type 2', 'personnel', 'chronic'),
    ('Insuffisance rénale chronique stade 3', 'personnel', 'chronic'),
    ('HTA traitée', 'personnel', 'chronic'),
])

u_rachid = make_patient(
    'rachid.benamar@demo.com', 'Rachid', 'Benamar', 'male',
    date(1958, 11, 5), '0661345678', 'DEMO-OFF2-2026-031',
    '7 Cité Mokhtar Zerhouni', '16016', 'Birkhadem', 'Alger',
    emg_name='Salima Benamar (fille)', emg_phone='0770345679',
    blood='B+', weight=88, height=174,
)
add_antecedents(u_rachid, [
    ('Maladie de Parkinson stade 2', 'personnel', 'chronic'),
    ('Dysphagie modérée', 'personnel', 'active'),
    ('Hypertension artérielle', 'personnel', 'chronic'),
])

u_nadia = make_patient(
    'nadia.kermiche@demo.com', 'Nadia', 'Kermiche', 'female',
    date(1975, 6, 22), '0555456789', 'DEMO-OFF3-2026-032',
    '15 Rue Ben M\'hidi', '16200', 'El Harrach', 'Alger',
    emg_name='Yacine Kermiche (mari)', emg_phone='0661456790',
    blood='O+', weight=72, height=162,
)
add_antecedents(u_nadia, [
    ('Sclérose en plaques', 'personnel', 'chronic'),
    ('Fatigue chronique', 'personnel', 'active'),
])

u_mourad = make_patient(
    'mourad.belarbi@demo.com', 'Mourad', 'Belarbi', 'male',
    date(1950, 9, 30), '0770567890', 'DEMO-OFF4-2026-033',
    '3 Impasse des Oliviers', '16100', 'Bachdjarah', 'Alger',
    emg_name='Leila Belarbi (épouse)', emg_phone='0555567891',
    blood='AB+', weight=79, height=169,
)
add_antecedents(u_mourad, [
    ('Fracture col du fémur (post-op)', 'personnel', 'active'),
    ('Ostéoporose', 'personnel', 'chronic'),
    ('Diabète type 2', 'personnel', 'chronic'),
])

u_fatna = make_patient(
    'fatna.ziani@demo.com', 'Fatna', 'Ziani', 'female',
    date(1938, 1, 7), '0661678901', 'DEMO-OFF5-2026-034',
    '9 Rue Larbi Ben M\'hidi', '16300', 'Dar El Beida', 'Alger',
    emg_name='Khaled Ziani (petit-fils)', emg_phone='0770678902',
    blood='O-', weight=48, height=149,
)
add_antecedents(u_fatna, [
    ('Démence sénile (début)', 'personnel', 'active'),
    ('Insuffisance cardiaque légère', 'personnel', 'chronic'),
    ('Cataracte bilatérale opérée', 'personnel', 'resolved'),
])

u_bilal = make_patient(
    'bilal.hammadi@demo.com', 'Bilal', 'Hammadi', 'male',
    date(1990, 4, 14), '0555789012', 'DEMO-OFF6-2026-035',
    '44 Avenue de l\'ALN', '16400', 'Ain Taya', 'Alger',
    emg_name='Sara Hammadi (épouse)', emg_phone='0661789013',
    blood='A-', weight=65, height=178,
)
add_antecedents(u_bilal, [
    ('Paraplégie post-traumatique', 'personnel', 'chronic'),
    ('Escarre stade 1 prévention', 'personnel', 'active'),
    ('Infection urinaire récidivante', 'personnel', 'active'),
])

# Créer les offres
print("\n--- Offres de mission ---")
make_offer(u_amina, 2, 32,
    "Madame Amina Chentouf, 84 ans, diabétique insulinodépendante avec insuffisance rénale. "
    "Besoin d'aide quotidienne : injections insuline matin/soir, surveillance glycémie, "
    "préparation repas sans sel et pauvre en sucre, accompagnement dialyse 3x/semaine. "
    "Présence souhaitée 6h/jour, du lundi au samedi.")

make_offer(u_rachid, 4, 64,
    "Monsieur Rachid Benamar, 68 ans, Parkinson stade 2 avec tremblements et difficulté à avaler. "
    "Soins quotidiens : aide repas (textures adaptées), exercices mobilité, "
    "surveillance médicaments (Levodopa 4x/jour), aide habillage et hygiène. "
    "Présence 8h/jour 6j/7, déplacements médicaux mensuels.")

make_offer(u_nadia, 1, 14,
    "Madame Nadia Kermiche, 51 ans, sclérose en plaques avec fatigue extrême. "
    "Mission temporaire 2 semaines suite à poussée : aide déplacements, "
    "administration traitement Interféron bêta, surveillance constantes. "
    "Disponibilité souhaitée 4h/jour le matin.")

make_offer(u_mourad, 0, 45,
    "Monsieur Mourad Belarbi, 75 ans, retour chirurgie hanche. "
    "Rééducation marche avec déambulateur, soins cicatrice, "
    "surveillance anticoagulants (Clexane), aide vie quotidienne. "
    "Présence 5h/jour, 7j/7 les 2 premières semaines puis 3h/jour.")

make_offer(u_fatna, 0, None,
    "Madame Fatna Ziani, 88 ans, début démence sénile — vit seule depuis 3 mois. "
    "Surveillance quotidienne : pilulier, repas, hygiène, stimulation cognitive légère. "
    "Famille non disponible en semaine. Présence 8h/jour du lundi au vendredi. "
    "Urgence : risque de fugues et oubli des médicaments.")

make_offer(u_bilal, 3, None,
    "Monsieur Bilal Hammadi, 36 ans, paraplégique suite à accident de la route. "
    "Soins spécialisés : prévention escarres (retournements 2h), sondage vésical, "
    "programme rééducation actif-passif membres inférieurs, aide transfert fauteuil. "
    "Mission longue durée — disponibilité 10h/jour idéale.")


# ═══════════════════════════════════════════════════════════════
# 2. NOUVEAUX PLANS DE TRAITEMENT
#    (nécessite des CareRequests acceptées pour ces patients)
# ═══════════════════════════════════════════════════════════════
print("\n--- Plans de traitement supplémentaires ---")

# Créer 2 patients supplémentaires avec demandes ACCEPTÉES
u_zineb = make_patient(
    'zineb.aouf@demo.com', 'Zineb', 'Aouf', 'female',
    date(1962, 8, 11), '0770890123', 'DEMO-OFF7-2026-036',
    '18 Rue Hassiba Ben Bouali', '16000', 'Hussein Dey', 'Alger',
    emg_name='Samir Aouf (mari)', emg_phone='0661890124',
    blood='B-', weight=64, height=160,
)
add_antecedents(u_zineb, [
    ('Hypothyroïdie traitée', 'personnel', 'chronic'),
    ('Anxiété généralisée', 'personnel', 'active'),
    ('Fibromyalgie', 'personnel', 'chronic'),
])

u_omar = make_patient(
    'omar.belkacem@demo.com', 'Omar', 'Belkacem', 'male',
    date(1945, 12, 25), '0555901234', 'DEMO-OFF8-2026-037',
    '6 Cité El Yasmine', '16050', 'Bab Ezzouar', 'Alger',
    emg_name='Yasmine Belkacem (fille)', emg_phone='0770901235',
    blood='A+', weight=70, height=170,
)
add_antecedents(u_omar, [
    ('BPCO sévère (stade 3)', 'personnel', 'chronic'),
    ('Insuffisance respiratoire', 'personnel', 'chronic'),
    ('Tabagisme sevré', 'personnel', 'resolved'),
])

# Créer les demandes acceptées pour Zineb et Omar
def make_accepted(patient_user, start_offset, end_offset, message):
    existing = CareRequest.objects.filter(
        patient=patient_user, caretaker=caretaker, status='accepted'
    ).first()
    if existing:
        print(f"  ⏭️  Demande acceptée existe : {patient_user.get_full_name()}")
        return existing
    try:
        req = CareRequest.objects.create(
            patient=patient_user,
            caretaker=caretaker,
            status='accepted',
            start_date=TODAY + timedelta(days=start_offset),
            end_date=TODAY + timedelta(days=end_offset) if end_offset else None,
            patient_message=message,
        )
        print(f"  ✅ Acceptée : {patient_user.get_full_name()}")
        return req
    except Exception as e:
        print(f"  ❌ {patient_user.get_full_name()} : {e}")
        return None

req_zineb = make_accepted(u_zineb, -3, 27,
    "Zineb Aouf, 63 ans, hypothyroïdie + fibromyalgie. Aide quotidienne médicaments, "
    "surveillance humeur et anxiété, accompagnement sorties thérapeutiques.")

req_omar = make_accepted(u_omar, -7, 53,
    "Omar Belkacem, 80 ans, BPCO sévère sous oxygénothérapie. Surveillance saturation O2, "
    "aérosols 3x/jour, aide mobilité limitée, accompagnement consultations pneumologie.")

# Plans de traitement pour Zineb et Omar
make_schedule(
    req_zineb,
    "Hypothyroïdie + Fibromyalgie + Anxiété",
    morning=[
        {'name': 'Levothyrox 100mcg',    'dose': '1 comprimé', 'note': 'À jeun 30 min avant petit-déjeuner'},
        {'name': 'Paroxétine 20mg',       'dose': '1 comprimé', 'note': 'Avec le repas du matin'},
    ],
    afternoon=[
        {'name': 'Paracétamol 500mg',    'dose': '2 comprimés si douleurs', 'note': 'Max 3g/jour'},
    ],
    evening=[
        {'name': 'Hydroxyzine 25mg',     'dose': '1 comprimé',  'note': 'Pour l\'anxiété et le sommeil'},
        {'name': 'Magnésium Marin 300mg','dose': '1 comprimé',  'note': 'Contre les douleurs musculaires'},
    ],
)

make_schedule(
    req_omar,
    "BPCO stade 3 + Insuffisance respiratoire chronique",
    morning=[
        {'name': 'Tiotropium 18mcg (Spiriva)', 'dose': '1 inhalation', 'note': 'Aérosol — vider les poumons avant'},
        {'name': 'Salbutamol 100mcg',          'dose': '2 bouffées si dyspnée', 'note': 'Bronchodilatateur de secours'},
        {'name': 'Prednisolone 20mg',          'dose': '1 comprimé',  'note': 'Avec repas — cure de 5 jours si exacerbation'},
    ],
    afternoon=[
        {'name': 'Aérosol Combivent',          'dose': '1 nébulisation 15 min', 'note': 'Masque à nébuliseur — surveiller SaO2'},
    ],
    evening=[
        {'name': 'Tiotropium 18mcg (Spiriva)', 'dose': '1 inhalation',  'note': '2ème prise du soir'},
        {'name': 'Fluoxétine 10mg',            'dose': '1 comprimé',    'note': 'Antidépresseur léger — qualité vie'},
        {'name': 'Alprazolam 0.25mg',          'dose': '½ comprimé si anxiété nocturne', 'note': 'Max 0.5mg/j'},
    ],
)

# Plans supplémentaires pour les patients déjà acceptés (Asma et Tarek)
# Vérifier que leurs plans existent et les enrichir si vides
for email, condition, morning, afternoon, evening in [
    (
        'asma.bouchama@demo.com',
        "Arthrose + HTA",
        [
            {'name': 'Amlodipine 5mg',   'dose': '1 cp', 'note': 'Avec un grand verre d\'eau'},
            {'name': 'Paracétamol 1g',   'dose': '1 cp si douleur > 5/10', 'note': ''},
        ],
        [{'name': 'Calcium Sandoz 500mg','dose': '1 cp effervescent', 'note': 'Diluer dans l\'eau'}],
        [
            {'name': 'Paracétamol 1g',      'dose': '1 cp si douleurs', 'note': 'Max 3g/j'},
            {'name': 'Magnésium 300mg',     'dose': '1 cp', 'note': 'Crampes nocturnes'},
        ],
    ),
    (
        'tarek.djilali@demo.com',
        "Séquelles AVC + FA + HTA",
        [
            {'name': 'Aspirine Cardio 100mg','dose': '1 cp', 'note': 'Après petit-déjeuner'},
            {'name': 'Amlodipine 10mg',      'dose': '1 cp', 'note': 'Avec le repas'},
            {'name': 'Ramipril 5mg',         'dose': '1 cp', 'note': 'À jeun ou repas léger'},
        ],
        [{'name': 'Furosémide 40mg', 'dose': '1 cp', 'note': 'Pas après 14h'}],
        [
            {'name': 'Atorvastatine 20mg', 'dose': '1 cp', 'note': 'Le soir — meilleure efficacité'},
            {'name': 'Magnésium B6',       'dose': '1 cp', 'note': 'Prévention crampes'},
        ],
    ),
]:
    try:
        u = User.objects.get(email=email)
        req = CareRequest.objects.filter(patient=u, caretaker=caretaker, status='accepted').first()
        if req and not MedicationSchedule.objects.filter(care_request=req).exists():
            MedicationSchedule.objects.create(
                care_request=req, condition=condition,
                medications={'morning': morning, 'afternoon': afternoon, 'evening': evening},
            )
            print(f"  ✅ Plan créé (rattrapage) : {u.get_full_name()}")
        elif req:
            print(f"  ⏭️  Plan déjà existant : {u.get_full_name()}")
    except User.DoesNotExist:
        pass


# ─── Rapport ──────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("RAPPORT FINAL")
print("=" * 60)
offers_n   = CareRequest.objects.filter(caretaker=caretaker, status='pending').count()
accepted_n = CareRequest.objects.filter(caretaker=caretaker, status='accepted').count()
plans_n    = MedicationSchedule.objects.filter(care_request__caretaker=caretaker).count()
print(f"✅ Offres en attente   : {offers_n}")
print(f"✅ Missions acceptées  : {accepted_n}")
print(f"✅ Plans de traitement : {plans_n}")
print("=" * 60)
print("Script terminé.")
