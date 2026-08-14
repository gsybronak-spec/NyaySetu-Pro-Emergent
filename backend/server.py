"""NyaySetu Pro - FastAPI backend."""

import os
import re
import uuid
import time
import json
import hmac
import hashlib
import logging
import secrets
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Union

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import jwt
import bcrypt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.x509 import load_pem_x509_certificate

from seed_data import CASE_TYPES, LAWS, DISTRICTS, TALUKAS, COURTS, POLICE_STATIONS, TEMPLATES, PLANS, QUOTES
from doc_generator import generate_pdf, generate_docx, generate_odt, render_template, build_blocks
from docx_import import analyze_docx, decode_upload, DocxImportError
from odt_import import analyze_odt, OdtImportError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# Production detection — set ENVIRONMENT=production explicitly when the deployment
# is declared production. RENDER=true alone does NOT trigger strict mode: the
# operator must opt in (and configure JWT_SECRET / SMS) in the same dashboard
# session, so pushing code can never silently crash a working deployment.
_PRODUCTION = os.environ.get("ENVIRONMENT", "").strip().lower() == "production"

# JWT secret — NO unsafe fallback in declared production. The dev default exists
# only for local development; ENVIRONMENT=production refuses to start without a
# strong JWT_SECRET. On Render without the declaration we warn loudly instead of
# crashing, so the current (legacy) deployment keeps working until the operator
# sets JWT_SECRET + ENVIRONMENT=production.
_DEV_JWT_FALLBACK = "nyaysetu-dev-secret-please-change"
JWT_SECRET = os.environ.get("JWT_SECRET", "")
if _PRODUCTION:
    if not JWT_SECRET or JWT_SECRET == _DEV_JWT_FALLBACK or len(JWT_SECRET) < 32:
        raise RuntimeError(
            "JWT_SECRET is not set to a strong random value. Refusing to start in "
            "production with an unsafe default. Set JWT_SECRET (>=32 chars) and "
            "ENVIRONMENT=production in the environment."
        )
if not JWT_SECRET:
    JWT_SECRET = _DEV_JWT_FALLBACK  # local development only
elif os.environ.get("RENDER", "").strip().lower() == "true" and not _PRODUCTION:
    logging.warning(
        "[SECURITY] Running on Render without ENVIRONMENT=production. If this is "
        "production, set ENVIRONMENT=production and a strong JWT_SECRET in the "
        "Render dashboard; until then the development JWT fallback is in use."
    )

# Admin seed — loaded from env, NEVER hard-coded
ADMIN_SEED_EMAIL = os.environ.get("ADMIN_SEED_EMAIL")
ADMIN_SEED_PASSWORD = os.environ.get("ADMIN_SEED_PASSWORD")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="NyaySetu Pro API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyaysetu")


# ============================================================
# RATE LIMITING — in-memory sliding window (per instance)
# ============================================================
_rate_buckets: dict = {}
_rate_lock = threading.Lock()


def rate_limit(key: str, limit: int, window_sec: int = 60) -> bool:
    """Return True when the request is allowed, False when rate-limited."""
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets.setdefault(key, [])
        bucket[:] = [t for t in bucket if t > now - window_sec]
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        if len(_rate_buckets) > 10000:
            _rate_buckets.clear()
        return True


# ============================================================
# OTP CONFIGURATION
# ============================================================
OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", "300"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", "60"))
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "console").strip().lower()
# The fixed 123456 OTP is a development-only convenience. It is never allowed in
# declared production AND never on Render (RENDER=true is set by every Render
# deployment, preview or production) — a belt-and-braces guard so a deployment
# that forgets ENVIRONMENT=production cannot run the dev-OTP auth bypass.
_DEV_OTP_ALLOWED = (not _PRODUCTION) and os.environ.get("RENDER", "").strip().lower() != "true"

# Razorpay — production payment. When keys are absent the payment API fails safely
# (503 with an exact message); no default/invented credentials are ever used.
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
RAZORPAY_API_BASE = os.environ.get("RAZORPAY_API_BASE", "https://api.razorpay.com").strip()

# Google OAuth — native Authorization Code flow (replaces the legacy Emergent
# session exchange). The frontend opens Google's consent URL directly and sends
# the returned `code` to POST /api/auth/google, which exchanges it server-side.
# Without client credentials the endpoint fails safely (503); no default or
# invented credentials are ever used.
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
GOOGLE_OAUTH_TOKEN_URL = os.environ.get(
    "GOOGLE_OAUTH_TOKEN_URL", "https://oauth2.googleapis.com/token"
).strip()
GOOGLE_OAUTH_USERINFO_URL = os.environ.get(
    "GOOGLE_OAUTH_USERINFO_URL", "https://www.googleapis.com/oauth2/v3/userinfo"
).strip()

# Legacy Emergent session exchange — kept only for backward compatibility with
# older clients. Production fails safe: it must be explicitly enabled via
# GOOGLE_SESSION_URL and is never silently pointed at a third-party demo endpoint.
_GOOGLE_SESSION_URL_ENV = os.environ.get("GOOGLE_SESSION_URL", "").strip()
GOOGLE_SESSION_URL = _GOOGLE_SESSION_URL_ENV or (
    "" if _PRODUCTION else "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
)

# Firebase Authentication — server-side verification of Firebase ID tokens.
# Verification uses Firebase's public signing keys (the documented verification
# path for servers without a service account); the public project id is the only
# configuration needed. Fails safe (503) when FIREBASE_PROJECT_ID is unset — no
# default or invented value is ever used. Real SMS from Firebase Phone Auth also
# requires the Firebase project (and Blaze billing for production SMS volumes).
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
FIREBASE_CERT_URL = os.environ.get(
    "FIREBASE_CERT_URL",
    "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com",
).strip()
_firebase_certs: Optional[dict] = None
_firebase_certs_fetched_at: Optional[float] = None


# ============================================================
# ADMIN-CONFIGURABLE OPERATIONAL SETTINGS (Phase 40)
# DB values override these defaults (which honor env vars where applicable).
# ============================================================
_SETTING_DEFAULTS = {
    "signup_credits": 5,
    "default_page_size": "A4",
    "otp_ttl_seconds": OTP_TTL_SECONDS,
    "otp_resend_cooldown_seconds": OTP_RESEND_COOLDOWN_SECONDS,
    "otp_max_attempts": OTP_MAX_ATTEMPTS,
}
_SETTING_DESCRIPTIONS = {
    "signup_credits": "Free credits granted to each new account",
    "default_page_size": "Default paper size for generated documents (A4 or Legal)",
    "otp_ttl_seconds": "OTP validity in seconds",
    "otp_resend_cooldown_seconds": "Minimum seconds between OTP resends",
    "otp_max_attempts": "Max incorrect OTP attempts before a new OTP is required",
}


def _setting_type(key: str):
    return int if isinstance(_SETTING_DEFAULTS[key], int) else str


async def _get_setting(key: str):
    """Resolve an operational setting: DB value if present, else the default."""
    doc = await db.settings.find_one({"key": key}, {"_id": 0, "value": 1})
    if doc is not None and "value" in doc:
        return doc["value"]
    return _SETTING_DEFAULTS[key]


# ============================================================
# MODELS
# ============================================================

class FirebaseAuthReq(BaseModel):
    id_token: str = Field(..., max_length=8192)
    referral_code: Optional[str] = Field(None, max_length=20)

class SendOtpReq(BaseModel):
    mobile: str = Field(..., max_length=15)

class VerifyOtpReq(BaseModel):
    mobile: str = Field(..., max_length=15)
    otp: str = Field(..., max_length=10)
    referral_code: Optional[str] = Field(None, max_length=20)

class GoogleSessionReq(BaseModel):
    session_id: str = Field(..., max_length=500)
    referral_code: Optional[str] = Field(None, max_length=20)

class GoogleCodeReq(BaseModel):
    code: str = Field(..., max_length=4000)
    redirect_uri: str = Field(..., max_length=2000)
    referral_code: Optional[str] = Field(None, max_length=20)

class RegisterReq(BaseModel):
    mobile: str = Field(..., max_length=15)
    otp: str = Field(..., max_length=10)
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    referral_code: Optional[str] = Field(None, max_length=20)

class LoginReq(BaseModel):
    identifier: str = Field(..., max_length=200)
    password: str = Field(..., max_length=128)
    referral_code: Optional[str] = Field(None, max_length=20)

class ForgotPasswordReq(BaseModel):
    mobile: str = Field(..., max_length=15)

class ResetPasswordReq(BaseModel):
    mobile: str = Field(..., max_length=15)
    otp: str = Field(..., max_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)

class SetPasswordReq(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)

class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    bar_council_no: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    court: Optional[str] = Field(None, max_length=200)

class CaseCreate(BaseModel):
    language: str = "en"
    nickname: Optional[str] = Field(None, max_length=200)
    case_number: Optional[str] = Field(None, max_length=100)
    case_type_id: Optional[str] = Field(None, max_length=50)
    case_type_custom: Optional[str] = Field(None, max_length=200)
    complaint_type: Optional[str] = Field(None, max_length=20)  # private/police/other
    law_id: Optional[str] = Field(None, max_length=50)
    law_custom: Optional[str] = Field(None, max_length=200)
    section_id: Optional[str] = Field(None, max_length=50)
    party_name: Optional[str] = Field(None, max_length=500)
    opposite_party: Optional[str] = Field(None, max_length=500)
    court: Optional[str] = Field(None, max_length=200)
    court_id: Optional[str] = Field(None, max_length=50)
    court_custom: Optional[str] = Field(None, max_length=200)
    district_id: Optional[str] = Field(None, max_length=50)
    police_station: Optional[str] = Field(None, max_length=200)
    police_station_id: Optional[str] = Field(None, max_length=50)
    police_station_custom: Optional[str] = Field(None, max_length=200)
    complaint_custom: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)
    # Admin-configured case form values (dynamic fields) — persisted on the case.
    custom_fields: Optional[dict] = None
    # Flat client details (from Client Lookup autofill). D3: stored flat on the case.
    client_name: Optional[str] = Field(None, max_length=500)
    client_mobile: Optional[str] = Field(None, max_length=20)
    client_email: Optional[str] = Field(None, max_length=200)
    client_address: Optional[str] = Field(None, max_length=1000)
    client_district: Optional[str] = Field(None, max_length=200)

class CaseUpdate(CaseCreate):
    pass

class GenerateReq(BaseModel):
    template_id: str = Field(..., max_length=50)
    case_id: Optional[str] = Field(None, max_length=50)
    language: str = "en"
    values: dict = {}
    filename: Optional[str] = Field(None, max_length=200)
    page_size: Optional[str] = Field(None, max_length=10)  # A4 | Legal

class DownloadReq(BaseModel):
    template_id: str = Field(..., max_length=50)
    case_id: Optional[str] = Field(None, max_length=50)
    language: str = "en"
    values: dict = {}
    format: str = "pdf"  # pdf | docx | odt
    filename: Optional[str] = Field(None, max_length=200)
    page_size: Optional[str] = Field(None, max_length=10)  # A4 | Legal
    consume_credit: bool = True  # DEPRECATED: ignored server-side — always consumes 1 credit

class PurchaseReq(BaseModel):
    plan_id: str = Field(..., max_length=50)

class RazorpayCreateOrderReq(BaseModel):
    plan_id: str = Field(..., max_length=50)

class RazorpayVerifyReq(BaseModel):
    plan_id: str = Field(..., max_length=50)
    order_id: str = Field(..., max_length=100)
    payment_id: str = Field(..., max_length=100)
    signature: str = Field(..., max_length=256)

class DraftSave(BaseModel):
    template_id: str = Field(..., max_length=50)
    case_id: Optional[str] = Field(None, max_length=50)
    language: str = "en"
    values: dict = {}

class CaseFormFieldSchema(BaseModel):
    key: str = Field(..., max_length=50)
    label_en: str = Field(..., max_length=150)
    label_gu: str = Field(..., max_length=150)
    type: str = Field("text", max_length=30)
    required: bool = True
    order: int = 0
    placeholder: Optional[str] = Field(None, max_length=150)
    default_value: Optional[str] = Field(None, max_length=200)
    options: Optional[List[dict]] = None
    autofill_map: Optional[str] = Field(None, max_length=50)

class CaseFormConfigReq(BaseModel):
    name_en: str = Field(..., max_length=150)
    name_gu: str = Field(..., max_length=150)
    category: str = Field("General", max_length=50)
    fields: List[CaseFormFieldSchema] = []


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc)

def make_token(user_id: str, token_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "ver": token_version,
        "iat": int(now().timestamp()),
        "exp": int((now() + timedelta(days=90)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def get_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing auth token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    if user.get("active") is False:
        raise HTTPException(401, "Account disabled. Contact support.")
    # Password reset bumps token_version, revoking previously issued JWTs.
    # Tokens issued before this feature (no `ver` claim) remain valid unless the
    # user has since bumped their version.
    if user.get("token_version") and payload.get("ver") != user["token_version"]:
        raise HTTPException(401, "Session expired. Please login again.")
    return user


def hash_password(password: str) -> str:
    """bcrypt-hash a plaintext password. Never stored or logged in plaintext."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _public_user(user: dict) -> dict:
    """User object safe for clients: strips the password hash and flags whether a
    password is set (so the UI can offer Set Password for legacy OTP-only users)."""
    u = {k: v for k, v in user.items() if k not in ("_id", "password_hash")}
    u["has_password"] = bool(user.get("password_hash"))
    return u


async def gen_referral_code() -> str:
    """Generate a unique short referral code."""
    for _ in range(10):
        code = "NS" + secrets.token_hex(3).upper()
        exists = await db.users.find_one({"referral_code": code}, {"_id": 1})
        if not exists:
            return code
    return "NS" + secrets.token_hex(4).upper()


async def create_new_user(*, mobile: Optional[str] = None, email: Optional[str] = None,
                          name: Optional[str] = None, picture: Optional[str] = None,
                          provider: str = "mobile") -> dict:
    """Create a user + wallet with 5 free credits and a referral code.

    IMPORTANT: absent optional identity fields (mobile/email/picture) are OMITTED
    from the document rather than stored as null. The unique sparse indexes on
    users.mobile / users.email index null values, so storing null for a field the
    other provider doesn't set would make the SECOND user collide and 500.
    """
    user_id = str(uuid.uuid4())
    code = await gen_referral_code()
    user = {
        "id": user_id,
        "name": name,
        "provider": provider,
        "bar_council_no": None,
        "state": None,
        "district": None,
        "court": None,
        "language_pref": "en",
        "theme_pref": "light",
        "token_version": 0,
        "referral_code": code,
        "referred_by": None,
        "favourite_courts": [],
        "created_at": now().isoformat(),
    }
    if mobile is not None:
        user["mobile"] = mobile
    if email is not None:
        user["email"] = email
    if picture is not None:
        user["picture"] = picture
    await db.users.insert_one(user.copy())
    signup_credits = await _get_setting("signup_credits")
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": signup_credits,
        "free_credits_granted": signup_credits,
        "total_used": 0,
        "updated_at": now().isoformat(),
    })
    return user


REFERRAL_REWARD = 10


async def apply_referral(referral_code: Optional[str], new_user: dict):
    """Reward the referrer with free templates. Anti-abuse: no self-referral,
    one reward per referred user."""
    if not referral_code:
        return
    code = referral_code.strip().upper()
    referrer = await db.users.find_one({"referral_code": code}, {"_id": 0})
    if not referrer:
        return
    # Prevent self-referral
    if referrer["id"] == new_user["id"]:
        return
    # Prevent duplicate reward for the same referred user
    existing = await db.referrals.find_one({"referred_user_id": new_user["id"]}, {"_id": 1})
    if existing:
        return
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()),
        "referrer_id": referrer["id"],
        "referrer_code": code,
        "referred_user_id": new_user["id"],
        "reward": REFERRAL_REWARD,
        "status": "rewarded",
        "created_at": now().isoformat(),
    })
    await db.wallets.update_one(
        {"user_id": referrer["id"]},
        {"$inc": {"balance": REFERRAL_REWARD}, "$set": {"updated_at": now().isoformat()}},
        upsert=True,
    )
    await db.users.update_one({"id": new_user["id"]}, {"$set": {"referred_by": referrer["id"]}})


# ============================================================
# AUTH (MOCK OTP + GOOGLE)
# ============================================================

SMS_REQUEST_TIMEOUT_SECONDS = 5  # explicit cap — production must never hang

async def send_sms(mobile: str, otp: str) -> None:
    """SMS provider abstraction. Real providers plug in here; when a provider is
    selected but not implemented, the exact required env vars are reported instead
    of inventing credentials. Every provider request uses an explicit timeout so
    an unreachable provider can never hang the HTTP request."""
    provider = SMS_PROVIDER
    if provider in ("", "console"):
        logger.info(f"[SMS-CONSOLE] {mobile}: your NyaySetu Pro OTP is {otp}")
        return
    if provider == "twilio":
        # Example contract — activate only with real credentials from the operator.
        account_sid = os.environ.get("SMS_ACCOUNT_SID", "").strip()
        auth_token = os.environ.get("SMS_AUTH_TOKEN", "").strip()
        if not account_sid or not auth_token:
            raise NotImplementedError(
                "Twilio is selected but SMS_ACCOUNT_SID / SMS_AUTH_TOKEN are not set."
            )
        async with httpx.AsyncClient(timeout=SMS_REQUEST_TIMEOUT_SECONDS) as http:
            await http.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                data={"To": f"+91{mobile}", "From": os.environ.get("SMS_FROM", "").strip(), "Body": f"Your NyaySetu Pro OTP is {otp}"},
                auth=(account_sid, auth_token),
            )
        return
    raise NotImplementedError(
        f"SMS provider '{provider}' is not implemented. Configure SMS_PROVIDER and its "
        "credentials (e.g. SMS_ACCOUNT_SID, SMS_AUTH_TOKEN) in the environment."
    )


async def _issue_otp(mobile: str, kind: str) -> dict:
    """Shared OTP issuance (login, signup, password reset). Rate-limited, with an
    explicit resend cooldown. Returns the stored OTP doc keys for callers."""
    if len(mobile) < 10:
        raise HTTPException(400, "Invalid mobile number")
    if not rate_limit(f"otp_send:{mobile}", 5, 60):
        raise HTTPException(429, "Too many OTP requests. Please try again later.")

    existing = await db.otps.find_one({"mobile": mobile}, {"_id": 0})
    if existing and existing.get("last_sent_at"):
        cooldown = await _get_setting("otp_resend_cooldown_seconds")
        elapsed = (now() - datetime.fromisoformat(existing["last_sent_at"])).total_seconds()
        if elapsed < cooldown:
            raise HTTPException(
                429,
                f"Please wait {int(cooldown - elapsed)}s before requesting another OTP.",
            )

    # Real random OTP in production via the configured SMS provider.
    # Fixed 123456 is development-only: never in declared production and never
    # on any Render deployment (even one missing ENVIRONMENT=production).
    if SMS_PROVIDER in ("", "console"):
        if not _DEV_OTP_ALLOWED:
            raise HTTPException(
                503,
                "OTP service is not configured. Please contact support.",
            )
        otp = "123456"
    else:
        otp = str(secrets.randbelow(1_000_000)).zfill(6)
        try:
            await send_sms(mobile, otp)
        except NotImplementedError as e:
            raise HTTPException(501, str(e))
        except (httpx.TimeoutException, TimeoutError) as e:
            logger.error(f"[OTP] SMS provider timeout for {mobile}: {type(e).__name__}")
            raise HTTPException(503, "OTP service is temporarily unavailable. Please try again shortly.")
        except Exception as e:
            logger.error(f"[OTP] SMS provider failure for {mobile}: {type(e).__name__}")
            raise HTTPException(503, "OTP service is temporarily unavailable. Please try again shortly.")

    ttl_seconds = await _get_setting("otp_ttl_seconds")
    await db.otps.update_one(
        {"mobile": mobile},
        {"$set": {
            "mobile": mobile,
            "otp": otp,
            "kind": kind,
            "expires_at": (now() + timedelta(seconds=ttl_seconds)).isoformat(),
            # BSON date for the Mongo TTL index (TTL indexes ignore ISO strings)
            "ttl_at": now() + timedelta(seconds=ttl_seconds + 60),
            "attempts": 0,
            "last_sent_at": now().isoformat(),
        }},
        upsert=True,
    )
    logger.info(f"[OTP] {kind} OTP issued to {mobile} via provider '{SMS_PROVIDER}'")
    return {"ttl_seconds": ttl_seconds}


@api.post("/auth/send-otp")
async def send_otp(req: SendOtpReq):
    mobile = req.mobile.strip()
    await _issue_otp(mobile, "login")
    return {
        "success": True,
        "message": "OTP sent successfully",
        "hint": "Use 123456 for testing" if _DEV_OTP_ALLOWED else None,
    }


@api.post("/auth/verify-otp")
async def verify_otp(req: VerifyOtpReq):
    mobile = req.mobile.strip()
    otp = req.otp.strip()
    if not rate_limit(f"otp_verify:{mobile}", 10, 60):
        raise HTTPException(429, "Too many OTP attempts. Please try again later.")

    doc = await db.otps.find_one({"mobile": mobile}, {"_id": 0})
    if not doc or doc.get("kind", "login") != "login":
        raise HTTPException(400, "No OTP requested for this number or OTP expired. Please request a new OTP.")
    if datetime.fromisoformat(doc["expires_at"]) < now():
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(400, "OTP expired. Please request a new OTP.")
    max_attempts = await _get_setting("otp_max_attempts")
    if doc.get("attempts", 0) >= max_attempts:
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(429, "Too many incorrect attempts. Please request a new OTP.")
    if doc.get("otp") != otp:
        await db.otps.update_one({"mobile": mobile}, {"$inc": {"attempts": 1}})
        raise HTTPException(400, "Invalid OTP")

    await db.otps.delete_one({"mobile": mobile})

    user = await db.users.find_one({"mobile": mobile}, {"_id": 0})
    is_new = False
    if not user:
        is_new = True
        user = await create_new_user(mobile=mobile, provider="mobile")
        await apply_referral(req.referral_code, user)
    elif user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")

    token = make_token(user["id"], user.get("token_version", 0))
    return {"token": token, "user": _public_user(user), "is_new": is_new}


# ============================================================
# PASSWORD AUTH — register / login / forgot / reset / set
# ============================================================

@api.post("/auth/register")
async def register(req: RegisterReq):
    """Create an account with a password. OTP-verified (single-use) so the mobile
    number is confirmed before the account exists; no duplicate users are created.
    Returns the same JWT/session contract as OTP/Google auth (auto-login)."""
    mobile = req.mobile.strip()
    if len(mobile) < 10 or not mobile.isdigit():
        raise HTTPException(400, "Invalid mobile number")
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    if not rate_limit(f"otp_verify:{mobile}", 10, 60):
        raise HTTPException(429, "Too many attempts. Please try again later.")

    doc = await db.otps.find_one({"mobile": mobile}, {"_id": 0})
    if not doc or doc.get("kind", "login") != "login":
        raise HTTPException(400, "No OTP requested for this number or OTP expired. Please request a new OTP.")
    if datetime.fromisoformat(doc["expires_at"]) < now():
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(400, "OTP expired. Please request a new OTP.")
    max_attempts = await _get_setting("otp_max_attempts")
    if doc.get("attempts", 0) >= max_attempts:
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(429, "Too many incorrect attempts. Please request a new OTP.")
    if doc.get("otp") != req.otp.strip():
        await db.otps.update_one({"mobile": mobile}, {"$inc": {"attempts": 1}})
        raise HTTPException(400, "Invalid OTP")
    await db.otps.delete_one({"mobile": mobile})

    if await db.users.find_one({"mobile": mobile}, {"_id": 1}):
        raise HTTPException(409, "An account with this mobile number already exists. Please login.")
    email = (req.email or "").strip().lower() or None
    if email and await db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(409, "An account with this email already exists. Please login.")

    user = await create_new_user(
        mobile=mobile,
        email=email,
        name=(req.name or "").strip() or None,
        provider="mobile",
    )
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(req.password)}},
    )
    await apply_referral(req.referral_code, user)
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    token = make_token(user["id"], fresh.get("token_version", 0))
    return {"token": token, "user": _public_user(fresh), "is_new": True}


@api.post("/auth/login")
async def login(req: LoginReq):
    """Password login by mobile or email. Generic error on any mismatch so the
    response never reveals whether a user or which field was wrong. Rate-limited."""
    identifier = req.identifier.strip()
    if not identifier or not req.password:
        raise HTTPException(401, "Invalid mobile/email or password.")
    if not rate_limit(f"login:{identifier.lower()}", 5, 60):
        raise HTTPException(429, "Too many login attempts. Please wait before trying again.")

    user = None
    digits = re.sub(r"\D", "", identifier)
    if 10 <= len(digits) <= 12:
        m = digits[2:] if len(digits) == 12 and digits.startswith("91") else digits
        if len(m) == 10:
            user = await db.users.find_one({"mobile": m}, {"_id": 0})
    if not user and "@" in identifier:
        user = await db.users.find_one({"email": identifier.strip().lower()}, {"_id": 0})

    if not user or not user.get("password_hash") or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid mobile/email or password.")
    if user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")
    token = make_token(user["id"], user.get("token_version", 0))
    return {"token": token, "user": _public_user(user), "is_new": False}


@api.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordReq):
    """Send a password-reset OTP to the registered mobile. Returns the same message
    whether or not the account exists (no user enumeration); no OTP is sent for
    unknown numbers and nothing else happens."""
    mobile = req.mobile.strip()
    existing = await db.users.find_one({"mobile": mobile}, {"_id": 1})
    if not existing:
        logger.info(f"[forgot-password] no account for {mobile} — no OTP sent")
        return {"success": True, "message": "If a matching account exists, an OTP has been sent."}
    await _issue_otp(mobile, "reset")
    return {"success": True, "message": "If a matching account exists, an OTP has been sent."}


@api.post("/auth/reset-password")
async def reset_password(req: ResetPasswordReq):
    """Verify a password-reset OTP and set a new password. Bumps token_version so
    previously issued JWTs are revoked. The OTP is single-use."""
    mobile = req.mobile.strip()
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    if not rate_limit(f"otp_verify:{mobile}", 10, 60):
        raise HTTPException(429, "Too many attempts. Please try again later.")

    doc = await db.otps.find_one({"mobile": mobile}, {"_id": 0})
    if not doc or doc.get("kind", "login") != "reset":
        raise HTTPException(400, "No password reset OTP requested or OTP expired. Please request a new OTP.")
    if datetime.fromisoformat(doc["expires_at"]) < now():
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(400, "OTP expired. Please request a new OTP.")
    max_attempts = await _get_setting("otp_max_attempts")
    if doc.get("attempts", 0) >= max_attempts:
        await db.otps.delete_one({"mobile": mobile})
        raise HTTPException(429, "Too many incorrect attempts. Please request a new OTP.")
    if doc.get("otp") != req.otp.strip():
        await db.otps.update_one({"mobile": mobile}, {"$inc": {"attempts": 1}})
        raise HTTPException(400, "Invalid OTP")
    await db.otps.delete_one({"mobile": mobile})

    user = await db.users.find_one({"mobile": mobile}, {"_id": 0})
    if not user:
        raise HTTPException(400, "No account found for this mobile number.")
    if user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")

    new_hash = hash_password(req.new_password)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": new_hash, "token_version": int(user.get("token_version", 0)) + 1}},
    )
    return {"success": True, "message": "Password reset successfully. Please login with your new password."}


@api.post("/auth/set-password")
async def set_password(req: SetPasswordReq, user=Depends(get_user)):
    """Authenticated: set a password on an existing (OTP-only) account so the user
    can also login with mobile/email + password."""
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(req.new_password)}},
    )
    return {"success": True, "message": "Password set successfully. You can now login with your mobile/email and password."}


@api.post("/auth/google-session")
async def google_session(req: GoogleSessionReq):
    """LEGACY: exchange an OAuth session_id for our JWT (Emergent-era clients).

    Kept for backward compatibility. Production fails safe — GOOGLE_SESSION_URL
    must be explicitly configured; it is never silently pointed at a third-party
    demo endpoint. New clients use the native POST /api/auth/google flow."""
    if not GOOGLE_SESSION_URL:
        raise HTTPException(503, "Google OAuth is not configured.")
    async with httpx.AsyncClient(timeout=15) as http:
        try:
            r = await http.get(GOOGLE_SESSION_URL, headers={"X-Session-ID": req.session_id})
        except Exception:
            raise HTTPException(401, "Auth service unavailable")
    if r.status_code != 200:
        raise HTTPException(401, "Invalid or expired session")
    data = r.json()
    email = (data.get("email") or "").strip().lower()
    name = data.get("name")
    picture = data.get("picture")
    if not email:
        raise HTTPException(401, "Email not provided by Google")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    is_new = False
    if not user:
        is_new = True
        user = await create_new_user(email=email, name=name, picture=picture, provider="google")
        await apply_referral(req.referral_code, user)
    elif user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")
    else:
        # Keep profile fresh
        updates = {}
        if name and not user.get("name"):
            updates["name"] = name
        if picture:
            updates["picture"] = picture
        if updates:
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    token = make_token(user["id"], user.get("token_version", 0))
    return {"token": token, "user": _public_user(user), "is_new": is_new}


async def _google_token_exchange(code: str, redirect_uri: str) -> tuple:
    """POST the authorization code to Google's token endpoint (network stub point)."""
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    try:
        body = r.json()
    except Exception:
        body = {}
    return r.status_code, body


async def _google_userinfo(access_token: str) -> tuple:
    """Fetch verified identity from Google's userinfo endpoint (network stub point)."""
    async with httpx.AsyncClient(timeout=15) as http:
        u = await http.get(
            GOOGLE_OAUTH_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    try:
        body = u.json()
    except Exception:
        body = {}
    return u.status_code, body


@api.post("/auth/google")
async def google_code_exchange(req: GoogleCodeReq):
    """Native Google OAuth Authorization Code exchange (replaces Emergent flow).

    The frontend opens Google's consent URL directly and sends the returned
    authorization `code`. We exchange it for tokens server-side (the client
    secret never leaves this backend), fetch verified identity from Google's
    userinfo endpoint, then upsert the user by verified email — same JWT/session
    contract as the rest of auth. Fails safe (503) when the OAuth client is not
    configured; no default or invented credentials are ever used.
    """
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            503,
            "Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID and "
            "GOOGLE_OAUTH_CLIENT_SECRET in the backend environment to enable it.",
        )
    try:
        status, tok = await _google_token_exchange(req.code, req.redirect_uri)
    except Exception:
        raise HTTPException(503, "Google OAuth service unavailable")
    if status != 200:
        raise HTTPException(401, "Invalid or expired Google authorization code")
    access_token = tok.get("access_token")
    if not access_token:
        raise HTTPException(401, "Google did not return an access token")

    try:
        u_status, info = await _google_userinfo(access_token)
    except Exception:
        raise HTTPException(503, "Google OAuth service unavailable")
    if u_status != 200:
        raise HTTPException(401, "Unable to verify Google identity")
    email = (info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(401, "Email not verified by Google")
    name = info.get("name")
    picture = info.get("picture")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    is_new = False
    if not user:
        is_new = True
        user = await create_new_user(email=email, name=name, picture=picture, provider="google")
        await apply_referral(req.referral_code, user)
    elif user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")
    else:
        # Keep profile fresh
        updates = {}
        if name and not user.get("name"):
            updates["name"] = name
        if picture:
            updates["picture"] = picture
        if updates:
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    token = make_token(user["id"], user.get("token_version", 0))
    return {"token": token, "user": _public_user(user), "is_new": is_new}


# ============================================================
# FIREBASE AUTH — verified ID-token exchange
# ============================================================

async def _get_firebase_certs() -> dict:
    """Fetch Firebase public signing keys (x509 certs), cached for 5 minutes.
    These are the keys Firebase uses to sign ID tokens; verification against
    them is the officially documented path for servers without a service
    account. Google rotates these keys, so a missing `kid` triggers a refresh.
    Never logs the keys or any token."""
    global _firebase_certs, _firebase_certs_fetched_at
    now_ts = time.time()
    if _firebase_certs and _firebase_certs_fetched_at and now_ts - _firebase_certs_fetched_at < 300:
        return _firebase_certs
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(FIREBASE_CERT_URL)
    if r.status_code != 200:
        raise HTTPException(503, "Firebase authentication service unavailable")
    _firebase_certs = r.json()
    _firebase_certs_fetched_at = now_ts
    return _firebase_certs


def _firebase_cert_to_key(cert_pem: str):
    """Turn a Firebase public signing key into a key PyJWT can verify against.

    The Google cert endpoint returns x509 CERTIFICATES (PEM) — PyJWT's RS256
    path parses `BEGIN PUBLIC KEY`, not certificates — so parse the x509 and
    take its public key. Some callers (tests) provide a plain public-key PEM,
    which we accept as a fallback.
    """
    try:
        return load_pem_x509_certificate(cert_pem.encode()).public_key()
    except Exception:
        return load_pem_public_key(cert_pem.encode())


def _verify_firebase_token_sync(id_token: str, cert_pem: str) -> dict:
    """RS256-verify a Firebase ID token with Firebase's public cert."""
    claims = jwt.decode(
        id_token,
        _firebase_cert_to_key(cert_pem),
        algorithms=["RS256"],
        audience=FIREBASE_PROJECT_ID,
        issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}",
    )
    return claims


async def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token server-side and return the verified identity.

    Enforces: RS256 signature against Firebase's public key, `aud` == project
    id, `iss` == securetoken.google.com/<project>, expiry, and presence of a
    `uid`. The returned email/phone come from the VERIFIED token claims — never
    from anything the client sends separately.
    """
    if not FIREBASE_PROJECT_ID:
        raise HTTPException(503, "Firebase authentication is not configured on the server.")
    try:
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
    except Exception:
        raise HTTPException(401, "Invalid Firebase token")
    if not kid:
        raise HTTPException(401, "Invalid Firebase token")
    certs = await _get_firebase_certs()
    cert_pem = certs.get(kid)
    # Key rotation: refresh once in case a fresh kid appeared since our cache.
    if not cert_pem:
        _firebase_certs_fetched_at = 0.0
        certs = await _get_firebase_certs()
        cert_pem = certs.get(kid)
    if not cert_pem:
        raise HTTPException(401, "Invalid Firebase token")
    try:
        claims = _verify_firebase_token_sync(id_token, cert_pem)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Firebase token expired. Please sign in again.")
    except Exception:
        raise HTTPException(401, "Invalid Firebase token")
    # Firebase ID tokens carry the uid in `sub` (and legacy `user_id`) — there
    # is no `uid` claim. Accept all three for robustness.
    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid Firebase token")
    return {
        "uid": uid,
        "email": ((claims.get("email") or "").strip().lower() or None),
        "email_verified": bool(claims.get("email_verified")),
        "phone": claims.get("phone_number"),
        "name": claims.get("name"),
        "picture": claims.get("picture"),
        "provider": (claims.get("firebase") or {}).get("sign_in_provider"),
    }


@api.post("/auth/firebase")
async def firebase_auth(req: FirebaseAuthReq):
    """Exchange a verified Firebase ID token for the existing NyaySetu session.

    Flow: Firebase client SDK authenticates (email/password, phone OTP, or
    Google) -> the client sends ONLY the Firebase ID token -> we verify it
    server-side -> find or link the NyaySetu user by verified identity
    (firebase_uid -> email -> phone) -> issue the existing NyaySetu JWT.
    The frontend-supplied identity is never trusted; everything comes from the
    verified token claims. Fails safe (503) when FIREBASE_PROJECT_ID is unset.
    """
    if not FIREBASE_PROJECT_ID:
        raise HTTPException(
            503,
            "Firebase authentication is not configured on the server. Set "
            "FIREBASE_PROJECT_ID in the backend environment to enable it.",
        )
    # Hash the token for the rate-limit key (never store/log the raw token; the
    # first characters of JWTs are a shared header so a prefix key would lump
    # unrelated attempts into one bucket).
    _rl_key = hashlib.sha256(req.id_token.encode("utf-8")).hexdigest()[:32]
    if not rate_limit(f"firebase_auth:{_rl_key}", 5, 60):
        raise HTTPException(429, "Too many login attempts. Please wait before trying again.")
    info = await verify_firebase_id_token(req.id_token)

    # 1) Already linked to this Firebase UID
    user = await db.users.find_one({"firebase_uid": info["uid"]}, {"_id": 0})
    # 2) Existing user with the verified email (only when Google verified it)
    if not user and info["email"] and info["email_verified"]:
        user = await db.users.find_one({"email": info["email"]}, {"_id": 0})
    # 3) Existing user with the verified phone
    if not user and info["phone"]:
        clean_phone = info["phone"].replace(" ", "")
        if clean_phone.startswith("+91"):
            clean_phone = clean_phone[3:]
        user = await db.users.find_one({"mobile": clean_phone}, {"_id": 0})

    is_new = False
    if not user:
        is_new = True
        mobile = None
        if info["phone"]:
            clean_phone = info["phone"].replace(" ", "")
            if clean_phone.startswith("+91"):
                clean_phone = clean_phone[3:]
            mobile = clean_phone if len(clean_phone) == 10 else None
        email = info["email"] if info["email_verified"] else None
        user = await create_new_user(
            mobile=mobile,
            email=email,
            name=info["name"],
            picture=info["picture"],
            provider="firebase",
        )
        await db.users.update_one({"id": user["id"]}, {"$set": {"firebase_uid": info["uid"]}})
        user["firebase_uid"] = info["uid"]
        await apply_referral(req.referral_code, user)
    elif user.get("active") is False:
        raise HTTPException(403, "Account disabled. Contact support.")
    else:
        # Existing user signing in via Firebase — link the UID and keep profile fresh.
        updates = {"firebase_uid": info["uid"]}
        if info["name"] and not user.get("name"):
            updates["name"] = info["name"]
        if info["picture"]:
            updates["picture"] = info["picture"]
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)

    token = make_token(user["id"], user.get("token_version", 0))
    return {"token": token, "user": _public_user(user), "is_new": is_new}


# ============================================================
# PROFILE
# ============================================================

@api.get("/profile/me")
async def me(user=Depends(get_user)):
    return _public_user(user)

@api.put("/profile/update")
async def update_profile(req: ProfileUpdate, user=Depends(get_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return _public_user(u)


@api.get("/clients/lookup")
async def lookup_client(mobile: str, user=Depends(get_user)):
    """Search registered clients/users by mobile number."""
    clean_mobile = re.sub(r"\D", "", mobile)
    if clean_mobile.startswith("91") and len(clean_mobile) == 12:
        clean_mobile = clean_mobile[2:]
    if len(clean_mobile) < 10:
        raise HTTPException(400, "Invalid mobile number. Please enter a 10-digit mobile number.")

    client_user = await db.users.find_one({"mobile": clean_mobile}, {"_id": 0})
    if not client_user:
        client_user = await db.users.find_one({"mobile": mobile}, {"_id": 0})

    if client_user:
        return {
            "found": True,
            "client": {
                "id": client_user["id"],
                "name": client_user.get("name"),
                "mobile": client_user.get("mobile"),
                "email": client_user.get("email"),
                "state": client_user.get("state"),
                "district": client_user.get("district"),
                "court": client_user.get("court"),
                "bar_council_no": client_user.get("bar_council_no"),
            }
        }
    return {
        "found": False,
        "client": None,
        "message": f"Client with mobile '{mobile}' not found. You can enter client details manually."
    }


# ============================================================
# CATALOG & DYNAMIC CASE FORMS
# ============================================================

DEFAULT_CASE_FORMS = [
    {
        "case_type_id": "civil",
        "name_en": "Civil Suit",
        "name_gu": "દીવાની મુકદ્દમો",
        "category": "Civil",
        "fields": [
            {"key": "client_name", "label_en": "Client / Party Name", "label_gu": "અરજદાર / પક્ષકારનું નામ", "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
            {"key": "mobile", "label_en": "Mobile Number", "label_gu": "મોબાઈલ નંબર", "type": "mobile", "required": True, "order": 1, "autofill_map": "user.mobile"},
            {"key": "email", "label_en": "Email Address", "label_gu": "ઈમેઈલ સરનામું", "type": "email", "required": False, "order": 2, "autofill_map": "user.email"},
            {"key": "address", "label_en": "Client Address", "label_gu": "રહેઠાણનું સરનામું", "type": "textarea", "required": False, "order": 3, "autofill_map": "user.address"},
            {"key": "district", "label_en": "District", "label_gu": "જીલ્લો", "type": "text", "required": True, "order": 4, "autofill_map": "user.district"},
            {"key": "property_value", "label_en": "Valuation of Suit (₹)", "label_gu": "દાવાની રકમ (રૂ.)", "type": "number", "required": False, "order": 5},
            {"key": "relief_sought", "label_en": "Relief Sought", "label_gu": "માગેલ દાદ", "type": "textarea", "required": True, "order": 6},
        ]
    },
    {
        "case_type_id": "bail",
        "name_en": "Bail Application",
        "name_gu": "જામીન અરજી",
        "category": "Bail",
        "fields": [
            {"key": "client_name", "label_en": "Accused / Client Name", "label_gu": "આરોપી / અરજદારનું નામ", "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
            {"key": "mobile", "label_en": "Mobile Number", "label_gu": "મોબાઈલ નંબર", "type": "mobile", "required": True, "order": 1, "autofill_map": "user.mobile"},
            {"key": "fir_number", "label_en": "FIR / Crime Number", "label_gu": "એફ.આઈ.આર. / ગુના નંબર", "type": "text", "required": True, "order": 2},
            {"key": "police_station", "label_en": "Police Station", "label_gu": "પોલીસ સ્ટેશન", "type": "text", "required": True, "order": 3},
            {"key": "sections", "label_en": "IPC / BNS Sections", "label_gu": "કલમો", "type": "text", "required": True, "order": 4},
            {"key": "arrest_date", "label_en": "Arrest Date", "label_gu": "ધરપકડ તારીખ", "type": "date", "required": False, "order": 5},
            {"key": "bail_grounds", "label_en": "Grounds for Bail", "label_gu": "જામીન મેળવવાના કારણો", "type": "textarea", "required": True, "order": 6},
        ]
    },
    {
        "case_type_id": "revenue",
        "name_en": "Revenue / Land Matter",
        "name_gu": "મહેસૂલી / જમીન કેસ",
        "category": "Revenue",
        "fields": [
            {"key": "client_name", "label_en": "Applicant / Landholder Name", "label_gu": "અરજદાર / ખાતેદારનું નામ", "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
            {"key": "mobile", "label_en": "Mobile Number", "label_gu": "મોબાઈલ નંબર", "type": "mobile", "required": True, "order": 1, "autofill_map": "user.mobile"},
            {"key": "survey_number", "label_en": "Block / Survey Number", "label_gu": "બ્લોક / સરવે નંબર", "type": "text", "required": True, "order": 2},
            {"key": "village", "label_en": "Village", "label_gu": "ગામ", "type": "text", "required": True, "order": 3},
            {"key": "taluka", "label_en": "Taluka", "label_gu": "તાલુકો", "type": "text", "required": True, "order": 4},
            {"key": "district", "label_en": "District", "label_gu": "જીલ્લો", "type": "text", "required": True, "order": 5, "autofill_map": "user.district"},
        ]
    }
]

@api.get("/catalog/case-forms")
async def get_all_case_forms():
    """List all dynamic case form schemas."""
    forms = await db.case_forms.find({}, {"_id": 0}).to_list(100)
    if not forms:
        return DEFAULT_CASE_FORMS
    return forms

@api.get("/catalog/case-forms/{case_type_id}")
async def get_case_form_config(case_type_id: str):
    """Get dynamic case form configuration for a specific case type."""
    cfg = await db.case_forms.find_one({"case_type_id": case_type_id}, {"_id": 0})
    if not cfg:
        cfg = next((c for c in DEFAULT_CASE_FORMS if c["case_type_id"] == case_type_id), None)
    if not cfg:
        # No admin-configured form for this case type -> no dynamic fields.
        # Client identity (name/mobile/email/address/district) is captured by the
        # dedicated Client Details fields on the case, so no generic fallback here.
        return {
            "case_type_id": case_type_id,
            "name_en": case_type_id.replace("_", " ").title(),
            "name_gu": case_type_id,
            "category": "General",
            "fields": [],
        }
    return cfg

@api.get("/catalog/case-types")
async def case_types():
    items = await _load_catalog("case-types")
    return [_catalog_public(p) for p in items if p.get("active") is not False]

@api.get("/catalog/laws")
async def laws():
    items = await _load_catalog("laws")
    return [_catalog_public(p) for p in items if p.get("active") is not False]

@api.get("/catalog/laws/{law_id}/sections")
async def law_sections(law_id: str):
    law = await db.laws.find_one({"id": law_id}, {"_id": 0})
    if not law:
        law = next((l for l in LAWS if l["id"] == law_id), None)
    if not law:
        return []
    return law.get("sections", [])

@api.get("/catalog/districts")
async def districts():
    items = await _load_catalog("districts")
    return [_catalog_public(p) for p in items if p.get("active") is not False]

@api.get("/catalog/courts")
async def courts(district_id: Optional[str] = None):
    items = await _load_catalog("courts")
    items = [p for p in items if p.get("active") is not False]
    items = [_catalog_public(p) for p in items]
    generic = [c for c in items if c["district_id"] == "generic"]
    if district_id:
        specific = [c for c in items if c["district_id"] == district_id]
        return specific + generic
    return items

@api.get("/catalog/talukas")
async def talukas(district_id: Optional[str] = None):
    """Talukas under a district (or all). Used for district -> taluka
    dependencies in forms, autofill and template field options."""
    items = await _load_catalog("talukas")
    items = [_catalog_public(p) for p in items if p.get("active") is not False]
    if district_id:
        return [t for t in items if t["district_id"] == district_id]
    return items


@api.get("/catalog/police-stations")
async def police_stations(district_id: Optional[str] = None):
    items = await _load_catalog("police-stations")
    items = [p for p in items if p.get("active") is not False]
    items = [_catalog_public(p) for p in items]
    if district_id:
        return [p for p in items if p["district_id"] == district_id]
    return items

async def _load_plans() -> list:
    """DB plans if any exist, else the seed PLANS (backward compat when the
    plans collection has not been initialized)."""
    items = await db.plans.find({}, {"_id": 0}).to_list(200)
    if items:
        return items
    return [dict(p, active=True) for p in PLANS]


async def _get_plan(plan_id: str) -> Optional[dict]:
    """Resolve a plan from the DB, falling back to the seed catalog."""
    p = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if p:
        return p
    seed = next((x for x in PLANS if x["id"] == plan_id), None)
    if seed:
        return dict(seed, active=True)
    return None


def _plan_public(p: dict) -> dict:
    """Public plan shape: computed per-template price, never raw DB internals."""
    price = p.get("price") or 0
    credits = p.get("credits") or 0
    return {
        "id": p["id"],
        "name": p["name"],
        "price": price,
        "credits": credits,
        "popular": bool(p.get("popular")),
        "description": p.get("description"),
        "per_template": round(price / credits, 2) if credits else 0,
        "active": p.get("active") is not False,
    }


@api.get("/catalog/plans")
async def plans():
    items = await _load_plans()
    return [_plan_public(p) for p in items if p.get("active") is not False]

@api.get("/catalog/quote")
async def daily_quote():
    idx = now().day % len(QUOTES)
    return {"quote": QUOTES[idx]}


# ============================================================
# CASES
# ============================================================

# Catalog maps are refreshed from MongoDB (via _refresh_catalog_maps) so that
# admin-managed catalog entries flow into case labels, validation and document
# rendering without code changes. Initial seed build keeps module import safe.
_CASE_TYPE_MAP = {c["id"]: c for c in CASE_TYPES}
_LAW_MAP = {l["id"]: l for l in LAWS}
_DISTRICT_MAP = {d["id"]: d for d in DISTRICTS}
_TALUKA_MAP = {t["id"]: t for t in TALUKAS}
_COURT_MAP = {c["id"]: c for c in COURTS}
_PS_MAP = {p["id"]: p for p in POLICE_STATIONS}
_COMPLAINT_LABELS = {"private": "Private Complaint", "police": "Police Complaint", "other": "Other"}

# entity kind -> (collection name, seed list)
_CATALOG_KINDS = {
    "case-types": ("case_types", CASE_TYPES),
    "laws": ("laws", LAWS),
    "districts": ("districts", DISTRICTS),
    "talukas": ("talukas", TALUKAS),
    "courts": ("courts", COURTS),
    "police-stations": ("police_stations", POLICE_STATIONS),
}

_CATALOG_INTERNAL_FIELDS = ("active", "created_at", "updated_at", "created_by", "updated_by")


async def _load_catalog(kind: str) -> list:
    """DB catalog entries if the collection has any, else the seed list
    (backward compat for uninitialized databases)."""
    coll, seed_list = _CATALOG_KINDS[kind]
    items = await db[coll].find({}, {"_id": 0}).to_list(1000)
    if items:
        return items
    return [dict(x, active=True) for x in seed_list]


async def _refresh_catalog_maps() -> None:
    """Rebuild in-memory catalog maps + valid-id sets from MongoDB. Called at
    startup and after every admin catalog mutation so labels, validation and
    document rendering see admin-managed entries immediately."""
    global _CASE_TYPE_MAP, _LAW_MAP, _DISTRICT_MAP, _TALUKA_MAP, _COURT_MAP, _PS_MAP
    global _VALID_CASE_TYPE_IDS, _VALID_LAW_IDS, _VALID_DISTRICT_IDS, _VALID_TALUKA_IDS, _VALID_COURT_IDS, _VALID_PS_IDS
    _CASE_TYPE_MAP = {c["id"]: c for c in await _load_catalog("case-types")}
    _LAW_MAP = {l["id"]: l for l in await _load_catalog("laws")}
    _DISTRICT_MAP = {d["id"]: d for d in await _load_catalog("districts")}
    _TALUKA_MAP = {t["id"]: t for t in await _load_catalog("talukas")}
    _COURT_MAP = {c["id"]: c for c in await _load_catalog("courts")}
    _PS_MAP = {p["id"]: p for p in await _load_catalog("police-stations")}
    _VALID_CASE_TYPE_IDS = {c["id"] for c in _CASE_TYPE_MAP.values()}
    _VALID_LAW_IDS = {l["id"] for l in _LAW_MAP.values()}
    _VALID_DISTRICT_IDS = {d["id"] for d in _DISTRICT_MAP.values()}
    _VALID_TALUKA_IDS = {t["id"] for t in _TALUKA_MAP.values()}
    _VALID_COURT_IDS = {c["id"] for c in _COURT_MAP.values()}
    _VALID_PS_IDS = {p["id"] for p in _PS_MAP.values()}


def _catalog_public(item: dict) -> dict:
    """Public catalog shape — identical to the legacy seed shape (no internals)."""
    return {k: v for k, v in item.items() if k not in _CATALOG_INTERNAL_FIELDS}


def enrich_case(c: dict) -> dict:
    """Attach human-readable labels + category so the frontend stays simple."""
    lang = c.get("language", "en")
    ct = _CASE_TYPE_MAP.get(c.get("case_type_id"))
    law = _LAW_MAP.get(c.get("law_id"))
    dist = _DISTRICT_MAP.get(c.get("district_id"))
    court = _COURT_MAP.get(c.get("court_id"))
    ps = _PS_MAP.get(c.get("police_station_id"))
    section = None
    if law and c.get("section_id"):
        section = next((s for s in law["sections"] if s["id"] == c.get("section_id")), None)
    c["category"] = ct["cat"] if ct else "Other"
    if c.get("case_type_id") == "other" and c.get("case_type_custom"):
        c["case_type_label"] = c.get("case_type_custom")
    elif ct:
        c["case_type_label"] = ct["gu"] if lang == "gu" else ct["en"]
    else:
        c["case_type_label"] = c.get("case_type_custom") or None
    c["law_label"] = (law["gu"] if lang == "gu" else law["en"]) if law else (c.get("law_custom") or None)
    c["section_label"] = section["label"] if section else None
    c["district_label"] = (dist["gu"] if lang == "gu" else dist["en"]) if dist else None
    if court:
        c["court_label"] = court["gu"] if lang == "gu" else court["en"]
    else:
        c["court_label"] = c.get("court_custom") or c.get("court") or None
    if ps:
        c["police_station_label"] = ps["gu"] if lang == "gu" else ps["en"]
    else:
        c["police_station_label"] = c.get("police_station_custom") or c.get("police_station") or None
    c["complaint_label"] = _COMPLAINT_LABELS.get(c.get("complaint_type")) if c.get("complaint_type") else None
    return c


# ============================================================
# REFERENCE VALIDATION
# ============================================================

_VALID_CASE_TYPE_IDS = {c["id"] for c in _CASE_TYPE_MAP.values()}
_VALID_LAW_IDS = {l["id"] for l in _LAW_MAP.values()}
_VALID_DISTRICT_IDS = {d["id"] for d in _DISTRICT_MAP.values()}
_VALID_TALUKA_IDS = {t["id"] for t in _TALUKA_MAP.values()}
_VALID_COURT_IDS = {c["id"] for c in _COURT_MAP.values()}
_VALID_PS_IDS = {p["id"] for p in _PS_MAP.values()}

MAX_TEMPLATE_VALUES_TOTAL = 100_000  # max total chars in template values dict


def validate_case_refs(data: dict):
    """Validate catalog reference IDs. Raises HTTPException on invalid."""
    cid = data.get("case_type_id")
    if cid and cid != "other" and cid not in _VALID_CASE_TYPE_IDS:
        raise HTTPException(400, f"Invalid case_type_id: {cid}")
    lid = data.get("law_id")
    if lid and lid != "other_law" and lid not in _VALID_LAW_IDS:
        raise HTTPException(400, f"Invalid law_id: {lid}")
    did = data.get("district_id")
    if did and did not in _VALID_DISTRICT_IDS:
        raise HTTPException(400, f"Invalid district_id: {did}")
    court = data.get("court_id")
    if court and court != "other" and court not in _VALID_COURT_IDS:
        raise HTTPException(400, f"Invalid court_id: {court}")
    if court == "other" and not (data.get("court_custom") or data.get("court")):
        raise HTTPException(400, "court_custom is required when court_id is 'other'")
    psid = data.get("police_station_id")
    if psid and psid != "other" and psid not in _VALID_PS_IDS:
        raise HTTPException(400, f"Invalid police_station_id: {psid}")
    if psid == "other" and not (data.get("police_station_custom") or data.get("police_station")):
        raise HTTPException(400, "police_station_custom is required when police_station_id is 'other'")


def validate_values_size(values: dict):
    """Prevent payload abuse via extremely large template values."""
    if len(values) > 100:
        raise HTTPException(400, "Too many template fields (max 100)")
    for k, v in values.items():
        if isinstance(v, str) and len(v) > 5000:
            raise HTTPException(400, f"Field '{k}' too long (max 5000 chars)")
    total = sum(len(str(k)) + len(str(v)) for k, v in values.items())
    if total > MAX_TEMPLATE_VALUES_TOTAL:
        raise HTTPException(400, "Template values payload too large")


MAX_CUSTOM_FIELDS = 200
MAX_CUSTOM_FIELD_LEN = 5000


def validate_custom_fields(custom: Optional[dict]) -> Optional[dict]:
    """Validate admin-configured case form values. Returns {} for None input."""
    if not custom:
        return {}
    if not isinstance(custom, dict):
        raise HTTPException(400, "custom_fields must be an object")
    if len(custom) > MAX_CUSTOM_FIELDS:
        raise HTTPException(400, f"Too many custom fields (max {MAX_CUSTOM_FIELDS})")
    for k, v in custom.items():
        if not isinstance(k, str) or len(k) > 100:
            raise HTTPException(400, "Invalid custom field key")
        if isinstance(v, str) and len(v) > MAX_CUSTOM_FIELD_LEN:
            raise HTTPException(400, f"Field '{k}' too long (max {MAX_CUSTOM_FIELD_LEN} chars)")
        if isinstance(v, (dict, list)):
            raise HTTPException(400, f"Field '{k}' must be a scalar value")
    total = sum(len(str(k)) + len(str(v)) for k, v in custom.items())
    if total > MAX_TEMPLATE_VALUES_TOTAL:
        raise HTTPException(400, "Custom fields payload too large")
    return custom


# autofill_map subject keys are resolved against the CLIENT context (D1):
# the looked-up client's name/mobile/email/address/district, NOT the advocate's user record.
_AUTOFILL_CLIENT_KEYS = {"name", "mobile", "email", "address", "district"}


def resolve_autofill_value(autofill_map: Optional[str], client_ctx: dict) -> Optional[str]:
    """Resolve an autofill_map like 'user.name' against the client context."""
    if not autofill_map:
        return None
    key = autofill_map.split(".", 1)[-1]
    if key in _AUTOFILL_CLIENT_KEYS:
        val = client_ctx.get(key)
        return val if val not in (None, "") else None
    return None


def client_ctx_from(payload: dict) -> dict:
    """Build the client autofill context from a case payload."""
    district = payload.get("client_district")
    did = payload.get("district_id")
    if not district and did:
        d = next((x for x in DISTRICTS if x["id"] == did), None)
        district = d["en"] if d else None
    return {
        "name": payload.get("client_name") or payload.get("party_name"),
        "mobile": payload.get("client_mobile"),
        "email": payload.get("client_email"),
        "address": payload.get("client_address"),
        "district": district,
    }


async def resolve_custom_autofill(case_type_id: Optional[str], custom_fields: Optional[dict], client_ctx: dict) -> dict:
    """Fill empty autofill-mapped custom fields from the client context.

    Uses the admin-configured case form schema for the case type (DB first,
    DEFAULT_CASE_FORMS fallback). Values the user already entered are never
    overwritten. This is server-side enforcement so no data is silently dropped.
    """
    custom = dict(custom_fields or {})
    if not case_type_id:
        return custom
    cfg = await db.case_forms.find_one({"case_type_id": case_type_id}, {"_id": 0})
    if not cfg:
        cfg = next((c for c in DEFAULT_CASE_FORMS if c["case_type_id"] == case_type_id), None)
    if not cfg:
        return custom
    for f in cfg.get("fields", []):
        key = f.get("key")
        if not key or key in custom and custom.get(key) not in (None, ""):
            continue
        val = resolve_autofill_value(f.get("autofill_map"), client_ctx)
        if val is not None:
            custom[key] = val
    return custom


@api.post("/cases")
async def create_case(req: CaseCreate, user=Depends(get_user)):
    payload = req.model_dump()
    validate_case_refs(payload)
    validate_custom_fields(payload.get("custom_fields"))
    client_ctx = client_ctx_from(payload)
    payload["custom_fields"] = await resolve_custom_autofill(
        payload.get("case_type_id"), payload.get("custom_fields"), client_ctx
    )
    # Flat client fields: default client_name to the primary party name (D3).
    if not payload.get("client_name"):
        payload["client_name"] = payload.get("party_name")
    case_id = str(uuid.uuid4())
    doc = {
        "id": case_id,
        "user_id": user["id"],
        "status": "active",
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
        "last_used_template": None,
        "application_count": 0,
        **payload,
    }
    await db.cases.insert_one(doc.copy())
    doc.pop("_id", None)
    return enrich_case(doc)


@api.get("/cases")
async def list_cases(user=Depends(get_user), q: Optional[str] = None,
                     status: str = "active", category: Optional[str] = None,
                     sort: str = "updated"):
    query: dict = {"user_id": user["id"]}
    if status != "all":
        # Treat missing status as active (legacy docs)
        if status == "active":
            query["status"] = {"$ne": "archived"}
        else:
            query["status"] = status
    cursor = db.cases.find(query, {"_id": 0}).sort("updated_at", -1)
    items = await cursor.to_list(500)
    items = [enrich_case(c) for c in items]
    if category and category != "All":
        items = [c for c in items if c.get("category") == category]
    if q:
        ql = q.lower()
        items = [c for c in items if
                 ql in (c.get("nickname") or "").lower()
                 or ql in (c.get("case_number") or "").lower()
                 or ql in (c.get("party_name") or "").lower()
                 or ql in (c.get("case_type_label") or "").lower()
                 or ql in (c.get("case_type_id") or "").lower()]
    if sort == "name":
        items.sort(key=lambda c: (c.get("nickname") or c.get("party_name") or c.get("case_type_label") or "").lower())
    elif sort == "type":
        items.sort(key=lambda c: (c.get("case_type_label") or "").lower())
    # default "updated" already sorted by query
    return items


@api.get("/cases/{case_id}")
async def get_case(case_id: str, user=Depends(get_user)):
    c = await db.cases.find_one({"id": case_id, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Case not found")
    return enrich_case(c)


@api.put("/cases/{case_id}")
async def update_case(case_id: str, req: CaseUpdate, user=Depends(get_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    validate_case_refs(updates)
    existing = await db.cases.find_one({"id": case_id, "user_id": user["id"]}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Case not found")
    # custom_fields: merge into existing so admin-configured values are never lost.
    if "custom_fields" in updates:
        validate_custom_fields(updates["custom_fields"])
        merged_custom = dict(existing.get("custom_fields") or {})
        merged_custom.update(updates["custom_fields"] or {})
        case_type_id = updates.get("case_type_id") or existing.get("case_type_id")
        merged_payload = {**existing, **updates}
        updates["custom_fields"] = await resolve_custom_autofill(
            case_type_id, merged_custom, client_ctx_from(merged_payload)
        )
    # Flat client fields: default client_name to the primary party name (D3).
    if "party_name" in updates and not updates.get("client_name"):
        updates["client_name"] = updates["party_name"]
    updates["updated_at"] = now().isoformat()
    r = await db.cases.update_one({"id": case_id, "user_id": user["id"]}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    c = await db.cases.find_one({"id": case_id, "user_id": user["id"]}, {"_id": 0})
    return enrich_case(c)


@api.post("/cases/{case_id}/archive")
async def archive_case(case_id: str, user=Depends(get_user)):
    r = await db.cases.update_one(
        {"id": case_id, "user_id": user["id"]},
        {"$set": {"status": "archived", "updated_at": now().isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    return {"success": True, "status": "archived"}


@api.post("/cases/{case_id}/restore")
async def restore_case(case_id: str, user=Depends(get_user)):
    r = await db.cases.update_one(
        {"id": case_id, "user_id": user["id"]},
        {"$set": {"status": "active", "updated_at": now().isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    return {"success": True, "status": "active"}


@api.delete("/cases/{case_id}")
async def delete_case(case_id: str, user=Depends(get_user)):
    r = await db.cases.delete_one({"id": case_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Case not found")
    return {"success": True}


# ============================================================
# TEMPLATES
# ============================================================
_AUTO_FILL_FIELDS = {
    "advocate_name", "today", "district", "court", "case_number", "case_type",
    "party_name", "opposite_party", "police_station", "law", "section",
    "client_name", "client_mobile", "client_email", "client_address", "client_district",
    # Derived values for the document-return application (never user-entered)
    "case_status_clause", "tense", "selected_party_role", "taluka_place",
    "date_display",
}

def public_template(t: dict) -> dict:
    """Return the public-facing template shape (unchanged for backward compat)."""
    fields = t.get("fields", [])
    clean_fields = []
    for f in fields:
        field_dict = {
            "key": f["key"],
            "label_en": f.get("label_en", ""),
            "label_gu": f.get("label_gu", ""),
            "type": f.get("type", "text"),
            "required": f.get("required", True),
        }
        if "options" in f and f["options"]:
            field_dict["options"] = f["options"]
        if "default_value" in f and f["default_value"] is not None:
            field_dict["default_value"] = f["default_value"]
        if f.get("placeholder"):
            field_dict["placeholder"] = f["placeholder"]
        clean_fields.append(field_dict)
    res = {
        "id": t["id"],
        "name_en": t["name_en"],
        "name_gu": t["name_gu"],
        "category": t["category"],
        "fields": clean_fields,
    }
    # settings (margins/fonts/page_size) stay internal to document generation —
    # never exposed to the lawyer client; the public shape must remain unchanged.
    for opt_key in ["sub_category", "description", "tags", "case_types", "courts", "jurisdiction"]:
        if opt_key in t and t[opt_key]:
            res[opt_key] = t[opt_key]
    return res


async def _get_published_templates() -> list:
    """Return published templates. Merges DB published templates with seed templates (DB overrides seed by ID).
    Hides archived templates."""
    db_templates = await db.templates.find({}, {"_id": 0}).to_list(500)
    db_by_id = {t["id"]: t for t in db_templates}

    merged = []
    # Add seed templates if not overridden or if published in DB
    for seed_t in TEMPLATES:
        t_id = seed_t["id"]
        if t_id in db_by_id:
            db_t = db_by_id[t_id]
            if db_t.get("status") == "published":
                merged.append(db_t)
            # If draft or archived, hide from public lawyer templates list
        else:
            # Not in DB yet -> seed template is active by default
            merged.append(seed_t)

    # Add newly created templates from DB that are published and not in seed
    seed_ids = {t["id"] for t in TEMPLATES}
    for db_t in db_templates:
        if db_t["id"] not in seed_ids and db_t.get("status") == "published":
            merged.append(db_t)

    return sorted(merged, key=lambda x: x.get("category", ""))


async def _get_template_by_id(template_id: str) -> Optional[dict]:
    """Get a single published template by ID. DB-first, seed fallback."""
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if t:
        if t.get("status") == "published":
            return t
        return None  # Draft or archived in DB -> hidden from public lawyer API
    return next((x for x in TEMPLATES if x["id"] == template_id), None)


@api.get("/templates")
async def list_templates(q: Optional[str] = None, category: Optional[str] = None):
    all_templates = await _get_published_templates()
    items = [public_template(t) for t in all_templates]
    if category:
        items = [t for t in items if t["category"].lower() == category.lower()]
    if q:
        ql = q.lower().strip()
        matched = []
        for t in all_templates:
            all_aliases = [t["name_en"].lower(), t["name_gu"].lower()] + [a.lower() for a in t.get("aliases", [])]
            if any(ql in a for a in all_aliases):
                matched.append(public_template(t))
        items = matched
    return items


@api.get("/templates/{template_id}")
async def get_template(template_id: str):
    t = await _get_template_by_id(template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    return {
        **public_template(t),
        "content_en": t["content_en"],
        "content_gu": t["content_gu"],
        "aliases": t.get("aliases", []),
    }


# ============================================================
# APPLICATION GENERATION
# ============================================================

def format_advocate_name(name: Optional[str] = None) -> str:
    """Display an advocate name as \"Adv. <Name>\" without double-prefixing.

    Mirrors the frontend helper (src/utils/advocate.ts) so documents render the
    same professional format regardless of generation path. Client-provided
    values are untouched; only the server-side default is formatted."""
    n = (name or "").strip()
    if not n:
        return "Advocate"
    return n if re.match(r"^adv\.?\s", n, re.IGNORECASE) else f"Adv. {n}"


async def build_render_context(user: dict, case: Optional[dict], values: dict, language: str) -> dict:
    ctx = dict(values or {})
    # Advocate (server-side default only; a client-provided advocate_name wins)
    ctx.setdefault("advocate_name", format_advocate_name(user.get("name")))
    # Today (formatted)
    ctx["today"] = now().strftime("%d-%m-%Y")
    # Guard: if a client sent a raw district id (e.g. "ahmedabad") instead of a
    # label, resolve it here so documents never print raw catalog ids.
    if isinstance(ctx.get("district"), str) and ctx["district"] in _DISTRICT_MAP:
        d = _DISTRICT_MAP[ctx["district"]]
        ctx["district"] = d["gu"] if language == "gu" else d["en"]
    # Same guard for court / case_type raw catalog ids sent as select values
    # so documents never print raw catalog ids (e.g. "gen_jmfc", "civil_suit").
    if isinstance(ctx.get("court"), str) and ctx["court"] in _COURT_MAP:
        cobj = _COURT_MAP[ctx["court"]]
        ctx["court"] = cobj["gu"] if language == "gu" else cobj["en"]
    if isinstance(ctx.get("case_type"), str) and ctx["case_type"] in _CASE_TYPE_MAP:
        ctobj = _CASE_TYPE_MAP[ctx["case_type"]]
        ctx["case_type"] = ctobj["gu"] if language == "gu" else ctobj["en"]
    if case:
        did = case.get("district_id") or user.get("district")
        d = next((x for x in DISTRICTS if x["id"] == did), None)
        if d:
            district_name = d["gu"] if language == "gu" else d["en"]
        else:
            district_name = ""
        ctx.setdefault("district", district_name or case.get("district_id") or "")
        court_obj = _COURT_MAP.get(case.get("court_id"))
        if court_obj:
            court_name = court_obj["gu"] if language == "gu" else court_obj["en"]
        else:
            court_name = case.get("court_custom") or case.get("court") or ""
        ctx.setdefault("court", court_name)
        ctx.setdefault("case_number", case.get("case_number") or "")
        # case type
        ct = next((x for x in CASE_TYPES if x["id"] == case.get("case_type_id")), None)
        if ct:
            ctx.setdefault("case_type", ct["gu"] if language == "gu" else ct["en"])
        else:
            ctx.setdefault("case_type", case.get("case_type_custom") or "")
        ctx.setdefault("party_name", case.get("party_name") or "")
        ctx.setdefault("opposite_party", case.get("opposite_party") or "")
        # Police station (label or custom)
        ps_obj = _PS_MAP.get(case.get("police_station_id"))
        if ps_obj:
            ctx.setdefault("police_station", ps_obj["gu"] if language == "gu" else ps_obj["en"])
        else:
            ctx.setdefault("police_station", case.get("police_station_custom") or case.get("police_station") or "")
        # Law / section labels
        law_obj = _LAW_MAP.get(case.get("law_id"))
        if law_obj:
            ctx.setdefault("law", law_obj["gu"] if language == "gu" else law_obj["en"])
            sec = None
            if case.get("section_id"):
                sec = next((s for s in law_obj["sections"] if s["id"] == case.get("section_id")), None)
            if sec:
                ctx.setdefault("section", sec["label"])
        # Flat client details (D3) — user-entered values win via setdefault.
        for ck in ("client_name", "client_mobile", "client_email", "client_address", "client_district"):
            if ck not in ctx and case.get(ck):
                ctx[ck] = case[ck]
        if not ctx.get("client_name"):
            ctx["client_name"] = case.get("client_name") or case.get("party_name") or ""
        # Admin-configured custom fields (D2) — merged so templates can reference {{custom_key}}.
        for k, v in (case.get("custom_fields") or {}).items():
            if k not in ctx and v not in (None, ""):
                ctx[k] = str(v)
    else:
        d = next((x for x in DISTRICTS if x["id"] == user.get("district")), None)
        ctx.setdefault("district", (d["gu"] if language == "gu" else d["en"]) if d else (user.get("district") or ""))
        ctx.setdefault("court", user.get("court") or "")
        ctx.setdefault("case_number", "")
        ctx.setdefault("case_type", "")
        ctx.setdefault("party_name", "")
        ctx.setdefault("opposite_party", "")
        ctx.setdefault("police_station", "")
        if not ctx.get("client_name"):
            ctx["client_name"] = ""

    # ---- Derived values for the document-return application (never user-entered) ----
    # case_status -> conditional Gujarati clause + verb tense, literal per the
    # source document: "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ [ચાલવા પર છે./ આપની કોર્ટમા
    # ડિસ્પોસ્ડ થયેલ છે]" and "કામમા રજૂ કરવામાં આવેલ [છે/હતો]". Both the current
    # (ડિસ્પોઝ્ડ) and source-document (ડિસ્પોસ્ડ) spellings are accepted so
    # previously saved drafts keep working.
    status = ctx.get("case_status")
    if status == "ચાલુ":
        ctx["case_status_clause"] = "ચાલવા પર છે"
        ctx["tense"] = "છે"
    elif status in ("ડિસ્પોઝ્ડ", "ડિસ્પોસ્ડ"):
        ctx["case_status_clause"] = "આપની કોર્ટમા ડિસ્પોસ્ડ થયેલ છે"
        ctx["tense"] = "હતો"
    else:
        ctx["case_status_clause"] = ""
        ctx["tense"] = "છે"
    # Signature/pleading role — applicant-side role, opposite-side as fallback
    ctx["selected_party_role"] = ctx.get("applicant_role") or ctx.get("opposite_party_role") or ""
    # Taluka/district line — taluka first when present (e.g. "કલોલ, ગાંધીનગર")
    _tal = (ctx.get("taluka") or "").strip()
    ctx["taluka_place"] = f"{_tal}, {ctx.get('district') or ''}" if _tal else (ctx.get("district") or "")
    # Date display — the source blank is "[__ / __ / 20__]" (DD/MM/YYYY); the
    # canonical stored value is YYYY-MM-DD. Derived key keeps {{date}} untouched
    # for every other template. Legacy DD-MM-YYYY values pass through unchanged.
    _d = ctx.get("date")
    if isinstance(_d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", _d):
        ctx["date_display"] = f"{_d[8:10]}/{_d[5:7]}/{_d[0:4]}"
    else:
        ctx["date_display"] = (_d or "") if isinstance(_d, str) else ""
    return ctx


def _validate_page_size(page_size: Optional[str]) -> None:
    if page_size and str(page_size).upper() not in ("A4", "LEGAL"):
        raise HTTPException(422, "page_size must be 'A4' or 'Legal'")


def _validate_template_settings(settings: Optional[dict]) -> None:
    """Validate admin-supplied template settings (page_size must be A4/Legal)."""
    if not settings:
        return
    _validate_page_size(settings.get("page_size"))

@api.post("/applications/preview")
async def preview_application(req: GenerateReq, user=Depends(get_user)):
    validate_values_size(req.values)
    _validate_page_size(req.page_size)
    t = await _get_template_by_id(req.template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    tpl_ps = (t.get("settings") or {}).get("page_size")
    _validate_page_size(tpl_ps)
    page_size = req.page_size or tpl_ps or await _get_setting("default_page_size")
    _validate_page_size(page_size)
    case = None
    if req.case_id:
        case = await db.cases.find_one({"id": req.case_id, "user_id": user["id"]}, {"_id": 0})
    ctx = await build_render_context(user, case, req.values, req.language)
    tpl = t["content_gu"] if req.language == "gu" else t["content_en"]
    rendered = render_template(tpl, ctx)
    blocks = build_blocks(rendered, t["name_en"], t["name_gu"],
                          (t.get("settings") or {}).get("block_align"))
    return {"content": rendered, "blocks": blocks, "language": req.language, "template_id": t["id"]}


@api.post("/applications/download")
async def download_application(req: DownloadReq, user=Depends(get_user)):
    validate_values_size(req.values)
    _validate_page_size(req.page_size)
    if req.format not in ("pdf", "docx", "odt"):
        raise HTTPException(422, "format must be 'pdf', 'docx' or 'odt'")
    if not rate_limit(f"download:{user['id']}", 30, 60):
        raise HTTPException(429, "Too many downloads. Please try again later.")
    t = await _get_template_by_id(req.template_id)
    if not t:
        raise HTTPException(404, "Template not found")
    tpl_ps = (t.get("settings") or {}).get("page_size")
    _validate_page_size(tpl_ps)
    page_size = req.page_size or tpl_ps or await _get_setting("default_page_size")
    _validate_page_size(page_size)

    # SERVER-CONTROLLED: Always consume exactly 1 credit for final downloads.
    # The consume_credit client flag is IGNORED for security.
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    if not wallet or wallet.get("balance", 0) < 1:
        raise HTTPException(402, "Insufficient template credits. Please purchase a plan.")

    # Atomic credit deduction FIRST (check-and-decrement prevents negative balance)
    r = await db.wallets.update_one(
        {"user_id": user["id"], "balance": {"$gte": 1}},
        {"$inc": {"balance": -1, "total_used": 1}, "$set": {"updated_at": now().isoformat()}},
    )
    if r.modified_count == 0:
        raise HTTPException(402, "Insufficient credits")

    # Generate document — if this fails, refund the credit
    app_id = str(uuid.uuid4())
    try:
        case = None
        if req.case_id:
            case = await db.cases.find_one({"id": req.case_id, "user_id": user["id"]}, {"_id": 0})
        ctx = await build_render_context(user, case, req.values, req.language)
        tpl = t["content_gu"] if req.language == "gu" else t["content_en"]
        rendered = render_template(tpl, ctx)
        blocks = build_blocks(rendered, t["name_en"], t["name_gu"],
                              (t.get("settings") or {}).get("block_align"))

        doc_settings = {"page_size": page_size}
        tpl_settings = t.get("settings") or {}
        for _k in ("margin_top_cm", "margin_bottom_cm", "margin_left_cm",
                   "margin_right_cm", "body_size", "heading_size", "line_spacing",
                   "paragraph_spacing", "alignment", "gujarati_font", "english_font",
                   "gujarati_font_docx", "english_font_docx"):
            if tpl_settings.get(_k) is not None:
                doc_settings[_k] = tpl_settings[_k]
        if req.format == "docx":
            b64 = generate_docx(blocks, req.language, doc_settings)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif req.format == "odt":
            b64 = generate_odt(blocks, req.language, doc_settings)
            mime = "application/vnd.oasis.opendocument.text"
        else:
            b64 = generate_pdf(blocks, req.language, doc_settings)
            mime = "application/pdf"
    except Exception as e:
        # Refund credit on generation failure — user must not be unfairly charged
        await db.wallets.update_one(
            {"user_id": user["id"]},
            {"$inc": {"balance": 1, "total_used": -1}, "$set": {"updated_at": now().isoformat()}},
        )
        await db.transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "type": "refund",
            "plan_name": t["name_en"],
            "credits": 1,
            "amount": 0,
            "status": "refunded",
            "reference": app_id,
            "created_at": now().isoformat(),
        })
        logger.error(f"Document generation failed, credit refunded: {e}")
        raise HTTPException(500, "Document generation failed. Your credit has been refunded.")

    # Log usage + record the credit consumption as a transaction (Phase 24/25:
    # transaction history must show actual activity with a type).
    filename = req.filename or f"{t['id']}_{now().strftime('%Y%m%d_%H%M%S')}.{req.format}"
    await db.applications.insert_one({
        "id": app_id,
        "user_id": user["id"],
        "template_id": t["id"],
        "template_name": t["name_en"],
        "case_id": req.case_id,
        "language": req.language,
        "format": req.format,
        "filename": filename,
        "created_at": now().isoformat(),
    })
    await db.transactions.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "type": "document",
        "plan_name": t["name_en"],
        "credits": -1,
        "amount": 0,
        "status": "success",
        "reference": app_id,
        "created_at": now().isoformat(),
    })
    if req.case_id:
        await db.cases.update_one(
            {"id": req.case_id, "user_id": user["id"]},
            {"$set": {"last_used_template": t["name_en"], "updated_at": now().isoformat()},
             "$inc": {"application_count": 1}},
        )
    # Delete related draft
    await db.drafts.delete_many({"user_id": user["id"], "template_id": t["id"], "case_id": req.case_id})

    return {"filename": filename, "mime_type": mime, "base64": b64}


@api.get("/applications/history")
async def application_history(user=Depends(get_user)):
    items = await db.applications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items


# ============================================================
# WALLET & PURCHASE
# ============================================================

@api.get("/wallet")
async def get_wallet(user=Depends(get_user)):
    w = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    if not w:
        # Wallet missing — recreate with ZERO balance (not 5).
        # Initial 5 free credits are granted only once via create_new_user() at signup.
        # Re-creating with 5 would allow infinite free credits by deleting the wallet.
        w = {"user_id": user["id"], "balance": 0, "free_credits_granted": 0, "total_used": 0,
             "updated_at": now().isoformat()}
        await db.wallets.insert_one(w.copy())
    return {"balance": w.get("balance", 0), "total_used": w.get("total_used", 0)}


@api.post("/purchase/mock")
async def mock_purchase(req: PurchaseReq, user=Depends(get_user)):
    """DEV-ONLY mock purchase — never used as the production payment path.
    Resolves plans from the admin-managed plans catalog so admin edits flow
    through; inactive plans cannot be purchased.

    Hard-disabled the moment real payment is available: refused when Razorpay
    keys are configured (the production payment path exists) or when the
    deployment is declared production (ENVIRONMENT=production), so free-credit
    mock purchases can never run in a real paying environment."""
    if _razorpay_enabled() or _PRODUCTION:
        raise HTTPException(
            403,
            "Mock purchases are disabled in this environment. Use the configured payment method.",
        )
    plan = await _get_plan(req.plan_id)
    if not plan or plan.get("active") is False:
        raise HTTPException(404, "Plan not found or inactive")
    txn_id = str(uuid.uuid4())
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"balance": plan["credits"]}, "$set": {"updated_at": now().isoformat()}},
        upsert=True,
    )
    await db.transactions.insert_one({
        "id": txn_id,
        "user_id": user["id"],
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "amount": plan["price"],
        "credits": plan["credits"],
        "status": "success",
        "mock": True,
        "created_at": now().isoformat(),
    })
    w = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"success": True, "transaction_id": txn_id, "balance": w.get("balance", 0)}


# ============================================================
# RAZORPAY PAYMENTS (production path)
# ============================================================


def _razorpay_enabled() -> bool:
    """True only when both Razorpay keys are configured — never a default pair."""
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


async def _razorpay_create_order(amount_paise: int, receipt: str) -> dict:
    """Create a Razorpay order. Network call isolated here so tests can stub it."""
    auth = (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.post(
            f"{RAZORPAY_API_BASE}/v1/orders",
            auth=auth,
            json={"amount": amount_paise, "currency": "INR", "receipt": receipt},
        )
    if r.status_code != 200:
        raise HTTPException(502, "Payment provider error. Please try again.")
    data = r.json()
    if not data.get("id"):
        raise HTTPException(502, "Payment provider returned an invalid order.")
    return data


def _razorpay_verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """HMAC-SHA256 over '{order_id}|{payment_id}' using the Razorpay key secret."""
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@api.post("/payments/razorpay/create-order")
async def razorpay_create_order(req: RazorpayCreateOrderReq, user=Depends(get_user)):
    """Create a Razorpay order for a plan. Fails safely (503) when keys are missing."""
    if not _razorpay_enabled():
        raise HTTPException(
            503,
            "Payments are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
            "in the environment.",
        )
    plan = await _get_plan(req.plan_id)
    if not plan or plan.get("active") is False:
        raise HTTPException(404, "Plan not found or inactive")
    amount_paise = int(round(plan["price"] * 100))
    receipt = f"nsp_{uuid.uuid4().hex[:16]}"
    rz = await _razorpay_create_order(amount_paise, receipt)
    await db.payment_orders.insert_one({
        "id": rz["id"],
        "receipt": receipt,
        "user_id": user["id"],
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "amount_paise": amount_paise,
        "currency": "INR",
        "status": "created",
        "created_at": now().isoformat(),
    })
    return {
        "order_id": rz["id"],
        "key_id": RAZORPAY_KEY_ID,
        "amount_paise": amount_paise,
        "currency": "INR",
        "plan": {"id": plan["id"], "name": plan["name"], "credits": plan["credits"]},
    }


@api.post("/payments/razorpay/verify")
async def razorpay_verify(req: RazorpayVerifyReq, user=Depends(get_user)):
    """Server-side verification of the client-side Razorpay checkout.

    Credits are granted ONLY after the payment signature verifies. Idempotent:
    a payment_id that already granted credits returns the existing transaction
    without granting again (duplicate / replay protection).
    """
    if not _razorpay_enabled():
        raise HTTPException(
            503,
            "Payments are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
            "in the environment.",
        )
    order = await db.payment_orders.find_one({"id": req.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("user_id") != user["id"]:
        raise HTTPException(403, "Order belongs to another user")
    if not _razorpay_verify_signature(req.order_id, req.payment_id, req.signature):
        raise HTTPException(400, "Payment signature verification failed")

    # Idempotency: a transaction already recorded for this payment_id means
    # credits were already granted — never grant twice.
    existing = await db.transactions.find_one(
        {"razorpay_payment_id": req.payment_id}, {"_id": 0}
    )
    if existing:
        w = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
        return {
            "success": True,
            "already_processed": True,
            "transaction_id": existing["id"],
            "balance": (w or {}).get("balance", 0),
        }

    plan = await _get_plan(req.plan_id)
    if not plan or plan.get("active") is False:
        raise HTTPException(404, "Plan not found or inactive")

    txn_id = str(uuid.uuid4())
    # Atomic credit grant. The unique sparse index on razorpay_payment_id makes
    # concurrent replays fail the insert instead of double-granting.
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"balance": plan["credits"]}, "$set": {"updated_at": now().isoformat()}},
        upsert=True,
    )
    try:
        await db.transactions.insert_one({
            "id": txn_id,
            "user_id": user["id"],
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "amount": plan["price"],
            "credits": plan["credits"],
            "status": "success",
            "provider": "razorpay",
            "razorpay_order_id": req.order_id,
            "razorpay_payment_id": req.payment_id,
            "created_at": now().isoformat(),
        })
    except Exception:
        # Insert failed (e.g. duplicate razorpay_payment_id race) — roll back
        # the credit grant so the user is never credited twice for one payment.
        await db.wallets.update_one(
            {"user_id": user["id"]},
            {"$inc": {"balance": -plan["credits"]}},
        )
        raise HTTPException(409, "Payment already processed")
    await db.payment_orders.update_one({"id": req.order_id}, {"$set": {"status": "paid"}})
    w = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    return {"success": True, "already_processed": False, "transaction_id": txn_id,
            "balance": w.get("balance", 0)}


@api.post("/payments/razorpay/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    """Razorpay webhook — verifies X-Razorpay-Signature over the RAW request body.

    Handles payment.captured with an idempotent credit grant. All events return
    200 so Razorpay does not retry forever; unknown events are no-ops.
    """
    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(
            503, "Webhook secret is not configured. Set RAZORPAY_WEBHOOK_SECRET."
        )
    if not x_razorpay_signature:
        raise HTTPException(400, "Missing signature header")
    raw = await request.body()
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, x_razorpay_signature):
        raise HTTPException(400, "Invalid webhook signature")
    try:
        data = json.loads(raw)
    except Exception:
        raise HTTPException(400, "Invalid webhook payload")

    event = data.get("event", "")
    if event != "payment.captured":
        return {"success": True, "handled": False}

    entity = (data.get("payload") or {}).get("payment") or {}
    payment_id = entity.get("id")
    order_id = entity.get("order_id")
    if not payment_id or not order_id:
        return {"success": True, "handled": False}

    # Idempotent grant — never credit the same payment twice.
    existing = await db.transactions.find_one(
        {"razorpay_payment_id": payment_id}, {"_id": 0}
    )
    if existing:
        return {"success": True, "handled": True, "already_processed": True}

    order = await db.payment_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        # Unknown order (e.g. created before this feature). Accept the event
        # silently and log — the client verify call is the authoritative path.
        logger.warning(f"[RAZORPAY] captured payment {payment_id} for unknown order {order_id}")
        return {"success": True, "handled": False}

    plan = await _get_plan(order.get("plan_id") or "")
    if not plan:
        logger.warning(f"[RAZORPAY] captured payment {payment_id} for missing plan")
        return {"success": True, "handled": False}

    txn_id = str(uuid.uuid4())
    await db.wallets.update_one(
        {"user_id": order["user_id"]},
        {"$inc": {"balance": plan["credits"]}, "$set": {"updated_at": now().isoformat()}},
        upsert=True,
    )
    try:
        await db.transactions.insert_one({
            "id": txn_id,
            "user_id": order["user_id"],
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "amount": plan["price"],
            "credits": plan["credits"],
            "status": "success",
            "provider": "razorpay",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "created_at": now().isoformat(),
        })
    except Exception:
        await db.wallets.update_one(
            {"user_id": order["user_id"]},
            {"$inc": {"balance": -plan["credits"]}},
        )
        raise HTTPException(409, "Payment already processed")
    await db.payment_orders.update_one({"id": order_id}, {"$set": {"status": "paid"}})
    return {"success": True, "handled": True}


@api.get("/transactions")
async def transactions(user=Depends(get_user)):
    items = await db.transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items


# ============================================================
# REFERRAL
# ============================================================

@api.get("/referral/me")
async def referral_me(user=Depends(get_user)):
    code = user.get("referral_code")
    if not code:
        code = await gen_referral_code()
        await db.users.update_one({"id": user["id"]}, {"$set": {"referral_code": code}})
    refs = await db.referrals.find({"referrer_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    total_reward = sum(r.get("reward", 0) for r in refs)
    return {
        "referral_code": code,
        "reward_per_referral": REFERRAL_REWARD,
        "total_referred": len(refs),
        "total_reward_credits": total_reward,
        "referrals": refs,
    }


# ============================================================
# COURT FAVOURITES
# ============================================================

@api.get("/favourites/courts")
async def get_fav_courts(user=Depends(get_user)):
    return {"favourite_courts": user.get("favourite_courts") or []}


@api.post("/favourites/courts/{court_id}")
async def add_fav_court(court_id: str, user=Depends(get_user)):
    if court_id not in _COURT_MAP:
        raise HTTPException(404, "Court not found")
    await db.users.update_one({"id": user["id"]}, {"$addToSet": {"favourite_courts": court_id}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"favourite_courts": u.get("favourite_courts") or []}


@api.delete("/favourites/courts/{court_id}")
async def remove_fav_court(court_id: str, user=Depends(get_user)):
    await db.users.update_one({"id": user["id"]}, {"$pull": {"favourite_courts": court_id}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"favourite_courts": u.get("favourite_courts") or []}



# ============================================================
# DRAFTS
# ============================================================

@api.post("/drafts")
async def save_draft(req: DraftSave, user=Depends(get_user)):
    t = next((x for x in TEMPLATES if x["id"] == req.template_id), None)
    template_name = t["name_en"] if t else req.template_id
    # Upsert
    key = {"user_id": user["id"], "template_id": req.template_id, "case_id": req.case_id}
    await db.drafts.update_one(
        key,
        {"$set": {
            **key,
            "language": req.language,
            "values": req.values,
            "template_name": template_name,
            "updated_at": now().isoformat(),
        }, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now().isoformat()}},
        upsert=True,
    )
    return {"success": True}


@api.get("/drafts")
async def list_drafts(user=Depends(get_user)):
    items = await db.drafts.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(50)
    return items


@api.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, user=Depends(get_user)):
    await db.drafts.delete_one({"id": draft_id, "user_id": user["id"]})
    return {"success": True}


# ============================================================
# GLOBAL SEARCH
# ============================================================

@api.get("/search")
async def global_search(q: str, user=Depends(get_user)):
    if len(q) > 200:
        raise HTTPException(400, "Search query too long (max 200 characters)")
    ql = q.lower().strip()
    # Templates
    tpls = []
    for t in TEMPLATES:
        aliases = [t["name_en"].lower(), t["name_gu"].lower()] + [a.lower() for a in t.get("aliases", [])]
        if any(ql in a for a in aliases):
            tpls.append(public_template(t))
    # Cases
    cases = await db.cases.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)
    matched_cases = [c for c in cases if
                     ql in (c.get("nickname") or "").lower()
                     or ql in (c.get("case_number") or "").lower()
                     or ql in (c.get("party_name") or "").lower()]
    return {"templates": tpls, "cases": matched_cases}


# ============================================================
# HEALTH
# ============================================================

@api.get("/")
async def root():
    return {"app": "NyaySetu Pro", "status": "ok", "version": "1.0.0"}


# ============================================================
# ADMIN PORTAL — MODELS
# ============================================================

class AdminLoginReq(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., max_length=200)

class FieldOptionDef(BaseModel):
    label_en: str = Field("", max_length=200)
    label_gu: str = Field("", max_length=200)
    value: str = Field(..., max_length=200)

class TemplateFieldDef(BaseModel):
    key: str = Field(..., max_length=50)
    label_en: str = Field(..., max_length=200)
    label_gu: str = Field(..., max_length=200)
    type: str = Field(default="text", max_length=30)  # text|textarea|number|date|select|radio|checkbox
    required: bool = True
    order: int = 0
    default_value: Optional[str] = None
    options: list[FieldOptionDef] = []
    validation: Optional[dict] = None

class AdminTemplateCreate(BaseModel):
    id: Optional[str] = Field(None, max_length=50)
    name_en: str = Field(..., max_length=200)
    name_gu: str = Field(..., max_length=200)
    category: str = Field(default="General", max_length=50)
    sub_category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    tags: list[str] = []
    aliases: list[str] = []
    case_types: list[str] = []
    courts: list[str] = []
    jurisdiction: Optional[str] = Field(None, max_length=200)
    fields: list[TemplateFieldDef] = []
    content_en: str = ""
    content_gu: str = ""
    settings: Optional[dict] = None

class AdminTemplateUpdate(BaseModel):
    name_en: Optional[str] = Field(None, max_length=200)
    name_gu: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=50)
    sub_category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[list[str]] = None
    aliases: Optional[list[str]] = None
    case_types: Optional[list[str]] = None
    courts: Optional[list[str]] = None
    jurisdiction: Optional[str] = Field(None, max_length=200)
    fields: Optional[list[TemplateFieldDef]] = None
    content_en: Optional[str] = None
    content_gu: Optional[str] = None
    settings: Optional[dict] = None

class AdminCloneReq(BaseModel):
    as_new_template: bool = False
    new_id: Optional[str] = Field(None, max_length=50)
    new_name_en: Optional[str] = Field(None, max_length=200)
    new_name_gu: Optional[str] = Field(None, max_length=200)

class AdminPreviewReq(BaseModel):
    values: Optional[dict] = {}
    content_en: Optional[str] = None
    content_gu: Optional[str] = None
    name_en: Optional[str] = None
    name_gu: Optional[str] = None
    fields: Optional[list[TemplateFieldDef]] = None
    settings: Optional[dict] = None


class WordImportAnalyzeReq(BaseModel):
    file_name: str = Field(..., max_length=200)
    content_base64: str = Field(..., max_length=5_000_000)


class WordImportCreateReq(BaseModel):
    id: Optional[str] = Field(None, max_length=50)
    name_en: str = Field(..., max_length=200)
    name_gu: str = Field(..., max_length=200)
    category: str = Field(default="General", max_length=50)
    sub_category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    tags: list[str] = []
    aliases: list[str] = []
    case_types: list[str] = []
    courts: list[str] = []
    jurisdiction: Optional[str] = Field(None, max_length=200)
    fields: list[TemplateFieldDef] = []
    content_en: str = ""
    content_gu: str = ""
    settings: Optional[dict] = None

class AdminUserStatusReq(BaseModel):
    active: bool = Field(..., description="True to enable the user, False to disable.")

class AdminPlanReq(BaseModel):
    name: str = Field(..., max_length=100)
    price: int = Field(..., ge=0, description="Price in INR")
    credits: int = Field(..., ge=1, description="Credits granted on purchase")
    popular: bool = False
    description: Optional[str] = Field(None, max_length=500)

class AdminPlanStatusReq(BaseModel):
    active: bool = Field(..., description="True to activate the plan, False to deactivate.")

class CatalogSectionDef(BaseModel):
    id: str = Field(..., max_length=50)
    label: str = Field(..., max_length=300)

class CatalogItemReq(BaseModel):
    en: str = Field(..., max_length=300)
    gu: str = Field("", max_length=300)
    cat: Optional[str] = Field(None, max_length=50)  # case types only
    district_id: Optional[str] = Field(None, max_length=50)  # courts / police stations
    sections: Optional[list[CatalogSectionDef]] = None  # laws only

class CatalogStatusReq(BaseModel):
    active: bool = Field(..., description="True to activate, False to deactivate.")

class SettingsUpdateReq(BaseModel):
    value: Union[int, str] = Field(..., description="New value for the setting")


# ============================================================
# ADMIN PORTAL — JWT & AUTH HELPERS
# ============================================================

ADMIN_TOKEN_EXPIRY_HOURS = 8


def make_admin_token(admin_id: str, email: str, role: str) -> str:
    """Create a JWT for admin users. Contains token_type='admin' to distinguish from lawyer JWTs."""
    payload = {
        "sub": admin_id,
        "email": email,
        "role": role,
        "token_type": "admin",
        "iat": int(now().timestamp()),
        "exp": int((now() + timedelta(hours=ADMIN_TOKEN_EXPIRY_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def get_admin(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency: validate admin JWT and return admin record.
    Rejects lawyer JWTs, expired tokens, and inactive admins."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing admin auth token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Admin token expired")
    except Exception:
        raise HTTPException(401, "Invalid admin token")
    # Reject non-admin tokens (e.g. lawyer JWTs)
    if payload.get("token_type") != "admin":
        raise HTTPException(401, "Not an admin token")
    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(401, "Invalid admin token")
    admin = await db.admin_users.find_one({"id": admin_id}, {"_id": 0})
    if not admin:
        raise HTTPException(401, "Admin not found")
    if not admin.get("active", False):
        raise HTTPException(401, "Admin account is disabled")
    return admin


async def require_super_admin(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency: like get_admin() but only allows super_admin role."""
    admin = await get_admin(authorization)
    if admin.get("role") != "super_admin":
        raise HTTPException(403, "Super admin access required")
    return admin


def admin_public(admin: dict) -> dict:
    """Return admin record without sensitive fields."""
    return {k: v for k, v in admin.items() if k not in ("_id", "password_hash")}


async def audit_log(*, admin: Optional[dict], action: str, target: Optional[str] = None,
                    metadata: Optional[dict] = None) -> None:
    """Record an admin action in the audit log. Never raises — auditing must not
    break the primary action it records."""
    entry = {
        "id": str(uuid.uuid4()),
        "admin_id": admin.get("id") if admin else None,
        "admin_email": admin.get("email") if admin else None,
        "admin_role": admin.get("role") if admin else None,
        "action": action,
        "target": target,
        "metadata": metadata or {},
        "timestamp": now().isoformat(),
    }
    try:
        await db.audit_logs.insert_one(entry)
    except Exception:
        logger.warning(f"audit_log insert failed for action={action}", exc_info=True)


# ============================================================
# ADMIN PORTAL — API ROUTER
# ============================================================

admin_api = APIRouter(prefix="/api/admin")


@admin_api.post("/auth/login")
async def admin_login(req: AdminLoginReq):
    """Admin login with email + password → JWT."""
    email = req.email.strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")
    if not rate_limit(f"admin_login:{email}", 5, 60):
        raise HTTPException(429, "Too many login attempts. Please try again later.")
    admin = await db.admin_users.find_one({"email": email}, {"_id": 0})
    if not admin:
        await audit_log(admin=None, action="admin_login_failed", target=email, metadata={"reason": "not_found"})
        raise HTTPException(401, "Invalid email or password")
    if not admin.get("active", False):
        await audit_log(admin=None, action="admin_login_failed", target=email, metadata={"reason": "disabled"})
        raise HTTPException(401, "Admin account is disabled")
    # Verify password
    stored_hash = admin.get("password_hash", "")
    if not stored_hash or not bcrypt.checkpw(req.password.encode("utf-8"), stored_hash.encode("utf-8")):
        await audit_log(admin=None, action="admin_login_failed", target=email, metadata={"reason": "bad_password"})
        raise HTTPException(401, "Invalid email or password")
    # Update last_login
    await db.admin_users.update_one(
        {"id": admin["id"]},
        {"$set": {"last_login": now().isoformat()}},
    )
    await audit_log(admin=admin, action="admin_login", target=admin["id"], metadata={"email": email})
    token = make_admin_token(admin["id"], admin["email"], admin["role"])
    return {"token": token, "admin": admin_public(admin)}


@admin_api.get("/auth/me")
async def admin_me(admin=Depends(get_admin)):
    """Return the currently authenticated admin's profile."""
    return admin_public(admin)


@admin_api.post("/auth/logout")
async def admin_logout(admin=Depends(get_admin)):
    """Logout is client-side (clear JWT). Server acknowledges."""
    return {"success": True, "message": "Logged out"}


@admin_api.get("/dashboard/stats")
async def admin_dashboard_stats(admin=Depends(get_admin)):
    """Aggregate real statistics from MongoDB for the admin dashboard."""
    # Total users
    total_users = await db.users.count_documents({})

    # Active users (users who have at least one case or application)
    # Simple proxy: users created in the last 30 days
    thirty_days_ago = (now() - timedelta(days=30)).isoformat()
    recent_users_count = await db.users.count_documents(
        {"created_at": {"$gte": thirty_days_ago}}
    )

    # Total cases
    total_cases = await db.cases.count_documents({})

    # Total documents generated (applications collection)
    total_documents = await db.applications.count_documents({})

    # Total credits consumed — sum of total_used across all wallets
    credits_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$total_used"}}}
    ]
    credits_result = await db.wallets.aggregate(credits_pipeline).to_list(1)
    total_credits_consumed = credits_result[0]["total"] if credits_result else 0

    # Total transactions
    total_transactions = await db.transactions.count_documents({})

    # Recent users (last 10)
    recent_users_cursor = db.users.find(
        {}, {"_id": 0, "id": 1, "name": 1, "mobile": 1, "email": 1, "created_at": 1, "provider": 1}
    ).sort("created_at", -1).limit(10)
    recent_users = await recent_users_cursor.to_list(10)

    # Recent applications (last 10)
    recent_apps_cursor = db.applications.find(
        {}, {"_id": 0, "id": 1, "user_id": 1, "template_name": 1, "language": 1, "format": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10)
    recent_applications = await recent_apps_cursor.to_list(10)

    return {
        "total_users": total_users,
        "recent_users_30d": recent_users_count,
        "total_cases": total_cases,
        "total_documents_generated": total_documents,
        "total_credits_consumed": total_credits_consumed,
        "total_transactions": total_transactions,
        "recent_users": recent_users,
        "recent_applications": recent_applications,
    }

@admin_api.get("/users")
async def admin_list_users(q: Optional[str] = None, limit: int = 50, offset: int = 0,
                          admin=Depends(get_admin)):
    """List platform users with optional search (name/mobile/email/id) and pagination."""
    query = {}
    if q:
        q_re = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [
            {"name": q_re},
            {"mobile": q_re},
            {"email": q_re},
            {"id": q_re},
        ]
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    cursor = db.users.find(query, {"_id": 0, "password_hash": 0})\
        .sort("created_at", -1).skip(offset).limit(limit)
    items = await cursor.to_list(limit)
    total = await db.users.count_documents(query)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@admin_api.get("/users/{user_id}")
async def admin_get_user(user_id: str, admin=Depends(get_admin)):
    """Full user detail: profile, wallet, and activity counts."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(404, "User not found")
    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    cases_count = await db.cases.count_documents({"user_id": user_id})
    applications_count = await db.applications.count_documents({"user_id": user_id})
    transactions_count = await db.transactions.count_documents({"user_id": user_id})
    return {
        "user": user,
        "wallet": wallet,
        "cases_count": cases_count,
        "applications_count": applications_count,
        "transactions_count": transactions_count,
    }


@admin_api.patch("/users/{user_id}/status")
async def admin_set_user_status(user_id: str, req: AdminUserStatusReq,
                                admin=Depends(require_super_admin)):
    """Enable/disable a user account (super admin only). Disabled users are
    rejected at login and at every authenticated endpoint."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    ts = now().isoformat()
    updates = {"active": req.active, "updated_at": ts}
    updates["enabled_at" if req.active else "disabled_at"] = ts
    await db.users.update_one({"id": user_id}, {"$set": updates})
    await audit_log(admin=admin, action="user_status_update", target=user_id,
                    metadata={"active": req.active,
                              "name": user.get("name"),
                              "mobile": user.get("mobile"),
                              "email": user.get("email")})
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "user": updated}


@admin_api.get("/audit-logs")
async def admin_audit_logs(limit: int = 50, offset: int = 0,
                           action: Optional[str] = None, admin_id: Optional[str] = None,
                           admin=Depends(get_admin)):
    """List recorded admin actions, newest first, with optional filters."""
    query = {}
    if action:
        query["action"] = action
    if admin_id:
        query["admin_id"] = admin_id
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(offset).limit(limit)
    items = await cursor.to_list(limit)
    total = await db.audit_logs.count_documents(query)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def _admin_owner_map(user_ids: set) -> dict:
    """Batch-fetch public user info for a set of case owner ids."""
    if not user_ids:
        return {}
    cursor = db.users.find(
        {"id": {"$in": list(user_ids)}},
        {"_id": 0, "id": 1, "name": 1, "mobile": 1, "email": 1, "provider": 1, "active": 1},
    )
    return {u["id"]: u for u in await cursor.to_list(2000)}


@admin_api.get("/cases")
async def admin_list_cases(q: Optional[str] = None, status: str = "all",
                          category: Optional[str] = None, user_id: Optional[str] = None,
                          limit: int = 50, offset: int = 0,
                          admin=Depends(get_admin)):
    """List all cases with search, filters and owner info (admin visibility)."""
    query: dict = {}
    if status != "all":
        if status == "active":
            query["status"] = {"$ne": "archived"}
        else:
            query["status"] = status
    if user_id:
        query["user_id"] = user_id
    if q:
        q_re = re.compile(re.escape(q), re.IGNORECASE)
        query["$or"] = [
            {"nickname": q_re},
            {"case_number": q_re},
            {"party_name": q_re},
            {"opposite_party": q_re},
            {"client_name": q_re},
            {"client_mobile": q_re},
            {"case_type_custom": q_re},
            {"court_custom": q_re},
        ]
    cursor = db.cases.find(query, {"_id": 0}).sort("updated_at", -1).limit(2000)
    items = await cursor.to_list(2000)
    items = [enrich_case(c) for c in items]
    if category and category != "All":
        items = [c for c in items if c.get("category") == category]
    total = len(items)
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    page = items[offset:offset + limit]
    owner_ids = {c.get("user_id") for c in page if c.get("user_id")}
    owners = await _admin_owner_map(owner_ids)
    for c in page:
        c["owner"] = owners.get(c.get("user_id"))
    return {"items": page, "total": total, "limit": limit, "offset": offset}


@admin_api.get("/cases/{case_id}")
async def admin_get_case(case_id: str, admin=Depends(get_admin)):
    """Full admin case detail: enriched case, owner profile, and generated documents."""
    c = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Case not found")
    c = enrich_case(c)
    owner = None
    if c.get("user_id"):
        owner = await db.users.find_one(
            {"id": c["user_id"]},
            {"_id": 0, "id": 1, "name": 1, "mobile": 1, "email": 1, "provider": 1, "active": 1,
             "bar_council_no": 1, "state": 1, "district": 1, "court": 1, "created_at": 1},
        )
    applications = await db.applications.find(
        {"case_id": case_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return {"case": c, "owner": owner, "applications": applications}


@admin_api.post("/cases/{case_id}/archive")
async def admin_archive_case(case_id: str, admin=Depends(get_admin)):
    """Admin archive of a case (preserves data, hides from active lawyer list)."""
    r = await db.cases.update_one(
        {"id": case_id},
        {"$set": {"status": "archived", "updated_at": now().isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    await audit_log(admin=admin, action="case_archive", target=case_id)
    return {"success": True, "status": "archived"}


@admin_api.post("/cases/{case_id}/restore")
async def admin_restore_case(case_id: str, admin=Depends(get_admin)):
    """Admin restore of an archived case back to active."""
    r = await db.cases.update_one(
        {"id": case_id},
        {"$set": {"status": "active", "updated_at": now().isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    await audit_log(admin=admin, action="case_restore", target=case_id)
    return {"success": True, "status": "active"}

@admin_api.get("/plans")
async def admin_list_plans(admin=Depends(get_admin)):
    """List all plans (including inactive) for admin management."""
    items = await _load_plans()
    items = sorted(items, key=lambda p: p.get("price") or 0)
    return [{**p, "per_template": round((p.get("price") or 0) / (p.get("credits") or 1), 2),
             "active": p.get("active") is not False} for p in items]


@admin_api.post("/plans")
async def admin_create_plan(req: AdminPlanReq, admin=Depends(require_super_admin)):
    """Create a new plan (super admin only)."""
    plan_id = "plan_" + str(int(now().timestamp()))
    existing = await db.plans.find_one({"id": plan_id})
    if existing:
        raise HTTPException(409, "Plan id collision — retry")
    ts = now().isoformat()
    doc = {
        "id": plan_id,
        "name": req.name,
        "price": req.price,
        "credits": req.credits,
        "popular": req.popular,
        "description": req.description,
        "active": True,
        "created_by": admin["id"],
        "updated_by": admin["id"],
        "created_at": ts,
        "updated_at": ts,
    }
    await db.plans.insert_one(doc.copy())
    await audit_log(admin=admin, action="plan_create", target=plan_id,
                    metadata={"name": req.name, "price": req.price, "credits": req.credits})
    return {"success": True, "plan": _plan_public(doc)}


@admin_api.put("/plans/{plan_id}")
async def admin_update_plan(plan_id: str, req: AdminPlanReq, admin=Depends(require_super_admin)):
    """Update plan name/price/credits (super admin only)."""
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Plan not found")
    updates = {
        "name": req.name,
        "price": req.price,
        "credits": req.credits,
        "popular": req.popular,
        "description": req.description,
        "updated_by": admin["id"],
        "updated_at": now().isoformat(),
    }
    await db.plans.update_one({"id": plan_id}, {"$set": updates})
    await audit_log(admin=admin, action="plan_update", target=plan_id,
                    metadata={"name": req.name, "price": req.price, "credits": req.credits})
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return {"success": True, "plan": _plan_public(updated)}


@admin_api.post("/plans/{plan_id}/status")
async def admin_set_plan_status(plan_id: str, req: AdminPlanStatusReq,
                                admin=Depends(require_super_admin)):
    """Activate/deactivate a plan (super admin only). Inactive plans are hidden
    from the lawyer catalog and cannot be purchased."""
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Plan not found")
    await db.plans.update_one(
        {"id": plan_id},
        {"$set": {"active": req.active, "updated_by": admin["id"], "updated_at": now().isoformat()}},
    )
    await audit_log(admin=admin, action="plan_status_update", target=plan_id,
                    metadata={"active": req.active, "name": existing.get("name")})
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return {"success": True, "plan": _plan_public(updated)}

def _catalog_item_id(en: str) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", en.lower().strip().replace(" ", "_"))[:40]
    return f"{base}_{uuid.uuid4().hex[:6]}"


def _build_catalog_doc(kind: str, req: CatalogItemReq, admin: dict, item_id: str) -> dict:
    ts = now().isoformat()
    doc = {
        "id": item_id,
        "en": req.en.strip(),
        "gu": req.gu.strip() or req.en.strip(),
        "active": True,
        "created_by": admin["id"],
        "updated_by": admin["id"],
        "created_at": ts,
        "updated_at": ts,
    }
    if kind == "case-types":
        doc["cat"] = req.cat or "Other"
    elif kind in ("courts", "police-stations", "talukas"):
        doc["district_id"] = req.district_id or "generic"
    elif kind == "laws":
        doc["sections"] = [s.model_dump() for s in (req.sections or [])]
    return doc


@admin_api.get("/catalog/{kind}")
async def admin_list_catalog(kind: str, admin=Depends(get_admin)):
    """List all catalog entries (including inactive) for a catalog kind."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    items = await _load_catalog(kind)
    return [{**i, "active": i.get("active") is not False} for i in items]


@admin_api.post("/catalog/{kind}")
async def admin_create_catalog_item(kind: str, req: CatalogItemReq,
                                     admin=Depends(require_super_admin)):
    """Create a catalog entry (super admin only). Immediately usable by lawyers."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    coll = _CATALOG_KINDS[kind][0]
    item_id = _catalog_item_id(req.en)
    doc = _build_catalog_doc(kind, req, admin, item_id)
    await db[coll].insert_one(doc.copy())
    await _refresh_catalog_maps()
    await audit_log(admin=admin, action="catalog_create", target=f"{kind}:{item_id}",
                    metadata={"kind": kind, "en": req.en, "id": item_id})
    return {"success": True, "item": {**doc, "active": True}}


@admin_api.put("/catalog/{kind}/{item_id}")
async def admin_update_catalog_item(kind: str, item_id: str, req: CatalogItemReq,
                                    admin=Depends(require_super_admin)):
    """Update labels/attributes of a catalog entry (super admin only)."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    coll = _CATALOG_KINDS[kind][0]
    existing = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Catalog entry not found")
    updates = {
        "en": req.en.strip(),
        "gu": req.gu.strip() or req.en.strip(),
        "updated_by": admin["id"],
        "updated_at": now().isoformat(),
    }
    if kind == "case-types":
        updates["cat"] = req.cat or "Other"
    elif kind in ("courts", "police-stations"):
        updates["district_id"] = req.district_id or "generic"
    elif kind == "laws" and req.sections is not None:
        updates["sections"] = [s.model_dump() for s in req.sections]
    await db[coll].update_one({"id": item_id}, {"$set": updates})
    await _refresh_catalog_maps()
    await audit_log(admin=admin, action="catalog_update", target=f"{kind}:{item_id}",
                    metadata={"kind": kind, "en": req.en})
    updated = await db[coll].find_one({"id": item_id}, {"_id": 0})
    return {"success": True, "item": {**updated, "active": updated.get("active") is not False}}


@admin_api.post("/catalog/{kind}/{item_id}/status")
async def admin_set_catalog_status(kind: str, item_id: str, req: CatalogStatusReq,
                                   admin=Depends(require_super_admin)):
    """Activate/deactivate a catalog entry (super admin only). Deactivated entries
    stay valid for existing cases (labels + validation preserved) but are hidden
    from new lawyer selections."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    coll = _CATALOG_KINDS[kind][0]
    existing = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Catalog entry not found")
    await db[coll].update_one(
        {"id": item_id},
        {"$set": {"active": req.active, "updated_by": admin["id"], "updated_at": now().isoformat()}},
    )
    await _refresh_catalog_maps()
    await audit_log(admin=admin, action="catalog_status_update", target=f"{kind}:{item_id}",
                    metadata={"kind": kind, "active": req.active, "en": existing.get("en")})
    updated = await db[coll].find_one({"id": item_id}, {"_id": 0})
    return {"success": True, "item": {**updated, "active": updated.get("active") is not False}}

def _validate_setting_value(key: str, value) -> None:
    """Validate a setting value against its schema. Raises HTTPException(422) on invalid."""
    expected = _setting_type(key)
    if expected is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise HTTPException(422, f"Setting '{key}' requires an integer value")
        ranges = {
            "signup_credits": (0, 1000),
            "otp_ttl_seconds": (60, 86400),
            "otp_resend_cooldown_seconds": (10, 3600),
            "otp_max_attempts": (1, 10),
        }
        lo, hi = ranges.get(key, (0, 10 ** 9))
        if not (lo <= value <= hi):
            raise HTTPException(422, f"Setting '{key}' must be between {lo} and {hi}")
    else:
        if not isinstance(value, str):
            raise HTTPException(422, f"Setting '{key}' requires a string value")
        if key == "default_page_size" and value.upper() not in ("A4", "LEGAL"):
            raise HTTPException(422, "default_page_size must be 'A4' or 'Legal'")


@admin_api.get("/settings")
async def admin_list_settings(admin=Depends(get_admin)):
    """List all operational settings with current values, defaults and types."""
    items = []
    for key in _SETTING_DEFAULTS:
        items.append({
            "key": key,
            "value": await _get_setting(key),
            "default": _SETTING_DEFAULTS[key],
            "description": _SETTING_DESCRIPTIONS[key],
            "type": "int" if _setting_type(key) is int else "str",
        })
    return items


@admin_api.put("/settings/{key}")
async def admin_update_setting(key: str, req: SettingsUpdateReq,
                               admin=Depends(require_super_admin)):
    """Update an operational setting (super admin only). Applied immediately."""
    if key not in _SETTING_DEFAULTS:
        raise HTTPException(404, "Unknown setting")
    value = req.value
    if key == "default_page_size":
        value = str(value).upper()
    _validate_setting_value(key, value)
    await db.settings.update_one(
        {"key": key},
        {"$set": {"value": value, "updated_by": admin["id"], "updated_at": now().isoformat()}},
        upsert=True,
    )
    await audit_log(admin=admin, action="settings_update", target=key, metadata={"value": value})
    return {"success": True, "key": key, "value": value,
            "default": _SETTING_DEFAULTS[key], "description": _SETTING_DESCRIPTIONS[key],
            "type": "int" if _setting_type(key) is int else "str"}


def _validate_placeholders(content_en: str, content_gu: str, template_fields: list) -> dict:
    """Validate that all placeholders in content match known fields.
    Returns {valid: bool, unknown: [...], unused: [...], duplicate_keys: [...]}. """
    declared_keys = {f["key"] for f in template_fields if "key" in f} | _AUTO_FILL_FIELDS
    found_en = set(re.findall(r"\{\{(\w+)\}\}", content_en or ""))
    found_gu = set(re.findall(r"\{\{(\w+)\}\}", content_gu or ""))
    all_found = found_en | found_gu
    unknown = all_found - declared_keys
    
    # Check duplicate field keys
    field_keys = [f["key"] for f in template_fields if "key" in f]
    seen = set()
    duplicate_keys = set()
    for k in field_keys:
        if k in seen:
            duplicate_keys.add(k)
        seen.add(k)
        
    unused = set(field_keys) - all_found
    is_valid = len(unknown) == 0 and len(duplicate_keys) == 0
    return {
        "valid": is_valid,
        "unknown": sorted(unknown),
        "unused": sorted(unused),
        "duplicate_keys": sorted(duplicate_keys),
    }


@admin_api.post("/case-forms/{case_type_id}")
async def admin_save_case_form(case_type_id: str, req: CaseFormConfigReq, admin=Depends(get_admin)):
    """Admin endpoint to create/update dynamic case form schema for a case type."""
    doc = {
        "case_type_id": case_type_id,
        "name_en": req.name_en,
        "name_gu": req.name_gu,
        "category": req.category,
        "fields": [f.model_dump() for f in req.fields],
        "updated_at": now().isoformat(),
        "updated_by": admin["id"],
    }
    await db.case_forms.update_one({"case_type_id": case_type_id}, {"$set": doc}, upsert=True)
    await audit_log(admin=admin, action="case_form_save", target=case_type_id,
                    metadata={"name_en": req.name_en, "name_gu": req.name_gu, "field_count": len(req.fields)})
    res = await db.case_forms.find_one({"case_type_id": case_type_id}, {"_id": 0})
    return res


@admin_api.get("/templates")
async def admin_list_templates(
    status: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    admin=Depends(get_admin),
):
    """List all templates (all statuses) for admin management.

    Merges DB templates with seed templates so EVERY template visible in the
    Lawyer App is manageable here: DB templates override seeds by ID (admin
    edits are never overwritten); seeds not yet in the DB appear as
    status="seed". The merge is idempotent — no writes, no duplicates."""
    db_templates = await db.templates.find({}, {"_id": 0}).sort("updated_at", -1).to_list(500)
    db_by_id = {t["id"]: t for t in db_templates}
    seed_ids = {t["id"] for t in TEMPLATES}

    merged = []
    for seed_t in TEMPLATES:
        if seed_t["id"] in db_by_id:
            merged.append({**db_by_id[seed_t["id"]], "is_seed_template": True})
        else:
            merged.append({
                **seed_t,
                "status": "seed",
                "version": 0,
                "source": "seed",
                "locked": False,
                "is_seed_template": True,
            })
    for db_t in db_templates:
        if db_t["id"] not in seed_ids:
            merged.append({**db_t, "is_seed_template": False})

    if status:
        merged = [t for t in merged if t.get("status") == status]
    if category:
        merged = [t for t in merged if t.get("category", "").lower() == category.lower()]
    if q:
        ql = q.lower().strip()
        merged = [
            t for t in merged
            if ql in t.get("name_en", "").lower()
            or ql in t.get("name_gu", "").lower()
            or ql in t.get("id", "").lower()
        ]
    return merged


@admin_api.get("/templates/{template_id}")
async def admin_get_template(template_id: str, admin=Depends(get_admin)):
    """Get full template details for admin editing."""
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        t = next((x for x in TEMPLATES if x["id"] == template_id), None)
        if t:
            # Merge (never replace) the seed's own settings so admin-configured
            # values like settings.page_size survive the fallback view.
            t = {
                **t,
                "status": "seed",
                "version": 0,
                "source": "seed",
                "locked": False,
                "settings": {
                    "margin_top_cm": 2.5,
                    "margin_bottom_cm": 2.5,
                    "margin_left_cm": 2.5,
                    "margin_right_cm": 2.5,
                    "gujarati_font": "LohitGujarati",
                    "english_font": "Times-Roman",
                    "body_size": 12,
                    "heading_size": 13,
                    "line_spacing": 18,
                    "paragraph_spacing": 6,
                    "page_size": "A4",
                    **((t.get("settings") or {})),
                },
            }
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@admin_api.post("/templates")
async def admin_create_template(req: AdminTemplateCreate, admin=Depends(get_admin)):
    """Create a new template as draft."""
    _validate_template_settings(req.settings)
    template_id = req.id or re.sub(r"[^a-z0-9_]", "_", req.name_en.lower().strip().replace(" ", "_"))[:50]
    existing = await db.templates.find_one({"id": template_id})
    if existing:
        raise HTTPException(409, f"Template with id '{template_id}' already exists")
    ts = now().isoformat()
    template_doc = {
        "id": template_id,
        "slug": template_id,
        "name_en": req.name_en,
        "name_gu": req.name_gu,
        "category": req.category,
        "sub_category": req.sub_category,
        "description": req.description,
        "tags": req.tags,
        "aliases": req.aliases,
        "case_types": req.case_types,
        "courts": req.courts,
        "jurisdiction": req.jurisdiction,
        "fields": [f.model_dump() for f in req.fields],
        "content_en": req.content_en,
        "content_gu": req.content_gu,
        "settings": req.settings or {
            "margin_top_cm": 2.5,
            "margin_bottom_cm": 2.5,
            "margin_left_cm": 2.5,
            "margin_right_cm": 2.5,
            "gujarati_font": "LohitGujarati",
            "english_font": "Times-Roman",
            "body_size": 12,
            "heading_size": 13,
            "line_spacing": 18,
            "paragraph_spacing": 6,
            "page_size": "A4",
        },
        "status": "draft",
        "version": 1,
        "locked": False,
        "source": "admin_created",
        "created_by": admin["id"],
        "updated_by": admin["id"],
        "created_at": ts,
        "updated_at": ts,
        "published_at": None,
    }
    await db.templates.insert_one(template_doc.copy())
    await audit_log(admin=admin, action="template_create", target=template_id,
                    metadata={"name_en": req.name_en, "category": req.category})
    template_doc.pop("_id", None)
    return template_doc


@admin_api.post("/templates/import-word/analyze")
async def admin_import_word_analyze(req: WordImportAnalyzeReq, admin=Depends(require_super_admin)):
    """Analyze an uploaded .docx and propose a template definition (fields, draft, settings).

    The uploaded Word document is the source of truth: page size, margins, fonts,
    formatting and wording are extracted deterministically. Nothing is published
    here — the admin reviews the extracted fields and explicitly creates the draft.
    """
    try:
        data = decode_upload(req.file_name, req.content_base64)
        if req.file_name.lower().endswith(".odt"):
            analysis = analyze_odt(data, req.file_name)
        else:
            analysis = analyze_docx(data, req.file_name)
    except (DocxImportError, OdtImportError) as e:
        raise HTTPException(400, str(e))
    await audit_log(admin=admin, action="template_import_analyze", target=req.file_name,
                    metadata={"page_size": analysis["page_size"], "fields": len(analysis["fields"]),
                              "unmapped": len(analysis["unmapped"])})
    return analysis


@admin_api.post("/templates/import-word")
async def admin_import_word_create(req: WordImportCreateReq, admin=Depends(require_super_admin)):
    """Create a draft template from an admin-reviewed Word import.

    The client sends back the reviewed field configuration plus the analyzed
    content/settings. Creates a DRAFT only — publishing is always an explicit
    admin action. source="imported" so the record is clearly identifiable.
    """
    _validate_template_settings(req.settings)
    template_id = req.id or re.sub(r"[^a-z0-9_]", "_", req.name_en.lower().strip().replace(" ", "_"))[:50]
    existing = await db.templates.find_one({"id": template_id})
    if existing:
        raise HTTPException(409, f"Template with id '{template_id}' already exists. Rename it or delete the existing draft first.")

    validation = _validate_placeholders(req.content_en, req.content_gu, [f.model_dump() for f in req.fields])
    if not validation["valid"]:
        errors = []
        if validation.get("unknown"):
            errors.append(f"unknown placeholders: {', '.join(validation['unknown'])}")
        if validation.get("duplicate_keys"):
            errors.append(f"duplicate field keys: {', '.join(validation['duplicate_keys'])}")
        raise HTTPException(
            400,
            "Cannot create template: " + "; ".join(errors)
            + ". Add matching fields for each placeholder before saving the draft."
        )

    ts = now().isoformat()
    template_doc = {
        "id": template_id,
        "slug": template_id,
        "name_en": req.name_en,
        "name_gu": req.name_gu,
        "category": req.category,
        "sub_category": req.sub_category,
        "description": req.description,
        "tags": req.tags,
        "aliases": req.aliases,
        "case_types": req.case_types,
        "courts": req.courts,
        "jurisdiction": req.jurisdiction,
        "fields": [f.model_dump() for f in req.fields],
        "content_en": req.content_en or "",
        "content_gu": req.content_gu or "",
        "settings": req.settings or {
            "margin_top_cm": 2.0,
            "margin_bottom_cm": 2.0,
            "margin_left_cm": 2.5,
            "margin_right_cm": 2.5,
            "gujarati_font": "LohitGujarati",
            "english_font": "Times-Roman",
            "body_size": 13,
            "heading_size": 14,
            "line_spacing": 19.5,
            "paragraph_spacing": 6,
            "page_size": "A4",
        },
        "status": "draft",
        "version": 1,
        "locked": False,
        "source": "imported",
        "created_by": admin["id"],
        "updated_by": admin["id"],
        "created_at": ts,
        "updated_at": ts,
        "published_at": None,
    }
    await db.templates.insert_one(template_doc.copy())
    await audit_log(admin=admin, action="template_import", target=template_id,
                    metadata={"name_en": req.name_en, "category": req.category,
                              "fields": len(req.fields), "source": "word_docx"})
    template_doc.pop("_id", None)
    return template_doc


@admin_api.put("/templates/{template_id}")
async def admin_update_template(template_id: str, req: AdminTemplateUpdate, admin=Depends(get_admin)):
    """Update a draft template. Published/locked templates cannot be directly modified."""
    _validate_template_settings(req.settings)
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        seed_t = next((x for x in TEMPLATES if x["id"] == template_id), None)
        if seed_t:
            # Seed template being edited for first time -> auto-initialize as draft in DB
            t = {
                **seed_t,
                "status": "draft",
                "version": 1,
                "locked": False,
                "source": "admin_edited",
            }
            await db.templates.insert_one({**t, "created_at": now().isoformat(), "updated_at": now().isoformat()})
        else:
            raise HTTPException(404, "Template not found")
    
    # Status is the authoritative lock: only PUBLISHED versions are immutable
    # (edits go through clone -> new draft). The `locked` flag is set at publish
    # as a marker; it must never lock a draft — a stale `locked: True` on a
    # draft (e.g. a malformed legacy record) would otherwise make it permanently
    # uneditable. Matches the admin editor's isLocked (status-based).
    if t.get("status") == "published":
        raise HTTPException(403, "Published templates cannot be directly modified. Clone or edit to create a new draft version.")

    updates = {}
    for key in ["name_en", "name_gu", "category", "sub_category", "description", "tags", "aliases", "case_types", "courts", "jurisdiction", "content_en", "content_gu", "settings"]:
        val = getattr(req, key, None)
        if val is not None:
            updates[key] = val
    if req.fields is not None:
        updates["fields"] = [f.model_dump() for f in req.fields]
    if updates:
        updates["updated_by"] = admin["id"]
        updates["updated_at"] = now().isoformat()
        updates["source"] = "admin_edited" if t.get("source") != "admin_created" else t["source"]
        # A draft is never locked — self-heal a stale lock marker so the admin
        # lock icon (published-only) stays truthful.
        updates["locked"] = False
        await db.templates.update_one({"id": template_id}, {"$set": updates})
        await audit_log(admin=admin, action="template_update", target=template_id,
                        metadata={"field_count": len(updates.get("fields", t.get("fields", [])))})
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return updated


@admin_api.post("/templates/{template_id}/publish")
async def admin_publish_template(template_id: str, admin=Depends(get_admin)):
    """Publish a draft template (makes it visible to lawyers)."""
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        seed_t = next((x for x in TEMPLATES if x["id"] == template_id), None)
        if seed_t:
            t = {**seed_t, "status": "draft", "version": 1, "locked": False, "source": "admin_edited"}
            await db.templates.insert_one({**t, "created_at": now().isoformat(), "updated_at": now().isoformat()})
        else:
            raise HTTPException(404, "Template not found")
            
    if t.get("status") == "published" and t.get("locked"):
        raise HTTPException(400, "Template is already published and locked")

    # Guard: malformed/incomplete DB records (e.g. the partial documents created
    # by the pre-24d0936 seed-clone bug) must fail with a readable error, never
    # an unhandled 500 (which surfaces as 'Failed to fetch' in the admin UI).
    # Names are mandatory in both languages; at least one language's content
    # must be present (Gujarati-only templates legitimately have empty content_en).
    missing = [k for k in ("name_en", "name_gu") if not str(t.get(k) or "").strip()]
    has_content = bool(str(t.get("content_en") or "").strip() or str(t.get("content_gu") or "").strip())
    if not has_content:
        missing.append("content (content_en/content_gu)")
    if missing:
        raise HTTPException(
            400,
            "Cannot publish: this template record is incomplete (missing: "
            + ", ".join(missing)
            + "). It is a malformed/partial record and cannot be published. "
            + "If it shadows a seed template, remove it with the 'Remove Shadow Draft' action "
            + "and re-edit the seed template instead.",
        )
    if not isinstance(t.get("fields"), list):
        raise HTTPException(
            400,
            "Cannot publish: the template's field list is missing or invalid. "
            + "This record is malformed; remove it and recreate the template draft.",
        )
        
    validation = _validate_placeholders(
        t.get("content_en", ""), t.get("content_gu", ""), t.get("fields", [])
    )
    if not validation["valid"]:
        errors = []
        if validation.get("unknown"):
            errors.append(f"unknown placeholders: {', '.join(validation['unknown'])}")
        if validation.get("duplicate_keys"):
            errors.append(f"duplicate field keys: {', '.join(validation['duplicate_keys'])}")
        raise HTTPException(
            400,
            f"Cannot publish: {'; '.join(errors)}. Please resolve these issues before publishing."
        )

    ts = now().isoformat()
    current_version = t.get("version", 1) or 1
    version_doc = {
        "id": str(uuid.uuid4()),
        "template_id": template_id,
        "version": current_version,
        "name_en": t["name_en"],
        "name_gu": t["name_gu"],
        "category": t.get("category", "General"),
        "sub_category": t.get("sub_category"),
        "description": t.get("description"),
        "tags": t.get("tags", []),
        "aliases": t.get("aliases", []),
        "case_types": t.get("case_types", []),
        "courts": t.get("courts", []),
        "jurisdiction": t.get("jurisdiction"),
        "fields": t.get("fields", []),
        "content_en": t.get("content_en", ""),
        "content_gu": t.get("content_gu", ""),
        "settings": t.get("settings"),
        "created_by": admin["id"],
        "created_at": ts,
    }
    await db.template_versions.update_one(
        {"template_id": template_id, "version": current_version},
        {"$set": version_doc},
        upsert=True,
    )
    await db.templates.update_one(
        {"id": template_id},
        {"$set": {
            "status": "published",
            "version": current_version,
            "locked": True,
            "published_at": ts,
            "updated_at": ts,
            "updated_by": admin["id"],
        }},
    )
    await audit_log(admin=admin, action="template_publish", target=template_id,
                    metadata={"version": current_version})
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "template": updated, "validation": validation}


@admin_api.post("/templates/{template_id}/archive")
async def admin_archive_template(template_id: str, admin=Depends(get_admin)):
    """Archive a template (hides from lawyers, preserves in DB)."""
    t = await db.templates.find_one({"id": template_id})
    if not t:
        raise HTTPException(404, "Template not found")
    await db.templates.update_one(
        {"id": template_id},
        {"$set": {"status": "archived", "updated_at": now().isoformat(), "updated_by": admin["id"]}},
    )
    await audit_log(admin=admin, action="template_archive", target=template_id)
    return {"success": True, "status": "archived"}


@admin_api.delete("/templates/{template_id}/draft")
async def admin_remove_shadow_draft(template_id: str, confirm: Optional[bool] = None,
                                    admin=Depends(require_super_admin)):
    """Remove an obsolete draft/archived DB record that is shadowing a seed template.

    A seed template becomes shadowed when an admin branches it for editing: the
    version-branch clone materialises a draft/archived record under the SAME id,
    which hides the seed from the lawyer-facing template list. This endpoint
    removes ONLY that shadow record so the (correct) seed template becomes
    visible again.

    Safety rules (super_admin only):
      - 404 if no DB record exists (idempotent — already-removed = clean 404)
      - 409 for published templates (published versions are never deleted)
      - 409 for ids with no seed counterpart (real admin-created templates are
        never touched)
      - archived shadows require explicit confirm=true before removal
      - every removal is audit-logged as template_shadow_draft_delete
    """
    rec = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Shadow record not found")
    seed = next((s for s in TEMPLATES if s["id"] == template_id), None)
    status = rec.get("status")
    if status == "published":
        raise HTTPException(409, "Published templates cannot be removed — only draft/archived shadow records of seed templates")
    if seed is None:
        raise HTTPException(409, "This template has no seed counterpart — it is a real template, not a shadow record")
    if status not in ("draft", "archived"):
        raise HTTPException(409, f"Cannot remove template in status '{status}' — only draft/archived shadows")
    if status == "archived" and not confirm:
        raise HTTPException(400, "Archived shadow removal requires explicit confirmation (confirm=true)")
    result = await db.templates.delete_one({"id": template_id, "status": status})
    if result.deleted_count == 0:
        raise HTTPException(404, "Shadow record not found")
    await audit_log(admin=admin, action="template_shadow_draft_delete", target=template_id,
                    metadata={"removed_status": status, "seed_id": template_id,
                              "seed_name_gu": seed.get("name_gu")})
    return {"success": True, "removed_status": status,
            "message": f"Removed the {status} shadow record for seed template '{template_id}'. The seed template is visible to lawyers again."}


@admin_api.post("/templates/{template_id}/clone")
async def admin_clone_template(template_id: str, req: Optional[AdminCloneReq] = None, admin=Depends(get_admin)):
    """Clone a template:
    1. If req.as_new_template=True -> creates a completely new separate template.
    2. Otherwise -> branches published/archived/seed template into an editable new Draft version (version N+1)."""
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        seed_t = next((x for x in TEMPLATES if x["id"] == template_id), None)
        if not seed_t:
            raise HTTPException(404, "Template not found")
        t = {**seed_t, "version": 0, "source": "seed"}

    ts = now().isoformat()
    as_new = req.as_new_template if req else False

    if as_new:
        # Create a separate, new template
        new_id = (req.new_id if req and req.new_id else None) or f"{template_id}_copy_{int(now().timestamp())}"
        new_name_en = (req.new_name_en if req and req.new_name_en else None) or f"{t.get('name_en', '')} (Copy)"
        new_name_gu = (req.new_name_gu if req and req.new_name_gu else None) or f"{t.get('name_gu', '')} (નકલ)"
        
        new_doc = {
            "id": new_id,
            "slug": new_id,
            "name_en": new_name_en,
            "name_gu": new_name_gu,
            "category": t.get("category", "General"),
            "sub_category": t.get("sub_category"),
            "description": t.get("description"),
            "tags": t.get("tags", []),
            "aliases": t.get("aliases", []),
            "case_types": t.get("case_types", []),
            "courts": t.get("courts", []),
            "jurisdiction": t.get("jurisdiction"),
            "fields": t.get("fields", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "settings": t.get("settings"),
            "status": "draft",
            "version": 1,
            "locked": False,
            "source": "admin_created",
            "created_by": admin["id"],
            "updated_by": admin["id"],
            "created_at": ts,
            "updated_at": ts,
            "published_at": None,
        }
        await db.templates.insert_one(new_doc.copy())
        await audit_log(admin=admin, action="template_clone", target=template_id,
                        metadata={"as_new_template": True, "new_id": new_id})
        new_doc.pop("_id", None)
        return {"success": True, "template": new_doc, "new_version": 1}

    # Version branch of existing template
    if t.get("status") == "draft" and not t.get("locked"):
        raise HTTPException(400, "Template is already a draft. Edit it directly.")

    # Seed template being branched for the first time -> materialize the FULL
    # seed document (name/content/fields/settings) in the DB first, otherwise
    # the upsert below creates a partial draft missing all template data.
    in_db = await db.templates.find_one({"id": template_id}, {"_id": 1})
    if not in_db:
        await db.templates.insert_one({**t, "created_at": ts, "updated_at": ts})

    new_version = (t.get("version") or 0) + 1
    # Save previous version to template_versions if not already archived
    if t.get("version", 0) > 0:
        prev_version_doc = {
            "id": str(uuid.uuid4()),
            "template_id": template_id,
            "version": t["version"],
            "name_en": t["name_en"],
            "name_gu": t["name_gu"],
            "category": t.get("category", "General"),
            "fields": t.get("fields", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "settings": t.get("settings"),
            "created_by": admin["id"],
            "created_at": ts,
        }
        await db.template_versions.update_one(
            {"template_id": template_id, "version": t["version"]},
            {"$set": prev_version_doc},
            upsert=True,
        )

    await db.templates.update_one(
        {"id": template_id},
        {"$set": {
            "status": "draft",
            "version": new_version,
            "locked": False,
            "source": "admin_edited",
            "updated_by": admin["id"],
            "updated_at": ts,
        }},
        upsert=True,
    )
    await audit_log(admin=admin, action="template_clone", target=template_id,
                    metadata={"as_new_template": False, "new_version": new_version})
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "template": updated, "new_version": new_version}


@admin_api.get("/templates/{template_id}/versions")
async def admin_template_versions(template_id: str, admin=Depends(get_admin)):
    """List all historical versions of a template."""
    versions = await db.template_versions.find(
        {"template_id": template_id}, {"_id": 0}
    ).sort("version", -1).to_list(100)
    return versions


@admin_api.post("/templates/{template_id}/preview")
async def admin_preview_template(template_id: str, req: Optional[AdminPreviewReq] = None, admin=Depends(get_admin)):
    """Preview a template with sample data. Supports live unsaved overrides from editor."""
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        t = next((x for x in TEMPLATES if x["id"] == template_id), None)
    if not t and not (req and req.content_en):
        raise HTTPException(404, "Template not found")
    if not t:
        t = {}

    content_en = req.content_en if (req and req.content_en is not None) else t.get("content_en", "")
    content_gu = req.content_gu if (req and req.content_gu is not None) else t.get("content_gu", "")
    name_en = req.name_en if (req and req.name_en is not None) else t.get("name_en", "Document")
    name_gu = req.name_gu if (req and req.name_gu is not None) else t.get("name_gu", "દસ્તાવેજ")
    fields = [f.model_dump() for f in req.fields] if (req and req.fields is not None) else t.get("fields", [])

    sample_values = {
        "advocate_name": "Advocate Ramesh Patel",
        "today": now().strftime("%d-%m-%Y"),
        "district": "Ahmedabad",
        "court": "City Civil Court, Ahmedabad",
        "case_number": "CMA/104/2026",
        "case_type": "Civil Suit",
        "party_name": "Rajesh Kumar",
        "opposite_party": "State of Gujarat",
    }
    if req and req.values:
        sample_values.update({k: v for k, v in req.values.items() if v is not None})

    for f in fields:
        key = f.get("key")
        if key and key not in sample_values:
            ftype = f.get("type", "text")
            if ftype == "date":
                sample_values[key] = now().strftime("%d-%m-%Y")
            elif ftype == "number":
                sample_values[key] = "100"
            elif ftype in ("select", "radio") and f.get("options"):
                sample_values[key] = f["options"][0].get("value", "")
            elif ftype == "checkbox":
                sample_values[key] = "Yes"
            else:
                sample_values[key] = f.get("default_value") or f.get("label_en", key)

    rendered_en = render_template(content_en, sample_values)
    blocks_en = build_blocks(rendered_en, name_en, name_gu,
                             (t.get("settings") or {}).get("block_align"))

    rendered_gu = render_template(content_gu, sample_values)
    blocks_gu = build_blocks(rendered_gu, name_en, name_gu,
                             (t.get("settings") or {}).get("block_align"))

    validation = _validate_placeholders(content_en, content_gu, fields)
    return {
        "preview": {
            "en": {"content": rendered_en, "blocks": blocks_en},
            "gu": {"content": rendered_gu, "blocks": blocks_gu},
        },
        "validation": validation,
    }


@admin_api.post("/templates/migrate-seed")
async def admin_migrate_seed(admin=Depends(require_super_admin)):
    """One-time migration: copy all 23 seed templates into MongoDB.
    Idempotent — does NOT overwrite existing templates."""
    created = []
    skipped = []
    errors = []
    ts = now().isoformat()
    for t in TEMPLATES:
        try:
            existing = await db.templates.find_one({"id": t["id"]})
            if existing:
                skipped.append(t["id"])
                continue
            template_doc = {
                "id": t["id"],
                "slug": t["id"],
                "name_en": t["name_en"],
                "name_gu": t["name_gu"],
                "category": t["category"],
                "aliases": t.get("aliases", []),
                "fields": [
                    {
                        "key": f["key"],
                        "label_en": f.get("label_en", ""),
                        "label_gu": f.get("label_gu", ""),
                        "type": f.get("type", "text"),
                        "required": f.get("required", True),
                        "order": idx,
                    }
                    for idx, f in enumerate(t.get("fields", []))
                ],
                "content_en": t.get("content_en", ""),
                "content_gu": t.get("content_gu", ""),
                "settings": {
                    "margin_top_cm": 2.5,
                    "margin_bottom_cm": 2.5,
                    "margin_left_cm": 2.5,
                    "margin_right_cm": 2.5,
                    "gujarati_font": "LohitGujarati",
                    "english_font": "Times-Roman",
                    "body_size": 12,
                    "heading_size": 13,
                    "line_spacing": 18,
                    "paragraph_spacing": 6,
                    **((t.get("settings") or {})),
                },
                "status": "published",
                "version": 1,
                "locked": True,
                "source": "seed",
                "created_by": None,
                "updated_by": None,
                "created_at": ts,
                "updated_at": ts,
                "published_at": ts,
            }
            await db.templates.insert_one(template_doc.copy())
            version_doc = {
                "id": str(uuid.uuid4()),
                "template_id": t["id"],
                "version": 1,
                "name_en": t["name_en"],
                "name_gu": t["name_gu"],
                "category": t["category"],
                "fields": template_doc["fields"],
                "content_en": t.get("content_en", ""),
                "content_gu": t.get("content_gu", ""),
                "created_by": None,
                "created_at": ts,
            }
            await db.template_versions.insert_one(version_doc.copy())
            created.append(t["id"])
        except Exception as e:
            errors.append({"id": t["id"], "error": str(e)})
    return {
        "total_seed_templates": len(TEMPLATES),
        "created": len(created),
        "skipped": len(skipped),
        "errors": len(errors),
        "created_ids": created,
        "skipped_ids": skipped,
        "error_details": errors,
    }


# ============================================================
# ADMIN SEED HELPER
# ============================================================

async def seed_catalogs():
    """Idempotently merge catalog seeds into their collections on startup.

    Only INSERTS seed ids that are missing — existing records (including
    admin edits and deactivations) are never overwritten. This keeps the
    collection in sync with the canonical seed list even when the DB was
    seeded by an older version with fewer entries (e.g. new districts).
    """
    ts = now().isoformat()
    for kind, (coll, seed_list) in _CATALOG_KINDS.items():
        existing_ids = {
            d["id"] for d in await db[coll].find({}, {"_id": 0, "id": 1}).to_list(10000)
        }
        added = 0
        for item in seed_list:
            if item["id"] in existing_ids:
                continue
            await db[coll].insert_one(
                {**item, "active": True, "created_at": ts, "updated_at": ts}
            )
            added += 1
        if added:
            logger.info(f"Seeded catalog '{kind}' (+{added} new entries).")
    await _refresh_catalog_maps()


async def seed_plans():
    """Idempotently seed the plans collection from the static catalog.
    Only inserts when the collection is empty — never overwrites admin edits."""
    count = await db.plans.count_documents({})
    if count > 0:
        return
    ts = now().isoformat()
    for p in PLANS:
        await db.plans.insert_one({
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "credits": p["credits"],
            "popular": p.get("popular", False),
            "active": True,
            "created_at": ts,
            "updated_at": ts,
        })
    logger.info(f"Seeded {len(PLANS)} plans.")


async def seed_super_admin():
    """Idempotently create the first super_admin from environment variables.
    Does NOT overwrite an existing admin with the same email."""
    if not ADMIN_SEED_EMAIL or not ADMIN_SEED_PASSWORD:
        logger.info("ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD not set — skipping admin seed.")
        return
    email = ADMIN_SEED_EMAIL.strip().lower()
    existing = await db.admin_users.find_one({"email": email})
    if existing:
        logger.info(f"Admin seed skipped — admin with email '{email}' already exists.")
        return
    hashed = bcrypt.hashpw(ADMIN_SEED_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hashed,
        "name": "Super Admin",
        "role": "super_admin",
        "active": True,
        "last_login": None,
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
    }
    await db.admin_users.insert_one(admin_doc.copy())
    logger.info(f"Super admin seeded: {email}")


# ============================================================
# APP WIRING
# ============================================================

app.include_router(api)
app.include_router(admin_api)
# CORS — explicit allowlist, never '*' in production. Env CORS_ORIGINS (comma-
# separated) overrides the defaults; localhost origins stay available for dev via
# a regex so local preview servers on any port keep working.
_DEFAULT_CORS_ORIGINS = [
    # Production Lawyer Frontend — custom domain + Vercel deployment
    "https://nyaysetupro.in",
    "https://www.nyaysetupro.in",
    "https://nyay-setu-pro-emergent-bo83.vercel.app",
    # Production Admin Portal
    "https://nyay-setu-pro-emergent-ebhh.vercel.app",
    # Legacy/other frontend deployments kept for compatibility
    "https://nyaysetu-frontend.vercel.app",
    "https://nyaysetu-pro-emergent.vercel.app",
]
_CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()] or _DEFAULT_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _existing_index_map(coll) -> dict:
    """Map normalized key patterns -> existing index docs for a collection.

    Key patterns are normalized to sorted (field, direction) tuples so specs
    written as strings ("id"), lists of tuples, or dicts all compare equal to
    what MongoDB reports back from list_indexes()."""
    indexes = await coll.list_indexes().to_list(200)
    return {tuple(sorted(ix.get("key", {}).items())): ix for ix in indexes}


def _normalize_spec(spec) -> tuple:
    """Normalize a create_index spec (str | list of tuples | dict) to a sorted
    tuple of (field, direction) pairs so it can be compared with index keys."""
    if isinstance(spec, str):
        items = [(spec, 1)]
    elif isinstance(spec, dict):
        items = list(spec.items())
    else:
        items = list(spec)
    return tuple(sorted((str(k), v) for k, v in items))


async def _ensure_index(coll, spec, **kwargs):
    """Create an index only when no index with the same key pattern exists.

    Production-safe and idempotent: an index that already exists (even with
    slightly different options than requested — e.g. an older version created
    it with a different TTL/sparse setting) is never re-created, so startup
    cannot crash with IndexOptionsConflict. The existing index still serves
    the same functional purpose (uniqueness / lookup on those fields)."""
    keys = _normalize_spec(spec)
    existing = await _existing_index_map(coll)
    if keys in existing:
        name = existing[keys].get("name", "?")
        logger.info(f"Index {name} on {getattr(coll, 'name', coll)} already exists — skipping creation.")
        return None
    return await coll.create_index(spec, **kwargs)


async def _ensure_ttl_index(coll, field: str, required_seconds: int):
    """Reconcile a TTL index to a required expireAfterSeconds value.

    The application is authoritative for TTL semantics: it stamps ttl_at =
    now + otp_ttl_seconds + 60 when issuing an OTP, so the index must expire
    documents no earlier than that (otherwise valid OTPs would be deleted
    before the app considers them expired). The reconcile is idempotent:
      - no index on the field  -> create with required_seconds
      - equal                  -> no-op
      - greater than required  -> keep (more conservative, never expires valid
        records early; avoids an unnecessary rebuild)
      - less than required     -> drop + recreate (the current index would
        delete valid records too early)
    This never deletes data and never crashes startup on option conflicts."""
    keys = tuple(sorted([(field, 1)]))
    existing = await _existing_index_map(coll)
    ix = existing.get(keys)
    if ix is None:
        await coll.create_index(field, expireAfterSeconds=required_seconds)
        logger.info(f"Created TTL index {field}_1 (expireAfterSeconds={required_seconds}).")
        return
    name = ix.get("name", f"{field}_1")
    current = ix.get("expireAfterSeconds")
    if current == required_seconds:
        logger.info(f"TTL index {name} already correct (expireAfterSeconds={current}).")
    elif current is not None and current > required_seconds:
        logger.info(f"TTL index {name} expireAfterSeconds={current} > required {required_seconds} — keeping existing (safe, never expires valid records early).")
    else:
        logger.warning(f"TTL index {name} expireAfterSeconds={current} < required {required_seconds} — rebuilding index to prevent early expiry.")
        await coll.drop_index(name)
        await coll.create_index(field, expireAfterSeconds=required_seconds)
        logger.info(f"TTL index {name} rebuilt with expireAfterSeconds={required_seconds}.")


@app.on_event("startup")
async def create_indexes():
    """Create MongoDB indexes idempotently on startup.

    Every index is created only if an index with the same key pattern does not
    already exist, so deployments and restarts never crash with
    IndexOptionsConflict (e.g. the otps.ttl_at_1 TTL index whose TTL may have
    drifted from the admin-configured otp_ttl_seconds setting)."""
    # Users
    await _ensure_index(db.users, "id", unique=True)
    await _ensure_index(db.users, "mobile", unique=True, sparse=True)
    await _ensure_index(db.users, "email", unique=True, sparse=True)
    # Firebase identity — sparse so legacy users (no firebase_uid) are unaffected,
    # unique so one Firebase UID can never map to two NyaySetu accounts.
    await _ensure_index(db.users, "firebase_uid", unique=True, sparse=True)
    await _ensure_index(db.users, "referral_code", unique=True, sparse=True)
    # Cases
    await _ensure_index(db.cases, "user_id")
    await _ensure_index(db.cases, [("user_id", 1), ("status", 1)])
    await _ensure_index(db.cases, [("user_id", 1), ("updated_at", -1)])
    # Wallets
    await _ensure_index(db.wallets, "user_id", unique=True)
    # Applications
    await _ensure_index(db.applications, "user_id")
    await _ensure_index(db.applications, [("user_id", 1), ("created_at", -1)])
    # Drafts
    await _ensure_index(db.drafts, "user_id")
    await _ensure_index(db.drafts, [("user_id", 1), ("template_id", 1), ("case_id", 1)])
    # Transactions
    await _ensure_index(db.transactions, "user_id")
    await _ensure_index(db.transactions, [("user_id", 1), ("created_at", -1)])
    # Razorpay idempotency: one payment_id may grant credits at most once.
    await _ensure_index(db.transactions, "razorpay_payment_id", unique=True, sparse=True)
    await _ensure_index(db.payment_orders, "id", unique=True)
    await _ensure_index(db.payment_orders, "user_id")
    # Referrals
    await _ensure_index(db.referrals, "referrer_id")
    await _ensure_index(db.referrals, "referred_user_id", unique=True)
    # OTPs (auto-cleaned by verify flow / TTL — index on the BSON-date field)
    await _ensure_index(db.otps, "mobile", unique=True)
    otp_ttl = await _get_setting("otp_ttl_seconds")
    await _ensure_ttl_index(db.otps, "ttl_at", otp_ttl + 60)
    # Admin users
    await _ensure_index(db.admin_users, "id", unique=True)
    await _ensure_index(db.admin_users, "email", unique=True)
    await _ensure_index(db.templates, "id", unique=True)
    await _ensure_index(db.templates, "slug", unique=True)
    await _ensure_index(db.templates, [("status", 1), ("category", 1)])
    await _ensure_index(db.template_versions, [("template_id", 1), ("version", 1)], unique=True)
    await _ensure_index(db.case_forms, "case_type_id", unique=True)
    logger.info("MongoDB indexes ensured.")
    # Seed super admin from env vars
    await seed_plans()
    await seed_catalogs()
    await seed_super_admin()


@app.on_event("shutdown")
async def shutdown():
    client.close()
