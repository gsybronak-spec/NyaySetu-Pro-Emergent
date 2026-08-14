"""One-time production-safe migration: restore core seed templates that were
bulk-archived on 2026-08-14 (23 archives in ~3 minutes, then the catalog was
left with zero published templates — breaking the lawyer template workflow).

Only STATUS changes (archived -> published). Content, versions, and metadata
are untouched. Every change is logged to audit_logs. No records are deleted.

Run: python scripts/restore_published_templates.py
"""
import os
import sys
from datetime import datetime, timezone

import pymongo

# The 24 core seed templates archived on 2026-08-14 (bulk archive events) that
# the admin never deliberately replaced. `aanke_padvani_arji` (archived 08-12
# 22:19) is deliberately excluded — it was superseded by
# `aanke_padvani_arji_copy_8834` ("Application to Exhibit Document 2.0").
RESTORE_IDS = [
    "adjournment", "certified_copy", "exemption_appearance", "cross_close",
    "evidence_produce", "document_produce", "time_extension", "case_transfer",
    "recall", "warrant_cancel", "bail_regular", "affidavit", "restoration",
    "condonation_delay", "interim_injunction", "vakalatnama", "inspection",
    "compromise", "withdrawal", "return_documents", "amendment", "surety",
    "early_hearing", "document_return_application",
]


def main() -> None:
    url = os.environ.get("MONGO_URL", "")
    dbname = os.environ.get("DB_NAME", "nyaysetu_pro")
    if not url:
        url = (open(".env", encoding="utf-8").read().split("MONGO_URL=")[1].splitlines()[0].strip())
    if "DB_NAME=" in open(".env", encoding="utf-8").read():
        for line in open(".env", encoding="utf-8").read().splitlines():
            if line.startswith("DB_NAME="):
                dbname = line.split("=", 1)[1].strip()

    client = pymongo.MongoClient(url, serverSelectionTimeoutMS=20000)
    db = client[dbname]

    now_iso = datetime.now(timezone.utc).isoformat()
    updated, missing, skipped = [], [], []
    for tid in RESTORE_IDS:
        doc = db.templates.find_one({"id": tid}, {"_id": 0, "id": 1, "status": 1, "name_en": 1})
        if not doc:
            missing.append(tid)
            continue
        if doc.get("status") == "published":
            skipped.append(tid)
            continue
        r = db.templates.update_one({"id": tid}, {"$set": {"status": "published", "updated_at": now_iso}})
        if r.modified_count or r.matched_count:
            updated.append(tid)
        db.audit_logs.insert_one({
            "action": "template_status_restore",
            "admin_email": "system@nyaysetu.in",
            "admin_id": "system",
            "admin_role": "system",
            "target": tid,
            "metadata": {"reason": "Bulk-archive on 2026-08-14 left 0 published templates; restoring core seed template", "from": doc.get("status")},
            "timestamp": now_iso,
        })

    print(f"Restored to published: {len(updated)}")
    print("  " + ", ".join(updated))
    print(f"Skipped (already published): {len(skipped)}")
    print(f"Missing (not found): {len(missing)}")
    if missing:
        print("  " + ", ".join(missing))

    # Verify
    total = db.templates.count_documents({"status": "published"})
    print(f"Now published in DB: {total}")

    client.close()
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
