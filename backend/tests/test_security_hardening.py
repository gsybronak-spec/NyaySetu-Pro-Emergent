"""Master-plan hardening regression tests.

Covers:
- A4 and Legal paper sizes: generated PDF MediaBox dimensions + DOCX pgSz
- page_size validation on preview/download APIs
- OTP lifecycle: single-use, wrong-attempt limit, expiry, resend cooldown,
  no-OTP rejection, mobile-bound storage
- Rate limiting: OTP send/verify, admin login, document downloads
- CORS allowlist (never "*")
- JWT production fail-safe (no unsafe default in production)
"""

import os
import re
import sys
import uuid
import time
import base64
import zipfile
import subprocess
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_hardening")

import pytest
import pytest_asyncio

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_hardening"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token
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
                 "template_versions", "case_forms", "otps"]:
        await db[coll].drop()
    yield
    for coll in ["users", "wallets", "cases", "applications", "drafts",
                 "transactions", "referrals", "admin_users", "templates",
                 "template_versions", "case_forms", "otps"]:
        await db[coll].drop()


def mobile(prefix="9"):
    return f"{prefix}{int(time.time() * 1000) % 1000000000:09d}"


async def create_test_lawyer(m=None):
    m = m or mobile()
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id, "mobile": m, "email": None, "name": "Test Lawyer",
        "provider": "mobile", "bar_council_no": None, "state": None,
        "district": None, "court": None, "language_pref": "en",
        "theme_pref": "light", "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "referred_by": None, "favourite_courts": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id, "balance": 50, "free_credits_granted": 50,
        "total_used": 0, "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return user, make_token(user_id)


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# PAPER SIZE — A4 + Legal with REAL file-dimension verification
# ============================================================

def pdf_mediabox(pdf_bytes: bytes):
    m = re.search(rb"/MediaBox\s*\[\s*([^\]]+)\]", pdf_bytes)
    assert m, "MediaBox not found in PDF"
    parts = [float(x) for x in m.group(1).split()]
    return parts[2], parts[3]  # width, height (pt)


def docx_pgsz(docx_bytes: bytes) -> tuple:
    z = zipfile.ZipFile(BytesIO(docx_bytes))
    xml = z.read("word/document.xml").decode("utf-8", "ignore")
    m = re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"', xml)
    assert m, f"pgSz not found: {xml[:300]}"
    return int(m.group(1)), int(m.group(2))


class TestPaperSize:
    @pytest.mark.asyncio
    async def test_pdf_a4_vs_legal_dimensions(self, client, clean_db):
        _, token = await create_test_lawyer()
        vals = {"reason": "test", "next_date": "01-01-2027"}
        sizes = {}
        for page in ("A4", "Legal"):
            r = await client.post(f"{API}/applications/download", headers=H(token), json={
                "template_id": "adjournment", "language": "gu", "values": vals,
                "format": "pdf", "page_size": page, "filename": f"t_{page}.pdf",
            })
            assert r.status_code == 200, r.text
            pdf = base64.b64decode(r.json()["base64"])
            assert pdf[:4] == b"%PDF"
            sizes[page] = pdf_mediabox(pdf)
        a4_w, a4_h = sizes["A4"]
        leg_w, leg_h = sizes["Legal"]
        # A4 = 595.28 x 841.89 pt ; Legal = 612 x 1008 pt
        assert abs(a4_w - 595.28) < 2 and abs(a4_h - 841.89) < 2, f"A4 wrong: {sizes['A4']}"
        assert abs(leg_w - 612) < 2 and abs(leg_h - 1008) < 2, f"Legal wrong: {sizes['Legal']}"
        # Legal must actually be taller than A4 (real dimension change, not a label)
        assert leg_h > a4_h + 100 and leg_w > a4_w

    @pytest.mark.asyncio
    async def test_docx_a4_vs_legal_pagesize(self, client, clean_db):
        _, token = await create_test_lawyer()
        vals = {"reason": "test", "next_date": "01-01-2027"}
        sizes = {}
        for page in ("A4", "Legal"):
            r = await client.post(f"{API}/applications/download", headers=H(token), json={
                "template_id": "adjournment", "language": "gu", "values": vals,
                "format": "docx", "page_size": page, "filename": f"t_{page}.docx",
            })
            assert r.status_code == 200, r.text
            sizes[page] = docx_pgsz(base64.b64decode(r.json()["base64"]))
        # A4: 11906 x 16838 twips ; Legal: 12240 x 20160 twips
        assert sizes["A4"] == (11906, 16838), f"A4 docx wrong: {sizes['A4']}"
        assert sizes["Legal"] == (12240, 20160), f"Legal docx wrong: {sizes['Legal']}"

    @pytest.mark.asyncio
    async def test_invalid_page_size_rejected(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/preview", headers=H(token), json={
            "template_id": "adjournment", "language": "gu", "values": {"reason": "x"},
            "page_size": "Letter",
        })
        assert r.status_code == 422
        r = await client.post(f"{API}/applications/preview", headers=H(token), json={
            "template_id": "adjournment", "language": "gu", "values": {"reason": "x"},
            "page_size": "legal",  # case-insensitive OK
        })
        assert r.status_code == 200


# ============================================================
# OTP LIFECYCLE
# ============================================================

class TestOtpLifecycle:
    @pytest.mark.asyncio
    async def test_otp_single_use(self, client, clean_db):
        m = mobile("98")
        await client.post(f"{API}/auth/send-otp", json={"mobile": m})
        r1 = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r1.status_code == 200
        r2 = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r2.status_code == 400  # consumed
        assert "OTP" in r2.json()["detail"]

    @pytest.mark.asyncio
    async def test_verify_without_send_rejected(self, client, clean_db):
        m = mobile("98")
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_wrong_attempts_exhaust(self, client, clean_db):
        m = mobile("98")
        await client.post(f"{API}/auth/send-otp", json={"mobile": m})
        for i in range(5):
            r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "000000"})
            assert r.status_code == 400, f"attempt {i}: {r.text}"
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 429  # attempts exhausted, OTP invalidated

    @pytest.mark.asyncio
    async def test_expired_otp_rejected(self, client, clean_db):
        m = mobile("98")
        await db.otps.insert_one({
            "mobile": m, "otp": "123456",
            "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
            "attempts": 0, "last_sent_at": datetime.now(timezone.utc).isoformat(),
        })
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": m, "otp": "123456"})
        assert r.status_code == 400
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resend_cooldown(self, client, clean_db):
        m = mobile("98")
        await client.post(f"{API}/auth/send-otp", json={"mobile": m})
        r = await client.post(f"{API}/auth/send-otp", json={"mobile": m})
        assert r.status_code == 429
        assert "wait" in r.json()["detail"].lower()


# ============================================================
# RATE LIMITING
# ============================================================

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_send_otp_rate_limit(self, client, clean_db):
        # 5 requests per 60s per key (mobile). Verify the shared limiter on one key.
        key = f"test:{mobile()}"
        allowed = sum(1 for _ in range(6) if server.rate_limit(key, 5, 60))
        assert allowed == 5
        assert server.rate_limit(key, 5, 60) is False

    @pytest.mark.asyncio
    async def test_download_rate_limit(self, client, clean_db):
        _, token = await create_test_lawyer()
        payload = {
            "template_id": "adjournment", "language": "en",
            "values": {"reason": "x", "next_date": "01-01-2027"},
            "format": "pdf", "filename": "t.pdf",
        }
        statuses = []
        for _ in range(31):
            r = await client.post(f"{API}/applications/download", headers=H(token), json=payload)
            statuses.append(r.status_code)
        # 30 allowed (some 402 once credits run out), 31st rate-limited
        assert statuses[30] == 429, statuses
        assert statuses.count(429) == 1
        assert statuses[:30].count(200) >= 5  # at least the funded downloads succeeded

    @pytest.mark.asyncio
    async def test_admin_login_rate_limit(self, client, clean_db):
        for i in range(6):
            r = await client.post(f"{API}/admin/auth/login", json={
                "email": "nobody@test.in", "password": "WrongPass123!",
            })
        assert r.status_code == 429


# ============================================================
# CORS + JWT FAIL-SAFE
# ============================================================

class TestCorsAndJwt:
    def test_cors_never_wildcard(self):
        from server import _CORS_ORIGINS
        assert "*" not in _CORS_ORIGINS
        assert "https://nyaysetu-frontend.vercel.app" in _CORS_ORIGINS
        found = False
        for mw in app.user_middleware:
            if mw.cls.__name__ == "CORSMiddleware":
                assert mw.kwargs.get("allow_origins") != ["*"]
                assert mw.kwargs.get("allow_origins") == _CORS_ORIGINS
                assert mw.kwargs.get("allow_origin_regex") is not None
                found = True
        assert found, "CORSMiddleware not found"

    def test_jwt_failsafe_production_missing_secret(self):
        code = (
            "import os\n"
            "os.environ['ENVIRONMENT']='production'\n"
            "os.environ['MONGO_URL']='mongodb://localhost:27017'\n"
            "os.environ['DB_NAME']='nyaysetu_jwt_fail'\n"
            "import server\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode != 0, "expected import failure without JWT_SECRET in declared production"
        assert "JWT_SECRET" in r.stderr

    def test_jwt_failsafe_production_dev_default_rejected(self):
        code = (
            "import os\n"
            "os.environ['ENVIRONMENT']='production'\n"
            "os.environ['JWT_SECRET']='nyaysetu-dev-secret-please-change'\n"
            "os.environ['MONGO_URL']='mongodb://localhost:27017'\n"
            "os.environ['DB_NAME']='nyaysetu_jwt_fail'\n"
            "import server\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode != 0

    def test_jwt_strong_secret_starts_in_production(self):
        code = (
            "import os\n"
            "os.environ['ENVIRONMENT']='production'\n"
            "os.environ['JWT_SECRET']='" + "x" * 64 + "'\n"
            "os.environ['MONGO_URL']='mongodb://localhost:27017'\n"
            "os.environ['DB_NAME']='nyaysetu_jwt_ok'\n"
            "import server\n"
            "print('OK')\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_jwt_render_without_declaration_starts_with_warning(self):
        # Render without ENVIRONMENT=production must NOT crash (operator hasn't
        # opted in / configured the secret yet) — it warns instead, preserving the
        # legacy deployment while the fail-safe awaits the explicit declaration.
        code = (
            "import os\n"
            "os.environ['RENDER']='true'\n"
            "os.environ['JWT_SECRET']='some-secret'\n"
            "os.environ['MONGO_URL']='mongodb://localhost:27017'\n"
            "os.environ['DB_NAME']='nyaysetu_jwt_warn'\n"
            "import logging\n"
            "logging.disable(logging.CRITICAL)\n"
            "import server\n"
            "print('OK')\n"
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout
