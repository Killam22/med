import os
import django
import random
from datetime import date, timedelta, time, datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appointment_backend.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from users.models import CustomUser
from doctors.models import Doctor, Exercice
from patients.models import Patient
from appointments.models import AvailabilitySlot

def populate():
    print("🧹 Nettoyage de la base de données...")
    # Supprimer les utilisateurs supprimera par cascade les profils Doctor et Patient
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
            city=city,
            wilaya=city,
            phone=f"0550{random.randint(100000, 999999)}",
            verification_status='verified'
        )
        
        doctor = Doctor.objects.create(
            user=user,
            specialty=spec,
            license_number=f"LIC-{random.randint(10000, 99999)}",
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
            address=f"Rue {random.randint(1, 100)} de la Liberté",
            city=city,
            phone=user.phone,
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
            city=random.choice(CITIES)
        )
        
        Patient.objects.create(
            user=user,
            blood_group=random.choice(['A+', 'B+', 'O+', 'O-', 'AB+']),
            medical_history="Aucun antécédent particulier."
        )

    print("📅 Génération des créneaux de disponibilité (7 prochains jours)...")
    today = date.today()
    
    for doctor in doctors_list:
        # Créer des créneaux pour les 7 prochains jours
        for day_offset in range(7):
            current_date = today + timedelta(days=day_offset)
            
            # 2 créneaux d'une heure par jour pour chaque doc pour le test
            times = [time(9, 0), time(10, 0), time(14, 0), time(15, 0)]
            selected_times = random.sample(times, 2)
            
            for start_t in selected_times:
                AvailabilitySlot.objects.create(
                    doctor=doctor,
                    date=current_date,
                    start_time=start_t,
                    end_time=(datetime.combine(date.today(), start_t) + timedelta(minutes=60)).time(),
                    is_booked=False
                )

    print("\n✅ Base de données initialisée avec succès !")
    print(f"--- {Doctor.objects.count()} Docteurs créés")
    print(f"--- {Patient.objects.count()} Patients créés")
    print(f"--- {AvailabilitySlot.objects.count()} Créneaux créés")
    print("\n--- INFOS DE TEST ---")
    print("Mot de passe global : testpass123")
    print(f"Exemple docteur : {doctors_list[0].user.email}")
    print("Exemple patient : patient0@test.com")

if __name__ == '__main__':
    populate()
