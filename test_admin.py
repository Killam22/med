import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.test import RequestFactory
from rest_framework.test import APIClient

User = get_user_model()

print("=== ADMINS ===")
admins = User.objects.filter(role='admin')
for u in admins:
    print(f"  id={u.id} email={u.email} superuser={u.is_superuser} active={u.is_active}")
if not admins.exists():
    print("  AUCUN ADMIN TROUVÉ")

print("\n=== STATS ===")
print(f"  Total users: {User.objects.count()}")
roles = ['doctor', 'pharmacist', 'caretaker']
pending = User.objects.filter(role__in=roles, verification_status='pending').count()
print(f"  Pending validation: {pending}")

for r in User.objects.values("role").annotate(c=Count("id")):
    print(f"  {r['role']}: {r['c']}")

print("\n=== USER MODEL FIELDS ===")
u = User.objects.first()
if u:
    fields_to_check = ['first_name', 'last_name', 'phone_number', 'wilaya', 'email', 'role', 'verification_status']
    for f in fields_to_check:
        try:
            val = getattr(u, f, '__MISSING__')
            print(f"  {f} = {repr(val)}")
        except Exception as e:
            print(f"  {f} => ERROR: {e}")

print("\n=== TEST API CLIENT - ADMIN DASHBOARD ===")
admin = User.objects.filter(role='admin').first() or User.objects.filter(is_superuser=True).first()
if admin:
    client = APIClient()
    client.force_authenticate(user=admin)
    response = client.get('/api/admin/dashboard/')
    print(f"  GET /api/admin/dashboard/ -> {response.status_code}")
    if response.status_code == 200:
        import json
        data = response.json()
        print(f"  kpis: {json.dumps(data.get('kpis', {}), indent=4)}")
    else:
        print(f"  Erreur: {response.content[:200]}")
    
    print("\n=== TEST - USERS LIST ===")
    response2 = client.get('/api/admin/users/')
    print(f"  GET /api/admin/users/ -> {response2.status_code}")
    if response2.status_code == 200:
        data2 = response2.json()
        users_list = data2 if isinstance(data2, list) else data2.get('results', [])
        print(f"  Total returned: {len(users_list)}")
        if users_list:
            first = users_list[0]
            print(f"  First user fields: {list(first.keys())}")
    else:
        print(f"  Erreur: {response2.content[:200]}")
    
    print("\n=== TEST - PENDING VALIDATION ===")
    response3 = client.get('/api/admin/users/?verification_status=pending')
    print(f"  GET /api/admin/users/?verification_status=pending -> {response3.status_code}")
    if response3.status_code == 200:
        data3 = response3.json()
        users_list3 = data3 if isinstance(data3, list) else data3.get('results', [])
        print(f"  Pending users: {len(users_list3)}")
        if users_list3:
            print(f"  First pending user: {users_list3[0]}")
    else:
        print(f"  Erreur: {response3.content[:200]}")

    print("\n=== TEST - AUDIT LOGS ===")
    response4 = client.get('/api/admin/audit-logs/')
    print(f"  GET /api/admin/audit-logs/ -> {response4.status_code}")
    if response4.status_code == 200:
        data4 = response4.json()
        logs = data4 if isinstance(data4, list) else data4.get('results', [])
        print(f"  Audit logs count: {len(logs)}")
    else:
        print(f"  Erreur: {response4.content[:200]}")
else:
    print("  PAS D'ADMIN - impossible de tester")

print("\n=== DONE ===")
