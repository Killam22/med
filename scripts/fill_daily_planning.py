"""
Remplit le planning du jour, les commandes pharmacie et les demandes garde-malade.
Lancer : python manage.py shell -c "exec(open('scripts/fill_daily_planning.py', encoding='utf-8').read())"
"""
import json
from datetime import date, time, datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

from patients.models import Patient, MedicalProfile, Allergy, Antecedent
from doctors.models import Doctor
from appointments.models import Appointment
from consultations.models import Consultation
from prescriptions.models import Prescription, PrescriptionItem
from pharmacy.models import Pharmacist, PharmacyOrder
from caretaker.models import Caretaker
from notifications.models import Notification

PASSWORD  = "Demo@2025"
TODAY     = date.today()


def make_dt(y, m, d, h, mn=0):
    return timezone.make_aware(datetime(y, m, d, h, mn))

def today_dt(h, mn=0):
    return timezone.make_aware(datetime(TODAY.year, TODAY.month, TODAY.day, h, mn))


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def create_patient(email, first_name, last_name, sex, dob, phone,
                   card_number, address, postal_code, city, wilaya):
    if User.objects.filter(email=email).exists():
        return User.objects.get(email=email), False
    try:
        user = User(
            username=email, email=email, role='patient',
            first_name=first_name, last_name=last_name, sex=sex,
            date_of_birth=dob, phone=phone, id_card_number=card_number,
            address=address, postal_code=postal_code, city=city, wilaya=wilaya,
            verification_status='verified', is_active=True,
        )
        user.set_password(PASSWORD)
        user.save()
        print(f"✅ Patient créé : {first_name} {last_name}")
        return user, True
    except Exception as e:
        print(f"❌ {email} : {e}")
        return None, False


def get_patient(user):
    try:
        return user.patient_profile
    except Exception:
        return Patient.objects.create(user=user)


def make_profile(patient, weight, height, blood_group, ec_name, ec_phone):
    try:
        patient.medical_profile
    except Exception:
        MedicalProfile.objects.create(
            patient=patient, weight=weight, height=height, blood_group=blood_group,
            emergency_contact_name=ec_name, emergency_contact_phone=ec_phone,
        )


def rdv(patient, doctor, rdv_date, sh, sm, eh, em, motif, status):
    existing = Appointment.objects.filter(
        doctor=doctor, date=rdv_date, start_time=time(sh, sm)
    ).first()
    if existing:
        return existing
    try:
        return Appointment.objects.create(
            patient=patient, doctor=doctor, date=rdv_date,
            start_time=time(sh, sm), end_time=time(eh, em),
            motif=motif, status=status,
        )
    except Exception as e:
        print(f"  ❌ RDV {sh}h{sm:02d} : {e}")
        return None


def consult(appt, doctor, patient, complaint, diagnosis, plan, notes, vitals_dict, h, mn=0, status='completed'):
    try:
        c = appt.consultation
        return c
    except Exception:
        pass
    try:
        return Consultation.objects.create(
            doctor=doctor, patient=patient, appointment=appt,
            consultation_type='in_person', status=status,
            chief_complaint=complaint, diagnosis=diagnosis,
            treatment_plan=plan, doctor_notes=notes,
            vitals=json.dumps(vitals_dict, ensure_ascii=False),
            consulted_at=today_dt(h, mn),
        )
    except Exception as e:
        print(f"  ❌ Consultation : {e}")
        return None


def presc(consultation, items):
    if not consultation:
        return None
    if consultation.prescriptions.exists():
        return consultation.prescriptions.first()
    try:
        p = Prescription.objects.create(
            consultation=consultation, status='active',
            valid_until=date(2026, 12, 31),
        )
        for item in items:
            PrescriptionItem.objects.create(prescription=p, **item)
        return p
    except Exception as e:
        print(f"  ❌ Ordonnance : {e}")
        return None


def notif(user, title, message, ntype):
    if not Notification.objects.filter(user=user, title=title).exists():
        Notification.objects.create(user=user, title=title, message=message, notification_type=ntype)


# ═══════════════════════════════════════════════════════════════════════════════
#  NOUVEAUX PATIENTS COMMUNS
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("NOUVEAUX PATIENTS")
print("=" * 60)

# — Pour Dr. Khelifi (médecine générale) —
u_farid, _   = create_patient('farid.bouzid@demo.com',   'Farid',   'Bouzid',   'male',   date(1990, 5, 12), '0555778899', 'DEMO-NP1-2026-013', '14 Rue Didouche Mourad',       '16000', 'Alger Centre', 'Alger')
u_zineb, _   = create_patient('zineb.mokhtar@demo.com',  'Zineb',   'Mokhtar',  'female', date(1998, 9, 3),  '0661445566', 'DEMO-NP2-2026-014', '7 Rue des Frères Mekideche',   '16000', 'Bab Ezzouar',  'Alger')
u_rachid, _  = create_patient('rachid.amrani@demo.com',  'Rachid',  'Amrani',   'male',   date(1975, 2, 18), '0770334455', 'DEMO-NP3-2026-015', '33 Boulevard Krim Belkacem',   '16100', 'El Harrach',   'Alger')

# — Pour Dr. Bensaid (cardiologie) —
u_djamel, _  = create_patient('djamel.aouf@demo.com',    'Djamel',  'Aouf',     'male',   date(1962, 11, 7), '0555223311', 'DEMO-NP4-2026-016', '9 Cité Diar El Mahçoul',       '16200', 'El Harrach',   'Alger')
u_rania, _   = create_patient('rania.larbi@demo.com',    'Rania',   'Larbi',    'female', date(1980, 6, 25), '0661778822', 'DEMO-NP5-2026-017', '21 Rue Abderrahmane Mira',     '16000', 'Alger Centre', 'Alger')
u_sofiane, _ = create_patient('sofiane.mebarki@demo.com','Sofiane', 'Mebarki',  'male',   date(1971, 3, 14), '0555991100', 'DEMO-NP6-2026-018', '5 Impasse des Jasmins',        '16300', 'Dar El Beida', 'Alger')
u_meryem, _  = create_patient('meryem.touati@demo.com',  'Meryem',  'Touati',   'female', date(1987, 8, 30), '0770556677', 'DEMO-NP7-2026-019', '48 Rue de l\'Indépendance',    '16000', 'Kouba',        'Alger')
u_hocine, _  = create_patient('hocine.ferhat@demo.com',  'Hocine',  'Ferhat',   'male',   date(1965, 1, 20), '0555443322', 'DEMO-NP8-2026-020', '12 Cité Amara Rachid',         '16100', 'Bachdjarah',   'Alger')

# — Pour pharmacie + garde-malade —
u_asma, _    = create_patient('asma.bouchama@demo.com',  'Asma',    'Bouchama', 'female', date(1955, 7, 9),  '0661112233', 'DEMO-NP9-2026-021', '6 Rue Ahmed Bouzrina',         '16000', 'Bab El Oued',  'Alger')
u_tarek, _   = create_patient('tarek.djilali@demo.com',  'Tarek',   'Djilali',  'male',   date(1948, 4, 15), '0555667788', 'DEMO-NP10-2026-022','3 Cité des Fleurs',             '16200', 'El Harrach',   'Alger')

# Profils médicaux
patients_info = [
    (u_farid,   67, 174, 'O+',  'Karima Bouzid',   '0555778800'),
    (u_zineb,   52, 160, 'A+',  'Ali Mokhtar',     '0661445500'),
    (u_rachid,  82, 177, 'B+',  'Nora Amrani',     '0770334400'),
    (u_djamel,  92, 172, 'AB-', 'Houria Aouf',     '0555223300'),
    (u_rania,   61, 164, 'O+',  'Kamel Larbi',     '0661778800'),
    (u_sofiane, 88, 179, 'A+',  'Djamila Mebarki', '0555991199'),
    (u_meryem,  58, 161, 'B-',  'Samir Touati',    '0770556600'),
    (u_hocine,  79, 168, 'O-',  'Meriem Ferhat',   '0555443300'),
    (u_asma,    65, 155, 'A-',  'Yacine Bouchama', '0661112200'),
    (u_tarek,   71, 170, 'O+',  'Naima Djilali',   '0555667700'),
]
for u, w, h, bg, ec_n, ec_p in patients_info:
    if u:
        p = get_patient(u)
        make_profile(p, w, h, bg, ec_n, ec_p)

# Antécédents spécifiques
for u, antec in [
    (u_djamel,  [('Coronaropathie', 'chronic', date(2018, 3, 1)), ('Tabagisme sevré', 'resolved', date(2020, 1, 1))]),
    (u_sofiane, [('Hypertension artérielle', 'chronic', date(2016, 5, 1))]),
    (u_hocine,  [('Insuffisance cardiaque légère', 'chronic', date(2021, 9, 1)), ('Diabète de type 2', 'chronic', date(2014, 2, 1))]),
    (u_asma,    [('Arthrose', 'chronic', date(2015, 6, 1)), ('Hypertension artérielle', 'chronic', date(2012, 3, 1))]),
    (u_tarek,   [('AVC ischémique', 'resolved', date(2022, 7, 1)), ('Fibrillation auriculaire', 'chronic', date(2019, 11, 1))]),
]:
    if u:
        p = get_patient(u)
        for name, status, dd in antec:
            Antecedent.objects.get_or_create(
                patient=p, name=name,
                defaults={'type': 'personnel', 'status': status, 'date_diagnosis': dd},
            )


# ═══════════════════════════════════════════════════════════════════════════════
#  PLANNING DU JOUR — DR. AMINA KHELIFI
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"PLANNING DU JOUR — Dr. Khelifi ({TODAY.strftime('%d/%m/%Y')})")
print("=" * 60)

try:
    doc_khelifi = Doctor.objects.get(user__email='dr.amina.khelifi@demo.com')

    slots_khelifi = [
        # (patient_user, sh, sm, eh, em, motif, status)
        (u_farid,   8,  0,  8, 30, 'Toux persistante et fièvre légère',      'completed'),
        (u_zineb,   8, 30,  9,  0, 'Douleurs abdominales et nausées',         'completed'),
        (u_rachid,  9,  0,  9, 30, 'Renouvellement ordonnance hypertension',  'completed'),
        (u_asma,    9, 30, 10,  0, 'Douleurs articulaires — suivi arthrose',  'in_progress'),
        (u_meryem, 10,  0, 10, 30, 'Consultation générale',                   'confirmed'),
        (u_zineb,  10, 30, 11,  0, 'Résultats analyses sanguines',            'confirmed'),
    ]
    # Récupérer patients Khelifi existants
    p_nadia   = Patient.objects.get(user__email='nadia.bouafia@demo.com')   if User.objects.filter(email='nadia.bouafia@demo.com').exists()   else None
    p_omar    = Patient.objects.get(user__email='omar.taleb@demo.com')      if User.objects.filter(email='omar.taleb@demo.com').exists()      else None
    p_samira  = Patient.objects.get(user__email='samira.hadjali@demo.com')  if User.objects.filter(email='samira.hadjali@demo.com').exists()  else None
    p_youcef  = Patient.objects.get(user__email='youcef.belkacem@demo.com') if User.objects.filter(email='youcef.belkacem@demo.com').exists() else None

    if p_nadia:
        slots_khelifi.append((u_nadia := User.objects.get(email='nadia.bouafia@demo.com'),  11,  0, 11, 30, 'Suivi rhinite — résultats allergo',     'confirmed'))
    if p_omar:
        slots_khelifi.append((User.objects.get(email='omar.taleb@demo.com'),    11, 30, 12,  0, 'Renouvellement ordonnance Metformine',   'confirmed'))
    if p_samira:
        slots_khelifi.append((User.objects.get(email='samira.hadjali@demo.com'), 14,  0, 14, 30, 'Suivi anxiété et troubles du sommeil',   'confirmed'))
    if p_youcef:
        slots_khelifi.append((User.objects.get(email='youcef.belkacem@demo.com'),14, 30, 15,  0, 'Résultats bilan lipidique',              'confirmed'))

    slots_khelifi += [
        (u_rachid, 15,  0, 15, 30, 'Certificat médical',                     'confirmed'),
        (u_tarek,  15, 30, 16,  0, 'Suivi post-AVC — bilan général',         'confirmed'),
    ]

    created_rdvs_k = {}
    for u_pat, sh, sm, eh, em, motif, status in slots_khelifi:
        if u_pat is None:
            continue
        p = get_patient(u_pat)
        r = rdv(p, doc_khelifi, TODAY, sh, sm, eh, em, motif, status)
        if r:
            created_rdvs_k[f"{sh}:{sm:02d}"] = (r, p, status)
            print(f"  {'✅' if status == 'completed' else '🔵' if status == 'in_progress' else '📅'} {sh}h{sm:02d} — {u_pat.get_full_name()} ({status})")

    # Consultations pour les créneaux terminés / en cours
    consult_data_k = {
        "8:00":  ("Toux sèche depuis 5 jours, fièvre 37.8°C",
                  "Rhinopharyngite aiguë virale",
                  "Repos, antihistaminiques, paracétamol si besoin. Revenir si pas d'amélioration sous 5j.",
                  "Gorge légèrement érythémateuse. Pas de surinfection.",
                  {'bp': '115/72', 'hr': 84, 'temp': 37.8, 'spo2': 98},
                  [{'drug_name': 'Paracétamol', 'dosage': '1g',    'frequency': '3x_day',  'duration': '5 jours', 'quantity': 15},
                   {'drug_name': 'Rhinofluimucil','dosage': 'spray','frequency': '3x_day',  'duration': '5 jours', 'quantity': 1}]),
        "8:30":  ("Douleurs épigastriques, nausées post-prandiales depuis 3 jours",
                  "Gastrite aiguë",
                  "Inhibiteur de pompe à protons, régime doux. Éviter AINS et alcool.",
                  "Abdomen souple. Douleur à la palpation épigastrique. Pas de défense.",
                  {'bp': '110/68', 'hr': 78, 'temp': 36.9, 'spo2': 99},
                  [{'drug_name': 'Oméprazole', 'dosage': '20mg', 'frequency': '1x_day', 'duration': '14 jours', 'quantity': 14},
                   {'drug_name': 'Spasfon',    'dosage': '80mg', 'frequency': '3x_day', 'duration': '5 jours',  'quantity': 15}]),
        "9:00":  ("Renouvellement traitement HTA — tension bien contrôlée ce mois",
                  "Hypertension artérielle équilibrée",
                  "Renouvellement ordonnance. Continuer Amlodipine. Prochain contrôle dans 3 mois.",
                  "Tension 128/82 à la consultation. Patient observant son traitement.",
                  {'bp': '128/82', 'hr': 68, 'temp': 36.6, 'spo2': 98},
                  [{'drug_name': 'Amlodipine', 'dosage': '5mg', 'frequency': '1x_day', 'duration': '90 jours', 'quantity': 90}]),
        "9:30":  ("Douleurs articulaires des genoux et hanches, raideur matinale",
                  "Arthrose modérée des membres inférieurs",
                  "Anti-inflammatoires locaux, kinésithérapie 10 séances. Perte de poids recommandée.",
                  "En cours d'examen. Mobilité réduite genou droit.",
                  {'bp': '142/88', 'hr': 76, 'temp': 36.7, 'spo2': 97},
                  [{'drug_name': 'Voltarène gel', 'dosage': 'application locale', 'frequency': '2x_day', 'duration': '15 jours', 'quantity': 1},
                   {'drug_name': 'Paracétamol',   'dosage': '1g',                'frequency': '2x_day', 'duration': '10 jours', 'quantity': 20}]),
    }

    for slot_key, (complaint, diagnosis, plan, notes, vitals, items) in consult_data_k.items():
        if slot_key in created_rdvs_k:
            r, p, status = created_rdvs_k[slot_key]
            c_status = 'in_progress' if status == 'in_progress' else 'completed'
            h, m = map(int, slot_key.split(':'))
            c = consult(r, doc_khelifi, p, complaint, diagnosis, plan, notes, vitals, h, m, c_status)
            if c and items:
                presc(c, items)

except Exception as e:
    print(f"❌ Erreur planning Khelifi : {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
#  PLANNING DU JOUR — DR. YACINE BENSAID
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"PLANNING DU JOUR — Dr. Bensaid ({TODAY.strftime('%d/%m/%Y')})")
print("=" * 60)

try:
    doc_bensaid = Doctor.objects.get(user__email='dr.yacine.bensaid@demo.com')
    p_karim     = Patient.objects.get(user__email='karim.meziane@demo.com')

    slots_bensaid = [
        (u_djamel,  8,  0,  8, 30, 'Douleurs thoraciques — bilan cardiaque',         'completed'),
        (u_hocine,  8, 30,  9,  0, 'Suivi insuffisance cardiaque — bilan mensuel',   'completed'),
        (u_sofiane, 9,  0,  9, 30, 'Contrôle tension et ajustement traitement',      'completed'),
        (u_rania,   9, 30, 10,  0, 'Palpitations et essoufflements à l\'effort',     'in_progress'),
        (User.objects.get(email='karim.meziane@demo.com'), 10, 0, 10, 30, 'Bilan cardio annuel — suivi DT2', 'confirmed'),
        (u_tarek,  10, 30, 11,  0, 'Suivi FA — renouvellement anticoagulant',        'confirmed'),
        (u_meryem, 11,  0, 11, 30, 'Douleurs précordiales — ECG de contrôle',        'confirmed'),
        (u_farid,  11, 30, 12,  0, 'Bilan cardiovasculaire préventif',               'confirmed'),
        (u_djamel, 14,  0, 14, 30, 'Résultats coronarographie',                      'confirmed'),
        (u_sofiane,14, 30, 15,  0, 'Renouvellement ordonnance HTA + bilan rénal',   'confirmed'),
        (u_hocine, 15,  0, 15, 30, 'Suivi IC — contrôle diurétiques',               'confirmed'),
        (u_rania,  15, 30, 16,  0, 'Résultats Holter ECG',                          'confirmed'),
    ]

    created_rdvs_b = {}
    for u_pat, sh, sm, eh, em, motif, status in slots_bensaid:
        if u_pat is None:
            continue
        p = get_patient(u_pat)
        r = rdv(p, doc_bensaid, TODAY, sh, sm, eh, em, motif, status)
        if r:
            created_rdvs_b[f"{sh}:{sm:02d}"] = (r, p, status)
            print(f"  {'✅' if status == 'completed' else '🔵' if status == 'in_progress' else '📅'} {sh}h{sm:02d} — {u_pat.get_full_name()} ({status})")

    consult_data_b = {
        "8:00":  ("Douleurs thoraciques oppressantes depuis 2 jours, irradiation épaule gauche",
                  "Angor stable — coronaropathie connue",
                  "Ajustement traitement anti-angineux. Repos strict. Éviter efforts. Nitré sublingual si crise.",
                  "ECG : dépression ST légère en V4-V6. Pas de sus-décalage. Troponine normale.",
                  {'bp': '150/95', 'hr': 82, 'temp': 36.8, 'spo2': 96},
                  [{'drug_name': 'Trinitrine spray',  'dosage': '0.3mg',  'frequency': 'as_needed', 'duration': '30 jours', 'quantity': 1},
                   {'drug_name': 'Aspirine',          'dosage': '100mg',  'frequency': '1x_day',    'duration': '90 jours', 'quantity': 90},
                   {'drug_name': 'Aténolol',          'dosage': '50mg',   'frequency': '1x_day',    'duration': '30 jours', 'quantity': 30}]),
        "8:30":  ("Bilan mensuel insuffisance cardiaque — dyspnée d'effort stable",
                  "Insuffisance cardiaque légère compensée",
                  "Continuer diurétiques. Restriction hydrosodée. Peser chaque matin.",
                  "FC 78. Pas d'œdèmes des membres inférieurs. Poumons clairs. Poids stable.",
                  {'bp': '124/78', 'hr': 78, 'temp': 36.6, 'spo2': 97},
                  [{'drug_name': 'Furosémide',   'dosage': '40mg',  'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
                   {'drug_name': 'Ramipril',     'dosage': '5mg',   'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
                   {'drug_name': 'Spironolactone','dosage': '25mg', 'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30}]),
        "9:00":  ("Tension mal contrôlée à domicile malgré traitement",
                  "HTA résistante — ajustement thérapeutique",
                  "Ajout Losartan. Vérifier observance. Éviter sel. Reprise activité physique douce.",
                  "Tension 158/96 à l'arrivée, 142/88 après repos. Fond d'œil normal.",
                  {'bp': '142/88', 'hr': 74, 'temp': 36.7, 'spo2': 98},
                  [{'drug_name': 'Amlodipine', 'dosage': '10mg', 'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
                   {'drug_name': 'Losartan',   'dosage': '50mg', 'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30}]),
        "9:30":  ("Palpitations irrégulières, essoufflements à la montée des escaliers",
                  "Exploration en cours — suspicion arythmie",
                  "Holter ECG 24h prescrit. Éviter café, alcool. Bilan thyroïdien demandé.",
                  "Examen en cours. FC irrégulière 88 bpm. ECG : extrasystoles supra-ventriculaires.",
                  {'bp': '132/84', 'hr': 88, 'temp': 36.5, 'spo2': 98},
                  []),
    }

    for slot_key, (complaint, diagnosis, plan, notes, vitals, items) in consult_data_b.items():
        if slot_key in created_rdvs_b:
            r, p, status = created_rdvs_b[slot_key]
            c_status = 'in_progress' if status == 'in_progress' else 'completed'
            h, m = map(int, slot_key.split(':'))
            c = consult(r, doc_bensaid, p, complaint, diagnosis, plan, notes, vitals, h, m, c_status)
            if c and items:
                presc(c, items)

except Exception as e:
    print(f"❌ Erreur planning Bensaid : {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMANDES PHARMACIE — El Shifa
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("COMMANDES PHARMACIE — El Shifa")
print("=" * 60)

try:
    u_pharmacie = User.objects.get(email='pharmacie.elshifa@demo.com')
    pharmacist  = u_pharmacie.pharmacist_profile

    def pharmacy_order(patient_user, prescription_obj, status, order_type,
                        patient_msg, pharmacist_note, total=0):
        existing = PharmacyOrder.objects.filter(
            patient=patient_user, status=status,
            prescription=prescription_obj,
        ).first()
        if existing:
            print(f"  ⏭️  Commande existe : {patient_user.get_full_name()} ({status})")
            return
        try:
            PharmacyOrder.objects.create(
                patient=patient_user,
                prescription=prescription_obj,
                pharmacist=u_pharmacie,
                order_type=order_type,
                withdrawal_method='patient',
                status=status,
                patient_message=patient_msg,
                pharmacist_note=pharmacist_note,
                total_price=total,
            )
            print(f"  ✅ Commande [{status}] : {patient_user.get_full_name()}")
        except Exception as e:
            print(f"  ❌ Erreur commande {patient_user.get_full_name()} : {e}")

    # Récupérer des ordonnances existantes
    def get_presc(email):
        try:
            return Prescription.objects.filter(
                consultation__patient__user__email=email
            ).first()
        except Exception:
            return None

    presc_nadia   = get_presc('nadia.bouafia@demo.com')
    presc_omar    = get_presc('omar.taleb@demo.com')
    presc_karim   = get_presc('karim.meziane@demo.com')

    # Ordonnances des consultations du jour
    def get_today_presc(doctor, slot_key):
        existing = Appointment.objects.filter(
            doctor=doctor, date=TODAY,
            start_time=time(*map(int, slot_key.split(':')))
        ).first()
        if existing and hasattr(existing, 'consultation'):
            return existing.consultation.prescriptions.first()
        return None

    presc_farid   = get_today_presc(doc_khelifi, "8:00")
    presc_zineb   = get_today_presc(doc_khelifi, "8:30")
    presc_djamel  = get_today_presc(doc_bensaid, "8:00")
    presc_hocine  = get_today_presc(doc_bensaid, "8:30")
    presc_sofiane = get_today_presc(doc_bensaid, "9:00")

    u_sarah  = User.objects.get(email='sarah.benali@demo.com')
    u_karim  = User.objects.get(email='karim.meziane@demo.com')
    u_nadia  = User.objects.get(email='nadia.bouafia@demo.com')  if User.objects.filter(email='nadia.bouafia@demo.com').exists()  else None
    u_omar   = User.objects.get(email='omar.taleb@demo.com')     if User.objects.filter(email='omar.taleb@demo.com').exists()     else None

    # Commandes avec statuts variés
    orders = [
        # PENDING — en attente de traitement
        (u_farid,   presc_farid,   'pending',   'prescription',
         "Bonjour, je viens déposer mon ordonnance pour la toux.",
         "", 0),
        (u_zineb,   presc_zineb,   'pending',   'prescription',
         "Ordonnance gastrite — médicaments urgents s'il vous plaît.",
         "", 0),
        (u_asma,    None,          'pending',   'direct',
         "Besoin de Voltarène gel et d'une pommade pour les articulations.",
         "", 850),

        # PREPARING — en préparation
        (u_djamel,  presc_djamel,  'preparing', 'prescription',
         "Ordonnance cardiologie — médicaments habituels.",
         "Trinitrine et Aspirine en stock. Aténolol en commande fournisseur.", 3200),
        (u_nadia,   presc_nadia,   'preparing', 'prescription',
         "Médicaments pour la rhinopharyngite.",
         "Rhinofluimucil disponible. Préparation en cours.", 1100),

        # READY — prête à retirer
        (u_hocine,  presc_hocine,  'ready',     'prescription',
         "Renouvellement mensuel traitement cardiaque.",
         "Furosémide, Ramipril et Spironolactone disponibles. Commande complète.", 4500),
        (u_omar,    presc_omar,    'ready',     'prescription',
         "Renouvellement Metformine pour 3 mois.",
         "Metformine 1000mg disponible. Boîtes de 3 mois préparées.", 2800),
        (u_sofiane, presc_sofiane, 'ready',     'prescription',
         "Amlodipine et Losartan — traitement HTA.",
         "Stock complet. Ordonnance vérifiée. Prêt.", 2100),

        # DELIVERED — livrée
        (u_karim,   presc_karim,   'delivered', 'prescription',
         "Bilan diabète — renouvellement Metformine.",
         "Livré le matin. Explication posologie fournie.", 3600),
        (u_tarek,   None,          'delivered', 'direct',
         "Achat direct — bandelettes glycémiques et tensiomètre.",
         "Matériel médical livré. Facture remise.", 7200),
    ]

    for args in orders:
        pharmacy_order(*args)

except Exception as e:
    print(f"❌ Erreur commandes pharmacie : {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
#  DEMANDES GARDE-MALADE — Fatima Hadj
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("DEMANDES GARDE-MALADE — Fatima Hadj")
print("=" * 60)

try:
    from caretaker.models import CareRequest

    u_hadj    = User.objects.get(email='fatima.hadj@demo.com')
    caretaker = u_hadj.caretaker_profile

    def care_request(patient_user, status, start_days, end_days, message):
        existing = CareRequest.objects.filter(
            patient=patient_user, caretaker=caretaker, status=status
        ).first()
        if existing:
            print(f"  ⏭️  Demande existe : {patient_user.get_full_name()} ({status})")
            return
        try:
            CareRequest.objects.create(
                patient=patient_user,
                caretaker=caretaker,
                status=status,
                start_date=TODAY + timedelta(days=start_days),
                end_date=TODAY + timedelta(days=end_days) if end_days else None,
                patient_message=message,
            )
            print(f"  ✅ Demande [{status}] : {patient_user.get_full_name()}")
        except Exception as e:
            print(f"  ❌ Erreur demande {patient_user.get_full_name()} : {e}")

    u_sarah = User.objects.get(email='sarah.benali@demo.com')
    u_karim = User.objects.get(email='karim.meziane@demo.com')

    care_requests = [
        # ACCEPTED — soins en cours
        (u_asma,   'accepted', 0, 30,
         "Madame Asma Bouchama, 70 ans, arthrose sévère et hypertension. "
         "Aide quotidienne pour la toilette, la prise de médicaments (matin/soir) "
         "et les déplacements médicaux. Présence 6h/jour, du lundi au samedi."),
        (u_tarek,  'accepted', 0, 60,
         "Monsieur Tarek Djilali, 78 ans, séquelles d'AVC avec hémiplégie partielle droite. "
         "Soins quotidiens : aide à la marche, exercices de rééducation prescrits, "
         "surveillance tension et glycémie, accompagnement médical. 8h/jour."),

        # PENDING — nouvelles demandes
        (u_hocine, 'pending', 3, 14,
         "Patient insuffisant cardiaque, 61 ans. Besoin d'aide après hospitalisation. "
         "Surveillance poids quotidien, prise médicaments, aide à la mobilisation. "
         "Disponibilité requise : 4h/jour, matin de préférence."),
        (u_meryem, 'pending', 5, 10,
         "Jeune femme ayant eu une opération, besoin d'aide temporaire pour les soins "
         "post-opératoires, pansements et accompagnement aux rendez-vous médicaux."),
        (u_sofiane,'pending', 1, 7,
         "Patient HTA mal contrôlée. Demande surveillance tension 2x/jour, "
         "préparation pilulier hebdomadaire, et rappel médicaments. Mi-temps suffisant."),

        # COMPLETED — terminées
        (u_sarah,  'completed', -20, -5,
         "Suite consultation cardiologie — surveillance tension post-ajustement traitement. "
         "Mission terminée avec succès. Patient bien orienté."),
        (u_karim,  'completed', -30, -10,
         "Accompagnement médical et aide à la gestion du diabète. "
         "Éducation thérapeutique réalisée. Patient autonome désormais."),
    ]

    for args in care_requests:
        care_request(*args)

    # Notifications pour Fatima Hadj
    notifs_hadj = [
        ("Nouvelle demande de soins — Hocine Ferhat",
         "Hocine Ferhat a soumis une demande de soins post-hospitalisation pour 14 jours.",
         'caretaker'),
        ("Nouvelle demande de soins — Meryem Touati",
         "Meryem Touati recherche une aide pour soins post-opératoires (10 jours).",
         'caretaker'),
        ("Nouvelle demande de soins — Sofiane Mebarki",
         "Sofiane Mebarki demande une surveillance tension et pilulier pour 7 jours.",
         'caretaker'),
    ]
    for title, msg, ntype in notifs_hadj:
        notif(u_hadj, title, msg, ntype)
        print(f"  ✅ Notification : {title[:55]}")

except Exception as e:
    print(f"❌ Erreur garde-malade : {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════════
#  RAPPORT FINAL
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print("RAPPORT FINAL")
print("=" * 60)

try:
    rdv_k_today = Appointment.objects.filter(doctor__user__email='dr.amina.khelifi@demo.com',  date=TODAY).count()
    rdv_b_today = Appointment.objects.filter(doctor__user__email='dr.yacine.bensaid@demo.com', date=TODAY).count()
    orders_total = PharmacyOrder.objects.filter(pharmacist__email='pharmacie.elshifa@demo.com').count()
    orders_by_status = {s: PharmacyOrder.objects.filter(pharmacist__email='pharmacie.elshifa@demo.com', status=s).count()
                        for s in ['pending', 'preparing', 'ready', 'delivered']}
    try:
        from caretaker.models import CareRequest
        cr_total = CareRequest.objects.filter(caretaker__user__email='fatima.hadj@demo.com').count()
        cr_by_status = {s: CareRequest.objects.filter(caretaker__user__email='fatima.hadj@demo.com', status=s).count()
                        for s in ['pending', 'accepted', 'completed']}
    except Exception:
        cr_total = 0
        cr_by_status = {}

    print(f"{'✅' if rdv_k_today >= 6 else '❌'} Planning Dr. Khelifi aujourd'hui  : {rdv_k_today} RDV")
    print(f"{'✅' if rdv_b_today >= 6 else '❌'} Planning Dr. Bensaid aujourd'hui  : {rdv_b_today} RDV")
    print()
    print(f"{'✅' if orders_total >= 8 else '❌'} Commandes pharmacie total : {orders_total}")
    for s, n in orders_by_status.items():
        print(f"    • {s:12s} : {n}")
    print()
    print(f"{'✅' if cr_total >= 5 else '❌'} Demandes garde-malade total : {cr_total}")
    for s, n in cr_by_status.items():
        print(f"    • {s:12s} : {n}")
except Exception as e:
    print(f"❌ Rapport : {e}")

print("=" * 60)
print("Script terminé.")
