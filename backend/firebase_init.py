"""Firebase Admin SDK initialization — idempotent for Vercel serverless.

This module initializes the Firebase Admin SDK exactly ONCE per process
and exposes the Firestore client as `firestore_db`. Vercel cold-starts
create a new process each time, so initialize_app() runs once per
invocation lifecycle.

Required environment variables (set in Vercel dashboard):
    FIREBASE_PROJECT_ID
    FIREBASE_CLIENT_EMAIL
    FIREBASE_PRIVATE_KEY  (with escaped \\n newlines)

Optional:
    FIREBASE_PRIVATE_KEY_ID
    FIREBASE_CLIENT_ID
    FIREBASE_CLIENT_X509_CERT_URL
    FIRESTORE_EMULATOR_HOST  (for local dev / testing)
"""

import os
import logging

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger("nyaysetu.firebase")

_app = None


def _get_firebase_app():
    """Return the singleton Firebase app, creating it if needed."""
    global _app
    if _app is not None:
        return _app

    # Check if already initialized (defensive — another module may init first)
    try:
        _app = firebase_admin.get_app()
        return _app
    except ValueError:
        pass  # No app exists yet — initialize below

    # If the emulator is in use, we can initialize without credentials
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST", "").strip()

    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "").strip()
    private_key_raw = os.environ.get("FIREBASE_PRIVATE_KEY", "").strip()

    if private_key_raw and client_email and project_id:
        # Production / Vercel: use service-account credentials from env vars
        private_key = private_key_raw.replace("\\n", "\n")
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": private_key,
            "client_email": client_email,
            "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ.get(
                "FIREBASE_CLIENT_X509_CERT_URL", ""
            ),
        }
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred)
        logger.info("[Firebase] Initialized with service-account credentials")
    elif emulator_host:
        # Local dev: emulator mode — no real credentials needed
        _app = firebase_admin.initialize_app(
            options={"projectId": project_id or "nyaysetu-dev"}
        )
        logger.info(
            f"[Firebase] Initialized in emulator mode (host={emulator_host})"
        )
    elif project_id:
        # Application Default Credentials (e.g., running on GCP)
        _app = firebase_admin.initialize_app(
            options={"projectId": project_id}
        )
        logger.info("[Firebase] Initialized with application default credentials")
    else:
        # No credentials at all — fail at startup so the error is clear
        raise RuntimeError(
            "Firebase credentials are not configured. Set FIREBASE_PROJECT_ID, "
            "FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY in the environment, "
            "or set FIRESTORE_EMULATOR_HOST for local development."
        )

    return _app


from google.cloud import firestore as google_firestore

def get_firestore_client():
    """Return the Async Firestore client, initializing the Firebase app if needed."""
    _get_firebase_app()
    # In order to use AsyncClient, we instantiate it directly from google.cloud.firestore
    # We must provide the project ID.
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "demo-nyaysetu")
    
    # If running against the emulator, we need dummy credentials to avoid ADC crash
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        from google.auth.credentials import AnonymousCredentials
        return google_firestore.AsyncClient(project=project_id, credentials=AnonymousCredentials())
    
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "").strip()
    private_key_raw = os.environ.get("FIREBASE_PRIVATE_KEY", "").strip()
    if private_key_raw and client_email:
        from google.oauth2 import service_account
        private_key = private_key_raw.replace("\\n", "\n")
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": private_key,
            "client_email": client_email,
            "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ.get(
                "FIREBASE_CLIENT_X509_CERT_URL", ""
            ),
        }
        creds = service_account.Credentials.from_service_account_info(cred_dict)
        return google_firestore.AsyncClient(project=project_id, credentials=creds)

    return google_firestore.AsyncClient(project=project_id)

# Eagerly initialize on import so server.py can reference `firestore_db`
# immediately. In test environments the caller patches this before import.
try:
    firestore_db = get_firestore_client()
except Exception:
    firestore_db = None
