"""
Remplit les données du garde-malade Fatima Hadj.
Script autonome : crée les patients manquants si nécessaire.
Lancer : python manage.py shell -c "exec(open('scripts/fill_caretaker_data.py', encoding='utf-8').read())"
"""
from datetime import date, timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

from caretaker.models import Caretaker, CaretakerService, CareRequest, CaretakerTask, MedicationSchedule
from notifications.models import Notification

TODAY    = date.today()
PASSWORD = "Demo@2025"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def upsert_patient(email, first_name, last_name, sex, dob, phone,
                   card_number, address, postal_code, city, wilaya,
                   emergency_name="", emergency_phone="",
                   blood_group="", weight=None, height=None):
    if User.objects.filter(email=email).exists():
        u = User.objects.get(email=email)
        # Mettre à jour les champs manquants sur un user existant
        changed = False
        if not u.address and address:
            u.address = address; changed = True
        if not u.phone and phone:
            u.phone = phone; changed = True
        if changed:
            u.save()
        return u
    user = User(
        username=email, email=email, role='patient',
        first_name=first_name, last_name=last_name, sex=sex,
        date_of_birth=dob, phone=phone, id_card_number=card_number,
        address=address, postal_code=postal_code, city=city, wilaya=wilaya,
        verification_status='verified', is_active=True,
    )
    user.set_password(PASSWORD)
    user.save()
    from patients.models import Patient, MedicalProfile
    p = Patient.objects.create(user=user)
    MedicalProfile.objects.create(
        patient=p,
        emergency_contact_name=emergency_name,
        emergency_contact_phone=emergency_phone,
        blood_group=blood_group,
        weight=weight,
        height=height,
    )
    print(f"  ✅ Patient créé : {first_name} {last_name}")
    return user


def add_antecedents(user_email, antecedents_list):
    from patients.models import Patient, Antecedent
    try:
        patient = Patient.objects.get(user__email=user_email)
    except Patient.DoesNotExist:
        return
    for name, atype, status in antecedents_list:
        if not Antecedent.objects.filter(patient=patient, name=name).exists():
            Antecedent.objects.create(
                patient=patient, name=name, type=atype, status=status
            )


def notif(user, title, message, ntype='caretaker'):
    if not Notification.objects.filter(user=user, title=title).exists():
        Notification.objects.create(
            user=user, title=title, message=message, notification_type=ntype
        )


# ─── 1. Récupérer / créer le profil Fatima Hadj ──────────────────────────────
print("=" * 60)
print("GARDE-MALADE — Fatima Hadj")
print("=" * 60)

try:
    u_hadj = User.objects.get(email='fatima.hadj@demo.com')
except User.DoesNotExist:
    print("❌ Compte fatima.hadj@demo.com introuvable. Lancez d'abord create_demo_accounts.py")
    raise SystemExit

try:
    caretaker = u_hadj.caretaker_profile
    print(f"✅ Profil garde-malade trouvé")
except Exception:
    caretaker = Caretaker.objects.create(
        user=u_hadj,
        experience_years=5,
        availability_area='Alger, Blida, Tipaza',
        tarif_de_base=1200.00,
        is_verified=True,
        is_available=True,
        bio=(
            "Garde-malade diplômée avec 5 ans d'expérience en soins à domicile. "
            "Spécialisée dans l'accompagnement des personnes âgées et les soins "
            "post-opératoires. Formée en premiers secours et éducation thérapeutique."
        ),
    )
    print(f"✅ Profil garde-malade créé")


# ─── 2. Services proposés ─────────────────────────────────────────────────────
print("\n--- Services ---")
SERVICES = [
    ("Soins infirmiers à domicile",     1200,
     "Pansements, injections, perfusions, surveillance des constantes vitales."),
    ("Accompagnement médical",           800,
     "Transport et accompagnement aux consultations, examens et hospitalisations."),
    ("Aide à la vie quotidienne",        900,
     "Aide à la toilette, habillage, repas, mobilisation et prévention des chutes."),
    ("Surveillance médicaments",         600,
     "Préparation du pilulier, rappel des prises médicamenteuses, suivi observance."),
    ("Rééducation fonctionnelle légère", 1000,
     "Exercices prescrits par kinésithérapeute, aide à la marche, prévention escarre."),
    ("Garde de nuit",                   1500,
     "Présence nocturne, surveillance, réponse aux urgences nocturnes."),
]
for name, price, desc in SERVICES:
    _, created = CaretakerService.objects.get_or_create(
        caretaker=caretaker, service_name=name,
        defaults={'price_per_hour': price, 'description': desc},
    )
    print(f"  {'✅' if created else '⏭️ '} {name}")


# ─── 3. Patients (créés ici si absents) ───────────────────────────────────────
print("\n--- Patients ---")
u_asma    = upsert_patient(
    'asma.bouchama@demo.com', 'Asma', 'Bouchama', 'female',
    date(1955, 7, 9), '0661112233', 'DEMO-NP9-2026-021',
    '6 Rue Ahmed Bouzrina', '16000', 'Bab El Oued', 'Alger',
    emergency_name='Karima Bouchama (fille)', emergency_phone='0770112244',
    blood_group='A+', weight=68, height=158,
)
u_tarek   = upsert_patient(
    'tarek.djilali@demo.com', 'Tarek', 'Djilali', 'male',
    date(1948, 4, 15), '0555667788', 'DEMO-NP10-2026-022',
    '3 Cité des Fleurs', '16200', 'El Harrach', 'Alger',
    emergency_name='Nadia Djilali (épouse)', emergency_phone='0661778899',
    blood_group='O+', weight=74, height=172,
)
u_hocine  = upsert_patient(
    'hocine.ferhat@demo.com', 'Hocine', 'Ferhat', 'male',
    date(1965, 1, 20), '0555443322', 'DEMO-NP8-2026-020',
    '12 Cité Amara Rachid', '16100', 'Bachdjarah', 'Alger',
    emergency_name='Samira Ferhat (épouse)', emergency_phone='0770443311',
    blood_group='B+', weight=82, height=175,
)
u_meryem  = upsert_patient(
    'meryem.touati@demo.com', 'Meryem', 'Touati', 'female',
    date(1987, 8, 30), '0770556677', 'DEMO-NP7-2026-019',
    "48 Rue de l'Indépendance", '16000', 'Kouba', 'Alger',
    emergency_name='Ahmed Touati (frère)', emergency_phone='0555556688',
    blood_group='A-', weight=61, height=165,
)
u_sofiane = upsert_patient(
    'sofiane.mebarki@demo.com', 'Sofiane', 'Mebarki', 'male',
    date(1971, 3, 14), '0555991100', 'DEMO-NP6-2026-018',
    '5 Impasse des Jasmins', '16300', 'Dar El Beida', 'Alger',
    emergency_name='Fatima Mebarki (mère)', emergency_phone='0660991122',
    blood_group='O-', weight=90, height=178,
)
u_sarah   = User.objects.filter(email='sarah.benali@demo.com').first()
u_karim   = User.objects.filter(email='karim.meziane@demo.com').first()

# Mise à jour des MedicalProfile existants (contacts d'urgence, groupe sanguin)
print("\n--- Mise à jour profils médicaux ---")
from patients.models import Patient, MedicalProfile

MEDICAL_UPDATES = {
    'asma.bouchama@demo.com':   dict(emergency_contact_name='Karima Bouchama (fille)', emergency_contact_phone='0770112244', blood_group='A+', weight=68, height=158),
    'tarek.djilali@demo.com':   dict(emergency_contact_name='Nadia Djilali (épouse)', emergency_contact_phone='0661778899', blood_group='O+', weight=74, height=172),
    'hocine.ferhat@demo.com':   dict(emergency_contact_name='Samira Ferhat (épouse)', emergency_contact_phone='0770443311', blood_group='B+', weight=82, height=175),
    'meryem.touati@demo.com':   dict(emergency_contact_name='Ahmed Touati (frère)', emergency_contact_phone='0555556688', blood_group='A-', weight=61, height=165),
    'sofiane.mebarki@demo.com': dict(emergency_contact_name='Fatima Mebarki (mère)', emergency_contact_phone='0660991122', blood_group='O-', weight=90, height=178),
}
for email, updates in MEDICAL_UPDATES.items():
    try:
        patient = Patient.objects.get(user__email=email)
        mp, _ = MedicalProfile.objects.get_or_create(patient=patient)
        for field, val in updates.items():
            if not getattr(mp, field, None):
                setattr(mp, field, val)
        mp.save()
        print(f"  ✅ {email} — profil médical mis à jour")
    except Patient.DoesNotExist:
        print(f"  ⚠️  Patient introuvable : {email}")

# Antécédents médicaux (apparaissent dans la section "Conditions" du dashboard)
print("\n--- Antécédents ---")
add_antecedents('asma.bouchama@demo.com', [
    ('Hypertension artérielle',        'personnel', 'chronic'),
    ('Arthrose des genoux',            'personnel', 'chronic'),
    ('Ostéoporose',                    'personnel', 'active'),
])
add_antecedents('tarek.djilali@demo.com', [
    ('AVC ischémique (séquelles)',     'personnel', 'chronic'),
    ('Fibrillation auriculaire',       'personnel', 'chronic'),
    ('Hypertension artérielle',        'personnel', 'chronic'),
    ('Diabète type 2',                 'personnel', 'active'),
])
add_antecedents('hocine.ferhat@demo.com', [
    ('Insuffisance cardiaque',         'personnel', 'chronic'),
    ('Dyslipidémie',                   'personnel', 'active'),
])
add_antecedents('meryem.touati@demo.com', [
    ('Appendicectomie (post-op)',      'personnel', 'active'),
    ('Allergie pénicilline',           'personnel', 'chronic'),
])
add_antecedents('sofiane.mebarki@demo.com', [
    ('Hypertension artérielle',        'personnel', 'active'),
    ('Surpoids (IMC 28)',              'personnel', 'active'),
])
print("  ✅ Antécédents ajoutés")


# ─── 4. Demandes de soins ─────────────────────────────────────────────────────
print("\n--- Demandes de soins ---")

def make_request(patient_user, status, start_offset, end_offset, message):
    if patient_user is None:
        return None
    existing = CareRequest.objects.filter(
        patient=patient_user, caretaker=caretaker
    ).first()
    if existing:
        if existing.status != status:
            existing.status = status
            existing.save(update_fields=['status'])
        print(f"  ⏭️  Existe déjà : {patient_user.get_full_name()} ({existing.status})")
        return existing
    try:
        req = CareRequest.objects.create(
            patient=patient_user,
            caretaker=caretaker,
            status=status,
            start_date=TODAY + timedelta(days=start_offset),
            end_date=TODAY + timedelta(days=end_offset) if end_offset is not None else None,
            patient_message=message,
        )
        label = {'accepted':'🟢 acceptée','pending':'🟡 en attente',
                 'completed':'✅ terminée','rejected':'🔴 refusée'}.get(status, status)
        print(f"  ✅ {patient_user.get_full_name():<25} [{label}]")
        return req
    except Exception as e:
        print(f"  ❌ {patient_user.get_full_name()} : {e}")
        return None


# Demandes acceptées (soins en cours — apparaissent dans "mes patients" du dashboard)
req_asma = make_request(
    u_asma, 'accepted', -10, 20,
    "Madame Asma Bouchama, 70 ans, arthrose sévère des genoux et hypertension artérielle. "
    "Besoin d'aide quotidienne pour la toilette (douche assistée), la prise de médicaments "
    "matin et soir, et les déplacements médicaux hebdomadaires. "
    "Présence souhaitée de 8h à 14h, du lundi au samedi."
)
req_tarek = make_request(
    u_tarek, 'accepted', -5, 55,
    "Monsieur Tarek Djilali, 78 ans, séquelles d'AVC ischémique avec hémiplégie partielle droite. "
    "Soins quotidiens requis : aide à la marche avec déambulateur, exercices de rééducation, "
    "surveillance tension artérielle et glycémie matin/soir, préparation des repas adaptés, "
    "accompagnement aux consultations médicales. Disponibilité 8h/jour, 7j/7."
)

# Demandes en attente (nouvelles)
make_request(
    u_hocine, 'pending', 3, 17,
    "Patient insuffisant cardiaque, 61 ans, retour d'hospitalisation prévu dans 3 jours. "
    "Besoin d'aide pour la convalescence : surveillance poids quotidien, "
    "préparation du pilulier hebdomadaire, aide à la mobilisation progressive. "
    "Présence souhaitée 4h/jour le matin."
)
make_request(
    u_meryem, 'pending', 5, 15,
    "Suite à une intervention chirurgicale abdominale, besoin d'aide temporaire : "
    "surveillance de la plaie, changement pansements, aide à la mobilisation, "
    "accompagnement consultation de contrôle J8. Mi-temps suffit."
)
make_request(
    u_sofiane, 'pending', 1, 8,
    "Monsieur Sofiane Mebarki, HTA mal contrôlée après changement de traitement. "
    "Surveillance tension 2x/jour (relevé quotidien), pilulier hebdomadaire, "
    "rappel médicaments. 2 à 3 heures/jour suffisent. Secteur El Harrach."
)

# Demandes terminées (historique)
if u_sarah:
    make_request(
        u_sarah, 'completed', -25, -10,
        "Surveillance post-consultation cardiologie — contrôle tension artérielle 2x/jour "
        "pendant 2 semaines suite à ajustement traitement. Mission accomplie avec succès."
    )
if u_karim:
    make_request(
        u_karim, 'completed', -40, -15,
        "Accompagnement médical et éducation thérapeutique diabète de type 2 sur 25 jours. "
        "Apprentissage autosurveillance glycémique, gestion diététique. "
        "Patient autonome à l'issue de la mission."
    )


# ─── 5. Tâches pour les demandes acceptées ────────────────────────────────────
print("\n--- Tâches ---")

def make_task(care_request, title, description, task_status, due_offset):
    if care_request is None:
        return
    if CaretakerTask.objects.filter(care_request=care_request, title=title).exists():
        print(f"  ⏭️  Tâche existe : {title[:45]}")
        return
    try:
        CaretakerTask.objects.create(
            care_request=care_request,
            title=title,
            description=description,
            status=task_status,
            due_date=TODAY + timedelta(days=due_offset),
        )
        label = {'done':'✅','pending':'🔲','cancelled':'❌'}.get(task_status, '•')
        print(f"  {label} {title[:50]}")
    except Exception as e:
        print(f"  ❌ Tâche {title[:30]} : {e}")


if req_asma:
    make_task(req_asma, "Prise de tension — matin",
              "Mesurer et noter la tension artérielle avant la prise du médicament.", 'done', -1)
    make_task(req_asma, "Aide à la douche",
              "Douche assistée avec siège de bain. Vérifier la température de l'eau.", 'done', -1)
    make_task(req_asma, "Préparation pilulier semaine",
              "Remplir le pilulier 7 jours : Amlodipine matin, Paracétamol si douleurs.", 'done', -2)
    make_task(req_asma, "Prise de tension — matin",
              "Mesurer et noter la tension artérielle avant la prise du médicament.", 'pending', 0)
    make_task(req_asma, "Accompagnement consultation Dr. Khelifi",
              "RDV médecin généraliste — préparer carnet de suivi tension.", 'pending', 3)
    make_task(req_asma, "Exercices mobilisation genou",
              "10 min exercices prescrits par le kiné : flexion/extension assis.", 'pending', 0)
    make_task(req_asma, "Renouvellement ordonnance",
              "Contacter la pharmacie El Shifa pour renouvellement Amlodipine.", 'pending', 5)

if req_tarek:
    make_task(req_tarek, "Séance rééducation marche — matin",
              "20 min marche assistée avec déambulateur dans le couloir.", 'done', -1)
    make_task(req_tarek, "Mesure tension et glycémie",
              "Relevé biquotidien — noter dans le carnet de suivi.", 'done', -1)
    make_task(req_tarek, "Exercices main droite",
              "Exercices de rééducation motricité fine main droite : 15 min.", 'done', 0)
    make_task(req_tarek, "Préparation repas adapté — déjeuner",
              "Repas sans sel, textures adaptées, riche en fibres. Éviter sucres rapides.", 'pending', 0)
    make_task(req_tarek, "Mesure tension et glycémie — soir",
              "Relevé du soir avant dîner. Contacter médecin si tension > 160.", 'pending', 0)
    make_task(req_tarek, "Accompagnement consultation Dr. Bensaid",
              "RDV cardiologie — préparer carnet de suivi et liste médicaments.", 'pending', 7)
    make_task(req_tarek, "Appel famille hebdomadaire",
              "Rapport téléphonique à la famille sur l'évolution du patient.", 'pending', 2)


# ─── 6. Plans médicamenteux ───────────────────────────────────────────────────
print("\n--- Plans médicamenteux ---")

def make_schedule(care_request, condition, morning, afternoon, evening):
    if care_request is None:
        return
    if MedicationSchedule.objects.filter(care_request=care_request).exists():
        print(f"  ⏭️  Plan existe déjà pour {care_request.patient.get_full_name()}")
        return
    try:
        MedicationSchedule.objects.create(
            care_request=care_request,
            condition=condition,
            medications={'morning': morning, 'afternoon': afternoon, 'evening': evening},
        )
        print(f"  ✅ Plan créé : {care_request.patient.get_full_name()} "
              f"({len(morning)}m / {len(afternoon)}am / {len(evening)}s)")
    except Exception as e:
        print(f"  ❌ Plan {care_request.patient.get_full_name()} : {e}")


if req_asma:
    make_schedule(
        req_asma,
        "Arthrose des membres inférieurs + Hypertension artérielle",
        morning=[
            {'name': 'Amlodipine 5mg',     'dose': '1 comprimé', 'note': 'Avec un grand verre d\'eau'},
            {'name': 'Paracétamol 1g',     'dose': '1 comprimé', 'note': 'Si douleurs > 5/10'},
        ],
        afternoon=[
            {'name': 'Calcium Sandoz 500mg','dose': '1 comprimé effervescent', 'note': 'Diluer dans l\'eau'},
        ],
        evening=[
            {'name': 'Paracétamol 1g',     'dose': '1 comprimé', 'note': 'Si douleurs — max 3g/jour'},
            {'name': 'Magnésium Marin 300mg','dose': '1 comprimé','note': 'Pour les crampes nocturnes'},
        ],
    )

if req_tarek:
    make_schedule(
        req_tarek,
        "Séquelles AVC + Fibrillation auriculaire + HTA",
        morning=[
            {'name': 'Aspirine Cardio 100mg','dose': '1 comprimé', 'note': 'Après le petit-déjeuner'},
            {'name': 'Amlodipine 10mg',      'dose': '1 comprimé', 'note': 'Avec le repas'},
            {'name': 'Ramipril 5mg',         'dose': '1 comprimé', 'note': 'À jeun ou avec repas léger'},
        ],
        afternoon=[
            {'name': 'Furosémide 40mg',      'dose': '1 comprimé', 'note': 'Pas après 14h (éviter nycturie)'},
        ],
        evening=[
            {'name': 'Atorvastatine 20mg',   'dose': '1 comprimé', 'note': 'Le soir — meilleure efficacité'},
            {'name': 'Magnésium B6',         'dose': '1 comprimé', 'note': 'Pour prévenir crampes'},
        ],
    )


# ─── 7. Notifications ─────────────────────────────────────────────────────────
print("\n--- Notifications ---")

notif(u_hadj, "Nouvelle demande — Hocine Ferhat",
      f"Hocine Ferhat demande une aide soins post-hospitalisation "
      f"à partir du {(TODAY + timedelta(days=3)).strftime('%d/%m/%Y')}.", 'caretaker')
notif(u_hadj, "Nouvelle demande — Meryem Touati",
      f"Meryem Touati recherche une aide soins post-opératoires "
      f"à partir du {(TODAY + timedelta(days=5)).strftime('%d/%m/%Y')}.", 'caretaker')
notif(u_hadj, "Nouvelle demande — Sofiane Mebarki",
      "Sofiane Mebarki demande surveillance tension et pilulier — secteur El Harrach.", 'caretaker')
notif(u_hadj, "Rappel mission — Asma Bouchama",
      f"Mission en cours chez Asma Bouchama jusqu'au "
      f"{(TODAY + timedelta(days=20)).strftime('%d/%m/%Y')}.", 'caretaker')
notif(u_hadj, "Rappel mission — Tarek Djilali",
      f"Mission longue durée chez Tarek Djilali (AVC) jusqu'au "
      f"{(TODAY + timedelta(days=55)).strftime('%d/%m/%Y')}.", 'caretaker')

if u_asma:
    notif(u_asma, "Demande acceptée — Fatima Hadj",
          "Fatima Hadj a accepté votre demande. Elle interviendra à domicile à partir d'aujourd'hui.",
          'caretaker')
if u_tarek:
    notif(u_tarek, "Demande acceptée — Fatima Hadj",
          "Fatima Hadj a accepté votre demande de prise en charge à domicile.",
          'caretaker')

print(f"  ✅ Notifications créées")


# ─── Rapport ──────────────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print("RAPPORT — Fatima Hadj")
print("=" * 60)

svc_n  = CaretakerService.objects.filter(caretaker=caretaker).count()
req_n  = CareRequest.objects.filter(caretaker=caretaker).count()
task_n = CaretakerTask.objects.filter(care_request__caretaker=caretaker).count()
sched_n = MedicationSchedule.objects.filter(care_request__caretaker=caretaker).count()
notif_n = Notification.objects.filter(user=u_hadj).count()

print(f"✅ Services            : {svc_n}")
print(f"✅ Demandes de soins   : {req_n}")
for s in ['accepted', 'pending', 'completed']:
    n = CareRequest.objects.filter(caretaker=caretaker, status=s).count()
    label = {'accepted':'🟢 en cours','pending':'🟡 en attente','completed':'✅ terminées'}[s]
    if n: print(f"   {label:<22} : {n}")
print(f"✅ Tâches              : {task_n}")
print(f"✅ Plans médicamenteux : {sched_n}")
print(f"✅ Notifications       : {notif_n}")
print("=" * 60)
print("Script terminé.")
