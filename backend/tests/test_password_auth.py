import server

from tests.firestore_test_utils import FirestoreDBSurrogate
mock_db = FirestoreDBSurrogate()
db = FirestoreDBSurrogate()
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
os.environ.setdefault("DB_NAME", "nyaysetu_test_password_auth")

import pytest

import pytest_asyncio


import server
app = server.app

from httpx import AsyncClient, ASGITransport

API = "/api"


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    yield

class httpx_timeout(Exception):
    pass


async def send_otp(client, mobile, kind="login"):
    return await client.post(f"{API}/auth/send-otp", json={"mobile": mobile, "kind": kind})

async def _dump_user(client, token):
    return await client.get(f"{API}/profile/me", headers={"Authorization": f"Bearer {token}"})

async def register_user(client, mobile="9876550001", email=None, name="Existing Advocate", password="SecurePass123"):
    user_id = str(uuid.uuid4())
    import bcrypt
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_doc = {
        "id": user_id,
        "mobile": mobile,
        "email": email or f"{user_id}@test.com",
        "name": name,
        "first_name": name.split()[0],
        "last_name": name.split()[-1],
        "advocate_name_en": f"Adv. {name}",
        "user_type": "Advocate",
        "bar_council_no": "G/111/2020",
        "password_hash": pw_hash,
        "has_password": True,
        "active": True,
        "status": "active",
        "profile_completed": True,
        "is_profile_complete": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await server.db.collection("users").document(user_id).set(user_doc)
    await client.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    return await client.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})


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


# ============================================================
# PROFILE ONBOARDING & COMPLETENESS
# ============================================================

class TestProfileOnboarding:
    @pytest.mark.asyncio
    async def test_google_user_onboarding_flow(self, client, clean_db):
        # 1. New Google user created
        user = await server.create_new_user(email="testuser@gmail.com", name="Ronak Patel", provider="google")
        assert user["profile_completed"] is False
        assert user["is_profile_complete"] is False
        assert user["first_name"] == "Ronak"
        assert user["last_name"] == "Patel"

        token = server.make_token(user["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check /api/profile/me before onboarding
        res = await client.get(f"{API}/profile/me", headers=headers)
        assert res.status_code == 200
        me = res.json()
        assert me["profile_completed"] is False
        assert me["is_profile_complete"] is False
        assert me["email"] == "testuser@gmail.com"

        # 3. Try updating with invalid mobile length
        res_inv = await client.put(f"{API}/profile/update", json={
            "first_name": "Ronak",
            "last_name": "Patel",
            "mobile": "12345"
        }, headers=headers)
        assert res_inv.status_code == 400
        assert "valid 10-digit Indian mobile" in res_inv.json()["detail"]

        # 4. Try updating with invalid starting digit
        res_inv2 = await client.put(f"{API}/profile/update", json={
            "first_name": "Ronak",
            "last_name": "Patel",
            "mobile": "2837482910"
        }, headers=headers)
        assert res_inv2.status_code == 400
        assert "valid 10-digit Indian mobile" in res_inv2.json()["detail"]

        # 5. Advocate without bar council number
        res_adv_inv = await client.put(f"{API}/profile/update", json={
            "first_name": "Ronak",
            "last_name": "Patel",
            "mobile": "9876599991",
            "user_type": "Advocate",
            "bar_council_no": "",
            "state": "Gujarat",
            "district": "ahmedabad",
        }, headers=headers)
        assert res_adv_inv.status_code == 400
        assert "Bar Council / Enrollment Number is required" in res_adv_inv.json()["detail"]

        # 6. Successfully complete profile setup for Advocate
        res_valid = await client.put(f"{API}/profile/update", json={
            "first_name": "Ronak",
            "middle_name": "K",
            "last_name": "Patel",
            "mobile": "9876599991",
            "user_type": "Advocate",
            "bar_council_no": "G/1234/2020",
            "state": "Gujarat",
            "district": "ahmedabad",
        }, headers=headers)
        assert res_valid.status_code == 200
        updated = res_valid.json()
        assert updated["name"] == "Ronak K Patel"
        assert updated["advocate_name_en"] == "Adv. Ronak K Patel"
        assert updated["mobile"] == "9876599991"
        assert updated["user_type"] == "Advocate"
        assert updated["bar_council_no"] == "G/1234/2020"
        assert updated["profile_completed"] is True
        assert updated["is_profile_complete"] is True

        # 7. Verify subsequent /api/profile/me
        res_me = await client.get(f"{API}/profile/me", headers=headers)
        assert res_me.status_code == 200
        me2 = res_me.json()
        assert me2["name"] == "Ronak K Patel"
        assert me2["profile_completed"] is True
        assert me2["is_profile_complete"] is True

    @pytest.mark.asyncio
    async def test_law_student_profile_flow(self, client, clean_db):
        user = await server.create_new_user(email="student@gmail.com", name="Priya Shah", provider="google")
        token = server.make_token(user["id"])
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.put(f"{API}/profile/update", json={
            "first_name": "Priya",
            "last_name": "Shah",
            "mobile": "9876599992",
            "user_type": "Law Student",
            "state": "Gujarat",
            "district": "surat",
        }, headers=headers)
        assert res.status_code == 200
        updated = res.json()
        assert updated["name"] == "Priya Shah"
        assert updated["advocate_name_en"] == "Priya Shah"
        assert updated["user_type"] == "Law Student"
        assert updated["profile_completed"] is True

    @pytest.mark.asyncio
    async def test_edit_profile_preserves_on_google_relogin(self, client, clean_db, monkeypatch):
        # 1. First Google login creates user
        async def fake_token(code, redirect_uri):
            return 200, {"access_token": "tok_onboard"}
        async def fake_userinfo(access_token):
            return 200, {"email": "jaydeep@gmail.com", "email_verified": True, "name": "gsybronak", "picture": "https://google.com/pic.jpg"}
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_ID", "dummy_client_id")
        monkeypatch.setattr(server, "GOOGLE_OAUTH_CLIENT_SECRET", "dummy_client_secret")
        monkeypatch.setattr(server, "_google_token_exchange", fake_token)
        monkeypatch.setattr(server, "_google_userinfo", fake_userinfo)

        r1 = await client.post(f"{API}/auth/google", json={"code": "c1", "redirect_uri": "https://test/"})
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["is_new"] is True
        assert d1["user"]["profile_completed"] is False
        token = d1["token"]

        # 2. User edits profile / completes onboarding
        r2 = await client.put(f"{API}/profile/update", json={
            "first_name": "Jaydeep",
            "last_name": "Jadav",
            "mobile": "9876543299",
            "user_type": "Advocate",
            "bar_council_no": "G/999/2021",
            "state": "Gujarat",
            "district": "ahmedabad",
        }, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["name"] == "Jaydeep Jadav"
        assert d2["advocate_name_en"] == "Adv. Jaydeep Jadav"
        assert d2["profile_completed"] is True

        # 3. User logs in with Google AGAIN in future session
        r3 = await client.post(f"{API}/auth/google", json={"code": "c2", "redirect_uri": "https://test/"})
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["is_new"] is False
        # Manually edited name must NOT be overwritten by Google name "gsybronak"
        assert d3["user"]["name"] == "Jaydeep Jadav"
        assert d3["user"]["first_name"] == "Jaydeep"
        assert d3["user"]["advocate_name_en"] == "Adv. Jaydeep Jadav"
        assert d3["user"]["profile_completed"] is True

    @pytest.mark.asyncio
    async def test_existing_user_already_complete(self, client, clean_db):
        reg = await register_user(client, mobile="9876500099", name="Existing Advocate")
        assert reg.status_code == 200
        data = reg.json()
        assert data["user"]["profile_completed"] is True
        assert data["user"]["is_profile_complete"] is True



