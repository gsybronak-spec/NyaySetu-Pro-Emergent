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
import base64
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional, Union

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends, Request, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import jwt
import bcrypt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.x509 import load_pem_x509_certificate

from seed_data import CASE_TYPES, LAWS, DISTRICTS, TALUKAS, COURTS, LEGACY_COURTS, POLICE_STATIONS, TEMPLATES, PLANS, QUOTES
from seed_data_templates_v2 import TEMPLATES_V2
from doc_generator import (
    generate_pdf,
    generate_pdf_detailed,
    generate_docx,
    generate_odt,
    generate_document_images,
    build_image_payload,
    document_sha256,
    GENERATOR_VERSION,
    _gujarati_font_family as _resolve_gujarati_font_family_doc,
    render_template,
    build_blocks,
    get_doc_settings,
    normalize_legal_text,
    NYAYSETU_LEGAL_FORMAT_V1,
    MASTER_LEGAL_DOC_SETTINGS,
)
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

class UserRefreshReq(BaseModel):
    refresh_token: Optional[str] = Field(None, max_length=4000)

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
    first_name: Optional[str] = Field(None, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    mobile: Optional[str] = Field(None, max_length=20)
    gender: Optional[str] = Field(None, max_length=20)
    dob: Optional[str] = Field(None, max_length=30)
    advocate_name_en: Optional[str] = Field(None, max_length=200)
    advocate_name_gu: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=200)
    bar_council_no: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    user_type: Optional[str] = Field(None, max_length=50)
    picture: Optional[str] = Field(None, max_length=500)
    is_profile_complete: Optional[bool] = None
    profile_completed: Optional[bool] = None

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
    taluka_id: Optional[str] = Field(None, max_length=50)
    police_station: Optional[str] = Field(None, max_length=200)
    police_station_id: Optional[str] = Field(None, max_length=50)
    police_station_custom: Optional[str] = Field(None, max_length=200)
    # Party roles (v2 catalog) — e.g. ફરિયાદી/અરજદાર/વાદી and
    # આરોપી/સામાવાળા/પ્રતિવાદી. Case-level, reused by every application.
    party_role: Optional[str] = Field(None, max_length=30)
    opposite_party_role: Optional[str] = Field(None, max_length=30)
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
    template_version: Optional[int] = None
    case_id: Optional[str] = Field(None, max_length=50)
    language: str = "en"
    values: dict = {}
    filename: Optional[str] = Field(None, max_length=200)
    page_size: Optional[str] = Field(None, max_length=10)  # A4 | Legal

class DownloadReq(BaseModel):
    template_id: str = Field(..., max_length=50)
    template_version: Optional[int] = None
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
    template_version: Optional[int] = None
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

USER_ACCESS_TOKEN_EXPIRY_MINUTES = 15
USER_SESSION_EXPIRY_DAYS = 90

def now():
    return datetime.now(timezone.utc)

def make_token(user_id: str, token_version: int = 0, session_id: Optional[str] = None) -> str:
    payload = {
        "sub": user_id,
        "ver": token_version,
        "iat": int(now().timestamp()),
        "exp": int((now() + timedelta(minutes=USER_ACCESS_TOKEN_EXPIRY_MINUTES)).timestamp()),
        "token_type": "user",
    }
    if session_id:
        payload["session_id"] = session_id
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

async def create_user_session(user_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[str, str]:
    session_id = str(uuid.uuid4())
    raw_refresh_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
    created = now()
    expires = created + timedelta(days=USER_SESSION_EXPIRY_DAYS)
    session_doc = {
        "id": session_id,
        "user_id": user_id,
        "token_hash": token_hash,
        "created_at": created.isoformat(),
        "last_used_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked": False,
        "revoked_at": None,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    await db.user_sessions.insert_one(session_doc)
    return session_id, raw_refresh_token

async def get_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing auth token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(401, "Invalid token")
    # Role isolation: admin tokens cannot be used as user tokens
    if payload.get("token_type") == "admin":
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
    
    # Profile completeness evaluation
    if user.get("profile_completed") is True or user.get("is_profile_complete") is True:
        is_complete = True
    else:
        has_name = bool(user.get("name") or (user.get("first_name") and user.get("last_name")))
        has_mobile = bool(user.get("mobile"))
        has_state = bool(user.get("state"))
        has_district = bool(user.get("district"))
        user_type = user.get("user_type") or ("Advocate" if user.get("bar_council_no") else None)
        has_user_type = bool(user_type)
        has_bar = bool(user.get("bar_council_no")) if user_type == "Advocate" else True

        # Existing mobile/password users registered before this requirement
        if user.get("provider") != "google" and has_mobile and has_name:
            is_complete = True
        else:
            is_complete = bool(has_name and has_mobile and has_state and has_district and has_user_type and has_bar)

    u["profile_completed"] = is_complete
    u["is_profile_complete"] = is_complete
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
    first_name, middle_name, last_name = None, None, None
    if name:
        parts = name.strip().split()
        if len(parts) == 1:
            first_name = parts[0]
        elif len(parts) == 2:
            first_name, last_name = parts[0], parts[1]
        elif len(parts) >= 3:
            first_name, middle_name, last_name = parts[0], " ".join(parts[1:-1]), parts[-1]

    # If mobile and name are provided at registration, profile is complete.
    is_comp = bool(mobile and (name or (first_name and last_name)))

    user = {
        "id": user_id,
        "name": name,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "gender": None,
        "dob": None,
        "provider": provider,
        "user_type": None,
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
        "profile_completed": is_comp,
        "is_profile_complete": is_comp,
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
async def verify_otp(req: VerifyOtpReq, request: Request = None, response: Response = None):
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

    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    session_id, refresh_token = await create_user_session(user["id"], ip_address, user_agent)
    token = make_token(user["id"], user.get("token_version", 0), session_id)

    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"token": token, "refresh_token": refresh_token, "user": _public_user(user), "is_new": is_new}


# ============================================================
# PASSWORD AUTH — register / login / forgot / reset / set
# ============================================================

@api.post("/auth/register")
async def register(req: RegisterReq, request: Request = None, response: Response = None):
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

    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    session_id, refresh_token = await create_user_session(user["id"], ip_address, user_agent)
    token = make_token(user["id"], fresh.get("token_version", 0), session_id)

    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"token": token, "refresh_token": refresh_token, "user": _public_user(fresh), "is_new": True}


@api.post("/auth/login")
async def login(req: LoginReq, request: Request = None, response: Response = None):
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

    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    session_id, refresh_token = await create_user_session(user["id"], ip_address, user_agent)
    token = make_token(user["id"], user.get("token_version", 0), session_id)

    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"token": token, "refresh_token": refresh_token, "user": _public_user(user), "is_new": False}


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


@api.post("/auth/refresh")
async def refresh_user_token(
    req: Optional[UserRefreshReq] = None,
    authorization: Optional[str] = Header(None),
    nyaysetu_refresh_token: Optional[str] = Cookie(None),
    response: Response = None,
):
    """Silent token renewal: validates the persistent 90-day refresh session,
    extends sliding expiration, and issues a fresh 15-minute access token."""
    raw_refresh = None
    if req and req.refresh_token:
        raw_refresh = req.refresh_token.strip()
    elif authorization and authorization.startswith("Bearer "):
        raw_refresh = authorization.split(" ", 1)[1].strip()
    elif nyaysetu_refresh_token:
        raw_refresh = nyaysetu_refresh_token.strip()

    if not raw_refresh:
        raise HTTPException(401, "Missing refresh token")

    token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
    session = await db.user_sessions.find_one({"token_hash": token_hash}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid refresh token")
    if session.get("revoked"):
        raise HTTPException(401, "Session has been revoked")
    if datetime.fromisoformat(session["expires_at"]) < now():
        raise HTTPException(401, "Session has expired")

    user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    if user.get("active") is False:
        raise HTTPException(401, "Account disabled. Contact support.")

    # Update last_used_at and extend sliding expiration by 90 days
    new_expires = now() + timedelta(days=USER_SESSION_EXPIRY_DAYS)
    await db.user_sessions.update_one(
        {"token_hash": token_hash},
        {"$set": {"last_used_at": now().isoformat(), "expires_at": new_expires.isoformat()}},
    )

    access_token = make_token(user["id"], user.get("token_version", 0), session.get("id"))
    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=raw_refresh,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {
        "token": access_token,
        "refresh_token": raw_refresh,
        "user": _public_user(user),
    }


@api.post("/auth/logout")
async def logout_user(
    req: Optional[UserRefreshReq] = None,
    authorization: Optional[str] = Header(None),
    nyaysetu_refresh_token: Optional[str] = Cookie(None),
    response: Response = None,
):
    """Explicit logout: revokes the persistent session in MongoDB and clears the refresh cookie."""
    raw_refresh = None
    if req and req.refresh_token:
        raw_refresh = req.refresh_token.strip()
    elif authorization and authorization.startswith("Bearer "):
        raw_refresh = authorization.split(" ", 1)[1].strip()
    elif nyaysetu_refresh_token:
        raw_refresh = nyaysetu_refresh_token.strip()

    if raw_refresh:
        token_hash = hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        await db.user_sessions.update_one(
            {"token_hash": token_hash},
            {"$set": {"revoked": True, "revoked_at": now().isoformat()}},
        )

    if response:
        response.delete_cookie(key="nyaysetu_refresh_token", path="/")

    return {"success": True, "message": "Logged out successfully"}


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
        # Keep profile fresh without overwriting user customizations
        updates = {}
        if name and not user.get("name"):
            updates["name"] = name
        if picture and not user.get("picture"):
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
async def google_code_exchange(req: GoogleCodeReq, request: Request = None, response: Response = None):
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
        # Keep profile fresh without overwriting user customizations
        updates = {}
        if name and not user.get("name"):
            updates["name"] = name
        if picture and not user.get("picture"):
            updates["picture"] = picture
        if updates:
            await db.users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    session_id, refresh_token = await create_user_session(user["id"], ip_address, user_agent)
    token = make_token(user["id"], user.get("token_version", 0), session_id)

    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"token": token, "refresh_token": refresh_token, "user": _public_user(user), "is_new": is_new}


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
async def firebase_auth(req: FirebaseAuthReq, request: Request = None, response: Response = None):
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

    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    session_id, refresh_token = await create_user_session(user["id"], ip_address, user_agent)
    token = make_token(user["id"], user.get("token_version", 0), session_id)

    if response:
        response.set_cookie(
            key="nyaysetu_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=USER_SESSION_EXPIRY_DAYS * 86400,
            path="/",
        )

    return {"token": token, "refresh_token": refresh_token, "user": _public_user(user), "is_new": is_new}


# ============================================================
# PROFILE
# ============================================================

@api.get("/profile/me")
async def me(user=Depends(get_user)):
    return _public_user(user)

@api.put("/profile/update")
@api.patch("/profile/update")
@api.patch("/profile")
async def update_profile(req: ProfileUpdate, user=Depends(get_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}

    first = (updates.get("first_name") or user.get("first_name") or "").strip()
    middle = (updates.get("middle_name") or user.get("middle_name") or "").strip()
    last = (updates.get("last_name") or user.get("last_name") or "").strip()

    if first or last:
        full = " ".join([p for p in [first, middle, last] if p]).strip()
        if full:
            updates["name"] = full
            u_type = (updates.get("user_type") or user.get("user_type") or "").strip()
            if not updates.get("advocate_name_en"):
                if u_type == "Advocate":
                    updates["advocate_name_en"] = f"Adv. {full}"
                elif u_type:
                    updates["advocate_name_en"] = full

    if "mobile" in updates and updates["mobile"]:
        clean_mobile = re.sub(r"\D", "", str(updates["mobile"]))
        if clean_mobile.startswith("91") and len(clean_mobile) == 12:
            clean_mobile = clean_mobile[2:]
        if len(clean_mobile) != 10 or not clean_mobile[0] in "6789":
            raise HTTPException(400, "Please enter a valid 10-digit Indian mobile number.")
        existing = await db.users.find_one({"mobile": clean_mobile, "id": {"$ne": user["id"]}}, {"_id": 1})
        if existing:
            raise HTTPException(400, "This mobile number is already registered with another account.")
        updates["mobile"] = clean_mobile

    if "user_type" in updates and updates["user_type"]:
        valid_roles = ["Advocate", "Legal Professional", "Law Student", "Other"]
        if updates["user_type"] not in valid_roles:
            raise HTTPException(400, f"Invalid User Type. Choose from: {', '.join(valid_roles)}")
        if updates["user_type"] == "Advocate":
            bar_no = updates.get("bar_council_no") or user.get("bar_council_no")
            if "bar_council_no" in updates and not (updates["bar_council_no"] or "").strip():
                raise HTTPException(400, "Bar Council / Enrollment Number is required for Advocates.")

    # Auto-detect profile completeness
    check_name = updates.get("name") or user.get("name") or (updates.get("first_name") and updates.get("last_name"))
    check_mobile = updates.get("mobile") or user.get("mobile")
    check_state = updates.get("state") or user.get("state")
    check_district = updates.get("district") or user.get("district")
    check_type = updates.get("user_type") or user.get("user_type")
    check_bar = bool((updates.get("bar_council_no") or user.get("bar_council_no") or "").strip()) if check_type == "Advocate" else True

    if check_name and check_mobile and check_state and check_district and check_type and check_bar:
        updates["profile_completed"] = True
        updates["is_profile_complete"] = True
    elif req.profile_completed is not None:
        updates["profile_completed"] = req.profile_completed
        updates["is_profile_complete"] = req.profile_completed
    elif req.is_profile_complete is not None:
        updates["profile_completed"] = req.is_profile_complete
        updates["is_profile_complete"] = req.is_profile_complete

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


@api.get("/catalog/template-base-fields")
async def get_template_base_fields():
    """Expose base header fields metadata needed to dynamically construct the No-Case base form."""
    return {
        "base_fields": [
            {
                "key": "district",
                "label_en": "District",
                "label_gu": "જિલ્લો",
                "type": "select",
                "required": True,
                "source": "districts",
            },
            {
                "key": "taluka",
                "label_en": "Taluka (Optional)",
                "label_gu": "તાલુકો (વૈકલ્પિક)",
                "type": "select",
                "required": False,
                "source": "talukas",
                "depends_on": "district",
            },
            {
                "key": "court",
                "label_en": "Court Name",
                "label_gu": "કોર્ટનું નામ",
                "type": "court_select",
                "required": True,
                "source": "courts",
            },
            {
                "key": "case_type",
                "label_en": "Case Type",
                "label_gu": "કેસનો પ્રકાર",
                "type": "select",
                "required": True,
                "source": "case_types",
            },
            {
                "key": "case_number",
                "label_en": "Case Number",
                "label_gu": "કેસ નંબર",
                "type": "text",
                "required": True,
                "placeholder_en": "e.g. 1234/2026",
                "placeholder_gu": "દા.ત. ૧૨૩૪/૨૦૨૬",
            },
            {
                "key": "party_role",
                "label_en": "Party 1 Role",
                "label_gu": "પક્ષકાર ૧ ની ભૂમિકા",
                "type": "role_chips",
                "required": True,
                "default": "plaintiff",
                "options": [
                    {"value": "plaintiff", "label_en": "Plaintiff", "label_gu": "વાદી"},
                    {"value": "applicant", "label_en": "Applicant", "label_gu": "અરજદાર"},
                    {"value": "complainant", "label_en": "Complainant", "label_gu": "ફરિયાદી"},
                ],
            },
            {
                "key": "party_name",
                "label_en": "Party 1 Name",
                "label_gu": "પક્ષકાર ૧ નું નામ",
                "type": "text",
                "required": True,
                "placeholder_en": "Full Name of Party 1",
                "placeholder_gu": "પક્ષકાર ૧ નું પૂરું નામ",
            },
            {
                "key": "opposite_party_role",
                "label_en": "Party 2 (Opposite) Role",
                "label_gu": "પક્ષકાર ૨ (સામાવાળા) ની ભૂમિકા",
                "type": "role_chips",
                "required": True,
                "default": "defendant",
                "options": [
                    {"value": "defendant", "label_en": "Defendant", "label_gu": "પ્રતિવાદી"},
                    {"value": "opponent", "label_en": "Opponent / Respondent", "label_gu": "સામાવાળા"},
                    {"value": "accused", "label_en": "Accused", "label_gu": "આરોપી"},
                ],
            },
            {
                "key": "opposite_party",
                "label_en": "Party 2 (Opposite) Name",
                "label_gu": "પક્ષકાર ૨ (સામાવાળા) નું નામ",
                "type": "text",
                "required": True,
                "placeholder_en": "Full Name of Opposite Party",
                "placeholder_gu": "સામાવાળા પક્ષકારનું પૂરું નામ",
            },
            {
                "key": "advocate_name",
                "label_en": "Advocate Name",
                "label_gu": "એડવોકેટનું નામ",
                "type": "text",
                "required": True,
                "autofill_source": "profile",
            },
        ]
    }

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
_COURT_MAP = {c["id"]: c for c in [*LEGACY_COURTS, *COURTS]}
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

_CATALOG_CACHE: dict[str, list] = {}

def _invalidate_catalog_cache(kind: Optional[str] = None) -> None:
    global _CATALOG_CACHE
    if kind:
        _CATALOG_CACHE.pop(kind, None)
    else:
        _CATALOG_CACHE.clear()


async def _load_catalog(kind: str) -> list:
    """DB catalog entries if the collection has any, else the seed list
    (backward compat for uninitialized databases).
    Cached in-memory to prevent repeated MongoDB roundtrips on static catalogs."""
    if kind in _CATALOG_CACHE:
        return _CATALOG_CACHE[kind]
    coll, seed_list = _CATALOG_KINDS[kind]
    items = await db[coll].find({}, {"_id": 0}).to_list(1000)
    if items:
        _CATALOG_CACHE[kind] = items
        return items
    res = [dict(x, active=True) for x in seed_list]
    _CATALOG_CACHE[kind] = res
    return res


async def _refresh_catalog_maps() -> None:
    """Rebuild in-memory catalog maps + valid-id sets from MongoDB. Called at
    startup and after every admin catalog mutation so labels, validation and
    document rendering see admin-managed entries immediately."""
    _invalidate_catalog_cache()
    global _CASE_TYPE_MAP, _LAW_MAP, _DISTRICT_MAP, _TALUKA_MAP, _COURT_MAP, _PS_MAP
    global _VALID_CASE_TYPE_IDS, _VALID_LAW_IDS, _VALID_DISTRICT_IDS, _VALID_TALUKA_IDS, _VALID_COURT_IDS, _VALID_PS_IDS
    _CASE_TYPE_MAP = {c["id"]: c for c in await _load_catalog("case-types")}
    _LAW_MAP = {l["id"]: l for l in await _load_catalog("laws")}
    _DISTRICT_MAP = {d["id"]: d for d in await _load_catalog("districts")}
    _TALUKA_MAP = {t["id"]: t for t in await _load_catalog("talukas")}
    _loaded_courts = {c["id"]: c for c in await _load_catalog("courts")}
    _legacy_courts = {c["id"]: c for c in LEGACY_COURTS}
    _COURT_MAP = {**_legacy_courts, **_loaded_courts}
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
    global _CASE_TYPE_MAP, _LAW_MAP, _DISTRICT_MAP, _TALUKA_MAP, _COURT_MAP, _PS_MAP
    case_type_map = _CASE_TYPE_MAP or {ct["id"]: ct for ct in CASE_TYPES}
    law_map = _LAW_MAP or {l["id"]: l for l in LAWS}
    district_map = _DISTRICT_MAP or {d["id"]: d for d in DISTRICTS}
    taluka_map = _TALUKA_MAP or {t["id"]: t for t in TALUKAS}
    court_map = _COURT_MAP or {c["id"]: c for c in [*LEGACY_COURTS, *COURTS]}
    ps_map = _PS_MAP or {p["id"]: p for p in POLICE_STATIONS}

    lang = c.get("language", "en")
    ct = case_type_map.get(c.get("case_type_id"))
    law = law_map.get(c.get("law_id"))
    dist = district_map.get(c.get("district_id"))
    tal = taluka_map.get(c.get("taluka_id"))
    court = court_map.get(c.get("court_id"))
    ps = ps_map.get(c.get("police_station_id"))
    section = None
    if law and c.get("section_id"):
        section = next((s for s in law.get("sections", []) if s["id"] == c.get("section_id")), None)
    c["category"] = ct.get("cat", "Other") if ct else "Other"
    if c.get("case_type_id") == "other" and c.get("case_type_custom"):
        c["case_type_label"] = c.get("case_type_custom")
    elif ct:
        c["case_type_label"] = ct.get("gu") if lang == "gu" else ct.get("en")
    else:
        c["case_type_label"] = c.get("case_type_custom") or None
    c["law_label"] = (law.get("gu") if lang == "gu" else law.get("en")) if law else (c.get("law_custom") or None)
    c["section_label"] = section.get("label") if section else None
    c["district_label"] = (dist.get("gu") if lang == "gu" else dist.get("en")) if dist else None
    c["taluka_label"] = (tal.get("gu") if lang == "gu" else tal.get("en")) if tal else None
    if court:
        c["court_label"] = court.get("gu") if lang == "gu" else court.get("en")
    else:
        c["court_label"] = c.get("court_custom") or c.get("court") or None
    if ps:
        c["police_station_label"] = ps.get("gu") if lang == "gu" else ps.get("en")
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
    tid = data.get("taluka_id")
    if tid and tid != "other" and tid not in _VALID_TALUKA_IDS:
        raise HTTPException(400, f"Invalid taluka_id: {tid}")
    if tid and tid != "other" and did and _TALUKA_MAP.get(tid, {}).get("district_id") not in (None, did):
        raise HTTPException(400, f"Taluka {tid} does not belong to district {did}")
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
    # Case-level party roles + derived lines (v2 catalog — never user-entered)
    "party_role", "opposite_party_role", "party_line", "opposite_party_line",
    "case_or_crime",
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
        # v2 catalog field behavior: conditional fields (depends_on/show_when —
        # the "અન્ય/Other" pattern) and case-party selects (source).
        for opt_key in ("depends_on", "show_when", "source"):
            if f.get(opt_key):
                field_dict[opt_key] = f[opt_key]
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


async def _ensure_seed_complete() -> None:
    """Ensure database has been initialized with seed templates on first run."""
    setting = await db.system_settings.find_one({"key": "seed_complete"})
    if not setting or setting.get("value") is not True:
        await seed_templates()


async def _get_published_templates() -> list:
    """Return published templates from db.templates ONLY (single source of truth).
    Hides draft, archived, or deleted templates."""
    await _ensure_seed_complete()
    db_templates = await db.templates.find({"status": "published"}, {"_id": 0}).sort("category", 1).to_list(1000)
    return [{**t, "format_version": t.get("format_version") or NYAYSETU_LEGAL_FORMAT_V1} for t in db_templates]


async def _get_template_by_id(template_id: str) -> Optional[dict]:
    """Get a single published template by ID from db.templates ONLY."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id, "status": "published"}, {"_id": 0})
    if t:
        return {**t, "format_version": t.get("format_version") or NYAYSETU_LEGAL_FORMAT_V1}
    return None


async def resolve_template_for_draft(template_id: Union[str, dict], template_version: Optional[int] = None) -> Optional[dict]:
    """Resolve the exact template version used by a draft.
    Supports either passing (template_id, template_version) or passing the draft dict directly.
    1. Search db.template_revisions by (template_id, template_version).
    2. Fallback to db.templates by template_id (backward compatibility for unversioned drafts or missing revisions)."""
    if isinstance(template_id, dict):
        draft = template_id
        t_id = draft.get("template_id", "")
        t_ver = draft.get("template_version")
    else:
        t_id = template_id
        t_ver = template_version

    if t_ver is not None:
        rev = await db.template_revisions.find_one(
            {"template_id": t_id, "version": t_ver},
            {"_id": 0}
        )
        if rev:
            return {
                **rev,
                "id": rev.get("template_id", t_id),
                "format_version": rev.get("format_version") or NYAYSETU_LEGAL_FORMAT_V1,
            }
        # Also check template_versions for legacy data
        old_v = await db.template_versions.find_one(
            {"template_id": t_id, "version": t_ver},
            {"_id": 0}
        )
        if old_v:
            return {
                **old_v,
                "id": old_v.get("template_id", t_id),
                "format_version": old_v.get("format_version") or NYAYSETU_LEGAL_FORMAT_V1,
            }
    # Fallback to current template in db.templates
    t = await db.templates.find_one({"id": t_id}, {"_id": 0})
    if t:
        return {
            **t,
            "format_version": t.get("format_version") or NYAYSETU_LEGAL_FORMAT_V1,
        }
    return None


@api.get("/templates")
async def list_templates(q: Optional[str] = None, category: Optional[str] = None, authorization: Optional[str] = Header(None)):
    user = None
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization[7:].strip()
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        except Exception:
            pass

    all_templates = await _get_published_templates()
    fav_set = set(user.get("favourite_templates") or []) if user else set()
    custom_order = user.get("template_order") or [] if user else []

    items = []
    for t in all_templates:
        p = public_template(t)
        if user is not None:
            p["is_favorite"] = p["id"] in fav_set
        items.append(p)

    if category:
        if category.lower() == "favorites":
            items = [t for t in items if t.get("is_favorite")]
        else:
            items = [t for t in items if t["category"].lower() == category.lower()]

    if q:
        ql = q.lower().strip()
        matched = []
        for t in all_templates:
            all_aliases = [t["name_en"].lower(), t["name_gu"].lower()] + [a.lower() for a in t.get("aliases", [])]
            if any(ql in a for a in all_aliases):
                p = public_template(t)
                if user is not None:
                    p["is_favorite"] = p["id"] in fav_set
                matched.append(p)
        if category:
            if category.lower() == "favorites":
                matched = [t for t in matched if t.get("is_favorite")]
            else:
                matched = [t for t in matched if t["category"].lower() == category.lower()]
        items = matched

    # Sort if user has custom order
    if custom_order and user is not None:
        order_index = {tid: idx for idx, tid in enumerate(custom_order)}
        items.sort(key=lambda x: order_index.get(x["id"], 999999))

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

# ============================================================
# PARTY ROLES ARCHITECTURE & BILINGUAL MAPPING
# ============================================================

ROLE_MAP = {
    "plaintiff": {"gu": "વાદી", "en": "Plaintiff"},
    "defendant": {"gu": "પ્રતિવાદી", "en": "Defendant"},
    "applicant": {"gu": "અરજદાર", "en": "Applicant"},
    "opponent": {"gu": "સામાવાળા", "en": "Opponent"},
    "complainant": {"gu": "ફરિયાદી", "en": "Complainant"},
    "accused": {"gu": "આરોપી", "en": "Accused"},
}

_ROLE_CANONICAL_LOOKUP = {
    # Canonical keys
    "plaintiff": "plaintiff",
    "defendant": "defendant",
    "applicant": "applicant",
    "opponent": "opponent",
    "complainant": "complainant",
    "accused": "accused",
    # Gujarati strings
    "વાદી": "plaintiff",
    "પ્રતિવાદી": "defendant",
    "અરજદાર": "applicant",
    "સામાવાળા": "opponent",
    "સામેવાળા": "opponent",
    "ફરિયાદી": "complainant",
    "ફરીયાદી": "complainant",
    "આરોપી": "accused",
    # English strings
    "plaintiff": "plaintiff",
    "defendant": "defendant",
    "applicant": "applicant",
    "opponent": "opponent",
    "respondent": "opponent",
    "complainant": "complainant",
    "accused": "accused",
}

def resolve_party_role_label(role: Optional[str], language: str = "gu") -> str:
    """Resolve a canonical or legacy role string into the appropriate language label."""
    if not role:
        return "ફરિયાદી" if language == "gu" else "Complainant"
    r_str = str(role).strip()
    r_lower = r_str.lower()
    canonical = _ROLE_CANONICAL_LOOKUP.get(r_lower) or _ROLE_CANONICAL_LOOKUP.get(r_str)
    if canonical and canonical in ROLE_MAP:
        return ROLE_MAP[canonical]["gu"] if language == "gu" else ROLE_MAP[canonical]["en"]
    return r_str

def format_advocate_name(name: Optional[str] = None, language: str = "en") -> str:
    """Display an advocate name with language-appropriate title without double-prefixing."""
    n = (name or "").strip()
    if not n:
        return "એડવોકેટ" if language == "gu" else "Advocate"
    if language == "gu":
        if re.match(r"^(એડવોકેટ|વકીલ|adv\.?)\s*", n, re.IGNORECASE):
            return re.sub(r"^adv\.?\s*", "એડવોકેટ ", n, flags=re.IGNORECASE)
        return f"એડવોકેટ {n}"
    else:
        if re.match(r"^adv\.?\s", n, re.IGNORECASE):
            return n
        if re.match(r"^(એડવોકેટ|વકીલ)\s*", n):
            return re.sub(r"^(એડવોકેટ|વકીલ)\s*", "Adv. ", n)
        return f"Adv. {n}"


async def build_render_context(user: dict, case: Optional[dict], values: dict, language: str) -> dict:
    ctx = dict(values or {})
    # Advocate name resolution:
    # 1. Client-provided advocate_name wins
    # 2. If language == "gu" -> user.get("advocate_name_gu") or user.get("name")
    # 3. If language == "en" -> user.get("advocate_name_en") or user.get("name")
    if not ctx.get("advocate_name"):
        if language == "gu":
            adv_name = user.get("advocate_name_gu") or user.get("name")
        else:
            adv_name = user.get("advocate_name_en") or user.get("name")
        ctx["advocate_name"] = format_advocate_name(adv_name, language)

    # Today (formatted)
    ctx["today"] = now().strftime("%d-%m-%Y")

    # Guard: if a client sent a raw district id (e.g. "ahmedabad") instead of a
    # label, resolve it here so documents never print raw catalog ids.
    if isinstance(ctx.get("district"), str) and ctx["district"] in _DISTRICT_MAP:
        d = _DISTRICT_MAP[ctx["district"]]
        ctx["district"] = d["gu"] if language == "gu" else d["en"]

    # Same guard for taluka raw catalog ids sent as select values (optional —
    # empty stays empty, never prints "None" / "null" / raw ids).
    if isinstance(ctx.get("taluka"), str) and ctx["taluka"] in _TALUKA_MAP:
        tobj = _TALUKA_MAP[ctx["taluka"]]
        ctx["taluka"] = tobj["gu"] if language == "gu" else tobj["en"]

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
        taluka_obj = _TALUKA_MAP.get(case.get("taluka_id"))
        if taluka_obj:
            taluka_name = taluka_obj["gu"] if language == "gu" else taluka_obj["en"]
        else:
            taluka_name = case.get("taluka") or ""
        ctx.setdefault("taluka", taluka_name)
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
        # Party roles (v2 catalog): stored on the Case, inherited by every application.
        raw_p_role = ctx.get("party_role") or case.get("party_role") or "complainant"
        raw_opp_role = ctx.get("opposite_party_role") or case.get("opposite_party_role") or "accused"
        ctx["party_role"] = resolve_party_role_label(raw_p_role, language)
        ctx["opposite_party_role"] = resolve_party_role_label(raw_opp_role, language)
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
        raw_p_role = ctx.get("party_role") or "complainant"
        raw_opp_role = ctx.get("opposite_party_role") or "accused"
        ctx["party_role"] = resolve_party_role_label(raw_p_role, language)
        ctx["opposite_party_role"] = resolve_party_role_label(raw_opp_role, language)
        if not ctx.get("client_name"):
            ctx["client_name"] = ""

    # ---- Derived values for the document-return application (never user-entered) ----
    status = ctx.get("case_status")
    if language == "gu":
        if status == "ચાલુ":
            ctx["case_status_clause"] = "ચાલવા પર છે"
            ctx["tense"] = "છે"
        elif status in ("ડિસ્પોઝ્ડ", "ડિસ્પોસ્ડ", "Disposed"):
            ctx["case_status_clause"] = "આપની કોર્ટમા ડિસ્પોસ્ડ થયેલ છે"
            ctx["tense"] = "હતો"
        else:
            ctx["case_status_clause"] = ""
            ctx["tense"] = "છે"
    else:
        if status in ("ચાલુ", "Ongoing"):
            ctx["case_status_clause"] = "is pending"
            ctx["tense"] = "is"
        elif status in ("ડિસ્પોઝ્ડ", "ડિસ્પોસ્ડ", "Disposed"):
            ctx["case_status_clause"] = "has been disposed of"
            ctx["tense"] = "was"
        else:
            ctx["case_status_clause"] = ""
            ctx["tense"] = "is"

    # Conditional "અન્ય/Other" fields (v2 catalog): when a select/radio is set
    # to "other", the companion "<key>_other" text field holds the real value
    # and replaces it in the rendered document (never prints the literal
    # English word "other"). Generic rule, no per-template wiring needed.
    for k in list(ctx.keys()):
        if ctx.get(k) == "other":
            ctx[k] = ctx.get(f"{k}_other") or ""

    # Signature/pleading role — the side the advocate represents.
    side = ctx.get("advocate_side")
    if side == "party":
        ctx["selected_party_role"] = ctx["party_role"]
    elif side == "opposite":
        ctx["selected_party_role"] = ctx["opposite_party_role"]
    elif side == "other":
        ctx["selected_party_role"] = ctx.get("advocate_other") or ("ત્રાહિત પક્ષ" if language == "gu" else "Third Party")
    else:
        ctx["selected_party_role"] = ctx.get("applicant_role") or ctx.get("opposite_party_role") or ctx["party_role"]

    # Party lines — "<role> <name>" for the case header block (never prints a
    # lone role or a leading space when a name/role is missing).
    p_name = (ctx.get("party_name") or "").strip()
    opp_name = (ctx.get("opposite_party") or "").strip()
    p_role = (ctx.get("party_role") or "").strip()
    opp_role = (ctx.get("opposite_party_role") or "").strip()

    ctx["party_line"] = f"{p_role} {p_name}".strip()
    ctx["opposite_party_line"] = f"{opp_role} {opp_name}".strip()

    # Case-or-crime line (Jamin Bond): case number wins; crime registration
    # number is used only when the charge-sheet is not yet filed (no case no.).
    if ctx.get("case_number"):
        pfx = "કેસ નં." if language == "gu" else "Case No."
        ctx["case_or_crime"] = f"{pfx} {ctx.get('case_number')}"
    elif ctx.get("crime_reg_number"):
        pfx = "ગુન્હા રજી. નં." if language == "gu" else "Crime Reg. No."
        ctx["case_or_crime"] = f"{pfx} {ctx.get('crime_reg_number')}"
    else:
        ctx["case_or_crime"] = ""

    # Taluka/district line — taluka first when present (e.g. "કલોલ, ગાંધીનગર")
    _tal = (ctx.get("taluka") or "").strip()
    ctx["taluka_place"] = f"{_tal}, {ctx.get('district') or ''}" if _tal else (ctx.get("district") or "")

    # Date display — the source blank is "[__ / __ / 20__]" (DD/MM/YYYY); the
    # canonical stored value is YYYY-MM-DD. Derived key keeps {{date}} untouched
    # for every other template. Legacy DD-MM-YYYY values pass through unchanged.
    _d = ctx.get("date")
    if isinstance(_d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", _d):
        ctx["date_display"] = f"{_d[8:10]}/{_d[5:7]}/{_d[0:4]}"
    elif _d:
        ctx["date_display"] = _d if isinstance(_d, str) else ""
    else:
        # No date chosen -> today (the system date). Matches the source blank
        # "[__ / __ / 20__]" rendered as DD/MM/YYYY.
        ctx["date_display"] = now().strftime("%d/%m/%Y")
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
    if getattr(req, "template_version", None) is not None:
        t = await resolve_template_for_draft(req.template_id, req.template_version)
    else:
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
    return {"content": rendered, "blocks": blocks, "language": req.language, "template_id": t.get("template_id", t["id"])}


@api.post("/applications/download")
async def download_application(req: DownloadReq, user=Depends(get_user)):
    validate_values_size(req.values)
    _validate_page_size(req.page_size)
    if req.format not in ("pdf", "docx", "odt", "png"):
        raise HTTPException(422, "format must be 'pdf', 'docx', 'odt' or 'png'")
    if not rate_limit(f"download:{user['id']}", 30, 60):
        raise HTTPException(429, "Too many downloads. Please try again later.")
    if getattr(req, "template_version", None) is not None:
        t = await resolve_template_for_draft(req.template_id, req.template_version)
    else:
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
    gen_meta = {}
    try:
        case = None
        if req.case_id:
            case = await db.cases.find_one({"id": req.case_id, "user_id": user["id"]}, {"_id": 0})
        ctx = await build_render_context(user, case, req.values, req.language)
        tpl = t["content_gu"] if req.language == "gu" else t["content_en"]
        rendered = render_template(tpl, ctx)
        blocks = build_blocks(rendered, t["name_en"], t["name_gu"],
                              (t.get("settings") or {}).get("block_align"))

        tpl_settings = t.get("settings") or {}
        doc_settings = get_doc_settings({
            **tpl_settings,
            "page_size": page_size,
            "template_id": t["id"],
            "raw_content": rendered,
            "ctx": ctx,
        })
        if req.format == "docx":
            b64 = generate_docx(blocks, req.language, doc_settings)
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif req.format == "odt":
            b64 = generate_odt(blocks, req.language, doc_settings)
            mime = "application/vnd.oasis.opendocument.text"
        elif req.format == "png":
            # Image export: rasterize the EXACT document PDF (same layout,
            # margins, fonts, shaping) into per-page PNGs. Single page -> one
            # PNG; multiple pages -> a ZIP of page-1.png ... page-N.png.
            pages = generate_document_images(blocks, req.language, doc_settings)
            b64, mime, img_filename = build_image_payload(pages, (req.filename or "document").rsplit(".", 1)[0])
            gen_meta = {"engine": "rasterize", "font_family": _resolve_gujarati_font_family_doc(doc_settings)}
        else:
            b64, gen_meta = generate_pdf_detailed(blocks, req.language, doc_settings)
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
    default_base = f"{t['id']}_{now().strftime('%Y%m%d_%H%M%S')}"
    if req.format == "png":
        filename = img_filename  # .png for one page, .zip for multiple pages
    else:
        filename = req.filename or f"{default_base}.{req.format}"
    # Download-integrity + artifact metadata (document artifact / cache safety):
    # every artifact is fingerprinted so an old engine's corrupted output can
    # never be served again — and so we can prove which engine/font built it.
    try:
        raw_size = len(base64.b64decode(b64))
        artifact_sha = document_sha256(b64)
    except Exception:
        raw_size = 0
        artifact_sha = ""
    await db.applications.insert_one({
        "id": app_id,
        "user_id": user["id"],
        "template_id": t.get("template_id", t["id"]),
        "template_version": t.get("version", 1),
        "template_name": t.get("name_en", ""),
        "case_id": req.case_id,
        "language": req.language,
        "format": req.format,
        "filename": filename,
        "file_size": raw_size,
        "sha256": artifact_sha,
        "generator_version": GENERATOR_VERSION,
        "engine": (gen_meta or {}).get("engine"),
        "font_family": (gen_meta or {}).get("font_family"),
        "font_version": (gen_meta or {}).get("font_version"),
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

    resp = {"filename": filename, "mime_type": mime, "base64": b64}
    if gen_meta:
        resp["artifact"] = gen_meta
    return resp


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
# TEMPLATE FAVOURITES & ORDERING
# ============================================================

@api.get("/favourites/templates")
async def get_fav_templates(user=Depends(get_user)):
    return {"favourite_templates": user.get("favourite_templates") or []}


@api.post("/favourites/templates/{template_id}")
async def add_fav_template(template_id: str, user=Depends(get_user)):
    all_tpls = await _get_published_templates()
    if not any(t["id"] == template_id for t in all_tpls):
        raise HTTPException(404, "Template not found")
    await db.users.update_one({"id": user["id"]}, {"$addToSet": {"favourite_templates": template_id}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"favourite_templates": u.get("favourite_templates") or []}


@api.delete("/favourites/templates/{template_id}")
async def remove_fav_template(template_id: str, user=Depends(get_user)):
    await db.users.update_one({"id": user["id"]}, {"$pull": {"favourite_templates": template_id}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"favourite_templates": u.get("favourite_templates") or []}


@api.get("/user/template-preferences")
async def get_template_preferences(user=Depends(get_user)):
    return {
        "favourite_templates": user.get("favourite_templates") or [],
        "template_order": user.get("template_order") or [],
    }


class TemplateOrderReq(BaseModel):
    template_order: list[str]


@api.put("/user/template-order")
async def update_template_order(req: TemplateOrderReq, user=Depends(get_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"template_order": req.template_order}})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {
        "favourite_templates": u.get("favourite_templates") or [],
        "template_order": u.get("template_order") or [],
    }



# ============================================================
# DRAFTS
# ============================================================

@api.post("/drafts")
async def save_draft(req: DraftSave, user=Depends(get_user)):
    t = await db.templates.find_one({"id": req.template_id}, {"_id": 0})
    template_name = t["name_en"] if t else req.template_id
    template_version = req.template_version or (t.get("version", 1) if t else 1)
    # Upsert
    key = {"user_id": user["id"], "template_id": req.template_id, "case_id": req.case_id}
    await db.drafts.update_one(
        key,
        {"$set": {
            **key,
            "template_version": template_version,
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
    # Templates from db.templates ONLY (single source of truth)
    all_templates = await _get_published_templates()
    tpls = []
    for t in all_templates:
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
@app.get("/")
@app.get("/healthz")
async def root():
    return {"app": "NyaySetu Pro", "status": "ok", "version": "1.0.0"}


# ============================================================
# ADMIN PORTAL — MODELS
# ============================================================

class AdminLoginReq(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., max_length=200)

class AdminRefreshReq(BaseModel):
    refresh_token: Optional[str] = Field(None, max_length=500)

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
    placeholders: Optional[list] = None
    content_en: str = ""
    content_gu: str = ""
    settings: Optional[dict] = None
    editor_content_en: Optional[dict] = None
    editor_content_gu: Optional[dict] = None

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
    placeholders: Optional[list] = None
    content_en: Optional[str] = None
    content_gu: Optional[str] = None
    settings: Optional[dict] = None
    editor_content_en: Optional[dict] = None
    editor_content_gu: Optional[dict] = None

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

class AdminUserUpdateReq(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=150)
    mobile: Optional[str] = Field(None, max_length=20)
    user_type: Optional[str] = Field(None, max_length=50)
    state: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    bar_council_number: Optional[str] = Field(None, max_length=100)
    profile_completed: Optional[bool] = None

class AdminUserBulkStatusReq(BaseModel):
    user_ids: list[str] = Field(..., min_length=1)
    action: str = Field(..., description="suspend, activate, or ban")
    reason: Optional[str] = Field(None, max_length=500)

class AdminWalletAdjustReq(BaseModel):
    amount: int = Field(..., description="Positive to credit, negative to debit")
    reason: str = Field(..., min_length=1, max_length=500, description="Mandatory reason for adjustment")
    reference: Optional[str] = Field(None, max_length=200)

class AdminTemplateBulkStatusReq(BaseModel):
    template_ids: list[str] = Field(..., min_length=1)
    action: str = Field(..., description="archive or restore")
    reason: Optional[str] = Field(None, max_length=500)

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

ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES = int(os.environ.get("ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES", "15"))
ADMIN_SESSION_EXPIRY_DAYS = int(os.environ.get("ADMIN_SESSION_EXPIRY_DAYS", "30"))
ADMIN_TOKEN_EXPIRY_HOURS = 8  # Retained for backward compatibility if referenced


def make_admin_token(admin_id: str, email: str, role: str, session_id: Optional[str] = None) -> str:
    """Create a short-lived JWT for admin users. Contains token_type='admin' to distinguish from lawyer JWTs."""
    payload = {
        "sub": admin_id,
        "email": email,
        "role": role,
        "token_type": "admin",
        "iat": int(now().timestamp()),
        "exp": int((now() + timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRY_MINUTES)).timestamp()),
    }
    if session_id:
        payload["session_id"] = session_id
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def create_admin_session(admin_id: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> tuple[str, str]:
    """Create a persistent admin session in MongoDB. Returns (raw_refresh_token, session_id).
    The raw refresh token is NEVER stored in the database — only its SHA-256 hash."""
    raw_refresh_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
    session_id = str(uuid.uuid4())
    ts = now().isoformat()
    expires_at = (now() + timedelta(days=ADMIN_SESSION_EXPIRY_DAYS)).isoformat()
    session_doc = {
        "id": session_id,
        "admin_id": admin_id,
        "token_hash": token_hash,
        "created_at": ts,
        "last_used_at": ts,
        "expires_at": expires_at,
        "revoked": False,
        "revoked_at": None,
        "ip_address": ip_address,
        "user_agent": user_agent,
    }
    await db.admin_sessions.insert_one(session_doc)
    return raw_refresh_token, session_id


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


async def create_admin_audit_log(
    *,
    admin: Optional[dict] = None,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    reason: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    target: Optional[str] = None,
) -> dict:
    """Record a standardized admin action in db.audit_logs. Never raises — auditing must not
    break the primary action it records."""
    ts = now().isoformat()
    # Mask sensitive credentials if any
    safe_old = {k: v for k, v in (old_value or {}).items() if "password" not in k and "token" not in k and "secret" not in k and "_id" not in k} if old_value else None
    safe_new = {k: v for k, v in (new_value or {}).items() if "password" not in k and "token" not in k and "secret" not in k and "_id" not in k} if new_value else None
    
    inferred_type = entity_type or (action.split("_")[0] if "_" in action else "general")
    entry = {
        "id": str(uuid.uuid4()),
        "admin_id": admin.get("id") if admin else None,
        "admin_name": admin.get("name") if admin else None,
        "admin_email": admin.get("email") if admin else None,
        "admin_role": admin.get("role") if admin else None,
        "action": action,
        "entity_type": inferred_type,
        "entity_id": entity_id or target,
        "target": target or entity_id,
        "old_value": safe_old,
        "new_value": safe_new,
        "reason": reason,
        "metadata": metadata or {},
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": ts,
        "timestamp": ts,
    }
    try:
        await db.audit_logs.insert_one(entry.copy())
    except Exception:
        logger.warning(f"audit_log insert failed for action={action}", exc_info=True)
    entry.pop("_id", None)
    return entry


# Backward compatibility alias
audit_log = create_admin_audit_log


# ============================================================
# ADMIN PORTAL — API ROUTER
# ============================================================

admin_api = APIRouter(prefix="/api/admin")


@admin_api.post("/auth/login")
async def admin_login(req: AdminLoginReq, request: Request = None, response: Response = None):
    """Admin login with email + password → Short-lived Access JWT + Long-lived Persistent Refresh Session."""
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
    ip_addr = (request.headers.get("x-forwarded-for") or (request.client.host if request and request.client else None)) if request else None
    u_agent = request.headers.get("user-agent") if request else None
    refresh_token, session_id = await create_admin_session(admin["id"], ip_address=ip_addr, user_agent=u_agent)
    token = make_admin_token(admin["id"], admin["email"], admin["role"], session_id=session_id)
    await audit_log(admin=admin, action="admin_login", target=admin["id"], metadata={"email": email})
    
    if response:
        response.set_cookie(
            key="admin_refresh_token",
            value=refresh_token,
            max_age=ADMIN_SESSION_EXPIRY_DAYS * 86400,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/api/admin/auth",
        )
    return {"token": token, "refresh_token": refresh_token, "admin": admin_public(admin)}


@admin_api.post("/auth/refresh")
async def admin_refresh(
    req: Optional[AdminRefreshReq] = None,
    request: Request = None,
    response: Response = None,
    authorization: Optional[str] = Header(None),
):
    """Silently renew an expired admin access token using a valid persistent refresh session."""
    refresh_token = (req.refresh_token if req and req.refresh_token else None)
    if not refresh_token and request:
        refresh_token = request.cookies.get("admin_refresh_token")
    if not refresh_token and authorization and authorization.startswith("Bearer "):
        refresh_token = authorization.split(" ", 1)[1]
    
    if not refresh_token:
        raise HTTPException(401, "Missing refresh token")
    
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    session = await db.admin_sessions.find_one({"token_hash": token_hash}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid refresh token")
    if session.get("revoked", False):
        raise HTTPException(401, "Session has been revoked")
    if session.get("expires_at", "") <= now().isoformat():
        raise HTTPException(401, "Session has expired")
    
    admin = await db.admin_users.find_one({"id": session["admin_id"]}, {"_id": 0})
    if not admin:
        raise HTTPException(401, "Admin account not found")
    if not admin.get("active", False):
        raise HTTPException(401, "Admin account is disabled")
    
    # Update last_used_at timestamp on the session
    await db.admin_sessions.update_one(
        {"id": session["id"]},
        {"$set": {"last_used_at": now().isoformat()}},
    )
    
    new_token = make_admin_token(admin["id"], admin["email"], admin["role"], session_id=session["id"])
    return {"token": new_token, "refresh_token": refresh_token, "admin": admin_public(admin)}


@admin_api.get("/auth/me")
async def admin_me(admin=Depends(get_admin)):
    """Return the currently authenticated admin's profile."""
    return admin_public(admin)


@admin_api.post("/auth/logout")
async def admin_logout(
    req: Optional[AdminRefreshReq] = None,
    request: Request = None,
    response: Response = None,
    authorization: Optional[str] = Header(None),
):
    """Explicit admin logout: revokes active session, clears cookie, and records audit log."""
    refresh_token = (req.refresh_token if req and req.refresh_token else None)
    if not refresh_token and request:
        refresh_token = request.cookies.get("admin_refresh_token")
    
    admin_record = None
    session_id_to_revoke = None
    
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(bearer_token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("token_type") == "admin":
                admin_record = await db.admin_users.find_one({"id": payload.get("sub")}, {"_id": 0})
                session_id_to_revoke = payload.get("session_id")
        except Exception:
            pass

    if refresh_token:
        token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        session = await db.admin_sessions.find_one({"token_hash": token_hash})
        if session:
            await db.admin_sessions.update_one(
                {"token_hash": token_hash},
                {"$set": {"revoked": True, "revoked_at": now().isoformat()}},
            )
            if not admin_record:
                admin_record = await db.admin_users.find_one({"id": session.get("admin_id")}, {"_id": 0})

    if session_id_to_revoke:
        await db.admin_sessions.update_one(
            {"id": session_id_to_revoke},
            {"$set": {"revoked": True, "revoked_at": now().isoformat()}},
        )

    if response:
        response.delete_cookie(key="admin_refresh_token", path="/api/admin/auth")

    await audit_log(
        admin=admin_record,
        action="admin_logout",
        target=admin_record.get("id") if admin_record else "unknown",
        metadata={"explicit": True},
    )
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

# ============================================================
# USERS ADMIN API
# ============================================================

@admin_api.get("/users")
async def admin_list_users(
    page: int = 1,
    page_size: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    q: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    user_type: Optional[str] = None,
    provider: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin=Depends(require_super_admin),
):
    """List platform users with search, role/status/provider filters, sorting, and pagination."""
    query = {}
    search_term = (search or q or "").strip()
    if search_term:
        q_re = re.compile(re.escape(search_term), re.IGNORECASE)
        query["$or"] = [
            {"name": q_re},
            {"mobile": q_re},
            {"email": q_re},
            {"id": q_re},
            {"bar_council_number": q_re},
            {"bar_council_no": q_re},
        ]
    
    if status and status != "all":
        if status == "active":
            query["active"] = True
        elif status in ("suspended", "banned", "inactive"):
            query["$or"] = [{"active": False}, {"status": status}]
        else:
            query["status"] = status

    role_val = role or user_type
    if role_val and role_val != "all":
        query["user_type"] = {"$regex": f"^{re.escape(role_val)}$", "$options": "i"}

    if provider and provider != "all":
        query["provider"] = {"$regex": f"^{re.escape(provider)}$", "$options": "i"}

    eff_limit = limit if limit is not None else page_size
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else (max(page, 1) - 1) * eff_limit
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    sort_direction = -1 if sort_order.lower() in ("desc", "-1") else 1
    sort_field = sort_by if sort_by in ("created_at", "updated_at", "name", "email", "mobile", "user_type") else "created_at"

    cursor = db.users.find(query, {"_id": 0, "password_hash": 0})\
        .sort(sort_field, sort_direction).skip(eff_offset).limit(eff_limit)
    items = await cursor.to_list(eff_limit)
    total = await db.users.count_documents(query)
    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    return {
        "users": items,
        "items": items,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total_pages": total_pages,
    }


@admin_api.get("/users/{user_id}")
async def admin_get_user(user_id: str, admin=Depends(require_super_admin)):
    """Full user detail: profile, wallet, case count, app count, activity, and bar info."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(404, "User not found")
    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    cases_count = await db.cases.count_documents({"user_id": user_id})
    applications_count = await db.applications.count_documents({"user_id": user_id})
    transactions_count = await db.transactions.count_documents({"user_id": user_id})
    recent_applications = await db.applications.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)
    recent_cases = await db.cases.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)

    return {
        "user": user,
        "profile": user,
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "mobile": user.get("mobile"),
        "role": user.get("user_type") or user.get("role", "Advocate"),
        "user_type": user.get("user_type", "Advocate"),
        "status": "active" if user.get("active", True) else user.get("status", "inactive"),
        "active": user.get("active", True),
        "profile_completed": user.get("profile_completed", False),
        "provider": user.get("provider", "mobile"),
        "state": user.get("state"),
        "district": user.get("district"),
        "bar_council_number": user.get("bar_council_number") or user.get("bar_council_no"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
        "wallet": wallet,
        "wallet_balance": (wallet or {}).get("balance", 0),
        "total_credits_used": (wallet or {}).get("total_used", 0),
        "cases_count": cases_count,
        "applications_count": applications_count,
        "transactions_count": transactions_count,
        "recent_activity": {
            "recent_applications": recent_applications,
            "recent_cases": recent_cases,
        },
    }


@admin_api.put("/users/{user_id}")
async def admin_update_user(user_id: str, req: AdminUserUpdateReq, admin=Depends(require_super_admin)):
    """Administrative profile update for a user. Credentials cannot be modified here."""
    existing = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "User not found")
    
    updates = {}
    for k in ("name", "email", "mobile", "user_type", "state", "district", "bar_council_number", "profile_completed"):
        v = getattr(req, k, None)
        if v is not None:
            updates[k] = v
            if k == "bar_council_number":
                updates["bar_council_no"] = v

    if updates:
        updates["updated_at"] = now().isoformat()
        await db.users.update_one({"id": user_id}, {"$set": updates})
        await create_admin_audit_log(
            admin=admin,
            action="user_profile_update",
            entity_type="user",
            entity_id=user_id,
            old_value=existing,
            new_value={**existing, **updates},
            reason="Administrative profile update",
        )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "user": updated}


@admin_api.post("/users/{user_id}/suspend")
async def admin_suspend_user(user_id: str, admin=Depends(require_super_admin)):
    """Suspend a user account."""
    existing = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "User not found")
    ts = now().isoformat()
    await db.users.update_one({"id": user_id}, {"$set": {"active": False, "status": "suspended", "updated_at": ts, "disabled_at": ts}})
    await create_admin_audit_log(
        admin=admin,
        action="user_suspend",
        entity_type="user",
        entity_id=user_id,
        old_value={"active": existing.get("active"), "status": existing.get("status")},
        new_value={"active": False, "status": "suspended"},
        reason="Admin suspended user",
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "status": "suspended", "user": updated}


@admin_api.post("/users/{user_id}/activate")
async def admin_activate_user(user_id: str, admin=Depends(require_super_admin)):
    """Activate a suspended/inactive user account."""
    existing = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "User not found")
    ts = now().isoformat()
    await db.users.update_one({"id": user_id}, {"$set": {"active": True, "status": "active", "updated_at": ts, "enabled_at": ts}})
    await create_admin_audit_log(
        admin=admin,
        action="user_activate",
        entity_type="user",
        entity_id=user_id,
        old_value={"active": existing.get("active"), "status": existing.get("status")},
        new_value={"active": True, "status": "active"},
        reason="Admin activated user",
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "status": "active", "user": updated}


@admin_api.post("/users/{user_id}/ban")
async def admin_ban_user(user_id: str, admin=Depends(require_super_admin)):
    """Permanently ban a user account."""
    existing = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "User not found")
    ts = now().isoformat()
    await db.users.update_one({"id": user_id}, {"$set": {"active": False, "status": "banned", "updated_at": ts, "disabled_at": ts}})
    await create_admin_audit_log(
        admin=admin,
        action="user_ban",
        entity_type="user",
        entity_id=user_id,
        old_value={"active": existing.get("active"), "status": existing.get("status")},
        new_value={"active": False, "status": "banned"},
        reason="Admin banned user",
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "status": "banned", "user": updated}


@admin_api.post("/users/bulk-status")
async def admin_bulk_user_status(req: AdminUserBulkStatusReq, admin=Depends(require_super_admin)):
    """Bulk update user statuses (suspend, activate, ban)."""
    action = req.action.lower().strip()
    if action not in ("suspend", "activate", "ban"):
        raise HTTPException(400, "Action must be suspend, activate, or ban")
    
    active_flag = (action == "activate")
    status_str = "active" if active_flag else ("banned" if action == "ban" else "suspended")
    ts = now().isoformat()

    res = await db.users.update_many(
        {"id": {"$in": req.user_ids}},
        {"$set": {"active": active_flag, "status": status_str, "updated_at": ts}}
    )
    await create_admin_audit_log(
        admin=admin,
        action=f"user_bulk_{action}",
        entity_type="user",
        reason=req.reason or f"Bulk {action} on {len(req.user_ids)} users",
        metadata={"user_ids": req.user_ids, "matched": res.matched_count, "modified": res.modified_count},
    )
    return {"success": True, "action": action, "affected_count": res.modified_count}


@admin_api.patch("/users/{user_id}/status")
async def admin_set_user_status(user_id: str, req: AdminUserStatusReq,
                                admin=Depends(require_super_admin)):
    """Enable/disable a user account (super admin only)."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    ts = now().isoformat()
    updates = {"active": req.active, "status": "active" if req.active else "suspended", "updated_at": ts}
    updates["enabled_at" if req.active else "disabled_at"] = ts
    await db.users.update_one({"id": user_id}, {"$set": updates})
    await create_admin_audit_log(
        admin=admin,
        action="user_status_update",
        entity_type="user",
        entity_id=user_id,
        old_value={"active": user.get("active")},
        new_value={"active": req.active},
        metadata={"name": user.get("name"), "mobile": user.get("mobile"), "email": user.get("email"), "active": req.active},
    )
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"success": True, "user": updated}


# ============================================================
# WALLET / CREDITS ADMIN API
# ============================================================

@admin_api.get("/users/{user_id}/wallet")
async def admin_get_user_wallet(user_id: str, admin=Depends(require_super_admin)):
    """Get wallet balance, credit stats, and recent transactions for a user."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    if not wallet:
        wallet = {"user_id": user_id, "balance": 0, "free_credits_granted": 0, "total_used": 0}
    
    credits_agg = await db.transactions.aggregate([
        {"$match": {"user_id": user_id, "credits": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$credits"}}}
    ]).to_list(1)
    total_credits_earned = credits_agg[0]["total"] if credits_agg else (wallet.get("free_credits_granted") or 0)
    
    recent_transactions = await db.transactions.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)

    return {
        "user_id": user_id,
        "balance": wallet.get("balance", 0),
        "free_credits_granted": wallet.get("free_credits_granted", 0),
        "total_credits_earned": total_credits_earned,
        "total_credits_consumed": wallet.get("total_used", 0),
        "total_used": wallet.get("total_used", 0),
        "recent_transactions": recent_transactions,
    }


@admin_api.get("/users/{user_id}/wallet/transactions")
async def admin_get_user_wallet_transactions(
    user_id: str,
    page: int = 1,
    page_size: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    type: Optional[str] = None,
    credit_debit: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin=Depends(require_super_admin),
):
    """List paginated wallet transactions for a specific user."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    
    query = {"user_id": user_id}
    if type and type != "all":
        query["type"] = type
    if credit_debit == "credit":
        query["credits"] = {"$gt": 0}
    elif credit_debit == "debit":
        query["credits"] = {"$lt": 0}
    
    if start_date or end_date:
        date_q = {}
        if start_date:
            date_q["$gte"] = start_date
        if end_date:
            date_q["$lte"] = end_date
        query["created_at"] = date_q

    eff_limit = limit if limit is not None else page_size
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else (max(page, 1) - 1) * eff_limit
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    cursor = db.transactions.find(query, {"_id": 0}).sort("created_at", -1).skip(eff_offset).limit(eff_limit)
    items = await cursor.to_list(eff_limit)
    total = await db.transactions.count_documents(query)
    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    return {
        "transactions": items,
        "items": items,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "total_pages": total_pages,
    }


@admin_api.post("/users/{user_id}/wallet/adjust")
async def admin_adjust_user_wallet(
    user_id: str,
    req: AdminWalletAdjustReq,
    admin=Depends(require_super_admin),
):
    """Adjust user wallet balance (credit or debit) with mandatory reason, atomic update, and transaction logging."""
    if not req.reason or not req.reason.strip():
        raise HTTPException(400, "Reason is mandatory for wallet adjustments")
    if req.amount == 0:
        raise HTTPException(400, "Adjustment amount cannot be zero")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")

    w = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    if not w:
        w = {"user_id": user_id, "balance": 0, "free_credits_granted": 0, "total_used": 0}
    
    before_balance = w.get("balance", 0)
    after_balance = before_balance + req.amount
    if after_balance < 0:
        raise HTTPException(400, f"Cannot debit wallet: balance cannot become negative (current balance: {before_balance}, debit: {abs(req.amount)})")

    ts = now().isoformat()
    if req.amount < 0:
        res = await db.wallets.update_one(
            {"user_id": user_id, "balance": {"$gte": abs(req.amount)}},
            {"$inc": {"balance": req.amount}, "$set": {"updated_at": ts}},
        )
        if res.modified_count == 0:
            raise HTTPException(400, "Insufficient wallet balance for debit")
    else:
        await db.wallets.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": req.amount}, "$set": {"updated_at": ts}},
            upsert=True,
        )

    txn_id = str(uuid.uuid4())
    txn_doc = {
        "id": txn_id,
        "user_id": user_id,
        "type": "admin_adjustment",
        "amount": 0,
        "credits": req.amount,
        "balance_before": before_balance,
        "balance_after": after_balance,
        "reason": req.reason.strip(),
        "reference": req.reference or "",
        "admin_id": admin["id"],
        "admin_email": admin.get("email"),
        "status": "success",
        "created_at": ts,
    }
    await db.transactions.insert_one(txn_doc.copy())
    txn_doc.pop("_id", None)

    await create_admin_audit_log(
        admin=admin,
        action="wallet_adjust",
        entity_type="wallet",
        entity_id=user_id,
        old_value={"balance": before_balance},
        new_value={"balance": after_balance},
        reason=req.reason.strip(),
        metadata={"amount": req.amount, "reference": req.reference or "", "transaction_id": txn_id},
    )

    return {
        "success": True,
        "user_id": user_id,
        "balance_before": before_balance,
        "balance_after": after_balance,
        "amount": req.amount,
        "reason": req.reason.strip(),
        "transaction_id": txn_id,
        "transaction": txn_doc,
    }


# ============================================================
# AUDIT LOGS ADMIN API
# ============================================================

@admin_api.get("/audit-logs")
async def admin_audit_logs(
    page: int = 1,
    page_size: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    action: Optional[str] = None,
    admin_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    q: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin=Depends(require_super_admin),
):
    """List recorded admin actions, newest first, with comprehensive filters."""
    query = {}
    if action and action != "all":
        query["action"] = action
    if admin_id and admin_id != "all":
        query["admin_id"] = admin_id
    if entity_type and entity_type != "all":
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    
    search_term = (search or q or "").strip()
    if search_term:
        q_re = re.compile(re.escape(search_term), re.IGNORECASE)
        query["$or"] = [
            {"action": q_re},
            {"admin_email": q_re},
            {"entity_id": q_re},
            {"reason": q_re},
            {"target": q_re},
        ]
    
    if start_date or end_date:
        date_q = {}
        if start_date:
            date_q["$gte"] = start_date
        if end_date:
            date_q["$lte"] = end_date
        query["timestamp"] = date_q

    eff_limit = limit if limit is not None else page_size
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else (max(page, 1) - 1) * eff_limit
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(eff_offset).limit(eff_limit)
    items = await cursor.to_list(eff_limit)
    total = await db.audit_logs.count_documents(query)
    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    return {
        "audit_logs": items,
        "items": items,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total_pages": total_pages,
    }


async def _admin_owner_map(user_ids: set) -> dict:
    """Batch-fetch public user info for a set of case owner ids."""
    if not user_ids:
        return {}
    cursor = db.users.find(
        {"id": {"$in": list(user_ids)}},
        {"_id": 0, "id": 1, "name": 1, "mobile": 1, "email": 1, "provider": 1, "active": 1},
    )
    return {u["id"]: u for u in await cursor.to_list(2000)}


# ============================================================
# APPLICATIONS ADMIN API
# ============================================================

@admin_api.get("/applications")
async def admin_list_applications(
    page: int = 1,
    page_size: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
    user_id: Optional[str] = None,
    template_id: Optional[str] = None,
    case_id: Optional[str] = None,
    format: Optional[str] = None,
    language: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    admin=Depends(require_super_admin),
):
    """List all generated documents across the platform with filters and owner info."""
    query = {}
    if user_id:
        query["user_id"] = user_id
    if template_id:
        query["template_id"] = template_id
    if case_id:
        query["case_id"] = case_id
    if format and format != "all":
        query["format"] = format
    if language and language != "all":
        query["language"] = language
    
    search_term = (search or q or "").strip()
    if search_term:
        q_re = re.compile(re.escape(search_term), re.IGNORECASE)
        query["$or"] = [
            {"filename": q_re},
            {"template_name": q_re},
            {"template_id": q_re},
            {"id": q_re},
        ]
    
    if start_date or end_date:
        date_q = {}
        if start_date:
            date_q["$gte"] = start_date
        if end_date:
            date_q["$lte"] = end_date
        query["created_at"] = date_q

    eff_limit = limit if limit is not None else page_size
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else (max(page, 1) - 1) * eff_limit
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    sort_direction = -1 if sort_order.lower() in ("desc", "-1") else 1
    sort_field = sort_by if sort_by in ("created_at", "filename", "template_name") else "created_at"

    cursor = db.applications.find(query, {"_id": 0}).sort(sort_field, sort_direction).skip(eff_offset).limit(eff_limit)
    items = await cursor.to_list(eff_limit)
    total = await db.applications.count_documents(query)
    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    u_ids = {a.get("user_id") for a in items if a.get("user_id")}
    owners = await _admin_owner_map(u_ids)
    for a in items:
        a["user"] = owners.get(a.get("user_id"))

    return {
        "applications": items,
        "items": items,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total_pages": total_pages,
    }


@admin_api.get("/applications/{application_id}")
async def admin_get_application(application_id: str, admin=Depends(require_super_admin)):
    """Full detail of a generated document: file metadata, case info, owner info, draft link."""
    app_doc = await db.applications.find_one({"id": application_id}, {"_id": 0})
    if not app_doc:
        raise HTTPException(404, "Application not found")
    
    owner = None
    if app_doc.get("user_id"):
        owner = await db.users.find_one({"id": app_doc["user_id"]}, {"_id": 0, "password_hash": 0})
    
    case_doc = None
    if app_doc.get("case_id"):
        c = await db.cases.find_one({"id": app_doc["case_id"]}, {"_id": 0})
        if c:
            case_doc = enrich_case(c)

    draft_doc = None
    if app_doc.get("user_id") and app_doc.get("template_id"):
        draft_doc = await db.drafts.find_one(
            {"user_id": app_doc["user_id"], "template_id": app_doc["template_id"]},
            {"_id": 0}
        )

    return {
        "application": app_doc,
        "id": app_doc.get("id"),
        "user_id": app_doc.get("user_id"),
        "template_id": app_doc.get("template_id"),
        "template_name": app_doc.get("template_name"),
        "case_id": app_doc.get("case_id"),
        "language": app_doc.get("language"),
        "format": app_doc.get("format"),
        "filename": app_doc.get("filename"),
        "file_size": app_doc.get("file_size"),
        "sha256": app_doc.get("sha256"),
        "generator_version": app_doc.get("generator_version"),
        "engine": app_doc.get("engine"),
        "font_family": app_doc.get("font_family"),
        "created_at": app_doc.get("created_at"),
        "user": owner,
        "case": case_doc,
        "draft": draft_doc,
    }


# ============================================================
# CASES ADMIN API
# ============================================================

@admin_api.get("/cases")
async def admin_list_cases(
    page: int = 1,
    page_size: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    q: Optional[str] = None,
    search: Optional[str] = None,
    status: str = "all",
    category: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    admin=Depends(require_super_admin),
):
    """List all cases with search, filters, pagination, and owner info."""
    query: dict = {}
    if status != "all":
        if status == "active":
            query["status"] = {"$ne": "archived"}
        else:
            query["status"] = status
    if user_id:
        query["user_id"] = user_id
    
    search_term = (search or q or "").strip()
    if search_term:
        q_re = re.compile(re.escape(search_term), re.IGNORECASE)
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
    
    if start_date or end_date:
        date_q = {}
        if start_date:
            date_q["$gte"] = start_date
        if end_date:
            date_q["$lte"] = end_date
        query["created_at"] = date_q

    eff_limit = limit if limit is not None else page_size
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else (max(page, 1) - 1) * eff_limit
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    sort_direction = -1 if sort_order.lower() in ("desc", "-1") else 1
    sort_field = sort_by if sort_by in ("created_at", "updated_at", "case_number", "nickname") else "updated_at"

    cursor = db.cases.find(query, {"_id": 0}).sort(sort_field, sort_direction).limit(2000)
    items = await cursor.to_list(2000)
    items = [enrich_case(c) for c in items]
    if category and category != "All" and category != "all":
        items = [c for c in items if c.get("category") == category]
    
    total = len(items)
    paged_items = items[eff_offset:eff_offset + eff_limit]
    owner_ids = {c.get("user_id") for c in paged_items if c.get("user_id")}
    owners = await _admin_owner_map(owner_ids)
    for c in paged_items:
        c["owner"] = owners.get(c.get("user_id"))

    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    return {
        "cases": paged_items,
        "items": paged_items,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total_pages": total_pages,
    }


@admin_api.get("/cases/{case_id}")
async def admin_get_case(case_id: str, admin=Depends(get_admin)):
    """Full admin case detail: enriched case, owner profile, drafts, and generated applications."""
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
    drafts = await db.drafts.find(
        {"case_id": case_id}, {"_id": 0}
    ).to_list(200)
    return {
        "case": c,
        "owner": owner,
        "applications": applications,
        "drafts": drafts,
    }


@admin_api.post("/cases/{case_id}/archive")
async def admin_archive_case(case_id: str, admin=Depends(get_admin)):
    """Admin archive of a case (preserves data, hides from active lawyer list)."""
    r = await db.cases.update_one(
        {"id": case_id},
        {"$set": {"status": "archived", "updated_at": now().isoformat()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    await create_admin_audit_log(admin=admin, action="case_archive", entity_type="case", entity_id=case_id)
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
    await create_admin_audit_log(admin=admin, action="case_restore", entity_type="case", entity_id=case_id)
    return {"success": True, "status": "active"}


# ============================================================
# PLANS ADMIN API
# ============================================================

@admin_api.get("/plans")
async def admin_list_plans(admin=Depends(require_super_admin)):
    """List all plans (including inactive) for admin management."""
    items = await _load_plans()
    items = sorted(items, key=lambda p: p.get("price") or 0)
    return [{**p, "per_template": round((p.get("price") or 0) / (p.get("credits") or 1), 2),
             "active": p.get("active") is not False} for p in items]


@admin_api.get("/plans/{plan_id}")
async def admin_get_plan(plan_id: str, admin=Depends(require_super_admin)):
    """Get single plan detail."""
    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        seed_plan = next((p for p in PLANS if p["id"] == plan_id), None)
        if seed_plan:
            plan = dict(seed_plan, active=True)
        else:
            raise HTTPException(404, "Plan not found")
    return {
        **plan,
        "per_template": round((plan.get("price") or 0) / (plan.get("credits") or 1), 2),
        "active": plan.get("active") is not False,
    }


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
    await create_admin_audit_log(
        admin=admin,
        action="plan_create",
        entity_type="plan",
        entity_id=plan_id,
        new_value=doc,
        metadata={"name": req.name, "price": req.price, "credits": req.credits},
    )
    doc.pop("_id", None)
    return {"success": True, "plan": _plan_public(doc)}


@admin_api.put("/plans/{plan_id}")
async def admin_update_plan(plan_id: str, req: AdminPlanReq, admin=Depends(require_super_admin)):
    """Update an existing plan (super admin only)."""
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    ts = now().isoformat()
    if not existing:
        seed = next((p for p in PLANS if p["id"] == plan_id), None)
        if not seed:
            raise HTTPException(404, "Plan not found")
        existing = {**seed, "active": True, "created_at": ts}
        await db.plans.insert_one(existing.copy())
    
    updates = {
        "name": req.name,
        "price": req.price,
        "credits": req.credits,
        "popular": req.popular,
        "description": req.description,
        "updated_by": admin["id"],
        "updated_at": ts,
    }
    await db.plans.update_one({"id": plan_id}, {"$set": updates})
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    await create_admin_audit_log(
        admin=admin,
        action="plan_update",
        entity_type="plan",
        entity_id=plan_id,
        old_value=existing,
        new_value=updated,
        metadata={"name": req.name, "price": req.price, "credits": req.credits},
    )
    return {"success": True, "plan": _plan_public(updated)}


@admin_api.post("/plans/{plan_id}/activate")
async def admin_activate_plan(plan_id: str, admin=Depends(require_super_admin)):
    """Activate a plan."""
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    ts = now().isoformat()
    if not existing:
        seed = next((p for p in PLANS if p["id"] == plan_id), None)
        if not seed:
            raise HTTPException(404, "Plan not found")
        existing = {**seed, "active": True, "created_at": ts}
        await db.plans.insert_one(existing.copy())
    
    await db.plans.update_one({"id": plan_id}, {"$set": {"active": True, "updated_at": ts, "updated_by": admin["id"]}})
    await create_admin_audit_log(
        admin=admin,
        action="plan_activate",
        entity_type="plan",
        entity_id=plan_id,
        old_value={"active": existing.get("active")},
        new_value={"active": True},
    )
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return {"success": True, "plan": _plan_public(updated)}


@admin_api.post("/plans/{plan_id}/deactivate")
async def admin_deactivate_plan(plan_id: str, admin=Depends(require_super_admin)):
    """Deactivate a plan."""
    existing = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    ts = now().isoformat()
    if not existing:
        seed = next((p for p in PLANS if p["id"] == plan_id), None)
        if not seed:
            raise HTTPException(404, "Plan not found")
        existing = {**seed, "active": True, "created_at": ts}
        await db.plans.insert_one(existing.copy())
    
    await db.plans.update_one({"id": plan_id}, {"$set": {"active": False, "updated_at": ts, "updated_by": admin["id"]}})
    await create_admin_audit_log(
        admin=admin,
        action="plan_deactivate",
        entity_type="plan",
        entity_id=plan_id,
        old_value={"active": existing.get("active")},
        new_value={"active": False},
    )
    updated = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    return {"success": True, "plan": _plan_public(updated)}


@admin_api.post("/plans/{plan_id}/status")
async def admin_set_plan_status(plan_id: str, req: AdminPlanStatusReq,
                                admin=Depends(require_super_admin)):
    """Activate/deactivate a plan (super admin only)."""
    if req.active:
        return await admin_activate_plan(plan_id, admin)
    else:
        return await admin_deactivate_plan(plan_id, admin)


# ============================================================
# CATALOG ADMIN API
# ============================================================

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
async def admin_list_catalog(kind: str, admin=Depends(require_super_admin)):
    """List all catalog entries (including inactive) for a catalog kind."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    items = await _load_catalog(kind)
    return [{**i, "active": i.get("active") is not False} for i in items]


@admin_api.get("/catalog/{kind}/{item_id}")
async def admin_get_catalog_item(kind: str, item_id: str, admin=Depends(require_super_admin)):
    """Get single catalog item."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    coll = _CATALOG_KINDS[kind][0]
    item = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Catalog entry not found")
    return {**item, "active": item.get("active") is not False}


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
    await create_admin_audit_log(
        admin=admin,
        action="catalog_create",
        entity_type="catalog",
        entity_id=f"{kind}:{item_id}",
        new_value=doc,
        metadata={"kind": kind, "en": req.en, "id": item_id},
    )
    doc.pop("_id", None)
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
    elif kind in ("courts", "police-stations", "talukas"):
        updates["district_id"] = req.district_id or "generic"
    elif kind == "laws" and req.sections is not None:
        updates["sections"] = [s.model_dump() for s in req.sections]
    await db[coll].update_one({"id": item_id}, {"$set": updates})
    await _refresh_catalog_maps()
    updated = await db[coll].find_one({"id": item_id}, {"_id": 0})
    await create_admin_audit_log(
        admin=admin,
        action="catalog_update",
        entity_type="catalog",
        entity_id=f"{kind}:{item_id}",
        old_value=existing,
        new_value=updated,
        metadata={"kind": kind, "en": req.en},
    )
    return {"success": True, "item": {**updated, "active": updated.get("active") is not False}}


@admin_api.post("/catalog/{kind}/{item_id}/status")
async def admin_set_catalog_status(kind: str, item_id: str, req: CatalogStatusReq,
                                   admin=Depends(require_super_admin)):
    """Activate/deactivate a catalog entry (super admin only)."""
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
    await create_admin_audit_log(
        admin=admin,
        action="catalog_status_update",
        entity_type="catalog",
        entity_id=f"{kind}:{item_id}",
        old_value={"active": existing.get("active")},
        new_value={"active": req.active},
        metadata={"kind": kind, "active": req.active, "en": existing.get("en")},
    )
    updated = await db[coll].find_one({"id": item_id}, {"_id": 0})
    return {"success": True, "item": {**updated, "active": updated.get("active") is not False}}


@admin_api.delete("/catalog/{kind}/{item_id}")
async def admin_delete_catalog_item(kind: str, item_id: str, hard: bool = False, admin=Depends(require_super_admin)):
    """Safe/soft deletion of a catalog item. If hard=True, permanently removes record if not referenced."""
    if kind not in _CATALOG_KINDS:
        raise HTTPException(404, "Unknown catalog kind")
    coll = _CATALOG_KINDS[kind][0]
    existing = await db[coll].find_one({"id": item_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Catalog entry not found")
    
    if hard:
        # Check referential safety
        ref = ""
        if kind == "case-types":
            if await db.cases.find_one({"case_type_id": item_id}): ref = "existing cases"
        elif kind == "laws":
            if await db.cases.find_one({"law_id": item_id}): ref = "existing cases"
        elif kind == "districts":
            if await db.users.find_one({"district": item_id}): ref = "existing users"
            elif await db.cases.find_one({"district_id": item_id}): ref = "existing cases"
            elif await db.courts.find_one({"district_id": item_id}): ref = "existing courts"
            elif await db.talukas.find_one({"district_id": item_id}): ref = "existing talukas"
            elif await db.police_stations.find_one({"district_id": item_id}): ref = "existing police stations"
        elif kind == "talukas":
            if await db.users.find_one({"taluka": item_id}): ref = "existing users"
            elif await db.cases.find_one({"taluka_id": item_id}): ref = "existing cases"
            elif await db.police_stations.find_one({"taluka_id": item_id}): ref = "existing police stations"
            elif await db.courts.find_one({"taluka_id": item_id}): ref = "existing courts"
        elif kind == "courts":
            if await db.cases.find_one({"court_id": item_id}): ref = "existing cases"
        elif kind == "police-stations":
            if await db.cases.find_one({"police_station_id": item_id}): ref = "existing cases"
            
        if ref:
            raise HTTPException(409, f"Cannot permanently delete '{item_id}' because it is currently referenced by {ref}. Please mark it as Inactive instead.")
            
        await db[coll].delete_one({"id": item_id})
    else:
        await db[coll].update_one(
            {"id": item_id},
            {"$set": {"active": False, "updated_by": admin["id"], "updated_at": now().isoformat()}},
        )
    await _refresh_catalog_maps()
    await create_admin_audit_log(
        admin=admin,
        action="catalog_deleted" if hard else "catalog_deactivated",
        entity_type=f"catalog/{kind}",
        entity_id=item_id,
        old_value=existing,
        new_value=None if hard else {"active": False},
        metadata={"hard": hard},
    )
    return {"success": True, "message": f"Catalog item '{item_id}' {'permanently deleted' if hard else 'deactivated'} successfully"}

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
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    format: Optional[str] = None,
    admin=Depends(get_admin),
):
    """List all templates from db.templates (single source of truth) with revision counts and pagination."""
    await _ensure_seed_complete()
    query: dict = {}
    if status and status != "all":
        query["status"] = status
    if category and category != "all":
        query["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
    
    search_term = (search or q or "").strip()
    if search_term:
        ql = re.escape(search_term)
        query["$or"] = [
            {"name_en": {"$regex": ql, "$options": "i"}},
            {"name_gu": {"$regex": ql, "$options": "i"}},
            {"id": {"$regex": ql, "$options": "i"}},
        ]

    is_paginated = (
        format == "paginated"
        or page is not None
        or page_size is not None
        or limit is not None
        or offset is not None
    ) and (format != "list")

    eff_limit = limit if limit is not None else (page_size if page_size is not None else 50)
    eff_limit = min(max(eff_limit, 1), 200)
    eff_offset = offset if offset is not None else ((max(page, 1) - 1) * eff_limit if page is not None else 0)
    eff_page = page if page is not None else (eff_offset // eff_limit + 1)

    sort_direction = -1 if sort_order.lower() in ("desc", "-1") else 1
    sort_field = sort_by if sort_by in ("updated_at", "created_at", "name_en", "name_gu", "version", "category") else "updated_at"

    if is_paginated:
        db_templates = await db.templates.find(query, {"_id": 0}).sort(sort_field, sort_direction).skip(eff_offset).limit(eff_limit).to_list(eff_limit)
    else:
        db_templates = await db.templates.find(query, {"_id": 0}).sort(sort_field, sort_direction).to_list(1000)

    total = await db.templates.count_documents(query)
    total_pages = math.ceil(total / eff_limit) if total > 0 else 1

    seed_ids = {t["id"] for t in [*TEMPLATES, *TEMPLATES_V2]}
    enriched = []
    for t in db_templates:
        rev_count = await db.template_revisions.count_documents({"template_id": t["id"]})
        enriched.append({
            **t,
            "revision_count": max(rev_count, 1),
            "is_seed_template": (t.get("source") == "seed" or t["id"] in seed_ids),
        })

    if not is_paginated:
        return enriched

    return {
        "templates": enriched,
        "items": enriched,
        "total": total,
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total_pages": total_pages,
    }


@admin_api.get("/templates/{template_id}")
async def admin_get_template(template_id: str, admin=Depends(require_super_admin)):
    """Get full template details from db.templates for admin editing, including revision count."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")
    rev_count = await db.template_revisions.count_documents({"template_id": template_id})
    return {
        **t,
        "revision_count": max(rev_count, 1),
        "current_version": t.get("version", 1),
    }


@admin_api.get("/templates/{template_id}/revisions")
async def admin_template_revisions_list(template_id: str, admin=Depends(require_super_admin)):
    """List immutable revision history from db.template_revisions."""
    await _ensure_seed_complete()
    revisions = await db.template_revisions.find(
        {"template_id": template_id}, {"_id": 0}
    ).sort("version", -1).to_list(200)
    if not revisions:
        revisions = await db.template_versions.find(
            {"template_id": template_id}, {"_id": 0}
        ).sort("version", -1).to_list(200)
    return {"revisions": revisions, "items": revisions, "total": len(revisions)}


@admin_api.post("/templates")
async def admin_create_template(req: AdminTemplateCreate, admin=Depends(require_super_admin)):
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
        "placeholders": req.placeholders,
        "content_en": normalize_legal_text(req.content_en),
        "content_gu": normalize_legal_text(req.content_gu),
        "format_version": NYAYSETU_LEGAL_FORMAT_V1,
        "settings": get_doc_settings(req.settings),
        "editor_content_en": req.editor_content_en,
        "editor_content_gu": req.editor_content_gu,
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
    await create_admin_audit_log(
        admin=admin,
        action="template_create",
        entity_type="template",
        entity_id=template_id,
        new_value=template_doc,
        metadata={"name_en": req.name_en, "category": req.category},
    )
    template_doc.pop("_id", None)
    return template_doc


@admin_api.post("/templates/import-word/analyze")
async def admin_import_word_analyze(req: WordImportAnalyzeReq, admin=Depends(require_super_admin)):
    """Analyze an uploaded .docx and propose a template definition (fields, draft, settings)."""
    try:
        data = decode_upload(req.file_name, req.content_base64)
        if req.file_name.lower().endswith(".odt"):
            analysis = analyze_odt(data, req.file_name)
        else:
            analysis = analyze_docx(data, req.file_name)
    except (DocxImportError, OdtImportError) as e:
        raise HTTPException(400, str(e))
    await create_admin_audit_log(
        admin=admin,
        action="template_import_analyze",
        entity_type="template",
        entity_id=req.file_name,
        metadata={"page_size": analysis["page_size"], "fields": len(analysis["fields"]),
                  "unmapped": len(analysis["unmapped"])},
    )
    return analysis


@admin_api.post("/templates/import-word")
async def admin_import_word_create(req: WordImportCreateReq, admin=Depends(require_super_admin)):
    """Create a draft template from an admin-reviewed Word import."""
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
    await create_admin_audit_log(
        admin=admin,
        action="template_import",
        entity_type="template",
        entity_id=template_id,
        metadata={"name_en": req.name_en, "category": req.category,
                  "fields": len(req.fields), "source": "word_docx"},
    )
    template_doc.pop("_id", None)
    return template_doc


@admin_api.put("/templates/{template_id}")
async def admin_update_template(template_id: str, req: AdminTemplateUpdate, admin=Depends(require_super_admin)):
    """Update a draft template. Published/locked templates cannot be directly modified."""
    await _ensure_seed_complete()
    _validate_template_settings(req.settings)
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")
    
    # Status is the authoritative lock: only PUBLISHED versions are immutable
    if t.get("status") == "published":
        raise HTTPException(403, "Published templates cannot be directly modified. Clone or edit to create a new draft version.")

    updates = {}
    for key in ["name_en", "name_gu", "category", "sub_category", "description", "tags", "aliases", "case_types", "courts", "jurisdiction", "content_en", "content_gu", "settings", "placeholders", "editor_content_en", "editor_content_gu"]:
        val = getattr(req, key, None)
        if val is not None:
            updates[key] = val
    if req.fields is not None:
        updates["fields"] = [f.model_dump() for f in req.fields]
    if updates:
        updates["updated_by"] = admin["id"]
        updates["updated_at"] = now().isoformat()
        updates["source"] = "admin_edited" if t.get("source") != "admin_created" else t["source"]
        updates["locked"] = False
        await db.templates.update_one({"id": template_id}, {"$set": updates})
        await create_admin_audit_log(
            admin=admin,
            action="template_update",
            entity_type="template",
            entity_id=template_id,
            old_value=t,
            new_value={**t, **updates},
            metadata={"field_count": len(updates.get("fields", t.get("fields", [])))},
        )
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return updated


@admin_api.post("/templates/{template_id}/publish")
async def admin_publish_template(template_id: str, admin=Depends(require_super_admin)):
    """Publish a draft template (makes it visible to lawyers) and creates a linear revision snapshot."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")
            
    if t.get("status") == "published" and t.get("locked"):
        raise HTTPException(400, "Template is already published and locked")

    missing = [k for k in ("name_en", "name_gu") if not str(t.get(k) or "").strip()]
    has_content = bool(str(t.get("content_en") or "").strip() or str(t.get("content_gu") or "").strip())
    if not has_content:
        missing.append("content (content_en/content_gu)")
    if missing:
        raise HTTPException(
            400,
            f"Cannot publish: this template record is incomplete (missing: {', '.join(missing)})."
        )
    if not isinstance(t.get("fields"), list):
        raise HTTPException(400, "Cannot publish: the template's field list is missing or invalid.")
        
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
    revision_doc = {
        "id": str(uuid.uuid4()),
        "template_id": template_id,
        "version": current_version,
        "title": t.get("name_en") or t.get("name_gu") or template_id,
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
        "placeholders": t.get("placeholders", []),
        "content_en": t.get("content_en", ""),
        "content_gu": t.get("content_gu", ""),
        "editor_content_en": t.get("editor_content_en"),
        "editor_content_gu": t.get("editor_content_gu"),
        "settings": t.get("settings") or {},
        "metadata": {
            "source": t.get("source", "admin_edited"),
            "status": "published",
        },
        "created_at": t.get("created_at") or ts,
        "created_by": admin["id"],
        "published_at": ts,
    }
    # Save snapshot into template_revisions (and keep template_versions in sync)
    await db.template_revisions.update_one(
        {"template_id": template_id, "version": current_version},
        {"$set": revision_doc},
        upsert=True,
    )
    await db.template_versions.update_one(
        {"template_id": template_id, "version": current_version},
        {"$set": revision_doc},
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
    await create_admin_audit_log(
        admin=admin,
        action="template_publish",
        entity_type="template",
        entity_id=template_id,
        metadata={"version": current_version},
    )
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "template": updated, "validation": validation}


@admin_api.post("/templates/{template_id}/unpublish")
async def admin_unpublish_template(template_id: str, admin=Depends(require_super_admin)):
    """Unpublish a template (reverts to draft)."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")
    ts = now().isoformat()
    await db.templates.update_one(
        {"id": template_id},
        {"$set": {"status": "draft", "locked": False, "updated_at": ts, "updated_by": admin["id"]}},
    )
    await create_admin_audit_log(
        admin=admin,
        action="template_unpublish",
        entity_type="template",
        entity_id=template_id,
    )
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "template": updated}


@admin_api.post("/templates/{template_id}/archive")
async def admin_archive_template(template_id: str, admin=Depends(require_super_admin)):
    """Archive a template (hides from lawyers, preserves in DB)."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id})
    if not t:
        raise HTTPException(404, "Template not found")
    await db.templates.update_one(
        {"id": template_id},
        {"$set": {"status": "archived", "updated_at": now().isoformat(), "updated_by": admin["id"]}},
    )
    await create_admin_audit_log(admin=admin, action="template_archive", entity_type="template", entity_id=template_id)
    return {"success": True, "status": "archived"}


@admin_api.post("/templates/{template_id}/restore")
async def admin_restore_template(template_id: str, admin=Depends(require_super_admin)):
    """Restore an archived template back to draft/published."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id})
    if not t:
        raise HTTPException(404, "Template not found")
    await db.templates.update_one(
        {"id": template_id},
        {"$set": {"status": "published", "updated_at": now().isoformat(), "updated_by": admin["id"]}},
    )
    await create_admin_audit_log(admin=admin, action="template_restore", entity_type="template", entity_id=template_id)
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "status": "published", "template": updated}


@admin_api.delete("/templates/{template_id}")
async def admin_delete_template(template_id: str, admin=Depends(require_super_admin)):
    """Permanently delete a template from db.templates.
    CRITICAL RULE: NEVER delete db.template_revisions, ensuring historical drafts remain 100% resolvable."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")
    
    await db.templates.delete_one({"id": template_id})
    await create_admin_audit_log(
        admin=admin,
        action="template_deleted",
        entity_type="template",
        entity_id=template_id,
        old_value=t,
        reason="Permanent deletion from template catalog",
    )
    return {
        "success": True,
        "message": f"Template '{template_id}' permanently deleted from catalog. Historical revisions preserved.",
    }


@admin_api.delete("/templates/{template_id}/draft")
async def admin_remove_shadow_draft(template_id: str, confirm: Optional[bool] = None,
                                    admin=Depends(require_super_admin)):
    """Remove an obsolete draft/archived DB record that is shadowing a seed template."""
    rec = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Shadow record not found")
    seed = next((s for s in [*TEMPLATES, *TEMPLATES_V2] if s["id"] == template_id), None)
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
    await create_admin_audit_log(
        admin=admin,
        action="template_shadow_draft_delete",
        entity_type="template",
        entity_id=template_id,
        metadata={"removed_status": status, "seed_id": template_id, "seed_name_gu": seed.get("name_gu")},
    )
    return {"success": True, "removed_status": status,
            "message": f"Removed the {status} shadow record for seed template '{template_id}'. The seed template is visible to lawyers again."}


@admin_api.post("/templates/{template_id}/clone")
async def admin_clone_template(template_id: str, req: Optional[AdminCloneReq] = None, admin=Depends(require_super_admin)):
    """Clone a template:
    1. If req.as_new_template=True -> creates a completely new separate template with new ID.
    2. Otherwise -> branches existing template into an editable new Draft version (version N+1) under the SAME stable template_id."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Template not found")

    ts = now().isoformat()
    as_new = req.as_new_template if req else False

    if as_new:
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
            "placeholders": t.get("placeholders", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "editor_content_en": t.get("editor_content_en"),
            "editor_content_gu": t.get("editor_content_gu"),
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
        await create_admin_audit_log(
            admin=admin,
            action="template_clone",
            entity_type="template",
            entity_id=template_id,
            metadata={"as_new_template": True, "new_id": new_id},
        )
        new_doc.pop("_id", None)
        return {"success": True, "template": new_doc, "new_version": 1}

    # Version branch of existing template (linear versioning under same template_id)
    if t.get("status") == "draft" and not t.get("locked"):
        raise HTTPException(400, "Template is already a draft. Edit it directly.")

    new_version = (t.get("version") or 0) + 1
    if t.get("version", 0) > 0:
        prev_version_doc = {
            "id": str(uuid.uuid4()),
            "template_id": template_id,
            "version": t["version"],
            "title": t.get("name_en") or t.get("name_gu") or template_id,
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
            "placeholders": t.get("placeholders", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "editor_content_en": t.get("editor_content_en"),
            "editor_content_gu": t.get("editor_content_gu"),
            "settings": t.get("settings"),
            "metadata": {
                "source": t.get("source", "seed"),
                "status": t.get("status", "published"),
            },
            "created_by": admin["id"],
            "created_at": t.get("created_at") or ts,
            "published_at": t.get("published_at") or ts,
        }
        await db.template_revisions.update_one(
            {"template_id": template_id, "version": t["version"]},
            {"$set": prev_version_doc},
            upsert=True,
        )
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
    )
    await create_admin_audit_log(
        admin=admin,
        action="template_clone",
        entity_type="template",
        entity_id=template_id,
        metadata={"as_new_template": False, "new_version": new_version},
    )
    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"success": True, "template": updated, "new_version": new_version}


@admin_api.post("/templates/{template_id}/duplicate")
async def admin_duplicate_template(template_id: str, req: Optional[AdminCloneReq] = None, admin=Depends(require_super_admin)):
    """Duplicate template as new independent template."""
    clone_req = req or AdminCloneReq(as_new_template=True)
    clone_req.as_new_template = True
    return await admin_clone_template(template_id, clone_req, admin)


@admin_api.post("/templates/bulk-status")
async def admin_bulk_template_status(req: AdminTemplateBulkStatusReq, admin=Depends(require_super_admin)):
    """Bulk archive or restore templates."""
    action = req.action.lower().strip()
    if action not in ("archive", "restore"):
        raise HTTPException(400, "Action must be archive or restore")
    
    target_status = "archived" if action == "archive" else "published"
    ts = now().isoformat()
    res = await db.templates.update_many(
        {"id": {"$in": req.template_ids}},
        {"$set": {"status": target_status, "updated_at": ts, "updated_by": admin["id"]}},
    )
    await create_admin_audit_log(
        admin=admin,
        action=f"template_bulk_{action}",
        entity_type="template",
        reason=req.reason or f"Bulk {action} on {len(req.template_ids)} templates",
        metadata={"template_ids": req.template_ids, "matched": res.matched_count, "modified": res.modified_count},
    )
    return {"success": True, "action": action, "affected_count": res.modified_count}


@admin_api.get("/templates/{template_id}/versions")
async def admin_template_versions(template_id: str, admin=Depends(require_super_admin)):
    """List all historical revisions/versions of a template."""
    await _ensure_seed_complete()
    revisions = await db.template_revisions.find(
        {"template_id": template_id}, {"_id": 0}
    ).sort("version", -1).to_list(200)
    if not revisions:
        revisions = await db.template_versions.find(
            {"template_id": template_id}, {"_id": 0}
        ).sort("version", -1).to_list(200)
    return revisions


@admin_api.post("/templates/{template_id}/preview")
async def admin_preview_template(template_id: str, req: Optional[AdminPreviewReq] = None, admin=Depends(get_admin)):
    """Preview a template with sample data. Supports live unsaved overrides from editor."""
    await _ensure_seed_complete()
    t = await db.templates.find_one({"id": template_id}, {"_id": 0})
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


async def migrate_templates_to_revisions(db_conn) -> dict:
    """Idempotently ensure every template in db.templates has a corresponding
    snapshot in db.template_revisions."""
    migrated = 0
    skipped = 0
    ts = now().isoformat()
    cursor = db_conn.templates.find({}, {"_id": 0})
    templates = await cursor.to_list(5000)
    for t in templates:
        t_id = t["id"]
        version = t.get("version", 1) or 1
        existing_rev = await db_conn.template_revisions.find_one(
            {"template_id": t_id, "version": version}
        )
        existing_ver = await db_conn.template_versions.find_one(
            {"template_id": t_id, "version": version}
        )
        if existing_rev and existing_ver:
            skipped += 1
            continue
        rev_doc = {
            "id": str(uuid.uuid4()),
            "template_id": t_id,
            "version": version,
            "title": t.get("name_en") or t.get("name_gu") or t_id,
            "name_en": t.get("name_en", ""),
            "name_gu": t.get("name_gu", ""),
            "category": t.get("category", "General"),
            "sub_category": t.get("sub_category"),
            "description": t.get("description"),
            "tags": t.get("tags", []),
            "aliases": t.get("aliases", []),
            "case_types": t.get("case_types", []),
            "courts": t.get("courts", []),
            "jurisdiction": t.get("jurisdiction"),
            "fields": t.get("fields", []),
            "placeholders": t.get("placeholders", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "editor_content_en": t.get("editor_content_en"),
            "editor_content_gu": t.get("editor_content_gu"),
            "settings": t.get("settings") or {},
            "metadata": {
                "source": t.get("source", "seed"),
                "status": t.get("status", "published"),
            },
            "created_at": t.get("created_at") or ts,
            "created_by": t.get("created_by") or "system",
            "published_at": t.get("published_at") or (ts if t.get("status") == "published" else None),
        }
        try:
            if not existing_rev:
                await db_conn.template_revisions.insert_one(rev_doc.copy())
            if not existing_ver:
                await db_conn.template_versions.insert_one(rev_doc.copy())
            migrated += 1
        except Exception:
            skipped += 1
    return {"migrated": migrated, "skipped": skipped, "total": len(templates)}


async def seed_templates(force: bool = False) -> dict:
    """One-time idempotent initialization of seed templates into db.templates.
    If seed_complete=True in db.system_settings and templates are present, skips execution (never overwrites or merges)."""
    setting = await db.system_settings.find_one({"key": "seed_complete"})
    all_seeds = [*TEMPLATES, *TEMPLATES_V2]
    if not force:
        template_count = await db.templates.count_documents({})
        if setting and setting.get("value") is True:
            logger.info("Template seeding skipped — seed_complete=True in system_settings.")
            return {
                "success": True,
                "seed_complete": True,
                "total_seed_templates": len(all_seeds),
                "created": 0,
                "skipped": template_count,
                "errors": 0,
                "created_ids": [],
                "skipped_ids": [t["id"] for t in all_seeds],
            }

    ts = now().isoformat()
    inserted = 0
    created_ids = []
    skipped_ids = []
    for t in all_seeds:
        existing = await db.templates.find_one({"id": t["id"]})
        if existing:
            skipped_ids.append(t["id"])
            continue
        template_doc = {
            "id": t["id"],
            "slug": t["id"],
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
            "fields": [
                {
                    "key": f["key"],
                    "label_en": f.get("label_en", ""),
                    "label_gu": f.get("label_gu", ""),
                    "type": f.get("type", "text"),
                    "required": f.get("required", True),
                    "order": idx,
                    **({k: v for k, v in f.items() if k not in ("key", "label_en", "label_gu", "type", "required", "order")})
                }
                for idx, f in enumerate(t.get("fields", []))
            ],
            "placeholders": t.get("placeholders", []),
            "content_en": t.get("content_en", ""),
            "content_gu": t.get("content_gu", ""),
            "format_version": NYAYSETU_LEGAL_FORMAT_V1,
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
        created_ids.append(t["id"])
        inserted += 1

    rev_res = await migrate_templates_to_revisions(db)
    await db.system_settings.update_one(
        {"key": "seed_complete"},
        {"$set": {"key": "seed_complete", "value": True, "completed_at": ts}},
        upsert=True,
    )
    if inserted:
        logger.info(f"Initialized {inserted} seed templates into db.templates (seed_complete=True).")

    return {
        "success": True,
        "seed_complete": True,
        "total_seed_templates": len(all_seeds),
        "created": inserted,
        "skipped": len(skipped_ids),
        "errors": 0,
        "created_ids": created_ids,
        "skipped_ids": skipped_ids,
        "revisions": rev_res,
    }


@admin_api.post("/templates/migrate-seed")
async def admin_migrate_seed(admin=Depends(require_super_admin)):
    """One-time migration: copy all seed templates into MongoDB and create initial revisions.
    Idempotent — does NOT overwrite existing templates."""
    return await seed_templates(force=True)


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
    await _ensure_index(db.users, "user_type")
    await _ensure_index(db.users, "active")
    await _ensure_index(db.users, "status")
    await _ensure_index(db.users, "created_at")
    # Firebase identity — sparse so legacy users (no firebase_uid) are unaffected,
    # unique so one Firebase UID can never map to two NyaySetu accounts.
    await _ensure_index(db.users, "firebase_uid", unique=True, sparse=True)
    await _ensure_index(db.users, "referral_code", unique=True, sparse=True)
    # Cases
    await _ensure_index(db.cases, "user_id")
    await _ensure_index(db.cases, "status")
    await _ensure_index(db.cases, "created_at")
    await _ensure_index(db.cases, [("user_id", 1), ("status", 1)])
    await _ensure_index(db.cases, [("user_id", 1), ("updated_at", -1)])
    # Wallets
    await _ensure_index(db.wallets, "user_id", unique=True)
    # Applications
    await _ensure_index(db.applications, "user_id")
    await _ensure_index(db.applications, "template_id")
    await _ensure_index(db.applications, "case_id")
    await _ensure_index(db.applications, "created_at")
    await _ensure_index(db.applications, [("user_id", 1), ("created_at", -1)])
    # Drafts
    await _ensure_index(db.drafts, "user_id")
    await _ensure_index(db.drafts, [("user_id", 1), ("template_id", 1), ("case_id", 1)])
    # Transactions
    await _ensure_index(db.transactions, "user_id")
    await _ensure_index(db.transactions, "type")
    await _ensure_index(db.transactions, "created_at")
    await _ensure_index(db.transactions, [("user_id", 1), ("created_at", -1)])
    # Audit Logs
    await _ensure_index(db.audit_logs, "admin_id")
    await _ensure_index(db.audit_logs, "action")
    await _ensure_index(db.audit_logs, "entity_type")
    await _ensure_index(db.audit_logs, "entity_id")
    await _ensure_index(db.audit_logs, "created_at")
    await _ensure_index(db.audit_logs, "timestamp")
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
    # User Sessions
    await _ensure_index(db.user_sessions, "id", unique=True)
    await _ensure_index(db.user_sessions, "token_hash", unique=True)
    await _ensure_index(db.user_sessions, "user_id")
    await _ensure_index(db.user_sessions, "expires_at")
    # Admin users & Sessions & Templates
    await _ensure_index(db.admin_users, "id", unique=True)
    await _ensure_index(db.admin_users, "email", unique=True)
    await _ensure_index(db.admin_sessions, "id", unique=True)
    await _ensure_index(db.admin_sessions, "token_hash", unique=True)
    await _ensure_index(db.admin_sessions, "admin_id")
    await _ensure_index(db.admin_sessions, "expires_at")
    await _ensure_index(db.templates, "id", unique=True)
    await _ensure_index(db.templates, "slug", unique=True)
    await _ensure_index(db.templates, [("status", 1), ("category", 1)])
    await _ensure_index(db.template_versions, [("template_id", 1), ("version", 1)], unique=True)
    await _ensure_index(db.template_revisions, [("template_id", 1), ("version", 1)], unique=True)
    await _ensure_index(db.system_settings, "key", unique=True)
    await _ensure_index(db.case_forms, "case_type_id", unique=True)
    logger.info("MongoDB indexes ensured.")
    # Seed super admin and static catalogs
    await seed_plans()
    await seed_catalogs()
    await seed_super_admin()
    await seed_templates()
    await migrate_templates_to_revisions(db)


@app.on_event("shutdown")
async def shutdown():
    client.close()
