"""
Comptes de démonstration avec données réalistes pour captures d'écran académiques.
Lancer : cd back && python manage.py shell < scripts/create_demo_accounts.py
"""
import json
from datetime import date, time, datetime, timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

from patients.models import Patient, MedicalProfile, Allergy, Antecedent
from doctors.models import Doctor, Exercice
from pharmacy.models import Pharmacist, Pharmacy, PharmacyOrder
from caretaker.models import Caretaker
from appointments.models import Appointment
from consultations.models import Consultation
from prescriptions.models import Prescription, PrescriptionItem
from notifications.models import Notification

PASSWORD = "Demo@2025"


def create_user(email, role, first_name, last_name, sex, dob, phone,
                card_number, address, postal_code, city, wilaya):
    if User.objects.filter(email=email).exists():
        print(f"⏭️  Existe déjà : {email}")
        return User.objects.get(email=email), False
    try:
        user = User(
            username=email,
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name,
            sex=sex,
            date_of_birth=dob,
            phone=phone,
            id_card_number=card_number,
            address=address,
            postal_code=postal_code,
            city=city,
            wilaya=wilaya,
            verification_status='verified',
            is_active=True,
        )
        user.set_password(PASSWORD)
        user.save()
        print(f"✅ Créé : {email} ({role})")
        return user, True
    except Exception as e:
        print(f"❌ Erreur création {email} : {e}")
        return None, False


# ─── PATIENT 1 : Sarah Benali ────────────────────────────────────────────────
print("--- Création des comptes ---")
try:
    user_sarah, _ = create_user(
        'sarah.benali@demo.com', 'patient',
        'Sarah', 'Benali', 'female',
        date(1990, 3, 15), '0555123456',
        'DEMO-P1-2025-001',
        '12 Rue Didouche Mourad', '16000', 'Alger Centre', 'Alger',
    )
    if user_sarah:
        try:
            patient_sarah = user_sarah.patient_profile
        except Exception:
            patient_sarah = Patient.objects.create(user=user_sarah)

        try:
            patient_sarah.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=patient_sarah,
                weight=62.0, height=165.0, blood_group='A+',
                emergency_contact_name='Mohamed Benali',
                emergency_contact_phone='0555987654',
            )
            Allergy.objects.get_or_create(
                profile=mp, substance='Pénicilline',
                defaults={'severity': 'severe', 'reaction': 'Rash cutané'},
            )
            Allergy.objects.get_or_create(
                profile=mp, substance='Aspirine',
                defaults={'severity': 'moderate', 'reaction': 'Urticaire'},
            )
            Antecedent.objects.get_or_create(
                patient=patient_sarah, name='Hypertension artérielle',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2018, 1, 1)},
            )
            Antecedent.objects.get_or_create(
                patient=patient_sarah, name='Fracture du poignet gauche',
                defaults={'type': 'personnel', 'status': 'resolved', 'date_diagnosis': date(2015, 6, 1)},
            )
except Exception as e:
    print(f"❌ Erreur patient Sarah Benali : {e}")


# ─── PATIENT 2 : Karim Meziane ───────────────────────────────────────────────
try:
    user_karim, _ = create_user(
        'karim.meziane@demo.com', 'patient',
        'Karim', 'Meziane', 'male',
        date(1985, 7, 22), '0661234567',
        'DEMO-P2-2025-002',
        '45 Boulevard Millenium', '31000', 'Oran', 'Oran',
    )
    if user_karim:
        try:
            patient_karim = user_karim.patient_profile
        except Exception:
            patient_karim = Patient.objects.create(user=user_karim)

        try:
            patient_karim.medical_profile
        except Exception:
            mp = MedicalProfile.objects.create(
                patient=patient_karim,
                weight=80.0, height=178.0, blood_group='O+',
                emergency_contact_name='Fatima Meziane',
                emergency_contact_phone='0661987654',
            )
            Antecedent.objects.get_or_create(
                patient=patient_karim, name='Diabète de type 2',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2020, 1, 1)},
            )
            Antecedent.objects.get_or_create(
                patient=patient_karim, name='Rhinite allergique',
                defaults={'type': 'personnel', 'status': 'chronic', 'date_diagnosis': date(2019, 1, 1)},
            )
except Exception as e:
    print(f"❌ Erreur patient Karim Meziane : {e}")


# ─── MÉDECIN 1 : Dr. Yacine Bensaid ─────────────────────────────────────────
try:
    user_bensaid, _ = create_user(
        'dr.yacine.bensaid@demo.com', 'doctor',
        'Yacine', 'Bensaid', 'male',
        date(1980, 6, 15), '0555234567',
        'DEMO-D1-2025-003',
        'Clinique El Rahma, Alger', '16000', 'Alger', 'Alger',
    )
    if user_bensaid:
        try:
            doctor_bensaid = user_bensaid.doctor_profile
        except Exception:
            doctor_bensaid = Doctor.objects.create(
                user=user_bensaid,
                specialty='cardiology',
                order_number='MED-16-CARD-2018-0472',
                clinic_name='Clinique El Rahma',
                experience_years=8,
                consultation_fee=2500.00,
                rating=4.80,
                total_reviews=124,
                is_verified=True,
                cnas_coverage=True,
                languages='Français, Arabe',
                bio="Cardiologue expérimenté, spécialisé dans le traitement de l'hypertension et des maladies coronariennes.",
            )
            Exercice.objects.get_or_create(
                doctor=doctor_bensaid,
                establishment_name='Clinique El Rahma',
                defaults={
                    'est_address': '12 Rue des Martyrs, Alger',
                    'est_city': 'Alger',
                    'pro_phone': '0555234567',
                    'is_main_location': True,
                },
            )
except Exception as e:
    print(f"❌ Erreur médecin Dr. Bensaid : {e}")


# ─── MÉDECIN 2 : Dr. Amina Khelifi ──────────────────────────────────────────
try:
    user_khelifi, _ = create_user(
        'dr.amina.khelifi@demo.com', 'doctor',
        'Amina', 'Khelifi', 'female',
        date(1975, 3, 20), '0661345678',
        'DEMO-D2-2025-004',
        'Cabinet Médical Khelifi, Alger', '16000', 'Alger', 'Alger',
    )
    if user_khelifi:
        try:
            doctor_khelifi = user_khelifi.doctor_profile
        except Exception:
            doctor_khelifi = Doctor.objects.create(
                user=user_khelifi,
                specialty='general',
                order_number='MED-16-GEN-2015-0231',
                clinic_name='Cabinet Médical Khelifi',
                experience_years=10,
                consultation_fee=1500.00,
                rating=4.60,
                total_reviews=89,
                is_verified=True,
                cnas_coverage=True,
                languages='Français, Arabe',
            )
            Exercice.objects.get_or_create(
                doctor=doctor_khelifi,
                establishment_name='Cabinet Médical Khelifi',
                defaults={
                    "est_address": "25 Rue Larbi Ben M'Hidi, Alger",
                    'est_city': 'Alger',
                    'pro_phone': '0661345678',
                    'is_main_location': True,
                },
            )
except Exception as e:
    print(f"❌ Erreur médecin Dr. Khelifi : {e}")


# ─── PHARMACIEN : Mohamed Cherif / Pharmacie El Shifa ────────────────────────
try:
    user_pharmacie, _ = create_user(
        'pharmacie.elshifa@demo.com', 'pharmacist',
        'Mohamed', 'Cherif', 'male',
        date(1975, 5, 10), '0555345678',
        'DEMO-PH-2025-005',
        '8 Rue Hassiba Ben Bouali', '16000', 'Alger Centre', 'Alger',
    )
    if user_pharmacie:
        try:
            pharmacist = user_pharmacie.pharmacist_profile
        except Exception:
            pharmacist = Pharmacist.objects.create(
                user=user_pharmacie,
                order_registration_number='PHARM-DEMO-2025-001',
                is_verified=True,
                cnas_coverage=True,
            )

        try:
            pharmacist.pharmacy
        except Exception:
            Pharmacy.objects.create(
                pharmacist=pharmacist,
                name='Pharmacie El Shifa',
                pharm_address='8 Rue Hassiba Ben Bouali',
                pharm_city='Alger Centre',
                pharm_phone='0555345679',
                agreement_number='AGR-DEMO-ELSHIFA-2025',
            )
except Exception as e:
    print(f"❌ Erreur pharmacien : {e}")


# ─── GARDE-MALADE : Fatima Hadj ──────────────────────────────────────────────
try:
    user_hadj, _ = create_user(
        'fatima.hadj@demo.com', 'caretaker',
        'Fatima', 'Hadj', 'female',
        date(1982, 9, 5), '0555456789',
        'DEMO-GM-2025-006',
        'Alger', '16000', 'Alger', 'Alger',
    )
    if user_hadj:
        try:
            user_hadj.caretaker_profile
        except Exception:
            Caretaker.objects.create(
                user=user_hadj,
                experience_years=5,
                availability_area='Alger, Blida, Tipaza',
                tarif_de_base=1200.00,
                is_verified=True,
                is_available=True,
            )
except Exception as e:
    print(f"❌ Erreur garde-malade Fatima Hadj : {e}")


# ─── RENDEZ-VOUS ─────────────────────────────────────────────────────────────
print("\n--- Création des rendez-vous ---")


def get_or_create_rdv(patient, doctor, rdv_date, sh, sm, eh, em, motif, status):
    existing = Appointment.objects.filter(
        doctor=doctor, date=rdv_date, start_time=time(sh, sm)
    ).first()
    if existing:
        print(f"⏭️  RDV existe déjà : Dr. {doctor.user.last_name} le {rdv_date}")
        return existing
    try:
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor,
            date=rdv_date,
            start_time=time(sh, sm), end_time=time(eh, em),
            motif=motif, status=status,
        )
        print(f"✅ RDV créé : Dr. {doctor.user.last_name} le {rdv_date}")
        return appt
    except Exception as e:
        print(f"❌ Erreur RDV {rdv_date} : {e}")
        return None


try:
    patient_sarah = Patient.objects.get(user__email='sarah.benali@demo.com')
    patient_karim = Patient.objects.get(user__email='karim.meziane@demo.com')
    doctor_bensaid = Doctor.objects.get(user__email='dr.yacine.bensaid@demo.com')
    doctor_khelifi = Doctor.objects.get(user__email='dr.amina.khelifi@demo.com')

    rdv1 = get_or_create_rdv(patient_sarah, doctor_bensaid, date(2025, 3, 12), 9, 0, 9, 30, 'Suivi hypertension artérielle', 'completed')
    rdv2 = get_or_create_rdv(patient_sarah, doctor_khelifi, date(2025, 4, 26), 10, 0, 10, 30, 'Rhinite et maux de tête', 'completed')
    rdv3 = get_or_create_rdv(patient_karim, doctor_bensaid, date(2025, 5, 3), 11, 0, 11, 30, 'Bilan diabète', 'completed')
    rdv4 = get_or_create_rdv(patient_sarah, doctor_bensaid, date.today() + timedelta(days=7), 9, 0, 9, 30, 'Contrôle tension artérielle', 'confirmed')
except Exception as e:
    print(f"❌ Erreur rendez-vous : {e}")


# ─── CONSULTATIONS ET ORDONNANCES ────────────────────────────────────────────
print("\n--- Création des consultations ---")


def make_dt(y, m, d, h, mn):
    return timezone.make_aware(datetime(y, m, d, h, mn))


def get_or_create_consultation(appt, doctor, patient, complaint, diagnosis,
                                plan, notes, vitals_dict, consulted_at):
    try:
        existing = appt.consultation
        print(f"⏭️  Consultation existe déjà pour RDV {appt.id}")
        return existing
    except Exception:
        pass
    try:
        c = Consultation.objects.create(
            doctor=doctor, patient=patient,
            appointment=appt,
            consultation_type='in_person',
            status='completed',
            chief_complaint=complaint,
            diagnosis=diagnosis,
            treatment_plan=plan,
            doctor_notes=notes,
            vitals=json.dumps(vitals_dict, ensure_ascii=False),
            consulted_at=consulted_at,
        )
        print(f"✅ Consultation créée : Dr. {doctor.user.last_name} / {patient.user.last_name}")
        return c
    except Exception as e:
        print(f"❌ Erreur consultation : {e}")
        return None


def get_or_create_prescription(consultation, items):
    existing = consultation.prescriptions.first()
    if existing:
        print(f"⏭️  Ordonnance existe déjà (consultation {consultation.id})")
        return existing
    try:
        presc = Prescription.objects.create(
            consultation=consultation,
            status='active',
            valid_until=date(2026, 12, 31),
        )
        for item in items:
            PrescriptionItem.objects.create(prescription=presc, **item)
        print(f"✅ Ordonnance créée : {len(items)} médicament(s)")
        return presc
    except Exception as e:
        print(f"❌ Erreur ordonnance : {e}")
        return None


try:
    patient_sarah = Patient.objects.get(user__email='sarah.benali@demo.com')
    patient_karim = Patient.objects.get(user__email='karim.meziane@demo.com')
    doctor_bensaid = Doctor.objects.get(user__email='dr.yacine.bensaid@demo.com')
    doctor_khelifi = Doctor.objects.get(user__email='dr.amina.khelifi@demo.com')

    rdv1 = Appointment.objects.get(doctor=doctor_bensaid, date=date(2025, 3, 12), start_time=time(9, 0))
    rdv2 = Appointment.objects.get(doctor=doctor_khelifi, date=date(2025, 4, 26), start_time=time(10, 0))
    rdv3 = Appointment.objects.get(doctor=doctor_bensaid, date=date(2025, 5, 3), start_time=time(11, 0))

    # Consultation 1 — Hypertension
    c1 = get_or_create_consultation(
        rdv1, doctor_bensaid, patient_sarah,
        complaint="Maux de tête, tension élevée",
        diagnosis="Hypertension artérielle stabilisée",
        plan="Continuer le traitement, réduire le sel, exercice modéré",
        notes="Tension 145/90 à l'arrivée, stable après repos. Renouvellement traitement.",
        vitals_dict={'bp': '145/90', 'hr': 78, 'temp': 36.8, 'spo2': 98},
        consulted_at=make_dt(2025, 3, 12, 9, 0),
    )
    presc1 = None
    if c1:
        presc1 = get_or_create_prescription(c1, [
            {'drug_name': 'Lisinopril',  'dosage': '10mg', 'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
            {'drug_name': 'Amlodipine',  'dosage': '5mg',  'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
        ])

    # Consultation 2 — Rhinite
    c2 = get_or_create_consultation(
        rdv2, doctor_khelifi, patient_sarah,
        complaint="Nez bouché, éternuements fréquents depuis 1 semaine",
        diagnosis="Rhinite allergique saisonnière",
        plan="Antihistaminiques + lavage nasal quotidien",
        notes="",
        vitals_dict={'bp': '120/80', 'hr': 72, 'temp': 37.0, 'spo2': 99},
        consulted_at=make_dt(2025, 4, 26, 10, 0),
    )
    if c2:
        get_or_create_prescription(c2, [
            {'drug_name': 'Loratadine',          'dosage': '10mg',  'frequency': '1x_day', 'duration': '10 jours', 'quantity': 10},
            {'drug_name': 'Rhinadvil spray nasal','dosage': 'spray', 'frequency': '2x_day', 'duration': '7 jours',  'quantity': 1},
        ])

    # Consultation 3 — Diabète
    c3 = get_or_create_consultation(
        rdv3, doctor_bensaid, patient_karim,
        complaint="Bilan de routine, glycémie légèrement élevée",
        diagnosis="Diabète de type 2 contrôlé",
        plan="Ajustement posologie Metformine, régime alimentaire strict",
        notes="",
        vitals_dict={'bp': '130/85', 'hr': 80, 'temp': 36.9, 'spo2': 97},
        consulted_at=make_dt(2025, 5, 3, 11, 0),
    )
    if c3:
        get_or_create_prescription(c3, [
            {'drug_name': 'Metformine', 'dosage': '1000mg', 'frequency': '2x_day', 'duration': '30 jours', 'quantity': 60},
            {'drug_name': 'Glucophage', 'dosage': '500mg',  'frequency': '1x_day', 'duration': '30 jours', 'quantity': 30},
        ])

except Exception as e:
    print(f"❌ Erreur consultations : {e}")


# ─── COMMANDE PHARMACIE ───────────────────────────────────────────────────────
print("\n--- Création de la commande pharmacie ---")
try:
    user_sarah    = User.objects.get(email='sarah.benali@demo.com')
    user_pharmacie = User.objects.get(email='pharmacie.elshifa@demo.com')

    rdv1_appt = Appointment.objects.get(
        doctor__user__email='dr.yacine.bensaid@demo.com',
        date=date(2025, 3, 12),
        start_time=time(9, 0),
    )
    presc1 = rdv1_appt.consultation.prescriptions.first()

    if PharmacyOrder.objects.filter(patient=user_sarah, prescription=presc1).exists():
        print("⏭️  Commande pharmacie existe déjà")
    else:
        PharmacyOrder.objects.create(
            patient=user_sarah,
            prescription=presc1,
            pharmacist=user_pharmacie,
            order_type='prescription',
            withdrawal_method='patient',
            status='ready',
            patient_message="Bonjour, je viens retirer mes médicaments pour l'hypertension.",
            pharmacist_note="Commande prête. Lisinopril 10mg et Amlodipine 5mg disponibles en stock.",
        )
        print("✅ Commande pharmacie créée (statut : prête à retirer)")
except Exception as e:
    print(f"❌ Erreur commande pharmacie : {e}")


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────
print("\n--- Création des notifications ---")


def create_notif(user, title, message, notif_type):
    if Notification.objects.filter(user=user, title=title).exists():
        print(f"⏭️  Notification existe déjà : {title[:50]}")
        return
    try:
        Notification.objects.create(
            user=user, title=title, message=message, notification_type=notif_type
        )
        print(f"✅ Notification créée pour {user.email}")
    except Exception as e:
        print(f"❌ Erreur notification : {e}")


try:
    u_sarah     = User.objects.get(email='sarah.benali@demo.com')
    u_bensaid   = User.objects.get(email='dr.yacine.bensaid@demo.com')
    u_pharmacie = User.objects.get(email='pharmacie.elshifa@demo.com')

    rdv4_date_str = (date.today() + timedelta(days=7)).strftime('%d/%m/%Y')

    create_notif(u_sarah,
        "Rendez-vous confirmé",
        f"Votre RDV du {rdv4_date_str} à 09h00 avec Dr. Bensaid est confirmé.",
        'appointment')
    create_notif(u_sarah,
        "Ordonnance prête",
        "Votre ordonnance est prête à être retirée à Pharmacie El Shifa.",
        'pharmacy')
    create_notif(u_bensaid,
        "Nouvelle demande de RDV",
        "Sarah Benali a confirmé un rendez-vous pour le contrôle de tension artérielle.",
        'appointment')
    create_notif(u_pharmacie,
        "Nouvelle ordonnance reçue",
        "Sarah Benali vous a envoyé une ordonnance pour préparation.",
        'pharmacy')
except Exception as e:
    print(f"❌ Erreur notifications : {e}")


# ─── RAPPORT FINAL ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RAPPORT FINAL")
print("=" * 60)

demo_emails = [
    'sarah.benali@demo.com',
    'karim.meziane@demo.com',
    'dr.yacine.bensaid@demo.com',
    'dr.amina.khelifi@demo.com',
    'pharmacie.elshifa@demo.com',
    'fatima.hadj@demo.com',
]
labels = [
    'Patient 1 Sarah Benali',
    'Patient 2 Karim Meziane',
    'Médecin 1 Dr. Bensaid',
    'Médecin 2 Dr. Khelifi',
    'Pharmacien Mohamed Cherif',
    'Garde-malade Fatima Hadj',
]
for email, label in zip(demo_emails, labels):
    ok = User.objects.filter(email=email, is_active=True).exists()
    print(f"{'✅' if ok else '❌'} {label} : {email}")

print()

rdv_count     = Appointment.objects.filter(patient__user__email__in=['sarah.benali@demo.com', 'karim.meziane@demo.com']).count()
consult_count = Consultation.objects.filter(patient__user__email__in=['sarah.benali@demo.com', 'karim.meziane@demo.com']).count()
presc_count   = Prescription.objects.filter(consultation__patient__user__email__in=['sarah.benali@demo.com', 'karim.meziane@demo.com']).count()
order_count   = PharmacyOrder.objects.filter(patient__email='sarah.benali@demo.com').count()
notif_count   = Notification.objects.filter(user__email__in=['sarah.benali@demo.com', 'dr.yacine.bensaid@demo.com', 'pharmacie.elshifa@demo.com']).count()

print(f"{'✅' if rdv_count     >= 4 else '❌'} RDV créés : {rdv_count}/4")
print(f"{'✅' if consult_count >= 3 else '❌'} Consultations : {consult_count}/3")
print(f"{'✅' if presc_count   >= 3 else '❌'} Ordonnances : {presc_count}/3")
print(f"{'✅' if order_count   >= 1 else '❌'} Commande pharmacie : {order_count}/1")
print(f"{'✅' if notif_count   >= 4 else '❌'} Notifications : {notif_count}/4")
print("=" * 60)
print("Script terminé.")
