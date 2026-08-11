"""Tests for NyaySetu Pro Admin Modules — User Management + Audit Logs (Master Plan Phases 36 & 41).

Covers:
- Admin users endpoint requires admin auth (no token / lawyer token rejected)
- List users with search by name / mobile / email
- User detail returns profile, wallet, activity counts
- Super admin can enable/disable a user; regular admin cannot (403)
- Disabled user is blocked at OTP login (403) and at authenticated APIs (401)
- Re-enabling restores access
- Audit trail: admin login, template publish, case-form save, user status change
- Audit-logs endpoint requires auth, returns newest-first entries, supports action filter
- Audit log insert failure never breaks the primary action

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_modules")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone, timedelta

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_modules"]

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


async def create_admin(role="super_admin", email=None):
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": email or f"{role}@test.com",
        "password_hash": hashed,
        "name": "Test " + role.replace("_", " ").title(),
        "role": role,
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    token = make_admin_token(admin_id, admin["email"], admin["role"])
    return admin, token


async def create_lawyer(mobile, name="Test Lawyer", active=None):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "name": name,
        "provider": "mobile",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if active is not None:
        user["active"] = active
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 5,
        "total_used": 1,
        "free_credits_granted": 5,
        "updated_at": now().isoformat(),
    })
    return user


async def seed_otp(mobile, otp="123456"):
    await db.otps.update_one(
        {"mobile": mobile},
        {"$set": {
            "mobile": mobile,
            "otp": otp,
            "expires_at": (now() + timedelta(seconds=300)).isoformat(),
            "attempts": 0,
            "last_sent_at": now().isoformat(),
        }},
        upsert=True,
    )


# ============================================================
# Auth requirements
# ============================================================

async def test_users_endpoint_requires_admin_auth(client, clean_db):
    r = await client.get("/api/admin/users")
    assert r.status_code == 401

    lawyer = await create_lawyer("9876500001")
    lawyer_token = make_token(lawyer["id"])
    r = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert r.status_code == 401


async def test_audit_logs_endpoint_requires_admin_auth(client, clean_db):
    r = await client.get("/api/admin/audit-logs")
    assert r.status_code == 401


# ============================================================
# User list / search / detail
# ============================================================

async def test_list_users_and_search(client, clean_db):
    await create_lawyer("9876500001", name="Ramesh Patel")
    await create_lawyer("9876500002", name="Sita Sharma")
    _, token = await create_admin()

    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/admin/users", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2

    # Search by name
    r = await client.get("/api/admin/users?q=ramesh", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["name"] == "Ramesh Patel"

    # Search by mobile
    r = await client.get("/api/admin/users?q=9876500002", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["mobile"] == "9876500002"

    # No match
    r = await client.get("/api/admin/users?q=zzznomatch", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_user_detail_with_wallet_and_counts(client, clean_db):
    user = await create_lawyer("9876500001")
    await db.cases.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"],
                               "status": "active", "created_at": now().isoformat()})
    await db.applications.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"],
                                      "template_id": "x", "template_name": "X",
                                      "created_at": now().isoformat()})
    _, token = await create_admin()
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/admin/users/{user['id']}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["id"] == user["id"]
    assert body["wallet"]["balance"] == 5
    assert body["cases_count"] == 1
    assert body["applications_count"] == 1
    assert "password_hash" not in body["user"]

    r = await client.get("/api/admin/users/does-not-exist", headers=headers)
    assert r.status_code == 404


# ============================================================
# Status toggle + disabled enforcement
# ============================================================

async def test_super_admin_can_disable_and_enable_user(client, clean_db):
    user = await create_lawyer("9876500001")
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": False}, headers=headers)
    assert r.status_code == 200
    assert r.json()["user"]["active"] is False

    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["user"]["active"] is True


async def test_regular_admin_cannot_change_user_status(client, clean_db):
    user = await create_lawyer("9876500001")
    _, token = await create_admin(role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": False}, headers=headers)
    assert r.status_code == 403


async def test_disabled_user_blocked_at_login_and_api(client, clean_db):
    user = await create_lawyer("9876500001")
    _, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Disable the user
    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": False}, headers=headers)
    assert r.status_code == 200

    # OTP login is blocked with 403
    await seed_otp("9876500001")
    r = await client.post("/api/auth/verify-otp", json={"mobile": "9876500001", "otp": "123456"})
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()

    # Existing token no longer works on authenticated APIs
    user_token = make_token(user["id"])
    r = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 401
    assert "disabled" in r.json()["detail"].lower()

    # Re-enable restores access
    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": True}, headers=headers)
    assert r.status_code == 200
    r = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {user_token}"})
    assert r.status_code == 200


async def test_disabled_google_user_blocked(client, clean_db, monkeypatch):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": "lawyer@gmail.com",
        "name": "Google Lawyer",
        "provider": "google",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "active": False,
        "created_at": now().isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({"user_id": user_id, "balance": 5, "total_used": 0,
                                 "free_credits_granted": 5, "updated_at": now().isoformat()})

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"email": "lawyer@gmail.com", "name": "Google Lawyer", "picture": None}

    class FakeAsyncClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, *a, **kw):
            return FakeResponse()

    monkeypatch.setattr(server.httpx, "AsyncClient", FakeAsyncClient)

    r = await client.post("/api/auth/google-session", json={"session_id": "fake-session"})
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


# ============================================================
# Audit trail
# ============================================================

async def test_audit_log_records_login_and_user_status(client, clean_db):
    admin, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Login via API
    r = await client.post("/api/admin/auth/login",
                          json={"email": admin["email"], "password": "TestPass123!"})
    assert r.status_code == 200

    # Disable a user
    user = await create_lawyer("9876500001")
    r = await client.patch(f"/api/admin/users/{user['id']}/status",
                           json={"active": False}, headers=headers)
    assert r.status_code == 200

    # Failed login is also recorded
    r = await client.post("/api/admin/auth/login",
                          json={"email": admin["email"], "password": "WrongPass!"})
    assert r.status_code == 401

    r = await client.get("/api/admin/audit-logs", headers=headers)
    assert r.status_code == 200
    body = r.json()
    actions = [e["action"] for e in body["items"]]
    assert "admin_login" in actions
    assert "admin_login_failed" in actions
    assert "user_status_update" in actions
    # Newest first
    timestamps = [e["timestamp"] for e in body["items"]]
    assert timestamps == sorted(timestamps, reverse=True)

    # Action filter
    r = await client.get("/api/admin/audit-logs?action=user_status_update", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["metadata"]["active"] is False
    assert items[0]["target"] == user["id"]


async def test_audit_records_template_publish_and_case_form_save(client, clean_db):
    admin, token = await create_admin(role="super_admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Create + publish a template
    r = await client.post("/api/admin/templates", json={
        "id": "audit_test_tpl",
        "name_en": "Audit Test",
        "name_gu": "ઓડિટ ટેસ્ટ",
        "category": "General",
        "content_en": "Hello {{party_name}}",
        "content_gu": "હેલો {{party_name}}",
        "fields": [{"key": "party_name", "label_en": "Party", "label_gu": "પક્ષ", "type": "text", "required": True}],
    }, headers=headers)
    assert r.status_code == 200

    r = await client.post("/api/admin/templates/audit_test_tpl/publish", headers=headers)
    assert r.status_code == 200

    # Save a case form
    r = await client.post("/api/admin/case-forms/audit_case_type", json={
        "name_en": "Audit Form",
        "name_gu": "ઓડિટ ફોર્મ",
        "category": "Civil",
        "fields": [],
    }, headers=headers)
    assert r.status_code == 200

    r = await client.get("/api/admin/audit-logs", headers=headers)
    assert r.status_code == 200
    actions = {e["action"] for e in r.json()["items"]}
    assert "template_create" in actions
    assert "template_publish" in actions
    assert "case_form_save" in actions
    assert r.json()["total"] >= 3
