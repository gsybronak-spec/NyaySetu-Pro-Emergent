"""Tests for NyaySetu Pro Admin Settings module (Master Plan Phase 40).

Covers:
- Settings endpoints require admin auth (no token / lawyer token rejected)
- Admin can list all settings with defaults
- Regular admin cannot update settings (403)
- Super admin can update signup_credits -> new accounts actually get them
- otp_max_attempts setting is enforced at OTP verification
- default_page_size setting flows into generated documents (real PDF MediaBox)
- Invalid values rejected (422)
- Unknown setting -> 404
- Audit trail records settings updates

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import re
import uuid
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_settings")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone, timedelta

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_settings"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, now
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs",
               "plans", "settings"]


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


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def pdf_mediabox(pdf_bytes: bytes):
    m = re.search(rb"/MediaBox\s*\[\s*([^\]]+)\]", pdf_bytes)
    assert m, "MediaBox not found"
    parts = [float(x) for x in m.group(1).split()]
    return parts[2], parts[3]


# ============================================================
# Auth
# ============================================================

async def test_settings_endpoints_require_admin_auth(client, clean_db):
    r = await client.get("/api/admin/settings")
    assert r.status_code == 401

    lawyer = await create_lawyer("9876500001")
    tok = make_token(lawyer["id"])
    r = await client.get("/api/admin/settings", headers=H(tok))
    assert r.status_code == 401


# ============================================================
# List / update permissions
# ============================================================

async def test_admin_lists_all_settings(client, clean_db):
    _, token = await create_admin()
    r = await client.get("/api/admin/settings", headers=H(token))
    assert r.status_code == 200
    keys = {s["key"] for s in r.json()}
    assert keys == {"signup_credits", "default_page_size",
                    "otp_ttl_seconds", "otp_resend_cooldown_seconds", "otp_max_attempts"}
    by_key = {s["key"]: s for s in r.json()}
    assert by_key["signup_credits"]["value"] == 5
    assert by_key["default_page_size"]["value"] == "A4"
    assert by_key["signup_credits"]["type"] == "int"
    assert by_key["default_page_size"]["type"] == "str"


async def test_regular_admin_cannot_update(client, clean_db):
    _, token = await create_admin(role="admin")
    r = await client.put("/api/admin/settings/signup_credits", json={"value": 10}, headers=H(token))
    assert r.status_code == 403


async def test_unknown_setting_404_and_invalid_values_422(client, clean_db):
    _, token = await create_admin(role="super_admin")
    r = await client.put("/api/admin/settings/not_a_setting", json={"value": 1}, headers=H(token))
    assert r.status_code == 404

    r = await client.put("/api/admin/settings/signup_credits", json={"value": -5}, headers=H(token))
    assert r.status_code == 422

    r = await client.put("/api/admin/settings/signup_credits", json={"value": "many"}, headers=H(token))
    assert r.status_code == 422

    r = await client.put("/api/admin/settings/default_page_size", json={"value": "Letter"}, headers=H(token))
    assert r.status_code == 422

    r = await client.put("/api/admin/settings/otp_max_attempts", json={"value": 50}, headers=H(token))
    assert r.status_code == 422


# ============================================================
# Behavior integration
# ============================================================

async def test_signup_credits_setting_applies(client, clean_db):
    _, token = await create_admin(role="super_admin")
    r = await client.put("/api/admin/settings/signup_credits", json={"value": 12}, headers=H(token))
    assert r.status_code == 200
    assert r.json()["value"] == 12

    # New user via OTP signup gets 12 credits
    r = await client.post("/api/auth/send-otp", json={"mobile": "9876543210"})
    assert r.status_code == 200
    r = await client.post("/api/auth/verify-otp", json={"mobile": "9876543210", "otp": "123456"})
    assert r.status_code == 200
    user_id = r.json()["user"]["id"]
    wallet = await db.wallets.find_one({"user_id": user_id})
    assert wallet["balance"] == 12
    assert wallet["free_credits_granted"] == 12


async def test_otp_max_attempts_setting_enforced(client, clean_db):
    _, token = await create_admin(role="super_admin")
    r = await client.put("/api/admin/settings/otp_max_attempts", json={"value": 1}, headers=H(token))
    assert r.status_code == 200

    await client.post("/api/auth/send-otp", json={"mobile": "9876543211"})
    # First wrong attempt is allowed (attempts 0 -> 1)
    r = await client.post("/api/auth/verify-otp", json={"mobile": "9876543211", "otp": "999999"})
    assert r.status_code == 400
    # Second attempt hits the cap -> OTP deleted, blocked
    r = await client.post("/api/auth/verify-otp", json={"mobile": "9876543211", "otp": "999999"})
    assert r.status_code == 429


async def test_default_page_size_setting_flows_into_pdf(client, clean_db):
    _, token = await create_admin(role="super_admin")
    r = await client.put("/api/admin/settings/default_page_size", json={"value": "Legal"}, headers=H(token))
    assert r.status_code == 200

    lawyer = await create_lawyer("9876500001")
    lt = make_token(lawyer["id"])
    # Download WITHOUT page_size -> should use the Legal default
    r = await client.post("/api/applications/download", headers=H(lt), json={
        "template_id": "adjournment", "language": "gu",
        "values": {"reason": "test", "next_date": "01-01-2027"},
        "format": "pdf", "filename": "default_legal.pdf",
    })
    assert r.status_code == 200, r.text
    w, h = pdf_mediabox(base64.b64decode(r.json()["base64"]))
    assert abs(w - 612) < 2 and abs(h - 1008) < 2, f"expected Legal, got {w}x{h}"

    # Back to A4 default
    r = await client.put("/api/admin/settings/default_page_size", json={"value": "A4"}, headers=H(token))
    assert r.status_code == 200


async def test_settings_update_is_audited(client, clean_db):
    _, token = await create_admin(role="super_admin")
    await client.put("/api/admin/settings/signup_credits", json={"value": 8}, headers=H(token))
    r = await client.get("/api/admin/audit-logs", headers=H(token))
    entries = [e for e in r.json()["items"] if e["action"] == "settings_update"]
    assert len(entries) == 1
    assert entries[0]["target"] == "signup_credits"
    assert entries[0]["metadata"]["value"] == 8
