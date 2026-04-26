import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

users = User.objects.all()

roles_dict = {
    'admin': [],
    'patient': [],
    'doctor': [],
    'pharmacist': [],
    'caretaker': []
}

for user in users:
    role = user.role if hasattr(user, 'role') and user.role else 'admin'
    if user.is_superuser or user.is_staff:
        role = 'admin'
    if role in roles_dict:
        roles_dict[role].append(user.email)
    else:
        roles_dict[role] = [user.email]

print("| Rôle | Emails (Mot de passe: testpass123) |")
print("|---|---|")

for role, emails in roles_dict.items():
    if not emails:
        continue
    # Capitalize the role name for the table
    role_name = role.capitalize()
    
    # Format emails as a markdown list or comma separated
    formatted_emails = "<br>".join([f"`{email}`" for email in emails])
    print(f"| **{role_name}** | {formatted_emails} |")
