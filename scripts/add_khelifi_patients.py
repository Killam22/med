"""
Ajoute des patients supplémentaires avec RDV et consultations chez Dr. Amina Khelifi.
Lancer : python manage.py shell -c "exec(open('scripts/add_khelifi_patients.py', encoding='utf-8').read())"
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
from notifications.models import Notification

PASSWORD = "Demo@2025"


def make_dt(y, m, d, h, mn=0):
    return timezone.make_aware(datetime(y, m, d, h, mn))


def create_patient(email, first_name, last_name, sex, dob, phone, card_number,
                   address, postal_code, city, wilaya):
    if User.objects.filter(email=email).exists():
        print(f"⏭️  Existe déjà : {email}")
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
        print(f"✅ Créé : {email} (patient)")
        return user, True
    except Exception as e:
        print(f"❌ Erreur {email} : {e}")
        return None, False


def get_or_make_patient(user):
    try:
        return user.patient_profile
    except Exception:
        return Patient.objects.create(user=user)


def make_rdv(patient, doctor, rdv_date, sh, sm, eh, em, motif, status):
    existing = Appointment.objects.filter(
        doctor=doctor, date=rdv_date, start_time=time(sh, sm)
    ).first()
    if existing:
        print(f"⏭️  RDV existe déjà : {rdv_date} {sh}h{sm:02d}")
        return existing
    try:
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor,
            date=rdv_date, start_time=time(sh, sm), end_time=time(eh, em),
            motif=motif, status=status,
        )
        print(f"✅ RDV : {patient.user.get_full_name()} → Dr. Khelifi le {rdv_date}")
        return appt
    except Exception as e:
        print(f"❌ Erreur RDV {rdv_date} : {e}")
        return None


def make_consult(appt, doctor, patient, complaint, diagnosis, plan, notes, vitals_dict, consulted_at):
    try:
        c = appt.consultation
        print(f"⏭️  Consultation existe déjà pour RDV {appt.id}")
        return c
    except Exception:
        pass
    try:
        c = Consultation.objects.create(
            doctor=doctor, patient=patient, appointment=appt,
            consultation_type='in_person', status='completed',
            chief_complaint=complaint, diagnosis=diagnosis,
            treatment_plan=plan, doctor_notes=notes,
            vitals=json.dumps(vitals_dict, ensure_ascii=False),
            consulted_at=consulted_at,
        )
        print(f"✅ Consultation créée : {patient.user.get_full_name()}")
        return c
    except Exception as e:
        print(f"❌ Erreur consultation : {e}")
        return None


def make_presc(consultation, items):
    if consultation.prescriptions.exists():
        print(f"⏭️  Ordonnance existe déjà")
        return consultation.prescriptions.first()
    try:
        presc = Prescription.objects.create(
            consultation=consultation, status='active',
            valid_until=date(2026, 12, 31),
        )
        for item in items:
            PrescriptionItem.objects.create(prescription=presc, **item)
        print(f"✅ Ordonnance : {len(items)} médicament(s)")
        return presc
    except Exception as e:
        print(f"❌ Erreur ordonnance : {e}")
        return None


# ─── Récupérer Dr. Khelifi ────────────────────────────────────────────────────
try:
    doctor_khelifi = Doctor.objects.get(user__email='dr.amina.khelifi@demo.com')
except Exception as e:
    print(f"❌ Dr. Khelifi introuvable : {e}")
    raise SystemExit

today = date.today()

# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 1 : Nadia Bouafia (grippe, suivi) ---")
try:
    u, _ = create_patient(
        'nadia.bouafia@demo.com', 'Nadia', 'Bouafia', 'female',
        date(1992, 11, 8), '0555112233', 'DEMO-KP1-2025-007',
        '3 Rue Ibn Khaldoun', '16000', 'Alger', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=p, weight=57.0, height=162.0, blood_group='B+',
                emergency_contact_name='Rachid Bouafia', emergency_contact_phone='0555112200',
            )

        # RDV 1 — complété (grippe)
        rdv = make_rdv(p, doctor_khelifi, date(2025, 1, 15), 9, 0, 9, 30,
                       'Fièvre et maux de gorge depuis 3 jours', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Fièvre 38.9°C, maux de gorge, fatigue intense',
                diagnosis='Grippe saisonnière',
                plan='Repos, hydratation, antipyrétiques. Arrêt de travail 5 jours.',
                notes='Pas de surinfection bactérienne. Réévaluation si pas d\'amélioration sous 5j.',
                vitals_dict={'bp': '118/75', 'hr': 92, 'temp': 38.9, 'spo2': 97},
                consulted_at=make_dt(2025, 1, 15, 9, 0))
            if c:
                make_presc(c, [
                    {'drug_name': 'Paracétamol', 'dosage': '1g', 'frequency': '3x_day', 'duration': '5 jours', 'quantity': 15},
                    {'drug_name': 'Ibuprofène',  'dosage': '400mg', 'frequency': '2x_day', 'duration': '3 jours', 'quantity': 6},
                ])

        # RDV 2 — complété (suivi)
        rdv2 = make_rdv(p, doctor_khelifi, date(2025, 2, 10), 11, 0, 11, 30,
                        'Douleurs abdominales, suivi', 'completed')
        if rdv2:
            c2 = make_consult(rdv2, doctor_khelifi, p,
                complaint='Douleurs abdominales basses, nausées depuis 2 jours',
                diagnosis='Gastro-entérite aiguë',
                plan='Régime sans résidu, rééhydratation orale, antispasmodiques',
                notes='Abdomen souple, pas de défense. Évolution favorable attendue sous 48h.',
                vitals_dict={'bp': '116/72', 'hr': 80, 'temp': 37.4, 'spo2': 99},
                consulted_at=make_dt(2025, 2, 10, 11, 0))
            if c2:
                make_presc(c2, [
                    {'drug_name': 'Spasfon', 'dosage': '80mg', 'frequency': '3x_day', 'duration': '5 jours', 'quantity': 15},
                    {'drug_name': 'Smecta',  'dosage': '3g',   'frequency': '3x_day', 'duration': '3 jours', 'quantity': 9},
                ])

        # RDV 3 — à venir (confirmé)
        make_rdv(p, doctor_khelifi, today + timedelta(days=3), 10, 0, 10, 30,
                 'Bilan de santé annuel', 'confirmed')

except Exception as e:
    print(f"❌ Erreur Nadia Bouafia : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 2 : Omar Taleb (suivi diabète + tension) ---")
try:
    u, _ = create_patient(
        'omar.taleb@demo.com', 'Omar', 'Taleb', 'male',
        date(1968, 4, 3), '0661445566', 'DEMO-KP2-2025-008',
        '17 Cité des Orangers', '16000', 'Bab El Oued', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=p, weight=88.0, height=174.0, blood_group='A-',
                emergency_contact_name='Souad Taleb', emergency_contact_phone='0661445500',
            )
            Antecedent.objects.get_or_create(
                patient=p, name='Diabète de type 2',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2015, 3, 1)},
            )
            Antecedent.objects.get_or_create(
                patient=p, name='Hypertension artérielle',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2017, 8, 1)},
            )

        # RDV 1 — complété
        rdv = make_rdv(p, doctor_khelifi, date(2025, 1, 28), 14, 0, 14, 30,
                       'Suivi diabète et hypertension', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Bilan trimestriel, glycémie élevée à domicile (1.8 g/L)',
                diagnosis='Diabète de type 2 déséquilibré, HTA stable',
                plan='Ajustement Metformine. Régime strict. Contrôle dans 1 mois.',
                notes='Glycémie à jeun 1.82 g/L. Tension 138/86. Poids stable.',
                vitals_dict={'bp': '138/86', 'hr': 74, 'temp': 36.7, 'spo2': 98},
                consulted_at=make_dt(2025, 1, 28, 14, 0))
            if c:
                make_presc(c, [
                    {'drug_name': 'Metformine',  'dosage': '1000mg', 'frequency': '2x_day', 'duration': '30 jours', 'quantity': 60},
                    {'drug_name': 'Amlodipine',  'dosage': '5mg',    'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
                    {'drug_name': 'Ramipril',    'dosage': '5mg',    'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
                ])

        # RDV 2 — complété
        rdv2 = make_rdv(p, doctor_khelifi, date(2025, 3, 4), 14, 0, 14, 30,
                        'Contrôle glycémie après ajustement', 'completed')
        if rdv2:
            c2 = make_consult(rdv2, doctor_khelifi, p,
                complaint='Contrôle suite à ajustement Metformine',
                diagnosis='Diabète de type 2 mieux équilibré',
                plan='Continuer traitement actuel. Prochain bilan HbA1c dans 3 mois.',
                notes='Glycémie 1.42 g/L. Amélioration notable. Tension 128/80.',
                vitals_dict={'bp': '128/80', 'hr': 70, 'temp': 36.6, 'spo2': 98},
                consulted_at=make_dt(2025, 3, 4, 14, 0))
            if c2:
                make_presc(c2, [
                    {'drug_name': 'Metformine', 'dosage': '1000mg', 'frequency': '2x_day', 'duration': '90 jours', 'quantity': 180},
                    {'drug_name': 'Amlodipine', 'dosage': '5mg',    'frequency': '1x_day', 'duration': '90 jours', 'quantity': 90},
                ])

        # RDV 3 — à venir
        make_rdv(p, doctor_khelifi, today + timedelta(days=10), 14, 0, 14, 30,
                 'Bilan HbA1c trimestriel', 'confirmed')

except Exception as e:
    print(f"❌ Erreur Omar Taleb : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 3 : Leila Mansouri (suivi grossesse) ---")
try:
    u, _ = create_patient(
        'leila.mansouri@demo.com', 'Leila', 'Mansouri', 'female',
        date(1995, 7, 19), '0770223344', 'DEMO-KP3-2025-009',
        '22 Rue Abane Ramdane', '16000', 'Hussein Dey', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            MedicalProfile.objects.create(
                patient=p, weight=68.0, height=167.0, blood_group='O+',
                emergency_contact_name='Kamel Mansouri', emergency_contact_phone='0770223300',
            )

        rdv = make_rdv(p, doctor_khelifi, date(2025, 2, 18), 10, 30, 11, 0,
                       'Suivi grossesse 2ème trimestre — nausées persistantes', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Nausées matinales persistantes, fatigue, 16 semaines d\'aménorrhée',
                diagnosis='Grossesse normale 2ème trimestre, nausées gravidiques',
                plan='Vitamine B6, alimentation fractionnée, repos. Suivi mensuel.',
                notes='Tension normale. Prise de poids adaptée (+3kg). Prochain écho dans 4 semaines.',
                vitals_dict={'bp': '110/68', 'hr': 82, 'temp': 36.5, 'spo2': 99},
                consulted_at=make_dt(2025, 2, 18, 10, 30))
            if c:
                make_presc(c, [
                    {'drug_name': 'Vitamine B6',  'dosage': '40mg', 'frequency': '2x_day', 'duration': '30 jours', 'quantity': 60},
                    {'drug_name': 'Acide folique', 'dosage': '5mg',  'frequency': '1x_day', 'duration': '60 jours', 'quantity': 60},
                ])

        rdv2 = make_rdv(p, doctor_khelifi, date(2025, 4, 7), 10, 30, 11, 0,
                        'Suivi grossesse 3ème trimestre', 'completed')
        if rdv2:
            c2 = make_consult(rdv2, doctor_khelifi, p,
                complaint='Consultation de suivi, 28 semaines, légers œdèmes aux chevilles',
                diagnosis='Grossesse normale 3ème trimestre, œdèmes modérés',
                plan='Surélever les jambes, diminuer sel, marche légère 20 min/jour.',
                notes='Tension 115/72. Bébé actif. Poids +8kg total. Pas de protéinurie.',
                vitals_dict={'bp': '115/72', 'hr': 85, 'temp': 36.6, 'spo2': 99},
                consulted_at=make_dt(2025, 4, 7, 10, 30))
            if c2:
                make_presc(c2, [
                    {'drug_name': 'Magnésium B6', 'dosage': '48mg', 'frequency': '2x_day', 'duration': '30 jours', 'quantity': 60},
                ])

        # RDV à venir
        make_rdv(p, doctor_khelifi, today + timedelta(days=5), 10, 30, 11, 0,
                 'Suivi post-partum — consultation de contrôle', 'confirmed')

except Exception as e:
    print(f"❌ Erreur Leila Mansouri : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 4 : Ahmed Zerrouki (lombalgies, stress) ---")
try:
    u, _ = create_patient(
        'ahmed.zerrouki@demo.com', 'Ahmed', 'Zerrouki', 'male',
        date(1978, 12, 25), '0555667788', 'DEMO-KP4-2025-010',
        '8 Impasse des Pins', '16200', 'El Harrach', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=p, weight=91.0, height=180.0, blood_group='AB+',
                emergency_contact_name='Amira Zerrouki', emergency_contact_phone='0555667700',
            )
            Antecedent.objects.get_or_create(
                patient=p, name='Lombalgies chroniques',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2020, 5, 1)},
            )

        rdv = make_rdv(p, doctor_khelifi, date(2025, 1, 9), 15, 0, 15, 30,
                       'Douleurs lombaires et fatigue chronique', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Douleurs lombaires intenses depuis 1 semaine, difficultés à dormir',
                diagnosis='Lombalgie aiguë sur fond chronique, syndrome de fatigue',
                plan='Anti-inflammatoires 5 jours, kinésithérapie recommandée, hygiène du sommeil.',
                notes='Contractures musculaires para-vertébrales. Pas de signes neurologiques.',
                vitals_dict={'bp': '132/84', 'hr': 76, 'temp': 36.8, 'spo2': 98},
                consulted_at=make_dt(2025, 1, 9, 15, 0))
            if c:
                make_presc(c, [
                    {'drug_name': 'Diclofénac',  'dosage': '75mg', 'frequency': '2x_day', 'duration': '5 jours',  'quantity': 10},
                    {'drug_name': 'Myolastan',   'dosage': '50mg', 'frequency': '2x_day', 'duration': '5 jours',  'quantity': 10},
                    {'drug_name': 'Paracétamol', 'dosage': '1g',   'frequency': '3x_day', 'duration': '7 jours',  'quantity': 21},
                ])

        # RDV en attente (patient qui a demandé mais pas encore confirmé)
        make_rdv(p, doctor_khelifi, today + timedelta(days=14), 15, 0, 15, 30,
                 'Réévaluation lombalgies et certificat médical', 'pending')

except Exception as e:
    print(f"❌ Erreur Ahmed Zerrouki : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 5 : Samira Hadj Ali (anxiété, céphalées) ---")
try:
    u, _ = create_patient(
        'samira.hadjali@demo.com', 'Samira', 'Hadj Ali', 'female',
        date(1988, 3, 30), '0661889900', 'DEMO-KP5-2025-011',
        '56 Avenue Colonel Amirouche', '16100', 'Kouba', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            MedicalProfile.objects.create(
                patient=p, weight=63.0, height=163.0, blood_group='A+',
                emergency_contact_name='Djamel Hadj Ali', emergency_contact_phone='0661889800',
            )

        rdv = make_rdv(p, doctor_khelifi, date(2025, 2, 25), 16, 0, 16, 30,
                       'Céphalées fréquentes et troubles du sommeil', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Maux de tête quotidiens depuis 3 semaines, insomnie, irritabilité',
                diagnosis='Syndrome anxieux, céphalées de tension',
                plan='Hygiène du sommeil, activité physique, consultation psychologue recommandée.',
                notes='Examen neurologique normal. Lien probable avec surcharge professionnelle.',
                vitals_dict={'bp': '122/78', 'hr': 88, 'temp': 36.7, 'spo2': 99},
                consulted_at=make_dt(2025, 2, 25, 16, 0))
            if c:
                make_presc(c, [
                    {'drug_name': 'Paracétamol',    'dosage': '1g',   'frequency': 'as_needed', 'duration': '15 jours', 'quantity': 20},
                    {'drug_name': 'Mélatonine',     'dosage': '1mg',  'frequency': '1x_day',    'duration': '30 jours', 'quantity': 30},
                    {'drug_name': 'Magnésium marin','dosage': '300mg','frequency': '1x_day',    'duration': '30 jours', 'quantity': 30},
                ])

        rdv2 = make_rdv(p, doctor_khelifi, date(2025, 4, 15), 16, 0, 16, 30,
                        'Suivi anxiété — amélioration attendue', 'completed')
        if rdv2:
            c2 = make_consult(rdv2, doctor_khelifi, p,
                complaint='Suivi, céphalées réduites, sommeil légèrement amélioré',
                diagnosis='Syndrome anxieux en amélioration',
                plan='Continuer magnésium, débuter relaxation/sophrologie.',
                notes='Patient mieux. Arrêt paracétamol régulier. Éviter automédication.',
                vitals_dict={'bp': '118/74', 'hr': 78, 'temp': 36.6, 'spo2': 99},
                consulted_at=make_dt(2025, 4, 15, 16, 0))

        # RDV en attente
        make_rdv(p, doctor_khelifi, today + timedelta(days=2), 16, 0, 16, 30,
                 'Bilan général annuel', 'pending')

except Exception as e:
    print(f"❌ Erreur Samira Hadj Ali : {e}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- Patient 6 : Youcef Belkacem (contrôle cholestérol) ---")
try:
    u, _ = create_patient(
        'youcef.belkacem@demo.com', 'Youcef', 'Belkacem', 'male',
        date(1972, 9, 14), '0555334455', 'DEMO-KP6-2025-012',
        '4 Rue des Frères Bouadou', '16100', 'Birtouta', 'Alger',
    )
    if u:
        p = get_or_make_patient(u)
        try:
            p.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=p, weight=84.0, height=176.0, blood_group='B-',
                emergency_contact_name='Houria Belkacem', emergency_contact_phone='0555334400',
            )
            Antecedent.objects.get_or_create(
                patient=p, name='Hypercholestérolémie',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2019, 2, 1)},
            )
            Antecedent.objects.get_or_create(
                patient=p, name='Tabagisme sevré',
                defaults={'type': 'personnel', 'status': 'resolved', 'date_diagnosis': date(2018, 1, 1)},
            )

        rdv = make_rdv(p, doctor_khelifi, date(2025, 3, 19), 9, 30, 10, 0,
                       'Contrôle bilan lipidique annuel', 'completed')
        if rdv:
            c = make_consult(rdv, doctor_khelifi, p,
                complaint='Résultats bilan sanguin : LDL 1.85 g/L, cholestérol total 2.4 g/L',
                diagnosis='Hypercholestérolémie modérée persistante',
                plan='Renforcer régime hypolipidémiant, statines réévaluées. Reprise sport.',
                notes='Patient sédentaire depuis 6 mois. LDL en hausse vs bilan N-1.',
                vitals_dict={'bp': '126/80', 'hr': 72, 'temp': 36.7, 'spo2': 98},
                consulted_at=make_dt(2025, 3, 19, 9, 30))
            if c:
                make_presc(c, [
                    {'drug_name': 'Atorvastatine', 'dosage': '20mg', 'frequency': '1x_day', 'duration': '90 jours', 'quantity': 90},
                    {'drug_name': 'Omega-3',       'dosage': '1g',   'frequency': '2x_day', 'duration': '90 jours', 'quantity': 180},
                ])

        # RDV confirmé
        make_rdv(p, doctor_khelifi, today + timedelta(days=18), 9, 30, 10, 0,
                 'Contrôle bilan lipidique — suivi statines', 'confirmed')

except Exception as e:
    print(f"❌ Erreur Youcef Belkacem : {e}")


# ─── Notifications pour Dr. Khelifi ──────────────────────────────────────────
print("\n--- Notifications ---")
try:
    u_khelifi = User.objects.get(email='dr.amina.khelifi@demo.com')
    notifs = [
        ("Nouveau rendez-vous — Nadia Bouafia",   f"Nadia Bouafia a confirmé un RDV le {(today + timedelta(days=3)).strftime('%d/%m/%Y')} à 10h00.", 'appointment'),
        ("Nouveau rendez-vous — Omar Taleb",      f"Omar Taleb a confirmé un RDV le {(today + timedelta(days=10)).strftime('%d/%m/%Y')} à 14h00.", 'appointment'),
        ("Rendez-vous en attente — Ahmed Zerrouki","Ahmed Zerrouki a demandé un RDV pour réévaluation lombalgies.", 'appointment'),
        ("Rendez-vous en attente — Samira Hadj Ali","Samira Hadj Ali a demandé un bilan général.", 'appointment'),
    ]
    for title, msg, ntype in notifs:
        if not Notification.objects.filter(user=u_khelifi, title=title).exists():
            Notification.objects.create(user=u_khelifi, title=title, message=msg, notification_type=ntype)
            print(f"✅ Notification : {title[:50]}")
        else:
            print(f"⏭️  Notification existe déjà : {title[:50]}")
except Exception as e:
    print(f"❌ Erreur notifications : {e}")


# ─── Rapport ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RAPPORT — Patients Dr. Khelifi")
print("=" * 60)

khelifi_emails = [
    'nadia.bouafia@demo.com', 'omar.taleb@demo.com',
    'leila.mansouri@demo.com', 'ahmed.zerrouki@demo.com',
    'samira.hadjali@demo.com', 'youcef.belkacem@demo.com',
]
for email in khelifi_emails:
    ok = User.objects.filter(email=email, is_active=True).exists()
    print(f"{'✅' if ok else '❌'} {email}")

rdv_total    = Appointment.objects.filter(doctor=doctor_khelifi).count()
consult_total = Consultation.objects.filter(doctor=doctor_khelifi).count()
print(f"\n✅ Total RDV Dr. Khelifi : {rdv_total}")
print(f"✅ Total consultations   : {consult_total}")
print("=" * 60)
