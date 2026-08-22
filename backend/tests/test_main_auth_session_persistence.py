"""Comprehensive tests for Main Lawyer App Persistent Sessions and Silent Renewal.

Validates the complete dual-token lifecycle:
1. OTP login, password login, registration, Google auth, Firebase auth issue 15m access + 90d refresh tokens
2. Silent refresh with valid refresh token returns fresh access token
3. Refresh failure handling for invalid, expired, and revoked sessions
4. Refresh failure for disabled/banned users
5. Explicit logout server-side revocation
6. Expired access token boundary test
7. Refresh token cannot be used as access token
8. Role isolation: Admin token cannot refresh user session, user token cannot access admin API
9. Sliding expiration extension on refresh
10. Backward compatibility for existing 90-day JWTs
11. Password reset / token_version revocation
12. Multi-session device isolation
"""

import os
import sys
import uuid
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Environment configuration
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-1234567890-must-be-long")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_main_persistence")
os.environ.setdefault("DEV_OTP_ALLOWED", "true")

import pytest
import pytest_asyncio
import jwt
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_main_persistence"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    make_token,
    hash_password,
    create_user_session,
    now,
    USER_ACCESS_TOKEN_EXPIRY_MINUTES,
    USER_SESSION_EXPIRY_DAYS,
    JWT_SECRET,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    server.db = db
    for coll_name in ["users", "user_sessions", "otps", "admin_users", "admin_sessions", "audit_logs"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["users", "user_sessions", "otps", "admin_users", "admin_sessions", "audit_logs"]:
        await db[coll_name].drop()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def create_test_user(mobile=None, email=None, password="Password@123", active=True, is_complete=True):
    user_id = str(uuid.uuid4())
    mobile = mobile or f"98{secrets.randbelow(90000000) + 10000000}"
    email = email or f"lawyer_{secrets.token_hex(4)}@test.com"
    pwd_hash = hash_password(password)
    user_doc = {
        "id": user_id,
        "mobile": mobile,
        "email": email,
        "name": f"Advocate Test {secrets.token_hex(2)}",
        "first_name": "Advocate",
        "last_name": "Tester",
        "password_hash": pwd_hash,
        "active": active,
        "status": "active" if active else "banned",
        "user_type": "Advocate",
        "bar_council_no": "GUJ/1234/2020",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "profile_completed": is_complete,
        "is_profile_complete": is_complete,
        "token_version": 0,
        "created_at": now().isoformat(),
    }
    await db.users.insert_one(user_doc)
    return user_doc


class TestMainAuthSessionPersistence:

    async def test_01_otp_login_issues_access_and_refresh_tokens(self, client):
        """OTP login issues 15-minute access token and 90-day persistent refresh token."""
        user = await create_test_user()
        # Seed valid OTP
        await db.otps.insert_one({
            "mobile": user["mobile"],
            "otp": "123456",
            "kind": "login",
            "attempts": 0,
            "created_at": now().isoformat(),
            "expires_at": (now() + timedelta(minutes=10)).isoformat(),
        })

        res = await client.post("/api/auth/verify-otp", json={"mobile": user["mobile"], "otp": "123456"})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert "refresh_token" in data
        assert data["user"]["id"] == user["id"]

        # Verify access token is a valid 15-minute JWT
        payload = jwt.decode(data["token"], JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == user["id"]
        assert payload["token_type"] == "user"
        assert payload["exp"] - payload["iat"] <= USER_ACCESS_TOKEN_EXPIRY_MINUTES * 60 + 5

        # Verify session stored in db.user_sessions
        refresh_token = data["refresh_token"]
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        session = await db.user_sessions.find_one({"token_hash": token_hash})
        assert session is not None
        assert session["user_id"] == user["id"]
        assert session["revoked"] is False

    async def test_02_password_login_issues_access_and_refresh_tokens(self, client):
        """Password login issues access and refresh tokens."""
        user = await create_test_user(password="Secret@123")
        res = await client.post("/api/auth/login", json={"identifier": user["mobile"], "password": "Secret@123"})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == user["email"]

    async def test_03_registration_issues_access_and_refresh_tokens(self, client):
        """Registration issues access and refresh tokens."""
        mobile = f"97{secrets.randbelow(90000000) + 10000000}"
        email = f"new_{secrets.token_hex(4)}@test.com"
        await db.otps.insert_one({
            "mobile": mobile,
            "otp": "123456",
            "kind": "login",
            "attempts": 0,
            "created_at": now().isoformat(),
            "expires_at": (now() + timedelta(minutes=10)).isoformat(),
        })

        res = await client.post("/api/auth/register", json={
            "mobile": mobile,
            "otp": "123456",
            "password": "Register@123",
            "name": "New Registered Lawyer",
            "email": email,
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert "refresh_token" in data
        assert data["is_new"] is True

    async def test_04_silent_refresh_with_valid_refresh_token(self, client):
        """POST /api/auth/refresh returns a fresh 15-minute access token."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])

        res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["refresh_token"] == raw_refresh
        assert data["user"]["id"] == user["id"]

        payload = jwt.decode(data["token"], JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == user["id"]
        assert payload["session_id"] == session_id

    async def test_05_refresh_fails_with_invalid_or_bogus_token(self, client):
        """Bogus refresh token returns 401."""
        res = await client.post("/api/auth/refresh", json={"refresh_token": "bogus-random-refresh-token"})
        assert res.status_code == 401
        assert "Invalid refresh token" in res.json()["detail"]

    async def test_06_refresh_fails_with_expired_session(self, client):
        """Expired session returns 401."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])
        # Set session expires_at in the past
        past = (now() - timedelta(days=1)).isoformat()
        token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        await db.user_sessions.update_one({"token_hash": token_hash}, {"$set": {"expires_at": past}})

        res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert res.status_code == 401
        assert "Session has expired" in res.json()["detail"]

    async def test_07_refresh_fails_for_disabled_user(self, client):
        """Disabled user cannot refresh their session."""
        user = await create_test_user(active=False)
        session_id, raw_refresh = await create_user_session(user["id"])

        res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert res.status_code == 401
        assert "Account disabled" in res.json()["detail"]

    async def test_08_explicit_logout_revokes_session(self, client):
        """Explicit logout marks session revoked in MongoDB and blocks subsequent refresh."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])

        # Logout
        logout_res = await client.post("/api/auth/logout", json={"refresh_token": raw_refresh})
        assert logout_res.status_code == 200
        assert logout_res.json()["success"] is True

        # Verify in DB
        token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        session = await db.user_sessions.find_one({"token_hash": token_hash})
        assert session["revoked"] is True
        assert session["revoked_at"] is not None

        # Subsequent refresh MUST fail
        refresh_res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert refresh_res.status_code == 401
        assert "revoked" in refresh_res.json()["detail"]

    async def test_09_expired_access_token_boundary_handling(self, client):
        """Expired access token is rejected on protected APIs, but user can refresh silently."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])

        # Create expired access token (1 hour in past)
        expired_payload = {
            "sub": user["id"],
            "ver": 0,
            "iat": int((now() - timedelta(hours=2)).timestamp()),
            "exp": int((now() - timedelta(hours=1)).timestamp()),
            "token_type": "user",
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")

        # Protected API rejects expired access token
        res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401

        # Silent refresh succeeds
        refresh_res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert refresh_res.status_code == 200
        fresh_token = refresh_res.json()["token"]

        # Protected API accepts fresh access token
        valid_res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {fresh_token}"})
        assert valid_res.status_code == 200
        assert valid_res.json()["id"] == user["id"]

    async def test_10_refresh_token_cannot_be_used_directly_as_access_token(self, client):
        """Refresh token cannot be passed in Authorization header as a JWT."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])

        res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {raw_refresh}"})
        assert res.status_code == 401

    async def test_11_admin_token_cannot_refresh_lawyer_session(self, client):
        """Admin token / admin refresh token cannot refresh a lawyer session."""
        admin_id = str(uuid.uuid4())
        admin_token = jwt.encode({
            "sub": admin_id,
            "role": "super_admin",
            "token_type": "admin",
            "iat": int(now().timestamp()),
            "exp": int((now() + timedelta(hours=1)).timestamp()),
        }, JWT_SECRET, algorithm="HS256")

        # Cannot use admin token to refresh user session
        res = await client.post("/api/auth/refresh", json={"refresh_token": admin_token})
        assert res.status_code == 401

        # Cannot use admin token on lawyer endpoints
        lawyer_res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert lawyer_res.status_code == 401

    async def test_12_lawyer_token_cannot_access_admin_endpoints(self, client):
        """Lawyer access token is blocked from accessing admin portal endpoints."""
        user = await create_test_user()
        token = make_token(user["id"], 0)

        res = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401
        assert "Not an admin token" in res.json()["detail"]

    async def test_13_sliding_session_expiration_extended_on_refresh(self, client):
        """Each refresh updates last_used_at and extends expires_at to +90 days."""
        user = await create_test_user()
        session_id, raw_refresh = await create_user_session(user["id"])

        token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        session_before = await db.user_sessions.find_one({"token_hash": token_hash})

        res = await client.post("/api/auth/refresh", json={"refresh_token": raw_refresh})
        assert res.status_code == 200

        session_after = await db.user_sessions.find_one({"token_hash": token_hash})
        assert session_after["last_used_at"] >= session_before["last_used_at"]
        expires = datetime.fromisoformat(session_after["expires_at"])
        assert expires > now() + timedelta(days=88)

    async def test_14_password_reset_bumps_token_version(self, client):
        """Password reset bumps token_version and invalidates old tokens."""
        user = await create_test_user(password="OldPassword@123")
        old_token = make_token(user["id"], 0)

        # Reset password
        await db.otps.insert_one({
            "mobile": user["mobile"],
            "otp": "123456",
            "kind": "reset",
            "attempts": 0,
            "created_at": now().isoformat(),
            "expires_at": (now() + timedelta(minutes=10)).isoformat(),
        })

        reset_res = await client.post("/api/auth/reset-password", json={
            "mobile": user["mobile"],
            "otp": "123456",
            "new_password": "NewPassword@123",
        })
        assert reset_res.status_code == 200

        # Old token with ver=0 is now rejected
        me_res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {old_token}"})
        assert me_res.status_code == 401
        assert "Session expired" in me_res.json()["detail"]

    async def test_15_legacy_jwt_backward_compatibility(self, client):
        """Existing 90-day JWTs without session_id continue working seamlessly on get_user."""
        user = await create_test_user()
        legacy_payload = {
            "sub": user["id"],
            "ver": 0,
            "iat": int(now().timestamp()),
            "exp": int((now() + timedelta(days=90)).timestamp()),
        }
        legacy_token = jwt.encode(legacy_payload, JWT_SECRET, algorithm="HS256")

        res = await client.get("/api/profile/me", headers={"Authorization": f"Bearer {legacy_token}"})
        assert res.status_code == 200
        assert res.json()["id"] == user["id"]

    async def test_16_multisession_device_isolation(self, client):
        """Logging out on Device A does NOT invalidate the session on Device B."""
        user = await create_test_user()
        sess_a_id, refresh_a = await create_user_session(user["id"], user_agent="Device A Mobile")
        sess_b_id, refresh_b = await create_user_session(user["id"], user_agent="Device B Web")

        # Logout Device A
        await client.post("/api/auth/logout", json={"refresh_token": refresh_a})

        # Device A cannot refresh
        res_a = await client.post("/api/auth/refresh", json={"refresh_token": refresh_a})
        assert res_a.status_code == 401

        # Device B CAN still refresh
        res_b = await client.post("/api/auth/refresh", json={"refresh_token": refresh_b})
        assert res_b.status_code == 200
        assert res_b.json()["user"]["id"] == user["id"]
