"""Tests for template-level page size (A4/Legal) and admin template visibility.

Covers:
- Seed affidavit (સોગંદનામું) defaults to Legal paper (real PDF MediaBox)
- Other seed templates default to A4
- Explicit request page_size overrides the template setting
- Admin-created template without page_size uses the global default_page_size
- Admin template settings validate page_size (A4/Legal only)
- Admin template list merges ALL seed templates (every lawyer-app template visible),
  DB overrides seed by ID, no duplicates
- Editing a seed creates a draft without touching other templates
- migrate-seed stays idempotent

Uses mongomock_motor (same pattern as the existing suite).
"""

import os
import sys
import re
import uuid
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_tpl_page_size")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_tpl_page_size"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, now
from seed_data import TEMPLATES
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs",
               "plans", "settings"]

SEED_IDS = {t["id"] for t in TEMPLATES}
assert "affidavit" in SEED_IDS and len(SEED_IDS) == 24


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll in COLLECTIONS:
        await db[coll].drop()
    yield
    for coll in COLLECTIONS:
        await db[coll].drop()


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def create_admin(role="super_admin"):
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": f"{role}@test.com",
        "password_hash": hashed,
        "name": "Test Admin",
        "role": role,
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    token = make_admin_token(admin_id, admin["email"], admin["role"])
    return admin, token


async def create_lawyer(mobile="9876500001"):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "name": "Test Lawyer",
        "provider": "mobile",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({"user_id": user_id, "balance": 10, "total_used": 0,
                                 "free_credits_granted": 5, "updated_at": now().isoformat()})
    return user


def pdf_mediabox(pdf_bytes: bytes):
    m = re.search(rb"/MediaBox\s*\[\s*([^\]]+)\]", pdf_bytes)
    assert m, "MediaBox not found"
    parts = [float(x) for x in m.group(1).split()]
    return parts[2], parts[3]


async def download(client, lawyer, template_id, page_size=None, values=None):
    payload = {
        "template_id": template_id,
        "language": "gu",
        "values": values or {"reason": "test", "next_date": "01-01-2027"},
        "format": "pdf",
        "filename": f"{template_id}.pdf",
    }
    if page_size:
        payload["page_size"] = page_size
    return await client.post("/api/applications/download", headers=H(make_token(lawyer["id"])), json=payload)


# ============================================================
# Template-level page size
# ============================================================

async def test_seed_affidavit_defaults_to_legal(client, clean_db):
    lawyer = await create_lawyer()
    r = await download(client, lawyer, "affidavit",
                       values={"declarant_name": "Test", "facts": "facts", "place": "Ahmedabad"})
    assert r.status_code == 200, r.text
    w, h = pdf_mediabox(base64.b64decode(r.json()["base64"]))
    assert abs(w - 612) < 2 and abs(h - 1008) < 2, f"expected Legal, got {w}x{h}"


async def test_seed_adjournment_defaults_to_a4(client, clean_db):
    lawyer = await create_lawyer()
    r = await download(client, lawyer, "adjournment")
    assert r.status_code == 200, r.text
    w, h = pdf_mediabox(base64.b64decode(r.json()["base64"]))
    assert abs(w - 595) < 3 and abs(h - 842) < 3, f"expected A4, got {w}x{h}"


async def test_request_page_size_overrides_template(client, clean_db):
    lawyer = await create_lawyer()
    r = await download(client, lawyer, "affidavit", page_size="A4",
                       values={"declarant_name": "Test", "facts": "facts", "place": "Ahmedabad"})
    assert r.status_code == 200, r.text
    w, h = pdf_mediabox(base64.b64decode(r.json()["base64"]))
    assert abs(w - 595) < 3 and abs(h - 842) < 3, f"expected A4 override, got {w}x{h}"


async def test_admin_created_template_without_page_size_uses_global_default(client, clean_db):
    # Set the global default to Legal
    _, admin_token = await create_admin()
    r = await client.put("/api/admin/settings/default_page_size", json={"value": "Legal"}, headers=H(admin_token))
    assert r.status_code == 200

    # Admin-created template with NO page_size in settings
    tpl = {
        "id": "custom_no_ps",
        "slug": "custom_no_ps",
        "name_en": "Custom No PS",
        "name_gu": "કસ્ટમ",
        "category": "General",
        "fields": [],
        "content_en": "Test content {{today}}",
        "content_gu": "કન્ટેન્ટ {{today}}",
        "settings": {"body_size": 12},
        "status": "published",
        "version": 1,
        "locked": True,
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
    }
    await db.templates.insert_one(tpl.copy())

    lawyer = await create_lawyer()
    r = await download(client, lawyer, "custom_no_ps", values={})
    assert r.status_code == 200, r.text
    w, h = pdf_mediabox(base64.b64decode(r.json()["base64"]))
    assert abs(w - 612) < 2 and abs(h - 1008) < 2, f"expected global Legal, got {w}x{h}"

    # Restore default
    await client.put("/api/admin/settings/default_page_size", json={"value": "A4"}, headers=H(admin_token))


async def test_admin_template_settings_page_size_validation(client, clean_db):
    _, admin_token = await create_admin()
    await db.templates.insert_one({
        "id": "draft_ps",
        "name_en": "Draft PS",
        "name_gu": "ડ્રાફ્ટ",
        "category": "General",
        "fields": [],
        "content_en": "x",
        "content_gu": "x",
        "settings": {"page_size": "A4"},
        "status": "draft",
        "version": 1,
        "locked": False,
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
    })
    r = await client.put("/api/admin/templates/draft_ps", headers=H(admin_token), json={
        "settings": {"page_size": "Letter"},
    })
    assert r.status_code == 422
    assert "page_size" in r.json()["detail"]

    r = await client.put("/api/admin/templates/draft_ps", headers=H(admin_token), json={
        "settings": {"page_size": "Legal"},
    })
    assert r.status_code == 200


# ============================================================
# Admin template visibility (seed + DB merge)
# ============================================================

async def test_admin_list_shows_all_seed_templates_with_partial_db(client, clean_db):
    # DB already has a couple of templates -> previously seeds were hidden
    await db.templates.insert_one({
        "id": "db_only_one", "name_en": "DB One", "name_gu": "એક",
        "category": "General", "fields": [], "content_en": "x", "content_gu": "x",
        "settings": {}, "status": "draft", "version": 1, "locked": False,
        "created_at": now().isoformat(), "updated_at": now().isoformat(),
    })
    _, admin_token = await create_admin()
    r = await client.get("/api/admin/templates", headers=H(admin_token))
    assert r.status_code == 200
    items = r.json()
    ids = [t["id"] for t in items]
    # Every seed template is visible
    for sid in SEED_IDS:
        assert sid in ids, f"seed template {sid} missing from admin list"
    assert "db_only_one" in ids
    assert len(ids) == len(SEED_IDS) + 1  # no duplicates
    # Seeds are marked as seed source
    seed_item = next(t for t in items if t["id"] == "adjournment" and t.get("status") == "seed")
    assert seed_item["source"] == "seed"


async def test_admin_list_db_overrides_seed_by_id(client, clean_db):
    await db.templates.insert_one({
        "id": "adjournment", "name_en": "Adjournment EDITED", "name_gu": "મુદત (બદલાયેલ)",
        "category": "Civil", "fields": [], "content_en": "edited", "content_gu": "edited",
        "settings": {"page_size": "Legal"}, "status": "draft", "version": 2, "locked": False,
        "created_at": now().isoformat(), "updated_at": now().isoformat(),
    })
    _, admin_token = await create_admin()
    r = await client.get("/api/admin/templates", headers=H(admin_token))
    items = r.json()
    adjournment = [t for t in items if t["id"] == "adjournment"]
    assert len(adjournment) == 1  # exactly one, DB overrides seed
    assert adjournment[0]["name_en"] == "Adjournment EDITED"
    assert adjournment[0]["status"] == "draft"
    assert len(items) == len(SEED_IDS)  # other seeds still present once each


async def test_admin_list_status_filter_seed(client, clean_db):
    _, admin_token = await create_admin()
    r = await client.get("/api/admin/templates?status=seed", headers=H(admin_token))
    items = r.json()
    assert len(items) == len(SEED_IDS)
    assert all(t["status"] == "seed" for t in items)


async def test_editing_seed_creates_draft_without_touching_others(client, clean_db):
    _, admin_token = await create_admin()
    r = await client.put("/api/admin/templates/adjournment", headers=H(admin_token), json={
        "name_en": "Adjournment (Draft)",
        "settings": {"page_size": "A4"},
    })
    assert r.status_code == 200
    db_t = await db.templates.find_one({"id": "adjournment"}, {"_id": 0})
    assert db_t and db_t["status"] == "draft" and db_t["source"] == "admin_edited"

    # Other seeds untouched (not in DB)
    other = await db.templates.find_one({"id": "affidavit"}, {"_id": 0})
    assert other is None

    # List still shows every template exactly once (DB draft overrides seed)
    r = await client.get("/api/admin/templates", headers=H(admin_token))
    items = r.json()
    ids = [t["id"] for t in items]
    assert len(ids) == len(set(ids)) == len(SEED_IDS)


async def test_cloning_seed_creates_full_draft(client, clean_db):
    """Edit (version-branch) on a seed template must materialize the FULL seed
    document (name/content/fields/settings) — not a partial upsert."""
    _, admin_token = await create_admin()
    r = await client.post("/api/admin/templates/affidavit/clone", headers=H(admin_token),
                          json={"as_new_template": False})
    assert r.status_code == 200, r.text

    draft = await db.templates.find_one({"id": "affidavit"}, {"_id": 0})
    assert draft is not None
    assert draft["status"] == "draft"
    assert draft["version"] == 1
    assert draft["name_en"] == "General Affidavit"
    assert draft["name_gu"]
    assert len(draft.get("fields", [])) == 5
    assert draft.get("content_gu")
    assert (draft.get("settings") or {}).get("page_size") == "Legal"
    # No duplicate rows
    assert await db.templates.count_documents({"id": "affidavit"}) == 1

    # Other seeds remain untouched (not materialized)
    assert await db.templates.count_documents({"id": "adjournment"}) == 0


async def test_migrate_seed_is_idempotent_no_duplicates(client, clean_db):
    _, admin_token = await create_admin()
    r = await client.post("/api/admin/templates/migrate-seed", headers=H(admin_token))
    assert r.status_code == 200
    first = await db.templates.count_documents({})
    assert first == len(SEED_IDS)

    r = await client.post("/api/admin/templates/migrate-seed", headers=H(admin_token))
    assert r.status_code == 200
    assert await db.templates.count_documents({}) == first  # no duplicates


async def test_public_lawyer_shape_unchanged_after_seed_settings(client, clean_db):
    r = await client.get("/api/templates")
    assert r.status_code == 200
    for t in r.json():
        assert set(t.keys()) == {"id", "name_en", "name_gu", "category", "fields"}
