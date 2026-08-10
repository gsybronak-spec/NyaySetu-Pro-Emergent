"""Phase 1 — Core Data Integrity regression tests.

Covers the locked Phase-1 pipeline:
  Admin Case Form -> Case Form API -> Lawyer Case Creation -> custom_fields
  -> MongoDB -> Case Edit -> Case Detail -> Template Autofill -> Preview -> PDF/DOCX

Specific fixes verified:
- custom_fields are persisted on case create AND merged on update (no silent drops)
- flat client detail fields (client_name/mobile/email/address/district) are stored (D3)
- autofill_map resolves against the CLIENT context, server-side (D1)
- build_render_context autofills police_station, client_name, law/section, and merges
  case.custom_fields into document context (D2)
- raw district ids are never printed in documents (label guard)
- generic case-form fallback returns no client-identity fields (dedicated Client Details)
"""

import os
import sys
import uuid
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_phase1")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_phase1"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token
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
                 "template_versions", "case_forms"]:
        await db[coll].drop()
    yield
    for coll in ["users", "wallets", "cases", "applications", "drafts",
                 "transactions", "referrals", "admin_users", "templates",
                 "template_versions", "case_forms"]:
        await db[coll].drop()


async def create_test_admin(email="admin@test.com", password="TestPass123!"):
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hashed,
        "name": "Test Admin",
        "role": "super_admin",
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin_doc.copy())
    return admin_doc


async def create_test_lawyer(mobile=None):
    mobile = mobile or f"9{int(time.time() * 1000) % 1000000000:09d}"
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": None,
        "name": "Test Lawyer",
        "provider": "mobile",
        "bar_council_no": None,
        "state": None,
        "district": None,
        "court": None,
        "language_pref": "en",
        "theme_pref": "light",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "referred_by": None,
        "favourite_courts": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 5,
        "free_credits_granted": 5,
        "total_used": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return user, make_token(user_id)


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# 0. Auth null-index safety — live bug: users storing email/mobile as null
#    collide on the unique sparse indexes and 500 on the 2nd signup.
# ============================================================

class TestAuthNullIndexSafety:
    @pytest.mark.asyncio
    async def test_two_mobile_signups_succeed(self, client, clean_db):
        for i in range(2):
            r = await client.post(f"{API}/auth/verify-otp", json={
                "mobile": f"98000000{i}1", "otp": "123456"
            })
            assert r.status_code == 200, f"signup #{i + 1} failed: {r.text}"
            assert r.json()["token"]

    @pytest.mark.asyncio
    async def test_mobile_then_google_signups_succeed(self, client, clean_db):
        # Mobile user stores no email; Google user stores no mobile.
        r = await client.post(f"{API}/auth/verify-otp", json={"mobile": "9800000012", "otp": "123456"})
        assert r.status_code == 200
        # Google session exchange requires the Emergent endpoint — simulate by
        # calling create_new_user directly for the google provider path.
        import server as srv
        gu = await srv.create_new_user(email="g-user@test.in", name="G", provider="google")
        assert gu["email"] == "g-user@test.in"
        assert "mobile" not in gu  # null mobile must not be stored
        mu = await db.users.find_one({"mobile": "9800000012"}, {"_id": 0})
        assert "email" not in mu  # null email must not be stored


# ============================================================
# 1. custom_fields persistence (B1) — create + update round-trip
# ============================================================

class TestCustomFieldsPersistence:
    @pytest.mark.asyncio
    async def test_create_case_stores_custom_fields(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_custom",
            "case_type_id": "civil_suit",
            "party_name": "Ravi",
            "custom_fields": {"relief_sought": "Refund of Rs. 10,000", "client_name": "Ravi"},
        })
        assert r.status_code == 200, r.text
        case_id = r.json()["id"]
        g = await client.get(f"{API}/cases/{case_id}", headers=H(token))
        assert g.status_code == 200
        cf = g.json().get("custom_fields") or {}
        assert cf.get("relief_sought") == "Refund of Rs. 10,000"
        assert cf.get("client_name") == "Ravi"

    @pytest.mark.asyncio
    async def test_update_case_merges_custom_fields(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_merge",
            "custom_fields": {"a": "1"},
        })
        case_id = r.json()["id"]
        r2 = await client.put(f"{API}/cases/{case_id}", headers=H(token), json={
            "custom_fields": {"b": "2"},
        })
        assert r2.status_code == 200
        cf = r2.json().get("custom_fields") or {}
        assert cf.get("a") == "1" and cf.get("b") == "2", f"merge failed: {cf}"

    @pytest.mark.asyncio
    async def test_update_case_preserves_custom_fields_when_omitted(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_keep",
            "custom_fields": {"keep": "yes"},
        })
        case_id = r.json()["id"]
        r2 = await client.put(f"{API}/cases/{case_id}", headers=H(token), json={"nickname": "renamed"})
        assert r2.status_code == 200
        assert (r2.json().get("custom_fields") or {}).get("keep") == "yes"

    @pytest.mark.asyncio
    async def test_oversized_custom_fields_rejected(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "custom_fields": {"big": "x" * 6000},
        })
        assert r.status_code == 400


# ============================================================
# 2. Flat client details (D3)
# ============================================================

class TestFlatClientDetails:
    @pytest.mark.asyncio
    async def test_client_fields_stored_and_client_name_defaults_to_party(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_client",
            "party_name": "Sneha Patel",
            "client_mobile": "9876543210",
            "client_email": "sneha@example.com",
            "client_address": "12, CG Road, Ahmedabad",
        })
        assert r.status_code == 200
        c = r.json()
        assert c["client_name"] == "Sneha Patel"          # defaulted from party_name
        assert c["client_mobile"] == "9876543210"
        assert c["client_email"] == "sneha@example.com"
        assert c["client_address"] == "12, CG Road, Ahmedabad"


# ============================================================
# 3. autofill_map resolution against CLIENT context (D1) + admin->lawyer form
# ============================================================

class TestAutofillResolution:
    @pytest.mark.asyncio
    async def test_admin_saved_case_form_served_to_lawyer(self, client, clean_db):
        admin = await create_test_admin()
        atoken = make_admin_token(admin["id"], admin["email"], admin["role"])
        r = await client.post(f"{API}/admin/case-forms/civil_suit", headers=H(atoken), json={
            "name_en": "Civil Suit",
            "name_gu": "સિવિલ સૂટ",
            "category": "Civil",
            "fields": [
                {"key": "client_name", "label_en": "Client Name", "label_gu": "અસીલનું નામ",
                 "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
                {"key": "relief_sought", "label_en": "Relief Sought", "label_gu": "માગેલ દાદ",
                 "type": "textarea", "required": False, "order": 1, "autofill_map": ""},
            ],
        })
        assert r.status_code == 200, r.text
        # Lawyer fetches the config for the SAME case type id
        cfg = await client.get(f"{API}/catalog/case-forms/civil_suit")
        assert cfg.status_code == 200
        fields = cfg.json()["fields"]
        assert any(f["key"] == "client_name" and f["autofill_map"] == "user.name" for f in fields)

    @pytest.mark.asyncio
    async def test_autofill_map_resolved_server_side(self, client, clean_db):
        admin = await create_test_admin()
        atoken = make_admin_token(admin["id"], admin["email"], admin["role"])
        await client.post(f"{API}/admin/case-forms/civil_suit", headers=H(atoken), json={
            "name_en": "Civil Suit",
            "name_gu": "સિવિલ સૂટ",
            "category": "Civil",
            "fields": [
                {"key": "client_name", "label_en": "Client Name", "label_gu": "અસીલનું નામ",
                 "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
                {"key": "mobile", "label_en": "Mobile", "label_gu": "મોબાઈલ",
                 "type": "mobile", "required": True, "order": 1, "autofill_map": "user.mobile"},
            ],
        })
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "case_type_id": "civil_suit",
            "party_name": "Kiran",
            "client_mobile": "9123456789",
            "custom_fields": {},
        })
        assert r.status_code == 200, r.text
        cf = r.json().get("custom_fields") or {}
        assert cf.get("client_name") == "Kiran", f"user.name not resolved: {cf}"
        assert cf.get("mobile") == "9123456789", f"user.mobile not resolved: {cf}"

    @pytest.mark.asyncio
    async def test_user_entered_value_never_overwritten(self, client, clean_db):
        admin = await create_test_admin()
        atoken = make_admin_token(admin["id"], admin["email"], admin["role"])
        await client.post(f"{API}/admin/case-forms/civil_suit", headers=H(atoken), json={
            "name_en": "Civil Suit",
            "name_gu": "સિવિલ સૂટ",
            "category": "Civil",
            "fields": [
                {"key": "client_name", "label_en": "Client Name", "label_gu": "અસીલનું નામ",
                 "type": "text", "required": True, "order": 0, "autofill_map": "user.name"},
            ],
        })
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "case_type_id": "civil_suit",
            "party_name": "Kiran",
            "custom_fields": {"client_name": "Typed Manually"},
        })
        assert (r.json().get("custom_fields") or {}).get("client_name") == "Typed Manually"

    @pytest.mark.asyncio
    async def test_generic_fallback_has_no_fields(self, client, clean_db):
        cfg = await client.get(f"{API}/catalog/case-forms/some_unmatched_type")
        assert cfg.status_code == 200
        assert cfg.json()["fields"] == []


# ============================================================
# 4. Document autofill (D2) — custom fields + labels in preview/PDF/DOCX context
# ============================================================

class TestDocumentAutofill:
    @pytest.mark.asyncio
    async def test_preview_resolves_custom_field_from_case(self, client, clean_db):
        """D2: case.custom_fields are merged into the render context, so a template
        referencing {{reason}} (an adjournment field) is filled from the case."""
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_doc",
            "case_type_id": "criminal_complaint",
            "custom_fields": {"reason": "witness not available this week"},
        })
        case_id = r.json()["id"]
        p = await client.post(f"{API}/applications/preview", headers=H(token), json={
            "template_id": "adjournment",
            "case_id": case_id,
            "language": "en",
            "values": {},
        })
        assert p.status_code == 200, p.text
        assert "witness not available this week" in p.json()["content"]

    @pytest.mark.asyncio
    async def test_preview_autofills_police_station_and_client_name(self, client, clean_db):
        user, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_ps",
            "case_type_id": "criminal_complaint",
            "complaint_type": "police",
            "party_name": "Meena",
            "district_id": "ahmedabad",
            "police_station_id": "ahd_naranpura",
        })
        case_id = r.json()["id"]
        # vakalatnama uses {{client_name}} (should default to party_name) and the
        # court/district header — police_station is resolved into the ctx but not
        # printed by vakalatnama; use a direct render-context check for the label.
        p = await client.post(f"{API}/applications/preview", headers=H(token), json={
            "template_id": "vakalatnama",
            "case_id": case_id,
            "language": "en",
            "values": {},
        })
        assert p.status_code == 200, p.text
        content = p.json()["content"]
        assert "Meena" in content, "client_name should default to party_name"
        assert "Ahmedabad" in content, "district label missing"

        # Direct render-context check for police_station label
        import server as srv
        case = await db.cases.find_one({"id": case_id}, {"_id": 0})
        ctx = await srv.build_render_context({"name": "Adv", "district": None}, case, {}, "en")
        assert ctx["police_station"] == "Naranpura P.S."
        assert ctx["client_name"] == "Meena"

    @pytest.mark.asyncio
    async def test_raw_district_id_never_printed(self, client, clean_db):
        """Frontend regression: values.district must never render the raw catalog id."""
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_dguard",
            "district_id": "ahmedabad",
        })
        case_id = r.json()["id"]
        p = await client.post(f"{API}/applications/preview", headers=H(token), json={
            "template_id": "adjournment",
            "case_id": case_id,
            "language": "en",
            "values": {"district": "ahmedabad", "next_date": "20-02-2026", "reason": "TEST"},
        })
        assert p.status_code == 200
        content = p.json()["content"]
        assert "Ahmedabad" in content
        assert "ahmedabad" not in content

    @pytest.mark.asyncio
    async def test_render_context_law_section_labels(self, client, clean_db):
        import server as srv
        case = {
            "law_id": "ni_act",
            "section_id": "138",
            "party_name": "Ravi",
            "district_id": "ahmedabad",
            "court_id": "gen_jmfc",
            "police_station_id": "ahd_naranpura",
            "client_mobile": "9876543210",
            "custom_fields": {"relief_sought": "Pay the cheque amount"},
        }
        ctx = await srv.build_render_context({"name": "Adv", "district": None}, case, {}, "en")
        assert ctx["law"] == "Negotiable Instruments Act"
        assert "Section 138" in ctx["section"]
        assert ctx["client_mobile"] == "9876543210"
        assert ctx["relief_sought"] == "Pay the cheque amount"

    @pytest.mark.asyncio
    async def test_download_pdf_docx_still_work_with_custom_fields(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/cases", headers=H(token), json={
            "nickname": "P1_dl",
            "custom_fields": {"reason": "matter settled"},
        })
        case_id = r.json()["id"]
        for fmt in ("pdf", "docx"):
            d = await client.post(f"{API}/applications/download", headers=H(token), json={
                "template_id": "adjournment",
                "case_id": case_id,
                "language": "en",
                "format": fmt,
                "values": {"next_date": "20-02-2026"},
            })
            assert d.status_code == 200, d.text
            import base64
            raw = base64.b64decode(d.json()["base64"])
            assert raw[:4] == (b"%PDF" if fmt == "pdf" else b"PK\x03\x04")
        # credit consumed exactly once
        w = await client.get(f"{API}/wallet", headers=H(token))
        assert w.json()["balance"] == 3  # started at 5, two downloads
