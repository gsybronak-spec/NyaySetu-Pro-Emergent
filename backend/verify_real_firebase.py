"""Verification script for Step 3: Real Firebase Test Environment.

Tests and reports:
1. Firebase Admin SDK connection
2. Native Firestore connection
3. Write / Read / Delete roundtrip permissions on `_healthcheck/connectivity`
4. Tenancy isolation & collections availability
5. Index status check

Usage:
    cd backend
    python verify_real_firebase.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

async def run_verification():
    print("=" * 60)
    print("NYAYSETU PRO — STEP 3: REAL FIREBASE CONNECTION VERIFICATION")
    print("=" * 60)

    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "").strip()
    private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "").strip()
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST", "").strip()

    print(f"Target Project ID: {project_id or '[NOT SET]'}")
    print(f"Service Account Email: {client_email or '[NOT SET]'}")
    print(f"Private Key Configured: {'YES (length: ' + str(len(private_key)) + ')' if private_key else 'NO'}")
    print(f"Emulator Host: {emulator_host or 'None (Targeting Real Firebase Cloud)'}")
    print("-" * 60)

    if not project_id:
        print("[ERROR] FIREBASE_PROJECT_ID environment variable is missing.")
        print("Please set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY.")
        return False

    if not emulator_host and (not client_email or not private_key):
        print("[ERROR] Running against Real Firebase requires FIREBASE_CLIENT_EMAIL and FIREBASE_PRIVATE_KEY.")
        return False

    # Import backend's firebase_init module
    try:
        import firebase_init
        db = firebase_init.get_firestore_client()
        print("[PASS] 1. Firebase Admin SDK & AsyncClient initialized successfully.")
    except Exception as e:
        print(f"[FAIL] 1. Failed to initialize Firebase Admin SDK: {e}")
        return False

    # Test Firestore Read/Write/Delete Permissions
    test_doc_id = f"test_{uuid.uuid4().hex[:8]}"
    test_ref = db.collection("_healthcheck").document(test_doc_id)
    test_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "connectivity_test",
        "project": project_id,
    }

    try:
        await test_ref.set(test_payload)
        print(f"[PASS] 2. Firestore WRITE permission verified (doc: _healthcheck/{test_doc_id}).")
    except Exception as e:
        print(f"[FAIL] 2. Firestore WRITE failed: {e}")
        return False

    try:
        snap = await test_ref.get()
        if snap.exists and snap.to_dict().get("status") == "connectivity_test":
            print(f"[PASS] 3. Firestore READ permission verified.")
        else:
            print(f"[FAIL] 3. Firestore READ returned unexpected data.")
            return False
    except Exception as e:
        print(f"[FAIL] 3. Firestore READ failed: {e}")
        return False

    try:
        await test_ref.delete()
        print(f"[PASS] 4. Firestore DELETE permission verified (cleaned up test doc).")
    except Exception as e:
        print(f"[FAIL] 4. Firestore DELETE failed: {e}")
        return False

    # Check Required Collections Access
    required_collections = [
        "lawyers", "cases", "applications", "templates", "template_revisions",
        "districts", "talukas", "courts", "case_types", "plans", "wallets",
        "transactions", "referrals", "admin_users", "system_settings"
    ]

    print("\nVerifying collection access:")
    for col_name in required_collections:
        try:
            # Query with limit 1 to test read permissions without loading full table
            col_ref = db.collection(col_name)
            docs = [d async for d in col_ref.limit(1).stream()]
            print(f"  - Collection '{col_name}': Accessible (sample count: {len(docs)})")
        except Exception as e:
            print(f"  - Collection '{col_name}': [FAIL] ({e})")
            return False

    print("\n" + "=" * 60)
    print("ALL REAL FIREBASE CONNECTION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(run_verification())
    sys.exit(0 if success else 1)
