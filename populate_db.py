import os
import django
import random
from django.utils import timezone
from datetime import date, timedelta, time
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from users.models import CustomUser
from doctors.models import Doctor, Exercice
from patients.models import Patient
from caretaker.models import Caretaker
from pharmacy.models import Pharmacist, Pharmacy
from medications.models import Medication
from doctors.models import WeeklySchedule
from pharmacy.models import PharmacyStock
from appointments.models import Appointment
from notifications.models import Notification

def populate():
    # Nettoyage en cascade manuel pour éviter les ProtectedError
    from consultations.models import Consultation
    from prescriptions.models import Prescription
    from patients.models import MedicalDocument, Treatment
    
    print("🗑️ Nettoyage des données médicales...")
    Consultation.objects.all().delete()
    Prescription.objects.all().delete()
    MedicalDocument.objects.all().delete()
    Treatment.objects.all().delete()
    
    print("🧹 Nettoyage des utilisateurs...")
    CustomUser.objects.filter(is_superuser=False).delete()

    SPECIALTIES = [
        ('general', 'Médecine Générale'),
        ('cardiology', 'Cardiologie'),
        ('dermatology', 'Dermatologie'),
        ('gynecology', 'Gynécologie'),
        ('pediatrics', 'Pédiatrie'),
        ('ophthalmology', 'Ophtalmologie'),
        ('ent', 'O.R.L'),
        ('orthopedics', 'Orthopédie'),
        ('neurology', 'Neurologie'),
        ('dentistry', 'Dentisterie'),
    ]

    CITIES = ['Alger', 'Oran', 'Constantine', 'Annaba', 'Sétif', 'Batna', 'Béjaïa']
    
    first_names_m = ['Amine', 'Mohamed', 'Yacine', 'Karim', 'Omar', 'Sofiane', 'Abdel']
    first_names_f = ['Lydia', 'Ines', 'Sonia', 'Amel', 'Meriem', 'Nadia', 'Sarah']
    last_names = ['Bensaid', 'Mansouri', 'Khelifi', 'Ziane', 'Hamidi', 'Belkacem', 'Ouali']

    print("👨‍⚕️ Création de 12 médecins...")
    doctors_list = []
    
    for i in range(12):
        sex = random.choice(['M', 'F'])
        fname = random.choice(first_names_m if sex == 'M' else first_names_f)
        lname = random.choice(last_names)
        city = random.choice(CITIES)
        spec = random.choice(SPECIALTIES)[0]
        
        email = f"dr.{fname.lower()}.{lname.lower()}{i}@test.com"
        username = f"dr_{fname.lower()}_{i}"
        
        user = CustomUser.objects.create(
            username=username,
            email=email,
            password=make_password('testpass123'),
            first_name=fname,
            last_name=lname,
            role='doctor',
            sex=sex,
            is_active=True,
            city=city,
            wilaya=city,
            phone=f"0550{random.randint(100000, 999999)}",
            verification_status='verified',
            id_card_number=f"DOC{i}{random.randint(100000, 999999)}"
        )
        
        doctor = Doctor.objects.create(
            user=user,
            specialty=spec,
            order_number=f"LIC-{random.randint(10000, 99999)}",
            clinic_name=f"Cabinet {lname}",
            experience_years=random.randint(2, 25),
            consultation_fee=random.randint(1500, 5000),
            rating=round(random.uniform(3.5, 5.0), 1),
            total_reviews=random.randint(5, 50),
            is_verified=True,
            bio=f"Le Dr {fname} {lname} est un expert en {spec} situé à {city}."
        )
        doctors_list.append(doctor)
        
        # Ajouter un lieu d'exercice
        Exercice.objects.create(
            doctor=doctor,
            establishment_name=f"Clinique {city} Santé",
            est_address=f"Rue {random.randint(1, 100)} de la Liberté",
            est_city=city,
            pro_phone=user.phone,
            is_main_location=True
        )

    print("👶 Création de 5 patients...")
    for i in range(5):
        sex = random.choice(['M', 'F'])
        fname = random.choice(first_names_m if sex == 'M' else first_names_f)
        lname = random.choice(last_names)
        
        user = CustomUser.objects.create(
            username=f"patient_{i}",
            email=f"patient{i}@test.com",
            password=make_password('testpass123'),
            first_name=fname,
            last_name=lname,
            role='patient',
            sex=sex,
            is_active=True,
            city=random.choice(CITIES),
            id_card_number=f"PAT{i}{random.randint(100000, 999999)}"
        )
        
        Patient.objects.create(
            user=user
        )

    print("💊 Création de 15 médicaments...")
    meds_data = [
        ("Lisinopril 10mg", "Lisinopril Dihydrate", "cardio", "Comprimé", 320, True),
        ("Metformin 500mg", "Metformin HCl", "diabetes", "Comprimé", 180, True),
        ("Vitamin D3 2000IU", "Cholecalciferol", "other", "Capsule", 450, False),
        ("Aspirin 100mg", "Acetylsalicylic Acid", "analgesic", "Comprimé", 90, False),
        ("Amoxicillin 500mg", "Amoxicillin Trihydrate", "antibiotic", "Gélule", 240, True),
        ("Omeprazole 20mg", "Omeprazole", "gastro", "Gélule", 280, True),
        ("Doliprane 1000mg", "Paracétamol", "analgesic", "Comprimé", 120, True),
        ("Spasfon", "Phloroglucinol", "gastro", "Comprimé", 200, True),
        ("Smecta", "Diosmectite", "gastro", "Sachet", 350, True),
        ("Augmentin 1g", "Amoxicilline + Acide Clavulanique", "antibiotic", "Sachet", 900, True),
        ("Levothyrox 50µg", "Levothyroxine", "other", "Comprimé", 150, True),
        ("Zyrtec 10mg", "Cétirizine", "other", "Comprimé", 250, True),
        ("Ibuprofène 400mg", "Ibuprofène", "anti_inflam", "Comprimé", 180, True),
        ("Ventoline 100µg", "Salbutamol", "other", "Aérosol", 450, True),
        ("Xanax 0.25mg", "Alprazolam", "neuro", "Comprimé", 300, True)
    ]
    for m in meds_data:
        Medication.objects.get_or_create(
            name=m[0],
            defaults={
                'molecule': m[1],
                'category': m[2],
                'form': m[3],
                'price_dzd': m[4],
                'cnas_covered': m[5],
                'is_active': True,
                'requires_prescription': True if m[2] in ['cardio', 'diabetes', 'antibiotic', 'neuro'] else False
            }
        )

    print("⚕️ Création de 3 pharmaciens et pharmacies...")
    for i in range(3):
        sex = random.choice(['M', 'F'])
        fname = random.choice(first_names_m if sex == 'M' else first_names_f)
        lname = random.choice(last_names)
        city = random.choice(CITIES)
        
        user = CustomUser.objects.create(
            username=f"pharmacist_{i}",
            email=f"pharmacist{i}@test.com",
            password=make_password('testpass123'),
            first_name=fname,
            last_name=lname,
            role='pharmacist',
            sex=sex,
            is_active=True,
            city=city,
            id_card_number=f"PHA{i}{random.randint(100000, 999999)}"
        )
        
        pharmacist = Pharmacist.objects.create(
            user=user,
            order_registration_number=f"PHARM-{random.randint(10000, 99999)}",
            is_verified=True,
            cnas_coverage=True
        )
        
        Pharmacy.objects.create(
            pharmacist=pharmacist,
            name=f"Pharmacie {lname}",
            pharm_address=f"Boulevard {random.randint(1, 50)} de la Santé",
            pharm_city=city,
            pharm_phone=f"021{random.randint(100000, 999999)}",
            is_open_24h=random.choice([True, False]),
            agreement_number=f"AGR-{random.randint(1000, 9999)}"
        )

    print("🩺 Création de 4 gardes-malades...")
    for i in range(4):
        sex = random.choice(['M', 'F'])
        fname = random.choice(first_names_m if sex == 'M' else first_names_f)
        lname = random.choice(last_names)
        city = random.choice(CITIES)
        
        user = CustomUser.objects.create(
            username=f"caretaker_{i}",
            email=f"caretaker{i}@test.com",
            password=make_password('testpass123'),
            first_name=fname,
            last_name=lname,
            role='caretaker',
            sex=sex,
            is_active=True,
            city=city,
            wilaya=city,
            id_card_number=f"CAR{i}{random.randint(100000, 999999)}"
        )
        
        Caretaker.objects.create(
            user=user,
            certification=random.choice(["Infirmière diplômée d'État", "Aide-soignant certifié", "Garde-malade certifiée"]),
            experience_years=random.randint(2, 15),
            tarif_de_base=Decimal(random.randint(1000, 3000)),
            bio=f"Garde-malade expérimenté(e) avec une excellente approche patient. Secteur: {city}.",
            is_verified=True,
            is_available=True
        )

    print("📅 Génération des plannings hebdomadaires des médecins...")
    today = date.today()
    for doctor in doctors_list:
        # Chaque médecin travaille du lundi au vendredi (0..4)
        for day in range(5):
            WeeklySchedule.objects.get_or_create(
                doctor=doctor,
                day_of_week=day,
                defaults={
                    'start_time': time(8, 0),
                    'end_time': time(17, 0),
                    'slot_duration': 30,
                    'is_active': True,
                },
            )

    print("🏥 Stock initial pour chaque pharmacie...")
    from pharmacy.models import Pharmacy as _Pharmacy
    all_meds = list(Medication.objects.all())
    for pharmacy in _Pharmacy.objects.all():
        for med in random.sample(all_meds, min(10, len(all_meds))):
            PharmacyStock.objects.get_or_create(
                pharmacy=pharmacy,
                medication=med,
                defaults={
                    'quantity': random.randint(15, 200),
                    'selling_price': med.price_dzd,
                    'expiry_date': today + timedelta(days=random.randint(60, 600)),
                },
            )

    print("📆 Création de 10 rendez-vous (pending/confirmed/completed)...")
    patients_list = list(Patient.objects.all())
    statuses_cycle = ['pending', 'pending', 'pending',
                      'confirmed', 'confirmed', 'confirmed', 'confirmed',
                      'completed', 'completed', 'completed']
    random.shuffle(statuses_cycle)
    created_appts = 0
    for i, status_val in enumerate(statuses_cycle):
        if not patients_list or not doctors_list:
            break
        patient = patients_list[i % len(patients_list)]
        doctor = doctors_list[i % len(doctors_list)]
        # offset : passé pour completed, futur pour pending/confirmed
        day_offset = -random.randint(1, 30) if status_val == 'completed' else random.randint(1, 10)
        appt_date = today + timedelta(days=day_offset)
        hour = random.choice([9, 10, 11, 14, 15, 16])
        try:
            appt = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                date=appt_date,
                start_time=time(hour, 0),
                end_time=time(hour, 30),
                motif=random.choice([
                    "Consultation de contrôle",
                    "Douleurs abdominales",
                    "Renouvellement ordonnance",
                    "Suivi post-opératoire",
                    "Première consultation",
                ]),
                status=status_val,
            )
            created_appts += 1
            # Notification pour le médecin à la création du RDV
            Notification.objects.create(
                user=doctor.user,
                title="Nouvelle réservation",
                message=f"Nouveau RDV — {patient.user.get_full_name()} ({appt.date})",
                notification_type=Notification.NotificationType.APPOINTMENT,
            )
            # Notification pour le patient sur confirmé / refusé
            if status_val == 'confirmed':
                Notification.objects.create(
                    user=patient.user,
                    title="Rendez-vous confirmé",
                    message=f"Votre RDV avec Dr.{doctor.user.last_name} est confirmé.",
                    notification_type=Notification.NotificationType.APPOINTMENT,
                )
        except Exception as e:
            print(f"  ⚠️ appointment skipped: {e}")

    print(f"  → {created_appts} RDV créés")

    # --- DONNÉES SPÉCIFIQUES POUR DASHBOARD PATIENT (patient0@test.com) ---
    print("📈 Peuplage des données spécifiques pour le Dashboard Patient (patient0)...")
    try:
        p0_user = CustomUser.objects.get(email="patient0@test.com")
        p0 = Patient.objects.get(user=p0_user)
        doc0 = Doctor.objects.first()
        
        # 1. Consultation
        from consultations.models import Consultation
        consult = Consultation.objects.create(
            doctor=doc0,
            patient=p0,
            consultation_type='in_person',
            status='completed',
            chief_complaint="Suivi de routine - Hypertension",
            diagnosis="Hypertension artérielle stabilisée",
            consulted_at=timezone.now() - timedelta(days=5)
        )
        
        # 2. Prescription
        from prescriptions.models import Prescription, PrescriptionItem
        rx = Prescription.objects.create(
            consultation=consult,
            status='active',
            valid_until=timezone.now().date() + timedelta(days=90),
            notes="À prendre régulièrement."
        )
        
        # 3. Items de prescription
        med1 = Medication.objects.get(name="Lisinopril 10mg")
        PrescriptionItem.objects.create(
            prescription=rx,
            medication=med1,
            drug_name=med1.name,
            dosage="10mg",
            frequency='1x_day',
            duration="3 mois"
        )
        
        # 4. Traitements en cours
        from patients.models import Treatment, MedicalDocument
        Treatment.objects.create(
            patient=p0,
            prescribed_by=doc0,
            medication=med1,
            medication_name=med1.name,
            dosage="1 comprimé",
            frequency='1x_day',
            start_date=timezone.now().date() - timedelta(days=30),
            is_ongoing=True
        )
        
        # 5. Documents médicaux
        MedicalDocument.objects.create(
            patient=p0,
            name="Bilan Sanguin Complet",
            document_type='lab_result',
            date=timezone.now().date() - timedelta(days=10),
            uploaded_by=doc0.user
        )
        MedicalDocument.objects.create(
            patient=p0,
            name="Radiographie Thoracique",
            document_type='imaging',
            date=timezone.now().date() - timedelta(days=20),
            uploaded_by=doc0.user
        )
        
        print("✅ Données de test pour patient0 créées !")
    except Exception as e:
        print(f"⚠️ Erreur lors du peuplage patient0: {e}")

    print("\n✅ Base de données initialisée avec succès !")
    print(f"--- {Doctor.objects.count()} Docteurs créés")
    print(f"--- {Patient.objects.count()} Patients créés")

    print("\n--- INFOS DE TEST ---")
    print("Mot de passe global : testpass123")
    print(f"Exemple docteur : {doctors_list[0].user.email}")
    print("Exemple patient : patient0@test.com")

if __name__ == '__main__':
    populate()
