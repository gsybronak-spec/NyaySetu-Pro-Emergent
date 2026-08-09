"""NyaySetu Pro - FastAPI backend."""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import jwt

from seed_data import CASE_TYPES, LAWS, DISTRICTS, TEMPLATES, PLANS, QUOTES
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
    district_id: Optional[str] = None
    police_station: Optional[str] = None
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


# ============================================================
# AUTH (MOCK OTP)
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
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "mobile": mobile,
            "name": None,
            "email": None,
            "bar_council_no": None,
            "state": None,
            "district": None,
            "court": None,
            "language_pref": "en",
            "theme_pref": "light",
            "created_at": now().isoformat(),
        }
        await db.users.insert_one(user.copy())
        # Init wallet with 5 free templates
        await db.wallets.insert_one({
            "user_id": user_id,
            "balance": 5,
            "free_credits_granted": 5,
            "total_used": 0,
            "updated_at": now().isoformat(),
        })

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

@api.post("/cases")
async def create_case(req: CaseCreate, user=Depends(get_user)):
    case_id = str(uuid.uuid4())
    doc = {
        "id": case_id,
        "user_id": user["id"],
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
        "last_used_template": None,
        **req.model_dump(),
    }
    await db.cases.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc

@api.get("/cases")
async def list_cases(user=Depends(get_user), q: Optional[str] = None):
    cursor = db.cases.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1)
    items = await cursor.to_list(500)
    if q:
        ql = q.lower()
        items = [c for c in items if
                 ql in (c.get("nickname") or "").lower()
                 or ql in (c.get("case_number") or "").lower()
                 or ql in (c.get("party_name") or "").lower()
                 or ql in (c.get("case_type_id") or "").lower()]
    return items

@api.get("/cases/{case_id}")
async def get_case(case_id: str, user=Depends(get_user)):
    c = await db.cases.find_one({"id": case_id, "user_id": user["id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Case not found")
    return c

@api.put("/cases/{case_id}")
async def update_case(case_id: str, req: CaseUpdate, user=Depends(get_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updates["updated_at"] = now().isoformat()
    r = await db.cases.update_one({"id": case_id, "user_id": user["id"]}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Case not found")
    c = await db.cases.find_one({"id": case_id}, {"_id": 0})
    return c

@api.delete("/cases/{case_id}")
async def delete_case(case_id: str, user=Depends(get_user)):
    await db.cases.delete_one({"id": case_id, "user_id": user["id"]})
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
        ctx.setdefault("court", case.get("court") or "")
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
            {"$set": {"last_used_template": t["name_en"], "updated_at": now().isoformat()}},
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
