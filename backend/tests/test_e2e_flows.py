"""NyaySetu Pro Phase G — End-to-End acceptance flows (API level).

Walks the complete approved user journeys:

Flow A — New lawyer:  OTP signup -> profile -> signup wallet credits
Flow B — Client + Case: client lookup (found/not-found) -> create case with an
        admin-configured dynamic case form (text/date/select/radio/checkbox)
        -> values persist -> edit -> reload
Flow C — Single application: template without a case -> fill required fields
        -> preview -> PDF -> DOCX -> credit deducted exactly once
        -> transaction recorded
Flow D — Full case application: case -> template autofill -> preview contains
        human-readable labels -> PDF -> DOCX
Flow E — Admin form configuration: admin saves a case form -> lawyer sees it
        -> values persist through the document pipeline

IMPORTANT (test isolation): like test_admin_catalog.py, this module seeds the
catalogs per test (clean_db fixture). The in-memory catalog maps are refreshed
by admin catalog mutations, so they must always be rebuilt from a DB that
contains the full seed catalog — otherwise later test modules would see
truncated maps and fail with "Invalid case_type_id".
"""

import os
import sys
import base64
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_e2e")

import pytest
import pytest_asyncio
import bcrypt

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_e2e"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_admin_token
from httpx import AsyncClient, ASGITransport

API = "/api"

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs", "plans",
               "case_types", "laws", "districts", "courts", "police_stations",
               "case_forms"]


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll in COLLECTIONS:
        await db[coll].drop()
    # Seed catalogs like startup does — keeps the shared in-memory catalog
    # maps complete when admin mutations refresh them.
    await server.seed_catalogs()
    yield
    for coll in COLLECTIONS:
        await db[coll].drop()


async def fresh_lawyer(client):
    """Flow A: OTP signup -> token -> user."""
    mobile = f"99{int(time.time() * 1000) % 100000000:08d}"
    r = await client.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_new"] is True
    return data["token"], mobile, data["user"]["id"]


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def seed_admin(client):
    """Flow E: super-admin user with a valid admin token."""
    admin_id = f"e2e-admin-{uuid.uuid4().hex[:8]}"
    doc = {
        "id": admin_id,
        "email": f"{admin_id}@nyaysetu.test",
        "password_hash": bcrypt.hashpw(b"E2eAdminPass!1", bcrypt.gensalt()).decode(),
        "name": "E2E Admin",
        "role": "super_admin",
        "active": True,
        "created_at": server.now(),
    }
    await server.db.admin_users.insert_one(doc)
    return make_admin_token(admin_id, doc["email"], "super_admin")


class TestFlowA_NewLawyer:
    @pytest.mark.asyncio
    async def test_signup_profile_and_signup_credits(self, client, clean_db):
        token, mobile, _ = await fresh_lawyer(client)
        h = H(token)
        r = await client.get(f"{API}/profile/me", headers=h)
        assert r.status_code == 200
        assert r.json()["mobile"] == mobile
        w = (await client.get(f"{API}/wallet", headers=h)).json()
        assert w["balance"] == 5, f"expected 5 signup credits, got {w}"


class TestFlowB_ClientAndCase:
    @pytest.mark.asyncio
    async def test_client_lookup_and_dynamic_case_lifecycle(self, client, clean_db):
        token, _, _ = await fresh_lawyer(client)
        h = H(token)

        # --- Client lookup: unknown mobile -> not found, manual entry allowed ---
        r = await client.get(f"{API}/clients/lookup?mobile=9999990000", headers=h)
        assert r.status_code == 200
        assert r.json().get("found") is False

        # --- Admin configures the catalog entry + a dynamic case form (Flow E) ---
        admin_tok = await seed_admin(client)
        ah = {"Authorization": f"Bearer {admin_tok}", "Content-Type": "application/json"}
        r = await client.post(f"{API}/admin/catalog/case-types", headers=ah,
                              json={"en": "Motor Accident Claim", "gu": "મોટર અકસ્માત દાવો", "cat": "Civil"})
        assert r.status_code == 200, r.text
        case_type_id = r.json()["item"]["id"]
        cfg = {
            "name_en": "Motor Accident Claim",
            "name_gu": "મોટર અકસ્માત દાવો",
            "category": "Civil",
            "fields": [
                {"key": "incident_date", "label_en": "Date of Incident", "label_gu": "ઘટનાની તારીખ",
                 "type": "date", "required": True, "order": 1},
                {"key": "vehicle_no", "label_en": "Vehicle Number", "label_gu": "વાહન નંબર",
                 "type": "text", "required": True, "order": 2},
                {"key": "fault", "label_en": "Fault", "label_gu": "ખામી",
                 "type": "select", "required": True, "order": 3,
                 "options": [{"value": "driver", "label_en": "Driver", "label_gu": "ચાલક"},
                             {"value": "other", "label_en": "Other", "label_gu": "અન્ય"}]},
                {"key": "claim_type", "label_en": "Claim Type", "label_gu": "દાવાનો પ્રકાર",
                 "type": "radio", "required": True, "order": 4,
                 "options": [{"value": "injury", "label_en": "Injury", "label_gu": "ઈજા"},
                             {"value": "property", "label_en": "Property", "label_gu": "મિલકત"}]},
                {"key": "legal_help", "label_en": "Legal Help Needed", "label_gu": "કાયદાકીય મદદ",
                 "type": "checkbox", "required": False, "order": 5,
                 "options": [{"value": "counsel", "label_en": "Counsel", "label_gu": "વકીલ"},
                             {"value": "compensation", "label_en": "Compensation", "label_gu": "વળતર"}]},
                {"key": "claim_amount", "label_en": "Claim Amount", "label_gu": "દાવાની રકમ",
                 "type": "number", "required": False, "order": 6},
            ],
        }
        r = await client.post(f"{API}/admin/case-forms/{case_type_id}", headers=ah, json=cfg)
        assert r.status_code == 200, r.text

        # --- Lawyer reads the config and creates the case with all field types ---
        r = await client.get(f"{API}/catalog/case-forms/{case_type_id}", headers=h)
        assert r.status_code == 200
        keys = {f["key"] for f in r.json()["fields"]}
        assert keys == {"incident_date", "vehicle_no", "fault", "claim_type", "legal_help", "claim_amount"}

        r = await client.post(f"{API}/cases", headers=h, json={
            "language": "en",
            "nickname": "E2E MAC Case",
            "case_number": "MAC/42/2026",
            "case_type_id": case_type_id,
            "party_name": "E2E Applicant",
            "opposite_party": "E2E Respondent",
            "district_id": "ahmedabad",
            "client_mobile": "9999990000",
            "custom_fields": {
                "incident_date": "2026-01-15",
                "vehicle_no": "GJ-01-AB-1234",
                "fault": "driver",
                "claim_type": "injury",
                "legal_help": "counsel,compensation",
                "claim_amount": "500000",
            },
        })
        assert r.status_code == 200, r.text
        case_id = r.json()["id"]

        # --- Reload: every custom field persisted ---
        c = (await client.get(f"{API}/cases/{case_id}", headers=h)).json()
        cf = c.get("custom_fields", {})
        assert cf.get("incident_date") == "2026-01-15"
        assert cf.get("vehicle_no") == "GJ-01-AB-1234"
        assert cf.get("fault") == "driver"
        assert cf.get("claim_type") == "injury"
        assert cf.get("legal_help") == "counsel,compensation"
        assert cf.get("claim_amount") == "500000"
        # Human-readable labels resolve from catalog ids
        assert c.get("district_label") and c["district_label"] != "ahmedabad"
        assert c.get("case_type_label") == "Motor Accident Claim"

        # --- Edit: change one value, keep the rest, reload ---
        r = await client.put(f"{API}/cases/{case_id}", headers=h, json={
            "language": "en",
            "nickname": "E2E MAC Case",
            "case_number": "MAC/42/2026",
            "case_type_id": case_type_id,
            "party_name": "E2E Applicant",
            "opposite_party": "E2E Respondent",
            "district_id": "ahmedabad",
            "client_mobile": "9999990000",
            "custom_fields": {
                "incident_date": "2026-02-20",   # changed
                "vehicle_no": "GJ-01-AB-1234",
                "fault": "driver",
                "claim_type": "injury",
                "legal_help": "counsel,compensation",
                "claim_amount": "500000",
            },
        })
        assert r.status_code == 200, r.text
        c2 = (await client.get(f"{API}/cases/{case_id}", headers=h)).json()
        assert c2["custom_fields"]["incident_date"] == "2026-02-20"
        assert c2["custom_fields"]["claim_amount"] == "500000"  # untouched value survives
        return case_id, token


class TestFlowC_SingleApplication:
    @pytest.mark.asyncio
    async def test_application_without_case_and_credit_deduction(self, client, clean_db):
        token, _, _ = await fresh_lawyer(client)
        h = H(token)
        # Single application: no case_id required
        r = await client.post(f"{API}/applications/preview", headers=h,
                              json={"template_id": "adjournment", "language": "en",
                                    "values": {"next_date": "20-01-2026", "reason": "Illness"}})
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        assert "Illness" in content and "ADJOURNMENT" in content.upper()

        wb = (await client.get(f"{API}/wallet", headers=h)).json()["balance"]
        # PDF download consumes exactly one credit
        r = await client.post(f"{API}/applications/download", headers=h,
                              json={"template_id": "adjournment", "language": "en", "format": "pdf",
                                    "values": {"next_date": "20-01-2026", "reason": "E2E"}})
        assert r.status_code == 200
        raw = base64.b64decode(r.json()["base64"])
        assert raw.startswith(b"%PDF")
        # DOCX download consumes exactly one credit
        r = await client.post(f"{API}/applications/download", headers=h,
                              json={"template_id": "adjournment", "language": "gu", "format": "docx",
                                    "values": {"next_date": "૨૦-૦૧-૨૦૨૬", "reason": "ટેસ્ટ"}})
        assert r.status_code == 200
        raw = base64.b64decode(r.json()["base64"])
        assert raw[:2] == b"PK"
        wa = (await client.get(f"{API}/wallet", headers=h)).json()["balance"]
        assert wa == wb - 2, f"expected exactly 2 credits consumed, got {wb - wa}"
        # Transaction records exist for both purchases and document consumption
        txs = (await client.get(f"{API}/transactions", headers=h)).json()
        assert len(txs) >= 2
        doc_tx = [t for t in txs if t.get("type") == "document"]
        assert len(doc_tx) == 2
        assert all(t["credits"] == -1 and t["status"] == "success" for t in doc_tx)


class TestFlowD_FullCaseApplication:
    @pytest.mark.asyncio
    async def test_case_autofill_into_document(self, client, clean_db):
        flow_b = TestFlowB_ClientAndCase()
        case_id, token = await flow_b.test_client_lookup_and_dynamic_case_lifecycle(client, clean_db)
        h = H(token)
        # Case-driven application: template consumes the case
        r = await client.post(f"{API}/applications/preview", headers=h,
                              json={"template_id": "adjournment", "case_id": case_id,
                                    "language": "en",
                                    "values": {"next_date": "25-02-2026", "reason": "Hearing clash"}})
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        # Autofilled case data appears with human-readable labels, not raw ids
        assert "MAC/42/2026" in content          # case number
        assert "E2E Applicant" in content        # party name
        assert "Respondent" in content           # opposite party value rendered
        assert "Ahmedabad" in content            # district label (no raw id "ahmedabad")
        assert "e2e_mac" not in content          # no raw case-type id leaks
        assert "ahmedabad" not in content        # no raw district id leaks
        assert "Hearing clash" in content        # manual field value rendered

        # PDF + DOCX from the same logical data
        for fmt in ("pdf", "docx"):
            r = await client.post(f"{API}/applications/download", headers=h,
                                  json={"template_id": "adjournment", "case_id": case_id,
                                        "language": "en", "format": fmt,
                                        "values": {"next_date": "25-02-2026", "reason": "Hearing clash"}})
            assert r.status_code == 200
            raw = base64.b64decode(r.json()["base64"])
            assert raw.startswith(b"%PDF" if fmt == "pdf" else b"PK")
