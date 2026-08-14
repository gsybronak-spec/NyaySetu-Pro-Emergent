"""Idempotent, additive migration: template-level Gujarati document font.

The Gujarati PDF engine now ships a font stack (Noto Sans Gujarati default ->
Noto Serif Gujarati -> Lohit Gujarati compatibility fallback) with full Latin
+ digit coverage, fixing corrupted conjuncts AND "boxes for English/numbers".

Templates created before this change stored settings.gujarati_font =
"LohitGujarati" (the old engine default) or "NirmalaUI" (a Windows-only system
font that does not exist on Render). This migration moves only that one key to
the new default; template content, fields, versions and every other setting
are untouched. Re-runnable (idempotent): only old values are rewritten.

Usage:
  python scripts/migrate_gujarati_font.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

LEGACY_VALUES = {"lohitgujarati", "lohit", "nirmalaui", "nirmala ui"}


def _norm(v):
    return str(v or "").strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def main():
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=15000)
    db = client[DB_NAME]
    changed, skipped = 0, 0
    for t in db.templates.find({"settings.gujarati_font": {"$exists": True}}, {"id": 1, "settings": 1, "name_en": 1}):
        cur = (t.get("settings") or {}).get("gujarati_font")
        if _norm(cur) in LEGACY_VALUES:
            r = db.templates.update_one(
                {"id": t["id"], "settings.gujarati_font": cur},
                {"$set": {"settings.gujarati_font": "Noto Sans Gujarati"}},
            )
            if r.modified_count:
                changed += 1
                print(f"  {t['id']} ({t.get('name_en', '?')}): {cur!r} -> Noto Sans Gujarati")
            else:
                skipped += 1
    print(f"Done: {changed} templates updated, {skipped} skipped/already-current.")
    client.close()


if __name__ == "__main__":
    main()
