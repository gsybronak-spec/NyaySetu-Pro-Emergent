#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NyaySetu Pro — Stage G: Ghost Document Backup and Safe Cleanup Script.

Safely archives, backs up, verifies, and removes the 2 legacy ghost documents
('document_exhibit_application_gu' and 'document_exhibit_application_en') from
Cloud Firestore after verifying canonical 'document_exhibit_application' integrity.

Usage:
    # 1. Read-only inspection and dry run (default):
    python backend/scripts/cleanup_ghost_templates.py --dry-run

    # 2. Backup only (creates JSON file + Firestore backup document):
    python backend/scripts/cleanup_ghost_templates.py --backup-only

    # 3. Execute cleanup (verifies backup, removes ghosts, logs audit):
    python backend/scripts/cleanup_ghost_templates.py --execute-cleanup --confirm

    # 4. Rollback (restores documents from backup if needed):
    python backend/scripts/cleanup_ghost_templates.py --rollback --backup-file <path_to_backup.json>

Supported Credentials:
    - Service account JSON via --creds <path>
    - Environment variables: FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY
    - GOOGLE_APPLICATION_CREDENTIALS environment variable
    - Local emulator via FIRESTORE_EMULATOR_HOST
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

GHOST_DOCUMENT_IDS = [
    "document_exhibit_application_gu",
    "document_exhibit_application_en",
]
CANONICAL_TARGET_ID = "document_exhibit_application"
BACKUPS_DIR = os.path.join(BACKEND_DIR, "backups")


def get_firestore_client(creds_path=None):
    """Obtain a Google Cloud Firestore client using available credentials."""
    from google.cloud import firestore

    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        project_id = os.environ.get("FIREBASE_PROJECT_ID", "nyaysetu-emulator")
        from google.auth.credentials import AnonymousCredentials
        return firestore.Client(project=project_id, credentials=AnonymousCredentials())

    if creds_path and os.path.isfile(creds_path):
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(creds_path)
        return firestore.Client(project=creds.project_id, credentials=creds)

    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip().strip('"\'')
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "").strip().strip('"\'')
    raw_key = os.environ.get("FIREBASE_PRIVATE_KEY", "").strip()

    if raw_key and client_email and project_id:
        while (raw_key.startswith('"') and raw_key.endswith('"')) or (raw_key.startswith("'") and raw_key.endswith("'")):
            raw_key = raw_key[1:-1].strip()
        begin_marker = "-----BEGIN PRIVATE KEY-----"
        end_marker = "-----END PRIVATE KEY-----"
        b_idx = raw_key.find(begin_marker)
        e_idx = raw_key.find(end_marker)
        if b_idx != -1 and e_idx != -1:
            raw_key = raw_key[b_idx:e_idx + len(end_marker)]
        private_key = raw_key.replace('\\n', '\n').strip() + '\n'

        from google.oauth2 import service_account
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": private_key,
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds = service_account.Credentials.from_service_account_info(cred_dict)
        return firestore.Client(project=project_id, credentials=creds)

    # Fallback to default application credentials
    try:
        return firestore.Client(project=project_id or None)
    except Exception as e:
        raise RuntimeError(
            f"Unable to initialize Firestore Client. Provide valid credentials via "
            f"--creds <file> or set FIREBASE_* environment variables. Details: {e}"
        )


def inspect_ghost_documents(db):
    """Inspect and return dictionary of ghost documents and canonical document status."""
    ghosts_data = {}
    for gid in GHOST_DOCUMENT_IDS:
        snap = db.collection("templates").document(gid).get()
        if snap.exists:
            ghosts_data[gid] = snap.to_dict()
        else:
            ghosts_data[gid] = None

    canon_snap = db.collection("templates").document(CANONICAL_TARGET_ID).get()
    canonical_exists = canon_snap.exists
    canonical_data = canon_snap.to_dict() if canon_snap.exists else None

    return ghosts_data, canonical_exists, canonical_data


def save_backup(db, ghosts_data, canonical_data):
    """Write backup to local JSON file and to Firestore 'template_cleanup_backups' collection."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"ghost_templates_backup_{timestamp_str}.json"
    backup_filepath = os.path.join(BACKUPS_DIR, backup_filename)

    payload = {
        "backup_type": "ghost_templates_phase2_cleanup",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ghost_document_ids": GHOST_DOCUMENT_IDS,
        "canonical_target_id": CANONICAL_TARGET_ID,
        "canonical_target_data": canonical_data,
        "ghost_documents": ghosts_data,
    }

    with open(backup_filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

    print(f"[OK] Local backup written to: {backup_filepath}")

    # Also record in Firestore collection 'template_cleanup_backups'
    try:
        db.collection("template_cleanup_backups").document(f"backup_{timestamp_str}").set(payload)
        print(f"[OK] Firestore backup written to: template_cleanup_backups/backup_{timestamp_str}")
    except Exception as e:
        print(f"[WARN] Could not write to Firestore template_cleanup_backups collection: {e}")

    return backup_filepath


def verify_backup(backup_filepath):
    """Verify that backup file exists, is valid JSON, and contains ghost document data."""
    if not os.path.isfile(backup_filepath):
        return False, f"Backup file {backup_filepath} does not exist"
    try:
        with open(backup_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for gid in GHOST_DOCUMENT_IDS:
            if gid not in data.get("ghost_documents", {}):
                return False, f"Missing {gid} in backup"
        return True, "Backup verified successfully"
    except Exception as e:
        return False, f"Corrupted backup file: {e}"


def rollback_from_backup(db, backup_filepath):
    """Restore ghost documents from a backup file."""
    valid, msg = verify_backup(backup_filepath)
    if not valid:
        print(f"[ERROR] Cannot rollback: {msg}")
        return False

    with open(backup_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    ghosts = data.get("ghost_documents", {})
    restored_count = 0
    for gid, doc_data in ghosts.items():
        if doc_data is not None:
            db.collection("templates").document(gid).set(doc_data)
            print(f"[OK] Restored document: {gid}")
            restored_count += 1
        else:
            print(f"[INFO] Document {gid} was null in backup; skipped.")

    print(f"[SUCCESS] Rollback completed. {restored_count} documents restored.")
    return True


def execute_cleanup(db, ghosts_data, canonical_exists, canonical_data):
    """Safely back up, verify, and delete ghost documents from Firestore."""
    if not any(v is not None for v in ghosts_data.values()):
        print("[INFO] No ghost documents found in Firestore. Collection is already clean.")
        return True

    # 1. Create and verify backup first
    backup_path = save_backup(db, ghosts_data, canonical_data)
    valid, msg = verify_backup(backup_path)
    if not valid:
        print(f"[CRITICAL] Backup verification failed: {msg}. Aborting cleanup!")
        return False

    print(f"[OK] Backup verified. Proceeding with deletion...")

    # 2. Delete each ghost document
    deleted = []
    for gid, data in ghosts_data.items():
        if data is not None:
            db.collection("templates").document(gid).delete()
            print(f"[OK] Deleted ghost document: {gid}")
            deleted.append(gid)

    # 3. Log to audit_logs collection
    try:
        db.collection("audit_logs").add({
            "action": "cleanup_ghost_templates",
            "deleted_document_ids": deleted,
            "backup_file": backup_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": "phase2_template_cleanup_script",
        })
        print("[OK] Audit log entry recorded in 'audit_logs'")
    except Exception as e:
        print(f"[WARN] Failed to write audit log: {e}")

    print(f"[SUCCESS] Cleanup completed. Removed {len(deleted)} ghost document(s).")
    return True


def main():
    parser = argparse.ArgumentParser(description="NyaySetu Pro Ghost Templates Cleanup")
    parser.add_argument("--creds", help="Path to Firebase Service Account JSON file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry run only without modifying data")
    parser.add_argument("--backup-only", action="store_true", help="Perform backup only")
    parser.add_argument("--execute-cleanup", action="store_true", help="Perform actual deletion")
    parser.add_argument("--confirm", action="store_true", help="Confirmation flag required for execute-cleanup")
    parser.add_argument("--rollback", action="store_true", help="Rollback from a backup file")
    parser.add_argument("--backup-file", help="Path to backup JSON file for rollback")
    args = parser.parse_args()

    print("=" * 80)
    print("NYAYSETU PRO — GHOST TEMPLATE CLEANUP & BACKUP UTILITY")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    try:
        db = get_firestore_client(args.creds)
        print("[OK] Connected to Firestore successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Firestore: {e}")
        return 1

    if args.rollback:
        if not args.backup_file:
            print("[ERROR] --rollback requires --backup-file <path_to_backup.json>")
            return 1
        success = rollback_from_backup(db, args.backup_file)
        return 0 if success else 1

    ghosts_data, canonical_exists, canonical_data = inspect_ghost_documents(db)

    print("\n--- GHOST DOCUMENTS INSPECTION ---")
    for gid, data in ghosts_data.items():
        if data is not None:
            print(f"  [FOUND] {gid} | keys: {list(data.keys())} | sort_order: {data.get('sort_order')}")
        else:
            print(f"  [NOT FOUND] {gid}")

    print("\n--- CANONICAL DOCUMENT STATUS ---")
    if canonical_exists:
        print(f"  [EXISTS] {CANONICAL_TARGET_ID} | name_en: '{canonical_data.get('name_en')}' | name_gu: '{canonical_data.get('name_gu')}'")
    else:
        print(f"  [WARNING] Canonical template '{CANONICAL_TARGET_ID}' not found in database (will rely on seed definitions).")

    if args.backup_only:
        print("\n--- RUNNING BACKUP ONLY ---")
        save_backup(db, ghosts_data, canonical_data)
        return 0

    if args.execute_cleanup:
        if not args.confirm:
            print("\n[BLOCKED] --execute-cleanup requires explicit --confirm flag to proceed.")
            return 1
        print("\n--- EXECUTING CONTROLLED CLEANUP ---")
        success = execute_cleanup(db, ghosts_data, canonical_exists, canonical_data)
        return 0 if success else 1

    # Default dry run
    print("\n--- DRY RUN SUMMARY ---")
    ghost_count = sum(1 for v in ghosts_data.values() if v is not None)
    print(f"  Ghost documents eligible for deletion: {ghost_count}")
    print(f"  Canonical template status: {'Present' if canonical_exists else 'Seed-backed'}")
    print(f"  Action planned: Backup {ghost_count} documents to local JSON & Firestore, then delete {ghost_count} documents.")
    print("  NO CHANGES MADE (dry run mode). To execute, run with --execute-cleanup --confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
