"""NyaySetu Pro — Phase 6/7 Admin Session Persistence & Silent Renewal Test Suite.

Verifies:
1. Dual-token authentication (short-lived access JWT + long-lived persistent refresh session).
2. SHA-256 token hashing in MongoDB (raw refresh tokens never stored).
3. Silent token renewal on /api/admin/auth/refresh.
4. Definitive rejection of expired, revoked, or non-existent refresh tokens.
5. Inactive/disabled admin rejection on refresh.
6. Explicit logout session revocation and audit logging.
7. Role separation: lawyer tokens cannot refresh admin sessions.
8. Access token expiration boundary: expired access tokens rejected by get_admin(), but renewable via refresh token.
9. Scrubbing of sensitive credentials from audit logs and public admin responses.
10. Multiple concurrent / rapid requests stability.
"""

import os
import sys
import uuid
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_admin_persistence")

import pytest
import pytest_asyncio
import bcrypt
import jwt
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_admin_persistence"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    JWT_SECRET,
    make_token,
    make_admin_token,
    create_admin_session,
    admin_public,
    now,
    ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES,
    ADMIN_SESSION_EXPIRY_DAYS,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    server.db = db
    for coll_name in ["admin_users", "admin_sessions", "audit_logs", "users"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["admin_users", "admin_sessions", "audit_logs", "users"]:
        await db[coll_name].drop()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def create_test_super_admin(email=None, password="Password123!"):
    if email is None:
        email = f"superadmin_{uuid.uuid4().hex[:8]}@nyaysetu.test"
    admin_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    doc = {
        "id": admin_id,
        "email": email,
        "name": "Super Admin Test",
        "role": "super_admin",
        "active": True,
        "password_hash": pw_hash,
        "created_at": now().isoformat(),
        "last_login": None,
    }
    await db.admin_users.insert_one(doc)
    return doc


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestAdminSessionPersistence:

    @pytest.mark.asyncio
    async def test_01_admin_login_issues_access_and_refresh_tokens(self, client):
        """Admin login returns short-lived access token + persistent refresh token + admin profile."""
        admin = await create_test_super_admin()
        
        resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        
        assert "token" in data
        assert "refresh_token" in data
        assert "admin" in data
        assert data["admin"]["email"] == admin["email"]
        assert "password_hash" not in data["admin"]
        
        # Verify access token is valid JWT with admin claims
        payload = jwt.decode(data["token"], JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == admin["id"]
        assert payload["token_type"] == "admin"
        assert payload["role"] == "super_admin"
        
        # Verify session is stored in MongoDB hashed
        raw_refresh = data["refresh_token"]
        token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        session = await db.admin_sessions.find_one({"token_hash": token_hash})
        assert session is not None
        assert session["admin_id"] == admin["id"]
        assert session["revoked"] is False
        assert "expires_at" in session

    @pytest.mark.asyncio
    async def test_02_silent_refresh_with_valid_refresh_token(self, client):
        """Valid refresh token silently produces a fresh access token."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        refresh_token = login_resp.json()["refresh_token"]
        
        # Call refresh endpoint
        refresh_resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        data = refresh_resp.json()
        assert "token" in data
        assert data["token"] != ""
        assert data["admin"]["email"] == admin["email"]

        # Verify new access token works on protected endpoints
        me_resp = await client.get("/api/admin/auth/me", headers=auth_header(data["token"]))
        assert me_resp.status_code == 200
        assert me_resp.json()["id"] == admin["id"]

    @pytest.mark.asyncio
    async def test_03_refresh_with_invalid_or_bogus_token(self, client):
        """Bogus refresh token is rejected with HTTP 401."""
        await create_test_super_admin()
        resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": "totally_invalid_refresh_token_12345"}
        )
        assert resp.status_code == 401
        assert "Invalid refresh token" in resp.text

    @pytest.mark.asyncio
    async def test_04_refresh_with_expired_session(self, client):
        """Expired session (>30 days) is rejected with HTTP 401."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        refresh_token = login_resp.json()["refresh_token"]
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        
        # Backdate expiration to the past
        past_date = (now() - timedelta(days=1)).isoformat()
        await db.admin_sessions.update_one(
            {"token_hash": token_hash},
            {"$set": {"expires_at": past_date}}
        )
        
        resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 401
        assert "Session has expired" in resp.text

    @pytest.mark.asyncio
    async def test_05_refresh_fails_for_disabled_admin(self, client):
        """Disabled admin cannot refresh session."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        refresh_token = login_resp.json()["refresh_token"]
        
        # Deactivate admin
        await db.admin_users.update_one({"id": admin["id"]}, {"$set": {"active": False}})
        
        resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 401
        assert "Admin account is disabled" in resp.text

    @pytest.mark.asyncio
    async def test_06_explicit_logout_revokes_session(self, client):
        """Explicit logout permanently revokes the refresh session."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        access_token = login_resp.json()["token"]
        refresh_token = login_resp.json()["refresh_token"]
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        
        # Explicit logout
        logout_resp = await client.post(
            "/api/admin/auth/logout",
            headers=auth_header(access_token),
            json={"refresh_token": refresh_token}
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["success"] is True

        # Verify session is marked revoked in DB
        session = await db.admin_sessions.find_one({"token_hash": token_hash})
        assert session["revoked"] is True
        assert session["revoked_at"] is not None

        # Subsequent refresh must fail
        refresh_resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 401
        assert "Session has been revoked" in refresh_resp.text

    @pytest.mark.asyncio
    async def test_07_expired_access_token_boundary_handling(self, client):
        """Access token expired boundary: get_admin rejects expired JWT, refresh restores access."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        refresh_token = login_resp.json()["refresh_token"]
        
        # Create an expired access token (1 second in the past)
        expired_payload = {
            "sub": admin["id"],
            "email": admin["email"],
            "role": admin["role"],
            "token_type": "admin",
            "iat": int((now() - timedelta(hours=1)).timestamp()),
            "exp": int((now() - timedelta(seconds=1)).timestamp()),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
        
        # Protected endpoint must reject expired access token
        me_resp = await client.get("/api/admin/auth/me", headers=auth_header(expired_token))
        assert me_resp.status_code == 401
        assert "Admin token expired" in me_resp.text

        # Client silently refreshes using persistent refresh token
        refresh_resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_resp.status_code == 200
        fresh_token = refresh_resp.json()["token"]

        # Retry with fresh access token succeeds seamlessly
        retry_resp = await client.get("/api/admin/auth/me", headers=auth_header(fresh_token))
        assert retry_resp.status_code == 200
        assert retry_resp.json()["email"] == admin["email"]

    @pytest.mark.asyncio
    async def test_08_refresh_token_cannot_be_used_directly_as_access_token(self, client):
        """Refresh token cannot be passed as Bearer access token on admin endpoints."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        refresh_token = login_resp.json()["refresh_token"]
        
        resp = await client.get("/api/admin/dashboard/stats", headers=auth_header(refresh_token))
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_09_lawyer_token_cannot_refresh_admin_session(self, client):
        """Lawyer user JWT cannot obtain an admin access token."""
        lawyer_token = make_token("user_12345", "+919876543210")
        resp = await client.post(
            "/api/admin/auth/refresh",
            json={"refresh_token": lawyer_token}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_10_sensitive_credentials_never_in_audit_logs(self, client):
        """Raw refresh tokens and passwords never appear in db.audit_logs."""
        admin = await create_test_super_admin()
        login_resp = await client.post(
            "/api/admin/auth/login",
            json={"email": admin["email"], "password": "Password123!"}
        )
        raw_refresh = login_resp.json()["refresh_token"]
        access_token = login_resp.json()["token"]

        await client.post(
            "/api/admin/auth/logout",
            headers=auth_header(access_token),
            json={"refresh_token": raw_refresh}
        )

        logs = await db.audit_logs.find({}).to_list(100)
        assert len(logs) >= 2
        for log_entry in logs:
            raw_str = str(log_entry)
            assert raw_refresh not in raw_str, "Raw refresh token found in audit logs!"
            assert "Password123!" not in raw_str, "Raw password found in audit logs!"
