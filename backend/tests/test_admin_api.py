"""Tests for NyaySetu Pro Admin Portal API — Phase 1.

Covers:
- Admin login (success, wrong password, unknown email, inactive admin)
- Admin JWT validation (valid, missing, expired, lawyer JWT rejected)
- Admin /auth/me endpoint
- Admin /auth/logout endpoint
- Admin /dashboard/stats endpoint
- require_super_admin authorization
- password_hash never exposed in API responses
- Security isolation between admin and lawyer JWTs

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
import time
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone, timedelta

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, JWT_SECRET
from httpx import AsyncClient, ASGITransport


# ============================================================
# Fixtures
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    """Drop all test collections before/after the test."""
    for coll_name in ["admin_users", "users", "wallets", "cases",
                      "applications", "transactions", "referrals", "drafts"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["admin_users", "users", "wallets", "cases",
                      "applications", "transactions", "referrals", "drafts"]:
        await db[coll_name].drop()


# ============================================================
# Helpers
# ============================================================

async def create_test_admin(
    email="admin@test.com",
    password="TestPass123!",
    role="super_admin",
    active=True,
    name="Test Admin",
):
    """Helper: create an admin user directly in the DB."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_id = str(uuid.uuid4())
    admin_doc = {
        "id": admin_id,
        "email": email,
        "password_hash": hashed,
        "name": name,
        "role": role,
        "active": active,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin_doc.copy())
    return admin_doc


async def create_test_lawyer(mobile="9999900001"):
    """Helper: create a lawyer user and return JWT."""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": None,
        "name": "Test Lawyer",
        "provider": "mobile",
        "bar_council_no": None,
        "state": None,
        "district": None,
        "court": None,
        "language_pref": "en",
        "theme_pref": "light",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "referred_by": None,
        "favourite_courts": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 5,
        "free_credits_granted": 5,
        "total_used": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_token(user_id)
    return user, token


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# 1. ADMIN LOGIN TESTS
# ============================================================

class TestAdminLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client, clean_db):
        """Admin login with correct credentials returns JWT and admin info."""
        await create_test_admin(email="admin@test.com", password="Secret123!")
        r = await client.post("/api/admin/auth/login", json={
            "email": "admin@test.com",
            "password": "Secret123!",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert "admin" in data
        assert data["admin"]["email"] == "admin@test.com"
        assert data["admin"]["role"] == "super_admin"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, clean_db):
        """Wrong password returns 401."""
        await create_test_admin(email="admin@test.com", password="Correct123!")
        r = await client.post("/api/admin/auth/login", json={
            "email": "admin@test.com",
            "password": "WrongPassword!",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(self, client, clean_db):
        """Non-existent admin email returns 401."""
        r = await client.post("/api/admin/auth/login", json={
            "email": "nobody@test.com",
            "password": "Whatever123!",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_admin(self, client, clean_db):
        """Inactive admin cannot login."""
        await create_test_admin(email="disabled@test.com", password="Pass123!", active=False)
        r = await client.post("/api/admin/auth/login", json={
            "email": "disabled@test.com",
            "password": "Pass123!",
        })
        assert r.status_code == 401
        assert "disabled" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_password_hash_not_exposed(self, client, clean_db):
        """password_hash must NEVER appear in login response."""
        await create_test_admin(email="admin@test.com", password="Secret123!")
        r = await client.post("/api/admin/auth/login", json={
            "email": "admin@test.com",
            "password": "Secret123!",
        })
        assert r.status_code == 200
        data = r.json()
        assert "password_hash" not in data["admin"]
        assert "password_hash" not in r.text


# ============================================================
# 2. ADMIN AUTH/ME TESTS
# ============================================================

class TestAdminAuthMe:
    @pytest.mark.asyncio
    async def test_me_with_valid_admin_token(self, client, clean_db):
        """GET /auth/me with valid admin token returns admin info."""
        admin = await create_test_admin()
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        r = await client.get("/api/admin/auth/me", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == admin["email"]
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_me_no_token(self, client, clean_db):
        """GET /auth/me without token returns 401."""
        r = await client.get("/api/admin/auth/me")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_lawyer_jwt(self, client, clean_db):
        """GET /auth/me with a LAWYER JWT must be REJECTED (401)."""
        _, lawyer_token = await create_test_lawyer()
        r = await client.get("/api/admin/auth/me", headers=auth(lawyer_token))
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, client, clean_db):
        """GET /auth/me with garbage token returns 401."""
        r = await client.get("/api/admin/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_with_expired_token(self, client, clean_db):
        """GET /auth/me with expired admin token returns 401."""
        import jwt as pyjwt
        admin = await create_test_admin()
        payload = {
            "sub": admin["id"],
            "email": admin["email"],
            "role": admin["role"],
            "token_type": "admin",
            "iat": int(time.time()) - 86400,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        expired_token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")
        r = await client.get("/api/admin/auth/me", headers=auth(expired_token))
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_inactive_admin_rejected(self, client, clean_db):
        """An admin that becomes inactive after token creation is rejected."""
        admin = await create_test_admin(active=True)
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        # Deactivate the admin
        await db.admin_users.update_one({"id": admin["id"]}, {"$set": {"active": False}})
        r = await client.get("/api/admin/auth/me", headers=auth(token))
        assert r.status_code == 401


# ============================================================
# 3. ADMIN DASHBOARD TESTS
# ============================================================

class TestAdminDashboard:
    @pytest.mark.asyncio
    async def test_dashboard_with_admin_token(self, client, clean_db):
        """GET /dashboard/stats with valid admin token returns real stats."""
        admin = await create_test_admin()
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        # Create some test data
        await create_test_lawyer(mobile="9999900002")
        await create_test_lawyer(mobile="9999900003")
        r = await client.get("/api/admin/dashboard/stats", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert "total_users" in data
        assert "total_cases" in data
        assert "total_documents_generated" in data
        assert "total_credits_consumed" in data
        assert "total_transactions" in data
        assert "recent_users" in data
        assert "recent_applications" in data
        assert data["total_users"] >= 2

    @pytest.mark.asyncio
    async def test_dashboard_with_lawyer_jwt(self, client, clean_db):
        """GET /dashboard/stats with lawyer JWT must be REJECTED."""
        _, lawyer_token = await create_test_lawyer()
        r = await client.get("/api/admin/dashboard/stats", headers=auth(lawyer_token))
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_dashboard_no_token(self, client, clean_db):
        """GET /dashboard/stats without token returns 401."""
        r = await client.get("/api/admin/dashboard/stats")
        assert r.status_code == 401


# ============================================================
# 4. ADMIN LOGOUT TESTS
# ============================================================

class TestAdminLogout:
    @pytest.mark.asyncio
    async def test_logout_success(self, client, clean_db):
        """POST /auth/logout with admin token returns success."""
        admin = await create_test_admin()
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        r = await client.post("/api/admin/auth/logout", headers=auth(token))
        assert r.status_code == 200
        assert r.json()["success"] is True


# ============================================================
# 5. SUPER ADMIN AUTHORIZATION TESTS
# ============================================================

class TestSuperAdminAuthorization:
    @pytest.mark.asyncio
    async def test_admin_role_rejected_by_require_super_admin(self, client, clean_db):
        """require_super_admin must reject admin-role users with 403."""
        admin = await create_test_admin(role="admin")
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        from server import require_super_admin
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(f"Bearer {token}")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_super_admin_accepted_by_require_super_admin(self, client, clean_db):
        """require_super_admin must accept super_admin-role users."""
        admin = await create_test_admin(role="super_admin")
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        from server import require_super_admin
        result = await require_super_admin(f"Bearer {token}")
        assert result["role"] == "super_admin"


# ============================================================
# 6. SECURITY ISOLATION TESTS
# ============================================================

class TestSecurityIsolation:
    @pytest.mark.asyncio
    async def test_admin_jwt_cannot_access_lawyer_profile(self, client, clean_db):
        """Admin JWT must NOT work on lawyer endpoints (GET /api/profile/me)."""
        admin = await create_test_admin()
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        r = await client.get("/api/profile/me", headers=auth(token))
        # get_user() looks up in users collection by admin_id → not found → 401
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_lawyer_jwt_cannot_access_admin_dashboard(self, client, clean_db):
        """Lawyer JWT must NOT work on admin endpoints."""
        _, lawyer_token = await create_test_lawyer()
        r = await client.get("/api/admin/dashboard/stats", headers=auth(lawyer_token))
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_password_hash_never_in_me_response(self, client, clean_db):
        """password_hash must never appear in /auth/me response."""
        admin = await create_test_admin()
        token = make_admin_token(admin["id"], admin["email"], admin["role"])
        r = await client.get("/api/admin/auth/me", headers=auth(token))
        assert r.status_code == 200
        assert "password_hash" not in r.text

    @pytest.mark.asyncio
    async def test_login_updates_last_login(self, client, clean_db):
        """Successful login should update last_login timestamp."""
        admin = await create_test_admin(email="track@test.com", password="Pass123!")
        assert admin["last_login"] is None
        r = await client.post("/api/admin/auth/login", json={
            "email": "track@test.com",
            "password": "Pass123!",
        })
        assert r.status_code == 200
        updated = await db.admin_users.find_one({"email": "track@test.com"})
        assert updated["last_login"] is not None
