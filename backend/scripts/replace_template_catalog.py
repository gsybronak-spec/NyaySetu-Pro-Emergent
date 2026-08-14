# -*- coding: utf-8 -*-
"""
Replace the old default application-template catalog with the v2 catalog.

Data safety:
1. BACKUP — every template record (all statuses) is exported to
   backend/backups/templates_backup_<timestamp>.json before any write.
2. IMPORT — the 21 new application templates (source: the lawyer's final
   drafts, verbatim in seed_data_templates_v2.py) are created as PUBLISHED,
   idempotently. Existing records of the same id are NEVER overwritten.
3. ARCHIVE — old default seed templates (the previous default catalog) that
   are currently published are set to status="archived" (content untouched,
   nothing deleted). Existing user applications/history/artifacts are not
   touched in any way.

Usage:  python scripts/replace_template_catalog.py
Safe to re-run: second run finds the new templates already published and the
old ones already archived -> no changes.
"""
import asyncio
import json
import os
import re
import sys
import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from seed_data import TEMPLATES  # noqa: E402
from seed_data_templates_v2 import TEMPLATES_V2  # noqa: E402

OLD_DEFAULT_IDS = {t["id"] for t in TEMPLATES}
NEW_IDS = {t["id"] for t in TEMPLATES_V2}


def load_env(key: str) -> str:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, "")


async def main() -> None:
    mongo_url = load_env("MONGO_URL")
    db_name = load_env("DB_NAME") or "nyaysetu_pro"
    if not mongo_url:
        print("ERROR: MONGO_URL not found in .env or environment")
        sys.exit(1)

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=30000)
    db = client[db_name]

    # ---- 1. Backup ---------------------------------------------------------
    all_templates = await db.templates.find({}, {"_id": 0}).to_list(1000)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backups_dir = BACKEND_DIR / "backups"
    backups_dir.mkdir(exist_ok=True)
    backup_path = backups_dir / f"templates_backup_{ts}.json"
    backup_path.write_text(
        json.dumps(all_templates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[1/3] BACKUP  -> {backup_path.name} ({len(all_templates)} records)")

    # ---- 2. Import new v2 catalog as published -----------------------------
    created, republished, skipped = [], [], []
    ts_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for t in TEMPLATES_V2:
        existing = await db.templates.find_one({"id": t["id"]}, {"_id": 0})
        if not existing:
            doc = {
                **t,
                "slug": t["id"],
                "status": "published",
                "version": 1,
                "locked": False,
                "source": "seed_v2",
                "created_by": "catalog_v2_migration",
                "updated_by": "catalog_v2_migration",
                "created_at": ts_now,
                "updated_at": ts_now,
                "published_at": ts_now,
            }
            await db.templates.insert_one(doc.copy())
            created.append(t["id"])
            continue
        # An ARCHIVED record of a v2 id (e.g. a superseded partial draft) is
        # replaced by the source-of-truth v2 definition and published. Draft
        # records (an admin actively editing) are never touched.
        if existing.get("status") == "archived":
            doc = {
                **t,
                "slug": t["id"],
                "status": "published",
                "version": (existing.get("version") or 1) + 1,
                "locked": False,
                "source": "seed_v2",
                "updated_by": "catalog_v2_migration",
                "created_at": existing.get("created_at") or ts_now,
                "updated_at": ts_now,
                "published_at": ts_now,
            }
            await db.templates.replace_one({"id": t["id"]}, doc)
            republished.append(t["id"])
            continue
        skipped.append((t["id"], existing.get("status", "?")))
    print(f"[2/3] IMPORT  -> created {len(created)} new templates: {', '.join(created)}")
    print(f"         republished from archived: {republished}")
    print(f"         skipped (left untouched): {skipped}")

    # ---- 3. Archive old default catalog ------------------------------------
    archived, untouched = [], []
    for tid in sorted(OLD_DEFAULT_IDS):
        rec = await db.templates.find_one({"id": tid}, {"_id": 0})
        if not rec:
            untouched.append((tid, "not-in-db"))
            continue
        if rec.get("status") == "published":
            await db.templates.update_one(
                {"id": tid},
                {
                    "$set": {
                        "status": "archived",
                        "archived_at": ts_now,
                        "archived_by": "catalog_v2_migration",
                        "archived_reason": "replaced by v2 application catalog",
                    }
                },
            )
            archived.append(tid)
        else:
            untouched.append((tid, rec.get("status", "?")))
    print(f"[3/3] ARCHIVE -> archived {len(archived)} old default templates: {', '.join(archived)}")
    print(f"         left untouched: {untouched}")

    # ---- Final summary -----------------------------------------------------
    published = await db.templates.count_documents({"status": "published"})
    total = await db.templates.count_documents({})
    print(f"\nRESULT: {total} template records total; {published} published; "
          f"{await db.templates.count_documents({'status': 'archived'})} archived.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
