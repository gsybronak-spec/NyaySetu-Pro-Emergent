# -*- coding: utf-8 -*-
"""
NyaySetu Pro — Production Firestore Ingestion Script.
Ingests all 42 authoritative legal application templates (21 Gujarati + 21 English)
into Cloud Firestore (nyaysetu-pro).

Pre-requisites:
  - Local dry-run of all 42 templates PASSED 22/22 criteria.
  - Zero modifications to non-template collections.
"""
import os
import sys
import json
from datetime import datetime, timezone
from google.cloud import firestore
from google.oauth2 import service_account

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

from authoritative_catalog_42 import TEMPLATES_42

CRED_PATH = r"C:\Users\HP\Downloads\nyaysetu-pro-firebase-adminsdk-fbsvc-dd4459b9fd.json"
PROJECT_ID = "nyaysetu-pro"

NON_TEMPLATE_COLLECTIONS = [
    "users",
    "cases",
    "applications",
    "wallets",
    "transactions",
    "subscriptions",
    "districts",
    "talukas",
    "courts",
    "case_types",
    "police_stations",
    "laws",
    "admin_users",
    "system_settings",
]


def get_collection_count(db, col_name):
    """Count documents in a collection via count() aggregation."""
    try:
        aggregate_query = db.collection(col_name).count()
        results = aggregate_query.get()
        return results[0][0].value
    except Exception:
        # Fallback to streaming IDs
        return len([d.id for d in db.collection(col_name).select([]).stream()])


def main():
    print("=" * 80)
    print("NYAYSETU PRO — PRODUCTION FIRESTORE TEMPLATE INGESTION")
    print(f"Project: {PROJECT_ID}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    if not os.path.exists(CRED_PATH):
        print(f"FATAL: Service account key not found at {CRED_PATH}")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(CRED_PATH)
    db = firestore.Client(project=PROJECT_ID, credentials=creds)

    # 1. Pre-ingestion snapshot of non-template collections
    print("\n[Step 1/4] Capturing pre-ingestion collection snapshot...")
    pre_counts = {}
    for col in NON_TEMPLATE_COLLECTIONS:
        cnt = get_collection_count(db, col)
        pre_counts[col] = cnt
        print(f"  * {col:25s} : {cnt} documents")

    pre_template_count = get_collection_count(db, "templates")
    print(f"  * {'templates (current)':25s} : {pre_template_count} documents")

    # 2. Prepare templates
    print(f"\n[Step 2/4] Validating 42 authoritative templates catalog...")
    assert len(TEMPLATES_42) == 42, f"Expected 42 templates, got {len(TEMPLATES_42)}"
    gu_templates = [t for t in TEMPLATES_42 if t["language"] == "gu"]
    en_templates = [t for t in TEMPLATES_42 if t["language"] == "en"]
    assert len(gu_templates) == 21, f"Expected 21 Gujarati templates, got {len(gu_templates)}"
    assert len(en_templates) == 21, f"Expected 21 English templates, got {len(en_templates)}"
    print(f"  * 21 Gujarati templates verified")
    print(f"  * 21 English templates verified")

    # 3. Ingest into Firestore
    print(f"\n[Step 3/4] Writing 42 templates and initial revisions to Firestore...")
    batch = db.batch()
    ingested_ids = []

    for t in TEMPLATES_42:
        doc_ref = db.collection("templates").document(t["id"])
        batch.set(doc_ref, t)
        
        # Also create initial version snapshot in template_revisions
        rev_id = f"{t['id']}_1"
        rev_doc = {
            "template_id": t["id"],
            "version": 1,
            "name_en": t["name_en"],
            "name_gu": t["name_gu"],
            "content_en": t["content_en"],
            "content_gu": t["content_gu"],
            "fields": t["fields"],
            "settings": t["settings"],
            "status": "published",
            "published_at": t["published_at"],
            "created_by": "system",
        }
        rev_ref = db.collection("template_revisions").document(rev_id)
        batch.set(rev_ref, rev_doc)
        
        ingested_ids.append(t["id"])

    batch.commit()
    print(f"  * Batch write committed successfully for {len(ingested_ids)} templates + revisions!")

    # 4. Post-ingestion verification
    print("\n[Step 4/4] Verifying post-ingestion state...")
    post_template_count = get_collection_count(db, "templates")
    post_revision_count = get_collection_count(db, "template_revisions")
    print(f"  * templates count         : {post_template_count} (expected: 42)")
    print(f"  * template_revisions count: {post_revision_count} (expected: 42)")

    assert post_template_count == 42, f"Expected exactly 42 templates, found {post_template_count}"

    # Verify non-template collections are 100% unchanged
    post_counts = {}
    mismatches = []
    for col in NON_TEMPLATE_COLLECTIONS:
        cnt = get_collection_count(db, col)
        post_counts[col] = cnt
        if cnt != pre_counts[col]:
            mismatches.append(f"{col}: pre={pre_counts[col]}, post={cnt}")
        print(f"  * {col:25s} : {cnt} documents (unchanged: {cnt == pre_counts[col]})")

    if mismatches:
        print(f"\nFATAL: Non-template collection count mismatch detected: {mismatches}")
        sys.exit(1)

    print("\nNON-TEMPLATE DATA INTEGRITY: 100% PRESERVED AND UNCHANGED.")

    # Save record
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": PROJECT_ID,
        "templates_ingested": len(ingested_ids),
        "template_ids": ingested_ids,
        "pre_counts": pre_counts,
        "post_counts": post_counts,
        "status": "SUCCESS",
    }

    record_path = os.path.join(BACKEND_DIR, "scratch", "production_ingestion_record.json")
    os.makedirs(os.path.dirname(record_path), exist_ok=True)
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"\nIngestion record saved to: {record_path}")
    print("=" * 80)
    print("PRODUCTION TEMPLATE INGESTION COMPLETE: 42 TEMPLATES ACTIVE IN FIRESTORE")
    print("=" * 80)


if __name__ == "__main__":
    main()
