import urllib.request, json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first()
if not admin:
    print('AUCUN SUPERUSER')
    exit(1)

refresh = RefreshToken.for_user(admin)
access_token = str(refresh.access_token)
print("Admin:", admin.email)
print("Token OK:", access_token[:40] + "...")

BASE = "http://127.0.0.1:8000"
HEADERS = {"Authorization": "Bearer " + access_token}

def get_json(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

# Test 1: admin dashboard
status, data = get_json("/api/admin/dashboard/")
print("\nGET /api/admin/dashboard/ ->", status)
if status == 200:
    kpis = data.get("kpis", {})
    for k, v in kpis.items():
        print(" ", k, "=", v)
else:
    print("  ERROR:", data)

# Test 2: admin users list
status2, data2 = get_json("/api/admin/users/?page=1")
print("\nGET /api/admin/users/ ->", status2)
if status2 == 200:
    results = data2.get("results", data2) if isinstance(data2, dict) else data2
    print("  count =", data2.get("count", len(results) if isinstance(results, list) else "?"))
    if isinstance(results, list) and results:
        first = results[0]
        print("  Fields:", list(first.keys()))
        print("  first_name:", first.get("first_name"))
        print("  phone:", first.get("phone"))
        print("  wilaya:", first.get("wilaya"))
else:
    print("  ERROR:", data2)

# Test 3: pending validation
status3, data3 = get_json("/api/admin/users/?verification_status=pending")
print("\nGET /api/admin/users/?verification_status=pending ->", status3)
if status3 == 200:
    results3 = data3.get("results", data3) if isinstance(data3, dict) else data3
    print("  pending count =", len(results3) if isinstance(results3, list) else data3.get("count", "?"))
else:
    print("  ERROR:", data3)

# Test 4: audit logs
status4, data4 = get_json("/api/admin/audit-logs/")
print("\nGET /api/admin/audit-logs/ ->", status4)
if status4 == 200:
    logs = data4.get("results", data4) if isinstance(data4, dict) else data4
    print("  logs count =", len(logs) if isinstance(logs, list) else data4.get("count", "?"))
    if isinstance(logs, list) and logs:
        print("  sample:", logs[0])
else:
    print("  ERROR:", data4)

# Test 5: appointments (admin route)
status5, data5 = get_json("/api/admin/appointments/")
print("\nGET /api/admin/appointments/ ->", status5)
if status5 == 200:
    results5 = data5.get("results", data5) if isinstance(data5, dict) else data5
    print("  appointments count =", data5.get("count", len(results5) if isinstance(results5, list) else "?"))
    if isinstance(results5, list) and results5:
        print("  sample:", results5[0])
else:
    print("  Response:", data5[:200] if isinstance(data5, str) else data5)

print("\n=== ALL TESTS DONE ===")
