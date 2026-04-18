import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

tables = [
    'patients_allergy', 'patients_documentfile', 'patients_medicaldocument',
    'patients_treatment', 'patients_antecedent', 'patients_medicalprofile',
    'patients_patient'
]

with connection.cursor() as cursor:
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"Dropped {table}")
        except Exception as e:
            print(f"Failed to drop {table}: {e}")
            
    try:
        cursor.execute("DELETE FROM django_migrations WHERE app='patients';")
        print("Cleared django_migrations for 'patients'.")
    except Exception as e:
        print(f"Failed to clear migrations: {e}")
