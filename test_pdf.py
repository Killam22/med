import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from prescriptions.models import Prescription
from prescriptions.services import PDFService

try:
    p = Prescription.objects.first()
    if p:
        print(f"Generating PDF for prescription {p.id}...")
        pdf = PDFService.generate(p)
        with open('test_output.pdf', 'wb') as f:
            f.write(pdf)
        print("PDF generated successfully: test_output.pdf")
    else:
        print("No prescriptions found in database.")
except Exception as e:
    import traceback
    traceback.print_exc()
