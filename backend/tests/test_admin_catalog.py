"""Tests for NyaySetu Pro Admin Catalog module (Master Plan Phase 39).

Covers:
- Catalog admin endpoints require admin auth (no token / lawyer token rejected)
- Admin lists seeded catalogs (all 5 kinds)
- Super admin can create catalog entries; regular admin cannot (403)
- Created entries appear in the public catalog with the legacy shape
- Created case-type/district ids pass case validation and label enrichment
- Update labels flows through to public catalog and case labels
- Deactivating hides from public catalog but preserves existing references
  (validation + labels still work for existing cases)
- Law sections update works
- Audit trail records catalog mutations
- Unknown catalog kind -> 404

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_catalog")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_catalog"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, now
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs", "plans",
               "case_types", "laws", "districts", "courts", "police_stations"]


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
    # Seed catalogs like startup does
    await server.seed_catalogs()
    yield
    for coll in COLLECTIONS:
        await db[coll].drop()


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


async def create_lawyer(mobile):
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
    await db.wallets.insert_one({"user_id": user_id, "balance": 5, "total_used": 0,
                                 "free_credits_granted": 5, "updated_at": now().isoformat()})
    return user


# ============================================================
# Auth
# ============================================================

async def test_catalog_endpoints_require_admin_auth(client, clean_db):
    r = await client.get("/api/admin/catalog/case-types")
    assert r.status_code == 401

    lawyer = await create_lawyer("9876500001")
    tok = make_token(lawyer["id"])
    r = await client.get("/api/admin/catalog/case-types", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401

    # Authenticated admin gets 404 for unknown kinds (auth is checked first)
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/admin/catalog/unknown-kind", headers=headers)
    assert r.status_code == 404


# ============================================================
# List / create / update
# ============================================================

async def test_admin_lists_seeded_catalogs(client, clean_db):
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}
    for kind, count in [("case-types", 23), ("laws", 8), ("districts", 12),
                        ("courts", 11), ("police-stations", 9)]:
        r = await client.get(f"/api/admin/catalog/{kind}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert len(body) == count, f"{kind}: {len(body)} != {count}"
        assert all(i["active"] is True for i in body)


async def test_super_admin_creates_case_type(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/catalog/case-types", json={
        "en": "Motor Accident Claim", "gu": "મોટર એક્સિડન્ટ ક્લેમ", "cat": "Civil",
    }, headers=headers)
    assert r.status_code == 200
    item = r.json()["item"]
    assert item["active"] is True
    assert item["cat"] == "Civil"
    new_id = item["id"]

    # Public catalog includes it with legacy shape
    r = await client.get("/api/catalog/case-types")
    pub = r.json()
    found = next((p for p in pub if p["id"] == new_id), None)
    assert found is not None
    assert found["en"] == "Motor Accident Claim"
    assert found["gu"] == "મોટર એક્સિડન્ટ ક્લેમ"
    assert found["cat"] == "Civil"
    # No internal fields leaked
    assert "active" not in found and "created_at" not in found

    # Audit recorded
    r = await client.get("/api/admin/audit-logs", headers=headers)
    assert "catalog_create" in {e["action"] for e in r.json()["items"]}


async def test_created_case_type_usable_in_case(client, clean_db):
    """New catalog ids must pass validation and label enrichment end-to-end."""
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/catalog/case-types", json={
        "en": "Motor Accident Claim", "gu": "મોટર એક્સિડન્ટ ક્લેમ", "cat": "Civil",
    }, headers=headers)
    new_id = r.json()["item"]["id"]

    lawyer = await create_lawyer("9876500001")
    lt = make_token(lawyer["id"])
    lh = {"Authorization": f"Bearer {lt}"}
    r = await client.post("/api/cases", json={
        "nickname": "MACP Case", "case_type_id": new_id, "party_name": "Rahul",
    }, headers=lh)
    assert r.status_code == 200
    case = r.json()
    assert case["case_type_label"] == "Motor Accident Claim"
    assert case["category"] == "Civil"


async def test_regular_admin_cannot_create_or_update(client, clean_db):
    _, token = await create_admin(role="admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/catalog/districts", json={
        "en": "Sabarkantha", "gu": "સાબરકાંઠા",
    }, headers=headers)
    assert r.status_code == 403

    r = await client.put("/api/admin/catalog/districts/ahmedabad", json={
        "en": "Ahmedabad", "gu": "અમદાવાદ",
    }, headers=headers)
    assert r.status_code == 403

    r = await client.post("/api/admin/catalog/districts/ahmedabad/status", json={"active": False}, headers=headers)
    assert r.status_code == 403


async def test_update_labels_flow_through(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.put("/api/admin/catalog/districts/ahmedabad", json={
        "en": "Ahmedabad Metro", "gu": "અમદાવાદ મેટ્રો",
    }, headers=headers)
    assert r.status_code == 200
    assert r.json()["item"]["en"] == "Ahmedabad Metro"

    r = await client.get("/api/catalog/districts")
    found = next(p for p in r.json() if p["id"] == "ahmedabad")
    assert found["en"] == "Ahmedabad Metro"

    r = await client.put("/api/admin/catalog/districts/missing", json={
        "en": "X", "gu": "X",
    }, headers=headers)
    assert r.status_code == 404


# ============================================================
# Deactivation preserves existing references
# ============================================================

async def test_deactivate_hides_but_preserves_references(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/catalog/case-types/ahmedabad_old/status",
                          json={"active": False}, headers=headers)
    # unknown id -> 404 (deactivation needs an existing entry; create one first)
    assert r.status_code == 404

    # Create a case type, use it in a case, then deactivate it
    r = await client.post("/api/admin/catalog/case-types", json={
        "en": "Temporary Type", "gu": "ટેમ્પરરી", "cat": "Other",
    }, headers=headers)
    new_id = r.json()["item"]["id"]

    lawyer = await create_lawyer("9876500001")
    lt = make_token(lawyer["id"])
    lh = {"Authorization": f"Bearer {lt}"}
    r = await client.post("/api/cases", json={
        "nickname": "Pre-deactivate", "case_type_id": new_id,
    }, headers=lh)
    assert r.status_code == 200

    # Deactivate
    r = await client.post(f"/api/admin/catalog/case-types/{new_id}/status",
                          json={"active": False}, headers=headers)
    assert r.status_code == 200
    assert r.json()["item"]["active"] is False

    # Hidden from public catalog
    r = await client.get("/api/catalog/case-types")
    assert new_id not in {p["id"] for p in r.json()}

    # Existing case still validates and keeps its label
    case_id = (await client.get("/api/cases", headers=lh)).json()[0]["id"]
    r = await client.get(f"/api/cases/{case_id}", headers=lh)
    assert r.status_code == 200
    assert r.json()["case_type_label"] == "Temporary Type"

    # Re-enable
    r = await client.post(f"/api/admin/catalog/case-types/{new_id}/status",
                          json={"active": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["item"]["active"] is True
    r = await client.get("/api/catalog/case-types")
    assert new_id in {p["id"] for p in r.json()}


# ============================================================
# Laws / sections
# ============================================================

async def test_law_sections_update(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.put("/api/admin/catalog/laws/ni_act", json={
        "en": "Negotiable Instruments Act",
        "gu": "નેગોશિએબલ ઇન્સ્ટ્રુમેન્ટ્સ એક્ટ",
        "sections": [
            {"id": "138", "label": "Section 138 - Dishonour of cheque"},
            {"id": "139", "label": "Section 139 - Presumption in favour of holder"},
        ],
    }, headers=headers)
    assert r.status_code == 200
    sections = r.json()["item"]["sections"]
    assert len(sections) == 2
    assert sections[1]["id"] == "139"

    # Public sections endpoint reflects it
    r = await client.get("/api/catalog/laws/ni_act/sections")
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[1]["id"] == "139"


# ============================================================
# Courts / police stations
# ============================================================

async def test_court_and_ps_creation(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/catalog/courts", json={
        "en": "Motor Accident Claims Tribunal", "gu": "મોટર દુર્ઘટના દાવા અધિકરણ",
        "district_id": "gandhinagar",
    }, headers=headers)
    assert r.status_code == 200
    court_id = r.json()["item"]["id"]

    r = await client.get("/api/catalog/courts?district_id=gandhinagar")
    found = next((c for c in r.json() if c["id"] == court_id), None)
    assert found is not None
    assert found["district_id"] == "gandhinagar"

    r = await client.post("/api/admin/catalog/police-stations", json={
        "en": "Gandhinagar Sector 7 P.S.", "gu": "ગાંધીનગર સેક્ટર ૭ પોલીસ સ્ટેશન",
        "district_id": "gandhinagar",
    }, headers=headers)
    assert r.status_code == 200
    ps_id = r.json()["item"]["id"]

    r = await client.get("/api/catalog/police-stations?district_id=gandhinagar")
    assert any(p["id"] == ps_id for p in r.json())
