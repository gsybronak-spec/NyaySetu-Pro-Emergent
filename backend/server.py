"""NyaySetu Pro - FastAPI backend."""

import os
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import jwt

from seed_data import CASE_TYPES, LAWS, DISTRICTS, COURTS, POLICE_STATIONS, TEMPLATES, PLANS, QUOTES
from doc_generator import generate_pdf, generate_docx, render_template

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "nyaysetu-dev-secret-please-change")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="NyaySetu Pro API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyaysetu")


# ============================================================
# MODELS
# ============================================================

class SendOtpReq(BaseModel):
    mobile: str

class VerifyOtpReq(BaseModel):
    mobile: str
    otp: str
    referral_code: Optional[str] = None

class GoogleSessionReq(BaseModel):
    session_id: str
    referral_code: Optional[str] = None

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bar_council_no: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    court: Optional[str] = None

class CaseCreate(BaseModel):
    language: str = "en"
    nickname: Optional[str] = None
    case_number: Optional[str] = None
    case_type_id: Optional[str] = None
    case_type_custom: Optional[str] = None
    complaint_type: Optional[str] = None  # private/police/other
    law_id: Optional[str] = None
    law_custom: Optional[str] = None
    section_id: Optional[str] = None
    party_name: Optional[str] = None
    opposite_party: Optional[str] = None
    court: Optional[str] = None
    court_id: Optional[str] = None
    court_custom: Optional[str] = None
    district_id: Optional[str] = None
    police_station: Optional[str] = None
    police_station_id: Optional[str] = None
    police_station_custom: Optional[str] = None
    complaint_custom: Optional[str] = None
    notes: Optional[str] = None

class CaseUpdate(CaseCreate):
    pass

class GenerateReq(BaseModel):
    template_id: str
    case_id: Optional[str] = None
    language: str = "en"
    values: dict = {}
    filename: Optional[str] = None

class DownloadReq(BaseModel):
    template_id: str
    case_id: Optional[str] = None
    language: str = "en"
    values: dict = {}
    format: str = "pdf"  # pdf | docx
    filename: Optional[str] = None
    consume_credit: bool = True

class PurchaseReq(BaseModel):
    plan_id: str

class DraftSave(BaseModel):
    template_id: str
    case_id: Optional[str] = None
    language: str = "en"
    values: dict = {}


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now(timezone.utc)

def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "iat": int(now().timestamp()), "exp": int((now() + timedelta(days=90)).timestamp())}
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
    return user


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
    """Create a user + wallet with 5 free credits and a referral code."""
    user_id = str(uuid.uuid4())
    code = await gen_referral_code()
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": email,
        "name": name,
        "picture": picture,
        "provider": provider,
        "bar_council_no": None,
        "state": None,
        "district": None,
        "court": None,
        "language_pref": "en",
        "theme_pref": "light",
        "referral_code": code,
        "referred_by": None,
        "favourite_courts": [],
        "created_at": now().isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 5,
        "free_credits_granted": 5,
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

@api.post("/auth/send-otp")
async def send_otp(req: SendOtpReq):
    mobile = req.mobile.strip()
    if len(mobile) < 10:
        raise HTTPException(400, "Invalid mobile number")
    # Mock: log OTP (always 123456)
    logger.info(f"[MOCK-OTP] mobile={mobile} otp=123456")
    return {"success": True, "message": "OTP sent successfully", "hint": "Use 123456 for testing"}


@api.post("/auth/verify-otp")
async def verify_otp(req: VerifyOtpReq):
    mobile = req.mobile.strip()
    otp = req.otp.strip()
    # Accept 123456 or any 6-digit code for mock
    if not (otp == "123456" or (len(otp) == 6 and otp.isdigit())):
        raise HTTPException(400, "Invalid OTP")

    user = await db.users.find_one({"mobile": mobile}, {"_id": 0})
    is_new = False
    if not user:
        is_new = True
        user = await create_new_user(mobile=mobile, provider="mobile")
        await apply_referral(req.referral_code, user)

    user_clean = {k: v for k, v in user.items() if k != "_id"}
    token = make_token(user["id"])
    return {"token": token, "user": user_clean, "is_new": is_new}


EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


@api.post("/auth/google-session")
async def google_session(req: GoogleSessionReq):
    """Exchange an Emergent OAuth session_id for our JWT. Upsert user by email."""
    async with httpx.AsyncClient(timeout=15) as http:
        try:
            r = await http.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": req.session_id})
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

    user_clean = {k: v for k, v in user.items() if k != "_id"}
    token = make_token(user["id"])
    return {"token": token, "user": user_clean, "is_new": is_new}


# ============================================================
# PROFILE
# ============================================================

@api.get("/profile/me")
async def me(user=Depends(get_user)):
    return user

@api.put("/profile/update")
async def update_profile(req: ProfileUpdate, user=Depends(get_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return u


# ============================================================
# CATALOG
# ============================================================

@api.get("/catalog/case-types")
async def case_types():
    return CASE_TYPES

@api.get("/catalog/laws")
async def laws():
    return LAWS

@api.get("/catalog/laws/{law_id}/sections")
async def law_sections(law_id: str):
    law = next((l for l in LAWS if l["id"] == law_id), None)
    if not law:
        return []
    return law["sections"]

@api.get("/catalog/districts")
async def districts():
    return DISTRICTS

@api.get("/catalog/courts")
async def courts(district_id: Optional[str] = None):
    generic = [c for c in COURTS if c["district_id"] == "generic"]
    if district_id:
        specific = [c for c in COURTS if c["district_id"] == district_id]
        return specific + generic
    return COURTS

@api.get("/catalog/police-stations")
async def police_stations(district_id: Optional[str] = None):
    if district_id:
        return [p for p in POLICE_STATIONS if p["district_id"] == district_id]
    return POLICE_STATIONS

@api.get("/catalog/plans")
async def plans():
    return PLANS

@api.get("/catalog/quote")
async def daily_quote():
    idx = now().day % len(QUOTES)
    return {"quote": QUOTES[idx]}


# ============================================================
# CASES
# ============================================================

_CASE_TYPE_MAP = {c["id"]: c for c in CASE_TYPES}
_LAW_MAP = {l["id"]: l for l in LAWS}
_DISTRICT_MAP = {d["id"]: d for d in DISTRICTS}
_COURT_MAP = {c["id"]: c for c in COURTS}
_PS_MAP = {p["id"]: p for p in POLICE_STATIONS}
_COMPLAINT_LABELS = {"private": "Private Complaint", "police": "Police Complaint", "other": "Other"}


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


@api.post("/cases")
async def create_case(req: CaseCreate, user=Depends(get_user)):
    case_id = str(uuid.uuid4())
    doc = {
        "id": case_id,
        "user_id": user["id"],
        "status": "active",
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
        "last_used_template": None,
        "application_count": 0,
        **req.model_dump(),
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
    updates["updated_at"] = now().isoformat()
    r = await db.cases.update_one({"id": case_id, "user_id": user["id"]}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    c = await db.cases.find_one({"id": case_id}, {"_id": 0})
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

def public_template(t: dict) -> dict:
    return {
        "id": t["id"],
        "name_en": t["name_en"],
        "name_gu": t["name_gu"],
        "category": t["category"],
        "fields": t["fields"],
    }

@api.get("/templates")
async def list_templates(q: Optional[str] = None, category: Optional[str] = None):
    items = [public_template(t) for t in TEMPLATES]
    if category:
        items = [t for t in items if t["category"].lower() == category.lower()]
    if q:
        ql = q.lower().strip()
        matched = []
        for t in TEMPLATES:
            all_aliases = [t["name_en"].lower(), t["name_gu"].lower()] + [a.lower() for a in t.get("aliases", [])]
            if any(ql in a for a in all_aliases):
                matched.append(public_template(t))
        items = matched
    return items

@api.get("/templates/{template_id}")
async def get_template(template_id: str):
    t = next((x for x in TEMPLATES if x["id"] == template_id), None)
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

async def build_render_context(user: dict, case: Optional[dict], values: dict, language: str) -> dict:
    ctx = dict(values or {})
    # Advocate
    ctx.setdefault("advocate_name", user.get("name") or "Advocate")
    # Today (formatted)
    ctx["today"] = now().strftime("%d-%m-%Y")
    # District / court
    district_name = ""
    if case:
        did = case.get("district_id") or user.get("district")
        d = next((x for x in DISTRICTS if x["id"] == did), None)
        if d:
            district_name = d["gu"] if language == "gu" else d["en"]
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
    else:
        d = next((x for x in DISTRICTS if x["id"] == user.get("district")), None)
        ctx.setdefault("district", (d["gu"] if language == "gu" else d["en"]) if d else (user.get("district") or ""))
        ctx.setdefault("court", user.get("court") or "")
        ctx.setdefault("case_number", "")
        ctx.setdefault("case_type", "")
        ctx.setdefault("party_name", "")
    return ctx


@api.post("/applications/preview")
async def preview_application(req: GenerateReq, user=Depends(get_user)):
    t = next((x for x in TEMPLATES if x["id"] == req.template_id), None)
    if not t:
        raise HTTPException(404, "Template not found")
    case = None
    if req.case_id:
        case = await db.cases.find_one({"id": req.case_id, "user_id": user["id"]}, {"_id": 0})
    ctx = await build_render_context(user, case, req.values, req.language)
    tpl = t["content_gu"] if req.language == "gu" else t["content_en"]
    rendered = render_template(tpl, ctx)
    return {"content": rendered, "language": req.language, "template_id": t["id"]}


@api.post("/applications/download")
async def download_application(req: DownloadReq, user=Depends(get_user)):
    t = next((x for x in TEMPLATES if x["id"] == req.template_id), None)
    if not t:
        raise HTTPException(404, "Template not found")

    # Check wallet
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    if req.consume_credit and (not wallet or wallet.get("balance", 0) < 1):
        raise HTTPException(402, "Insufficient template credits. Please purchase a plan.")

    case = None
    if req.case_id:
        case = await db.cases.find_one({"id": req.case_id, "user_id": user["id"]}, {"_id": 0})
    ctx = await build_render_context(user, case, req.values, req.language)
    tpl = t["content_gu"] if req.language == "gu" else t["content_en"]
    rendered = render_template(tpl, ctx)

    if req.format == "docx":
        b64 = generate_docx(rendered, req.language)
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        b64 = generate_pdf(rendered, req.language)
        mime = "application/pdf"

    # Consume credit atomically
    if req.consume_credit:
        r = await db.wallets.update_one(
            {"user_id": user["id"], "balance": {"$gte": 1}},
            {"$inc": {"balance": -1, "total_used": 1}, "$set": {"updated_at": now().isoformat()}},
        )
        if r.modified_count == 0:
            raise HTTPException(402, "Insufficient credits")

    # Log usage
    filename = req.filename or f"{t['id']}_{now().strftime('%Y%m%d_%H%M%S')}.{req.format}"
    await db.applications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "template_id": t["id"],
        "template_name": t["name_en"],
        "case_id": req.case_id,
        "language": req.language,
        "format": req.format,
        "filename": filename,
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
        w = {"user_id": user["id"], "balance": 5, "free_credits_granted": 5, "total_used": 0}
        await db.wallets.insert_one(w.copy())
    return {"balance": w.get("balance", 0), "total_used": w.get("total_used", 0)}


@api.post("/purchase/mock")
async def mock_purchase(req: PurchaseReq, user=Depends(get_user)):
    plan = next((p for p in PLANS if p["id"] == req.plan_id), None)
    if not plan:
        raise HTTPException(404, "Plan not found")
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


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
