"""Tests for NyaySetu Pro Admin Plans module (Master Plan Phase 38).

Covers:
- Plans endpoint requires admin auth (no token / lawyer token rejected)
- Admin can list plans (seeded catalog present)
- Super admin can create a plan; regular admin cannot (403)
- Super admin can update a plan; regular admin cannot (403)
- Deactivating a plan hides it from the public catalog and blocks mock purchase
- Reactivating restores it
- Public /catalog/plans shape stays backward compatible (id/name/price/credits)
- Audit trail records plan create/update/status changes
- Plan id validation (bad id -> 404)

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_plans")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_plans"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, now
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs", "plans"]


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
    # Seed plans like startup does
    await server.seed_plans()
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

async def test_plans_endpoint_requires_admin_auth(client, clean_db):
    r = await client.get("/api/admin/plans")
    assert r.status_code == 401

    lawyer = await create_lawyer("9876500001")
    tok = make_token(lawyer["id"])
    r = await client.get("/api/admin/plans", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


# ============================================================
# List / create / update
# ============================================================

async def test_admin_lists_seeded_plans(client, clean_db):
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/admin/plans", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 4  # seeded catalog
    ids = {p["id"] for p in body}
    assert ids == {"single", "plan_299", "plan_499", "plan_999"}
    assert all(p["active"] is True for p in body)
    # per_template computed
    plan_499 = next(p for p in body if p["id"] == "plan_499")
    assert plan_499["per_template"] == 1.99


async def test_super_admin_can_create_plan(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/plans", json={
        "name": "Trial Pack", "price": 99, "credits": 10, "popular": False,
        "description": "Trial credits",
    }, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    plan = body["plan"]
    assert plan["name"] == "Trial Pack"
    assert plan["price"] == 99
    assert plan["credits"] == 10
    assert plan["active"] is True
    assert plan["per_template"] == 9.9
    plan_id = plan["id"]

    # Visible in public catalog
    r = await client.get("/api/catalog/plans")
    assert r.status_code == 200
    assert any(p["id"] == plan_id for p in r.json())

    # Audit recorded
    r = await client.get("/api/admin/audit-logs", headers=headers)
    assert "plan_create" in {e["action"] for e in r.json()["items"]}


async def test_regular_admin_cannot_create_or_update(client, clean_db):
    _, token = await create_admin(role="admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/admin/plans", json={
        "name": "Hacked Plan", "price": 1, "credits": 1,
    }, headers=headers)
    assert r.status_code == 403

    r = await client.put("/api/admin/plans/plan_299", json={
        "name": "Renamed", "price": 1, "credits": 1,
    }, headers=headers)
    assert r.status_code == 403

    r = await client.post("/api/admin/plans/plan_299/status", json={"active": False}, headers=headers)
    assert r.status_code == 403


async def test_super_admin_can_update_plan(client, clean_db):
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.put("/api/admin/plans/plan_299", json={
        "name": "Starter Pro", "price": 349, "credits": 60, "popular": True,
    }, headers=headers)
    assert r.status_code == 200
    plan = r.json()["plan"]
    assert plan["name"] == "Starter Pro"
    assert plan["price"] == 349
    assert plan["credits"] == 60

    # Public catalog reflects the update
    r = await client.get("/api/catalog/plans")
    updated = next(p for p in r.json() if p["id"] == "plan_299")
    assert updated["name"] == "Starter Pro"
    assert updated["price"] == 349
    assert updated["credits"] == 60

    r = await client.put("/api/admin/plans/missing-plan", json={
        "name": "X", "price": 1, "credits": 1,
    }, headers=headers)
    assert r.status_code == 404


# ============================================================
# Active/inactive
# ============================================================

async def test_deactivate_hides_and_blocks_purchase(client, clean_db):
    lawyer = await create_lawyer("9876500001")
    lawyer_tok = make_token(lawyer["id"])
    lh = {"Authorization": f"Bearer {lawyer_tok}"}

    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Deactivate plan_499
    r = await client.post("/api/admin/plans/plan_499/status", json={"active": False}, headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"]["active"] is False

    # Hidden from public catalog
    r = await client.get("/api/catalog/plans")
    ids = {p["id"] for p in r.json()}
    assert "plan_499" not in ids

    # Mock purchase rejects inactive plan
    r = await client.post("/api/purchase/mock", json={"plan_id": "plan_499"}, headers=lh)
    assert r.status_code == 404

    # Still visible in admin list
    r = await client.get("/api/admin/plans", headers=headers)
    assert any(p["id"] == "plan_499" and p["active"] is False for p in r.json())

    # Reactivate -> purchasable again
    r = await client.post("/api/admin/plans/plan_499/status", json={"active": True}, headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/catalog/plans")
    assert "plan_499" in {p["id"] for p in r.json()}

    r = await client.post("/api/admin/plans/missing/status", json={"active": True}, headers=headers)
    assert r.status_code == 404


# ============================================================
# Backward compatibility
# ============================================================

async def test_public_catalog_shape_backward_compatible(client, clean_db):
    r = await client.get("/api/catalog/plans")
    assert r.status_code == 200
    for p in r.json():
        for key in ["id", "name", "price", "credits", "popular", "per_template"]:
            assert key in p, f"missing {key}"


async def test_seed_plans_is_idempotent(client, clean_db):
    await server.seed_plans()
    await server.seed_plans()
    assert await db.plans.count_documents({}) == 4
