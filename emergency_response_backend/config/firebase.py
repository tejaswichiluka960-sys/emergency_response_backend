import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
service_account_path = BASE_DIR / "config" / "service-account.json"

if not firebase_admin._apps:
    if service_account_path.exists():
        cred = credentials.Certificate(str(service_account_path))
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully")
    else:
        logger.warning(
            "Firebase service-account.json not found at %s. Firebase push notifications may not function.",
            service_account_path
        )