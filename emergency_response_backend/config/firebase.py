import firebase_admin
from firebase_admin import credentials
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

service_account_path = BASE_DIR / "config" / "service-account.json"

cred = credentials.Certificate(str(service_account_path))

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

print("Firebase initialized successfully")