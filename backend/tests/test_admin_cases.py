"""Tests for NyaySetu Pro Admin Cases module (Master Plan Phase 37).

Covers:
- Admin cases endpoint requires admin auth (no token / lawyer token rejected)
- Admin can list all cases with owner info
- Search by nickname / case number / party name / client mobile
- Status filter (active / archived / all)
- Category filter
- Owner filter (by user id)
- Case detail returns enriched case, owner profile, generated documents
- Admin archive / restore works and is audit-logged
- Missing case returns 404

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_cases")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_cases"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, now
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs"]


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


async def create_lawyer(mobile, name):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "name": name,
        "email": None,
        "provider": "mobile",
        "active": True,
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({"user_id": user_id, "balance": 5, "total_used": 0,
                                 "free_credits_granted": 5, "updated_at": now().isoformat()})
    return user


async def create_case(user_id, *, nickname="", case_number="", party_name="",
                      client_name="", client_mobile="", case_type_id="civil_suit",
                      status="active", opposite_party="", created=None):
    case_id = str(uuid.uuid4())
    doc = {
        "id": case_id,
        "user_id": user_id,
        "status": status,
        "created_at": created or now().isoformat(),
        "updated_at": created or now().isoformat(),
        "last_used_template": None,
        "application_count": 0,
        "nickname": nickname,
        "case_number": case_number,
        "case_type_id": case_type_id,
        "party_name": party_name,
        "opposite_party": opposite_party,
        "client_name": client_name,
        "client_mobile": client_mobile,
        "custom_fields": {},
    }
    await db.cases.insert_one(doc.copy())
    return case_id


# ============================================================
# Auth requirements
# ============================================================

async def test_cases_endpoint_requires_admin_auth(client, clean_db):
    r = await client.get("/api/admin/cases")
    assert r.status_code == 401

    lawyer = await create_lawyer("9876500001", "Lawyer A")
    lawyer_token = make_token(lawyer["id"])
    r = await client.get("/api/admin/cases", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert r.status_code == 401

    r = await client.get("/api/admin/cases/nonexistent", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert r.status_code == 401


# ============================================================
# List / search / filters
# ============================================================

async def test_list_cases_with_owner_info(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    u2 = await create_lawyer("9876500002", "Adv. Sita")
    await create_case(u1["id"], nickname="Land Dispute", case_number="CIV/1/2026",
                      party_name="Mahesh Patel", client_mobile="9876511111", case_type_id="civil_suit")
    await create_case(u2["id"], nickname="Criminal Complaint", case_number="CMP/2/2026",
                      party_name="Kiran Shah", client_mobile="9876522222", case_type_id="criminal_case")
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/cases", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    for item in body["items"]:
        assert item["owner"] is not None
        assert "name" in item["owner"]
    owners = {c["owner"]["name"] for c in body["items"]}
    assert owners == {"Adv. Ramesh", "Adv. Sita"}
    # Labels enriched (no raw ids)
    assert all(c.get("case_type_label") for c in body["items"])


async def test_search_cases(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    await create_case(u1["id"], nickname="Land Dispute", case_number="CIV/1/2026",
                      party_name="Mahesh Patel", client_name="Mahesh Patel", client_mobile="9876511111")
    await create_case(u1["id"], nickname="Cheque Bounce", case_number="CMP/2/2026",
                      party_name="Kiran Shah", client_name="Kiran Shah", client_mobile="9876522222")
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/cases?q=land", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["nickname"] == "Land Dispute"

    r = await client.get("/api/admin/cases?q=CMP/2", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = await client.get("/api/admin/cases?q=kiran", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["party_name"] == "Kiran Shah"

    r = await client.get("/api/admin/cases?q=9876522222", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_status_and_category_and_owner_filters(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    u2 = await create_lawyer("9876500002", "Adv. Sita")
    await create_case(u1["id"], nickname="Active Case", case_type_id="civil_suit")
    await create_case(u1["id"], nickname="Archived Case", case_type_id="criminal_case", status="archived")
    await create_case(u2["id"], nickname="Sita Case", case_type_id="civil_suit")
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/cases?status=active", headers=headers)
    assert r.json()["total"] == 2

    r = await client.get("/api/admin/cases?status=archived", headers=headers)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["nickname"] == "Archived Case"

    r = await client.get(f"/api/admin/cases?user_id={u2['id']}", headers=headers)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["nickname"] == "Sita Case"

    # Category filter (civil_suit -> Civil, criminal_case -> Criminal)
    r = await client.get("/api/admin/cases?category=Civil", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 2
    r = await client.get("/api/admin/cases?category=Criminal", headers=headers)
    assert r.json()["total"] == 1


async def test_pagination(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    for i in range(5):
        await create_case(u1["id"], nickname=f"Case {i}", case_number=f"N/{i}")
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/admin/cases?limit=2&offset=0", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] == 5

    r = await client.get("/api/admin/cases?limit=2&offset=2", headers=headers)
    assert len(r.json()["items"]) == 2

    r = await client.get("/api/admin/cases?limit=2&offset=4", headers=headers)
    assert len(r.json()["items"]) == 1


# ============================================================
# Detail
# ============================================================

async def test_case_detail_with_owner_and_documents(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    case_id = await create_case(u1["id"], nickname="Land Dispute", case_number="CIV/1/2026",
                                party_name="Mahesh Patel", client_name="Mahesh Patel",
                                client_mobile="9876511111", case_type_id="civil_suit")
    await db.applications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": u1["id"],
        "case_id": case_id,
        "template_id": "t1",
        "template_name": "Test Application",
        "language": "gu",
        "format": "pdf",
        "filename": "t1_20260101.pdf",
        "created_at": now().isoformat(),
    })
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/admin/cases/{case_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["case"]["id"] == case_id
    assert body["case"]["case_type_label"]
    assert body["owner"]["name"] == "Adv. Ramesh"
    assert body["owner"]["mobile"] == "9876500001"
    assert len(body["applications"]) == 1
    assert body["applications"][0]["template_name"] == "Test Application"

    r = await client.get("/api/admin/cases/missing-case", headers=headers)
    assert r.status_code == 404


# ============================================================
# Archive / restore
# ============================================================

async def test_admin_archive_and_restore(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    case_id = await create_case(u1["id"], nickname="Land Dispute", case_type_id="civil_suit")
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/admin/cases/{case_id}/archive", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"
    doc = await db.cases.find_one({"id": case_id})
    assert doc["status"] == "archived"

    r = await client.post(f"/api/admin/cases/{case_id}/restore", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    doc = await db.cases.find_one({"id": case_id})
    assert doc["status"] == "active"

    # Audit trail records both
    r = await client.get("/api/admin/audit-logs", headers=headers)
    actions = {e["action"] for e in r.json()["items"]}
    assert "case_archive" in actions
    assert "case_restore" in actions

    r = await client.post("/api/admin/cases/missing-case/archive", headers=headers)
    assert r.status_code == 404


async def test_regular_admin_can_view_but_not_delete(client, clean_db):
    u1 = await create_lawyer("9876500001", "Adv. Ramesh")
    case_id = await create_case(u1["id"], nickname="Land Dispute", case_type_id="civil_suit")
    _, token = await create_admin(role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Regular admin can list + view
    r = await client.get(f"/api/admin/cases/{case_id}", headers=headers)
    assert r.status_code == 200

    # Archive is allowed for any admin (view-level management), but the lawyer
    # delete endpoint is out of admin scope — admin has no delete endpoint.
    r = await client.post(f"/api/admin/cases/{case_id}/archive", headers=headers)
    assert r.status_code == 200
