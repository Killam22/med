# 🏥 Backend Django — Système de Prise de Rendez-vous Médical

API REST complète pour la gestion de rendez-vous médicaux entre patients et médecins. Authentification JWT, gestion des créneaux, réservation, annulation et planning.

---

## 🗂 Structure du projet

```
appointment back/
├── appointment_backend/        # Config Django
│   ├── settings.py
│   └── urls.py
├── appointments/               # App principale
│   ├── models.py               # CustomUser, Patient, Doctor, AvailabilitySlot, Appointment
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── permissions.py
│   └── admin.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🚀 Lancer le projet

### 1. Créer un environnement virtuel (recommandé)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Appliquer les migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Créer un superutilisateur (accès admin)
```bash
python manage.py createsuperuser
```

### 5. Lancer le serveur de développement
```bash
python manage.py runserver
```

L'API est disponible sur : **http://127.0.0.1:8000/api/**  
L'interface admin : **http://127.0.0.1:8000/admin/**

---

## 🔐 Authentification JWT

### Inscription Patient
```http
POST /api/auth/register/patient/
Content-Type: application/json

{
  "email": "patient@example.com",
  "first_name": "Mériem",
  "last_name": "Kaci",
  "password": "motdepasse123",
  "password2": "motdepasse123",
  "phone": "+213 550 000 001",
  "city": "Alger",
  "date_of_birth": "1992-05-14"
}
```

### Inscription Médecin
```http
POST /api/auth/register/doctor/
Content-Type: application/json

{
  "email": "docteur@example.com",
  "first_name": "Sarah",
  "last_name": "Smith",
  "password": "motdepasse123",
  "password2": "motdepasse123",
  "specialty": "cardiology",
  "license_number": "ALG-2024-001",
  "clinic_name": "Clinique El Rahma",
  "city": "Alger",
  "experience_years": 12,
  "accepts_teleconsultation": true
}
```

### Login → Récupérer les tokens JWT
```http
POST /api/auth/token/
Content-Type: application/json

{
  "email": "patient@example.com",
  "password": "motdepasse123"
}
```

**Réponse :**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "role": "patient",
  "full_name": "Mériem Kaci",
  "email": "patient@example.com"
}
```

### Rafraîchir le token
```http
POST /api/auth/token/refresh/
Content-Type: application/json

{ "refresh": "eyJ..." }
```

> Toutes les requêtes suivantes nécessitent l'en-tête :  
> `Authorization: Bearer <access_token>`

---

## 👩‍⚕️ Endpoints — Patient

### Rechercher des médecins
```http
GET /api/doctors/?specialty=cardiology&city=Alger
GET /api/doctors/?search=Sarah
GET /api/doctors/?ordering=-rating
```

### Voir le profil complet d'un médecin
```http
GET /api/doctors/1/
```

### Voir les créneaux disponibles d'un médecin
```http
GET /api/doctors/1/slots/
GET /api/doctors/1/slots/?date=2026-03-20
GET /api/doctors/1/slots/?slot_type=tele
```

### Réserver un rendez-vous
```http
POST /api/appointments/
Content-Type: application/json

{
  "doctor": 1,
  "slot": 5,
  "motif": "Douleurs thoraciques - première consultation"
}
```

### Voir mes rendez-vous
```http
GET /api/appointments/
GET /api/appointments/?status=pending
GET /api/appointments/?status=confirmed
```

### Annuler un rendez-vous
```http
POST /api/appointments/3/cancel/
```

### Modifier (reprogrammer) un rendez-vous
```http
POST /api/appointments/3/reschedule/
Content-Type: application/json

{ "slot_id": 12 }
```

### Mon profil patient
```http
GET /api/patient/profile/
PUT /api/patient/profile/
```

---

## 🩺 Endpoints — Médecin

### Mon profil médecin
```http
GET /api/doctor/profile/
PUT /api/doctor/profile/
```

### Créer un créneau disponible
```http
POST /api/doctor/slots/
Content-Type: application/json

{
  "date": "2026-03-20",
  "start_time": "09:00",
  "end_time": "09:30",
  "slot_type": "in_person"
}
```

### Voir / modifier / supprimer mes créneaux
```http
GET    /api/doctor/slots/
GET    /api/doctor/slots/?date=2026-03-20
GET    /api/doctor/slots/?is_booked=false
PUT    /api/doctor/slots/5/
DELETE /api/doctor/slots/5/
```

### Voir les demandes de rendez-vous
```http
GET /api/doctor/appointments/
GET /api/doctor/appointments/?status=pending
GET /api/doctor/appointments/?date=2026-03-20
```

### Confirmer un rendez-vous
```http
POST /api/doctor/appointments/3/confirm/
```

### Refuser un rendez-vous
```http
POST /api/doctor/appointments/3/refuse/
Content-Type: application/json

{ "reason": "Indisponible ce jour-là" }
```

### Marquer comme terminé + notes
```http
POST /api/doctor/appointments/3/complete/
Content-Type: application/json

{ "notes": "Patient suivi pour hypertension. Prochain RDV dans 3 mois." }
```

---

## 📋 Modèles de données

### CustomUser
| Champ | Type | Description |
|-------|------|-------------|
| email | EmailField | Identifiant unique |
| first_name / last_name | CharField | Nom complet |
| role | CharField | `patient` / `doctor` / `admin` |

### Patient
| Champ | Type |
|-------|------|
| date_of_birth | DateField |
| phone, address, city | CharField |
| blood_type | CharField |
| medical_history | TextField |

### Doctor
| Champ | Type |
|-------|------|
| specialty | ChoiceField (12 spécialités) |
| license_number | CharField |
| clinic_name, city, address | CharField |
| experience_years | IntegerField |
| consultation_fee | DecimalField |
| rating, total_reviews | Computed |
| accepts_teleconsultation | BooleanField |
| accepts_home_visit | BooleanField |

### AvailabilitySlot
| Champ | Type |
|-------|------|
| date | DateField |
| start_time / end_time | TimeField |
| slot_type | `in_person` / `tele` / `home` |
| is_booked | BooleanField |

### Appointment
| Champ | Type |
|-------|------|
| patient, doctor | ForeignKey |
| slot | OneToOneField |
| motif | CharField |
| status | `pending` / `confirmed` / `cancelled` / `refused` / `completed` |
| appointment_type | (hérité du slot) |
| notes | TextField (médecin) |
| refusal_reason | TextField |

---

## ⚙️ Variables d'environnement (Production)

Créer un fichier `.env` et adapter `settings.py` :

```env
SECRET_KEY=votre-cle-secrete
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
CORS_ALLOWED_ORIGINS=https://votre-frontend.com
```

---

## 🔧 Spécialités disponibles

`cardiology`, `dermatology`, `general`, `neurology`, `pediatrics`, `dentistry`, `ophthalmology`, `orthopedics`, `gynecology`, `psychiatry`, `physiotherapy`, `other`
