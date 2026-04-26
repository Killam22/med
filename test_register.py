import requests
import io
from PIL import Image

base_url = "http://127.0.0.1:8000/api"

# Create valid dummy images using PIL
def create_dummy_image():
    file = io.BytesIO()
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    image.save(file, "jpeg")
    file.seek(0)
    return file

print("--- Registering Patient ---")
register_data = {
    "email": "test_patient_125@example.com",
    "password": "Password123!",
    "password_confirm": "Password123!",
    "role": "patient",
    "first_name": "Test",
    "last_name": "Patient",
    "phone": "0555000000",
    "date_of_birth": "1990-01-01",
    "sex": "male",
    "address": "123 Rue Test",
    "id_card_number": "1234567892",
    "postal_code": "16000",
    "city": "Alger",
    "wilaya": "Alger",
}

files = {
    "id_card_recto": ("recto.jpg", create_dummy_image(), "image/jpeg"),
    "id_card_verso": ("verso.jpg", create_dummy_image(), "image/jpeg"),
    "photo": ("photo.jpg", create_dummy_image(), "image/jpeg")
}

resp = requests.post(f"{base_url}/auth/register/patient/", data=register_data, files=files)
print("Status:", resp.status_code)
try:
    print(resp.json())
except:
    print(resp.text)

print("\n--- Logging in ---")
login_data = {
    "email": "test_patient_125@example.com",
    "password": "Password123!"
}
resp2 = requests.post(f"{base_url}/auth/login/", json=login_data)
print("Status:", resp2.status_code)
try:
    print(resp2.json())
except:
    print(resp2.text)
