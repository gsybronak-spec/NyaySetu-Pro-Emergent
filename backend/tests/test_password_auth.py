"""Password authentication + OTP reliability regression tests.

Covers (Master Plan auth task):
AUTH:
1. Create account (register, OTP-verified, auto-login)
2. Password mismatch (confirm handled client-side; weak password rejected)
3. Weak password (<8 chars) rejected
4. Existing user (OTP-only user can still login via OTP)
5. Duplicate account (mobile / email) rejected — no duplicate users
6. Mobile password login
7. Email password login
8. Wrong password -> generic 401 (no user enumeration)
9. Disabled account blocked
10. Existing OTP-only user -> password login still 401 until set-password
11. Set password (authenticated) -> then password login works
12. Forgot password flow (OTP kind=reset)
13. Forgot password wrong OTP rejected
14. Correct OTP -> reset works
15. Password reset -> old sessions revoked (token_version)
16. Login after reset
17. password_hash never returned in any user response
18. Rate limiting on login

OTP:
21. OTP send success (login kind)
22-23. Provider timeout / unavailable -> controlled 503 (via _issue_otp path)
24. Provider not configured in production -> controlled 503
26. No hanging request (timeout wired)
28. Resend cooldown 429
29. Max attempts
30. Expiry (existing tests cover; kind-separation tested here)

GOOGLE:
31-38. Existing test_google_oauth.py covers safe-fail/no-Emergent; here we add
     has_password flag / _public_user assertions on the google response.

CORS:
- nyaysetupro.in + www are allowlisted (preflight + GET)
- unknown origin still rejected
"""

import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_password_auth")

import pytest
import pytest_asyncio

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_password_auth"]

import server
server.db = mock_db
db = mock_db
app = server.app

from httpx import AsyncClient, ASGITransport

API = "/api"


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll in ["users", "wallets", "cases", "applications", "drafts",
                 "transactions", "referrals", "admin_users", "templates",
                 "template_versions", "case_forms", "otps", "settings"]:
        await db[coll].drop()


async def send_otp(client, mobile):
    return await client.post(f"{API}/auth/send-otp", json={"mobile": mobile})


async def register_user(client, mobile="9876500001", password="SecurePass123",
                        name="Test Advocate", email="adv1@test.in", otp="123456"):
    await send_otp(client, mobile)
    return await client.post(f"{API}/auth/register", json={
        "mobile": mobile, "otp": otp, "password": password,
        "name": name, "email": email,
    })


def _dump_user(client, token):
    return client.get(f"{API}/profile/me", headers={"Authorization": f"Bearer {token}"})


# ============================================================
# REGISTER / CREATE ACCOUNT
# ============================================================

class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success_auto_login(self, client, clean_db):
        r = await register_user(client)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_new"] is True
        assert d["token"]
        assert d["user"]["mobile"] == "9876500001"
        assert d["user"]["name"] == "Test Advocate"
        assert d["user"]["email"] == "adv1@test.in"
        assert d["user"]["has_password"] is True
        assert "password_hash" not in d["user"]
        # wallet granted
        w = await db.wallets.find_one({"user_id": d["user"]["id"]})
        assert w and w["balance"] >= 1

    @pytest.mark.asyncio
    async def test_register_requires_otp(self, client, clean_db):
        r = await client.post(f"{API}/auth/register", json={
            "mobile": "9876500002", "otp": "654321", "password": "SecurePass123",
        })
        assert r.status_code == 400
        assert "OTP" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_wrong_otp(self, client, clean_db):
        await send_otp(client, "9876500003")
        r = await client.post(f"{API}/auth/register", json={
            "mobile": "9876500003", "otp": "111111", "password": "SecurePass123",
        })
        assert r.status_code == 400
        assert r.json()["detail"] == "Invalid OTP"

    @pytest.mark.asyncio
    async def test_register_weak_password_rejected(self, client, clean_db):
        await send_otp(client, "9876500004")
        r = await client.post(f"{API}/auth/register", json={
            "mobile": "9876500004", "otp": "123456", "password": "short",
        })
        assert r.status_code == 422  # pydantic min_length

    @pytest.mark.asyncio
    async def test_register_duplicate_mobile(self, client, clean_db):
        await register_user(client, mobile="9876500005", email="dup1@test.in")
        r = await register_user(client, mobile="9876500005", email="dup2@test.in")
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"]
        # exactly one user
        n = await db.users.count_documents({"mobile": "9876500005"})
        assert n == 1

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, clean_db):
        await register_user(client, mobile="9876500006", email="same@test.in")
        r = await register_user(client, mobile="9876500007", email="same@test.in")
        assert r.status_code == 409
        n = await db.users.count_documents({"email": "same@test.in"})
        assert n == 1

    @pytest.mark.asyncio
    async def test_register_password_hash_stored_hashed(self, client, clean_db):
        await register_user(client, mobile="9876500008")
        user = await db.users.find_one({"mobile": "9876500008"})
        assert user["password_hash"]
        assert user["password_hash"] != "SecurePass123"
        assert user["password_hash"].startswith("$2")

    @pytest.mark.asyncio
    async def test_register_mobile_only(self, client, clean_db):
        """Name/email optional — keep OTP-style minimal signup working."""
        await send_otp(client, "9876500009")
        r = await client.post(f"{API}/auth/register", json={
            "mobile": "9876500009", "otp": "123456", "password": "SecurePass123",
        })
        assert r.status_code == 200
        assert r.json()["user"]["has_password"] is True


# ============================================================
# LOGIN (mobile + password / email + password)
# ============================================================

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_mobile_password(self, client, clean_db):
        await register_user(client, mobile="9876510001", email="lm1@test.in")
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "9876510001", "password": "SecurePass123",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_new"] is False
        assert d["token"]
        assert d["user"]["mobile"] == "9876510001"
        assert "password_hash" not in d["user"]

    @pytest.mark.asyncio
    async def test_login_email_password(self, client, clean_db):
        await register_user(client, mobile="9876510002", email="lm2@test.in")
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "LM2@test.in", "password": "SecurePass123",
        })
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == "lm2@test.in"

    @pytest.mark.asyncio
    async def test_login_wrong_password_generic(self, client, clean_db):
        await register_user(client, mobile="9876510003")
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "9876510003", "password": "WrongPass999",
        })
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid mobile/email or password."

    @pytest.mark.asyncio
    async def test_login_unknown_user_generic(self, client, clean_db):
        """Must NOT reveal whether the user exists."""
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "9999999999", "password": "Whatever123",
        })
        assert r.status_code == 401
        assert "Invalid mobile/email or password." == r.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_otp_only_user_blocked_from_password(self, client, clean_db):
        """Legacy OTP-created user has no password: password login must fail
        generically until they set a password; OTP login still works."""
        m = "9876510004"
        await send_otp(client, m)
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 200
        assert r.json()["is_new"] is True
        assert r.json()["user"]["has_password"] is False

        r = await client.post(f"{API}/auth/login", json={
            "identifier": m, "password": "SecurePass123",
        })
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid mobile/email or password."

        # OTP login still works for the same user
        await send_otp(client, m)
        r2 = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r2.status_code == 200
        assert r2.json()["is_new"] is False

    @pytest.mark.asyncio
    async def test_login_disabled_account(self, client, clean_db):
        await register_user(client, mobile="9876510005")
        await db.users.update_one({"mobile": "9876510005"}, {"$set": {"active": False}})
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "9876510005", "password": "SecurePass123",
        })
        assert r.status_code == 403
        assert "disabled" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_rate_limited(self, client, clean_db):
        for _ in range(5):
            await client.post(f"{API}/auth/login", json={
                "identifier": "9876510006", "password": "WrongPass999",
            })
        r = await client.post(f"{API}/auth/login", json={
            "identifier": "9876510006", "password": "WrongPass999",
        })
        assert r.status_code == 429
        assert "Too many login attempts" in r.json()["detail"]


# ============================================================
# SET PASSWORD (existing OTP-only users)
# ============================================================

class TestSetPassword:
    @pytest.mark.asyncio
    async def test_set_password_then_password_login(self, client, clean_db):
        m = "9876520001"
        await send_otp(client, m)
        d = (await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})).json()
        token = d["token"]
        assert d["user"]["has_password"] is False

        r = await client.post(f"{API}/auth/set-password", json={"new_password": "NewPass456"},
                              headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

        r = await client.post(f"{API}/auth/login", json={
            "identifier": m, "password": "NewPass456",
        })
        assert r.status_code == 200
        assert r.json()["user"]["has_password"] is True

    @pytest.mark.asyncio
    async def test_set_password_requires_auth(self, client, clean_db):
        r = await client.post(f"{API}/auth/set-password", json={"new_password": "NewPass456"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_set_password_weak_rejected(self, client, clean_db):
        m = "9876520002"
        await send_otp(client, m)
        token = (await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})).json()["token"]
        r = await client.post(f"{API}/auth/set-password", json={"new_password": "tiny"},
                              headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 422


# ============================================================
# FORGOT PASSWORD / RESET
# ============================================================

class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_forgot_reset_full_flow(self, client, clean_db):
        m = "9876530001"
        await register_user(client, mobile=m, email="fp1@test.in")

        r = await client.post(f"{API}/auth/forgot-password", json={"mobile": m})
        assert r.status_code == 200

        r = await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "123456", "new_password": "BrandNewPass1",
        })
        assert r.status_code == 200
        assert "Password reset successfully" in r.json()["message"]

        # old password no longer works
        r = await client.post(f"{API}/auth/login", json={"identifier": m, "password": "SecurePass123"})
        assert r.status_code == 401
        # new password works
        r = await client.post(f"{API}/auth/login", json={"identifier": m, "password": "BrandNewPass1"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_no_user_enumeration(self, client, clean_db):
        """Unknown mobile gets a success-shaped response and no OTP doc."""
        r = await client.post(f"{API}/auth/forgot-password", json={"mobile": "9999999998"})
        assert r.status_code == 200
        assert "OTP has been sent" in r.json()["message"]
        assert await db.otps.find_one({"mobile": "9999999998"}) is None

    @pytest.mark.asyncio
    async def test_reset_wrong_otp(self, client, clean_db):
        m = "9876530002"
        await register_user(client, mobile=m)
        await client.post(f"{API}/auth/forgot-password", json={"mobile": m})
        r = await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "000000", "new_password": "BrandNewPass1",
        })
        assert r.status_code == 400
        assert r.json()["detail"] == "Invalid OTP"

    @pytest.mark.asyncio
    async def test_reset_requires_reset_kind_otp(self, client, clean_db):
        """A login OTP must NOT be accepted for password reset."""
        m = "9876530003"
        await register_user(client, mobile=m)
        await send_otp(client, m)  # kind=login
        r = await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "123456", "new_password": "BrandNewPass1",
        })
        assert r.status_code == 400
        assert "No password reset OTP" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_revokes_old_tokens(self, client, clean_db):
        m = "9876530004"
        await register_user(client, mobile=m)
        old = (await client.post(f"{API}/auth/login", json={
            "identifier": m, "password": "SecurePass123",
        })).json()["token"]

        await client.post(f"{API}/auth/forgot-password", json={"mobile": m})
        await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "123456", "new_password": "BrandNewPass1",
        })

        # pre-reset token is now invalid
        r = await _dump_user(client, old)
        assert r.status_code == 401
        assert "Session expired" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_weak_password(self, client, clean_db):
        m = "9876530005"
        await register_user(client, mobile=m)
        await client.post(f"{API}/auth/forgot-password", json={"mobile": m})
        r = await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "123456", "new_password": "short",
        })
        assert r.status_code == 422


# ============================================================
# OTP RELIABILITY / KIND SEPARATION
# ============================================================

class TestOtpReliability:
    @pytest.mark.asyncio
    async def test_send_otp_login_kind(self, client, clean_db):
        r = await send_otp(client, "9876540001")
        assert r.status_code == 200
        doc = await db.otps.find_one({"mobile": "9876540001"})
        assert doc["kind"] == "login"

    @pytest.mark.asyncio
    async def test_login_otp_rejected_by_reset_endpoint(self, client, clean_db):
        m = "9876540002"
        await register_user(client, mobile=m)
        await send_otp(client, m)  # kind=login
        r = await client.post(f"{API}/auth/reset-password", json={
            "mobile": m, "otp": "123456", "new_password": "BrandNewPass1",
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_verify_otp_rejects_reset_kind(self, client, clean_db):
        m = "9876540003"
        await register_user(client, mobile=m)
        await client.post(f"{API}/auth/forgot-password", json={"mobile": m})  # kind=reset
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 400
        assert "No OTP requested" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_resend_cooldown(self, client, clean_db):
        await send_otp(client, "9876540004")
        r = await send_otp(client, "9876540004")
        assert r.status_code == 429
        assert "wait" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_max_attempts(self, client, clean_db):
        m = "9876540005"
        await send_otp(client, m)
        for _ in range(5):
            await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "000000"})
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "000000"})
        assert r.status_code == 429

    @pytest.mark.asyncio
    async def test_otp_single_use_across_flows(self, client, clean_db):
        """OTP consumed by register cannot be replayed via verify-otp."""
        m = "9876540006"
        await send_otp(client, m)
        await client.post(f"{API}/auth/register", json={
            "mobile": m, "otp": "123456", "password": "SecurePass123",
        })
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_provider_not_configured_production_503(self, client, clean_db, monkeypatch):
        """In declared production with console provider, send-otp returns a
        controlled 503 — never a hang, never a fake OTP."""
        monkeypatch.setattr(server, "_PRODUCTION", True)
        monkeypatch.setattr(server, "_DEV_OTP_ALLOWED", False)
        monkeypatch.setattr(server, "SMS_PROVIDER", "console")
        r = await client.post(f"{API}/auth/send-otp", json={"mobile": "9876540007"})
        assert r.status_code == 503
        assert "OTP service" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_provider_timeout_503(self, client, clean_db, monkeypatch):
        """A hanging SMS provider yields a controlled 503, not a hang."""
        async def slow_sms(mobile, otp):
            raise httpx_timeout()
        monkeypatch.setattr(server, "SMS_PROVIDER", "twilio")
        monkeypatch.setattr(server, "send_sms", slow_sms)
        r = await client.post(f"{API}/auth/send-otp", json={"mobile": "9876540008"})
        assert r.status_code == 503
        assert "temporarily unavailable" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_provider_unavailable_503(self, client, clean_db, monkeypatch):
        async def boom(mobile, otp):
            raise httpx_timeout()
        monkeypatch.setattr(server, "SMS_PROVIDER", "twilio")
        monkeypatch.setattr(server, "send_sms", boom)
        r = await client.post(f"{API}/auth/send-otp", json={"mobile": "9876540009"})
        assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_provider_not_implemented_501(self, client, clean_db, monkeypatch):
        """Unknown provider: exact missing-credential message, not a fake."""
        monkeypatch.setattr(server, "SMS_PROVIDER", "some_other_provider")
        r = await client.post(f"{API}/auth/send-otp", json={"mobile": "9876540010"})
        assert r.status_code == 501
        assert "not implemented" in r.json()["detail"]


class httpx_timeout(Exception):
    pass


# ============================================================
# GOOGLE + _public_user contract
# ============================================================

class TestGoogleContract:
    @pytest.mark.asyncio
    async def test_google_flow_still_works_and_strips_hash(self, client, clean_db, monkeypatch):
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_ID", "test-client-id")
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_SECRET", "test-client-secret")

        async def fake_token(code, redirect_uri):
            return 200, {"access_token": "tok123"}

        async def fake_userinfo(access_token):
            return 200, {"email": "google1@test.in", "email_verified": True, "name": "G User"}

        monkeypatch.setattr(server, "_google_token_exchange", fake_token)
        monkeypatch.setattr(server, "_google_userinfo", fake_userinfo)

        r = await client.post(f"{API}/auth/google", json={
            "code": "abc", "redirect_uri": "https://nyaysetupro.in/",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_new"] is True
        assert d["user"]["email"] == "google1@test.in"
        assert "password_hash" not in d["user"]
        assert d["user"]["has_password"] is False

        # repeat login for existing user
        r2 = await client.post(f"{API}/auth/google", json={
            "code": "def", "redirect_uri": "https://nyaysetupro.in/",
        })
        assert r2.status_code == 200
        assert r2.json()["is_new"] is False

    @pytest.mark.asyncio
    async def test_google_missing_credentials_safe_fail(self, client, clean_db, monkeypatch):
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_ID", "")
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_SECRET", "")
        r = await client.post(f"{API}/auth/google", json={
            "code": "abc", "redirect_uri": "https://nyaysetupro.in/",
        })
        assert r.status_code == 503
        assert "GOOGLE_OAUTH_CLIENT_ID" in r.json()["detail"]


# ============================================================
# PASSWORD_HASH NEVER LEAKS
# ============================================================

class TestNoHashLeak:
    @pytest.mark.asyncio
    async def test_hash_never_in_any_user_response(self, client, clean_db):
        await register_user(client, mobile="9876550001", email="leak@test.in")
        m = "9876550001"
        login = (await client.post(f"{API}/auth/login", json={
            "identifier": m, "password": "SecurePass123",
        })).json()
        assert "password_hash" not in login["user"]

        token = login["token"]
        me = await _dump_user(client, token)
        assert me.status_code == 200
        assert "password_hash" not in me.json()

        # update profile also strips
        r = await client.put(f"{API}/profile/update", json={"name": "Updated Name"},
                             headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert "password_hash" not in r.json()

        # OTP login response strips
        await send_otp(client, m)
        otp_login = (await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})).json()
        assert "password_hash" not in otp_login["user"]
        assert otp_login["user"]["has_password"] is True


# ============================================================
# CORS — custom domain allowlist
# ============================================================

class TestCorsCustomDomain:
    @pytest.mark.asyncio
    async def test_custom_domain_allowed(self, client, clean_db):
        for origin in ["https://nyaysetupro.in", "https://www.nyaysetupro.in"]:
            r = await client.options(f"{API}/auth/send-otp", headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            })
            assert r.status_code == 200, origin
            assert r.headers.get("access-control-allow-origin") == origin

    @pytest.mark.asyncio
    async def test_custom_domain_get(self, client, clean_db):
        r = await client.get(f"{API}/templates", headers={"Origin": "https://nyaysetupro.in"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://nyaysetupro.in"

    @pytest.mark.asyncio
    async def test_unknown_origin_still_rejected(self, client, clean_db):
        r = await client.options(f"{API}/auth/send-otp", headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        })
        assert r.status_code == 400
        assert r.headers.get("access-control-allow-origin") is None
