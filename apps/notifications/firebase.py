import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

if not firebase_admin._apps:
    # Try environment variable first, then settings/django paths
    env_path = os.getenv("FIREBASE_CREDENTIALS")
    base_dir = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))

    possible_paths = []
    if env_path:
        possible_paths.append(env_path)
        # Also try relative to base dir if env path is relative
        possible_paths.append(os.path.join(base_dir, env_path.lstrip('/')))

    possible_paths.extend([
        os.path.join(base_dir, "firebase", "firebase-service-account.json"),
        os.path.join(base_dir, "firebase", "serviceAccountKey.json"),
        "/app/firebase/firebase-service-account.json",
        "/app/firebase-service-account.json",
        "firebase/firebase-service-account.json",
        "firebase/serviceAccountKey.json"
    ])
    
    cred_file = None
    for path in possible_paths:
        if os.path.exists(path):
            cred_file = path
            break
            
    if not cred_file:
        # Fallback to avoid breaking build, log warning instead of crashing
        print("[WARNING] Firebase credentials file not found! Push notifications will fail.")
    else:
        print(f"[OK] Firebase initialized with credentials at: {cred_file}")
        cred = credentials.Certificate(cred_file)
        firebase_admin.initialize_app(cred)