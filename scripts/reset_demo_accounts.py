"""
Supprime proprement tous les comptes de démonstration et leurs données liées.
Lancer : python manage.py shell -c "exec(open('scripts/reset_demo_accounts.py', encoding='utf-8').read())"
"""
from django.contrib.auth import get_user_model
from appointments.models import Appointment
from consultations.models import Consultation
from pharmacy.models import PharmacyOrder
from notifications.models import Notification
from patients.models import Patient
from doctors.models import Doctor

User = get_user_model()

DEMO_EMAILS = [
    'sarah.benali@demo.com',
    'karim.meziane@demo.com',
    'dr.yacine.bensaid@demo.com',
    'dr.amina.khelifi@demo.com',
    'pharmacie.elshifa@demo.com',
    'fatima.hadj@demo.com',
]

users       = User.objects.filter(email__in=DEMO_EMAILS)
demo_docs   = Doctor.objects.filter(user__in=users)
demo_pats   = Patient.objects.filter(user__in=users)

# 1. PharmacyOrders en premier (FK PROTECT vers Prescription)
n, _ = PharmacyOrder.objects.filter(patient__in=users).delete()
print(f"  Commandes pharmacie supprimées : {n}")

# 2. Notifications
n, _ = Notification.objects.filter(user__in=users).delete()
print(f"  Notifications supprimées : {n}")

# 3. Consultations → cascade Prescriptions → PrescriptionItems
n, _ = Consultation.objects.filter(doctor__in=demo_docs).delete()
print(f"  Consultations + ordonnances supprimées : {n}")

# 4. Appointments
n, _ = Appointment.objects.filter(patient__in=demo_pats).delete()
n2, _ = Appointment.objects.filter(doctor__in=demo_docs).delete()
print(f"  Rendez-vous supprimés : {n + n2}")

# 5. Users → cascade Patient/Doctor/Pharmacist/Caretaker/MedicalProfile/Allergy/Antecedent
n, _ = users.delete()
print(f"  Utilisateurs + profils supprimés : {n}")

print("✅ Réinitialisation terminée. Vous pouvez relancer create_demo_accounts.py")
