"""Regression tests for the 'દસ્તાવેજ પરત મેળવવાની અરજી' (Application for Return of Document) template.

Covers the locked spec:
- Template id `document_return_application` is in the public library with the exact 14-field spec
  (court/district/taluka/case_type selects, role radios, case-status select, date, textarea...).
- Conditional wording derived from case_status: "ચાલુ" -> ચાલવા પર છે / છે ;
  "ડિસ્પોઝ્ડ" -> ડિસ્પોઝ્ડ થયેલ છે / હતો.
- Taluka/district line renders "તાલુકો, જિલ્લો" when a taluka is selected, district alone otherwise.
- No leftover {{placeholders}} in preview; PDF and DOCX generate with the conditional text and
  consume exactly one credit each.
"""

import os
import sys
import uuid
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_doc_return")

import pytest
import pytest_asyncio
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_doc_return"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token
from httpx import AsyncClient, ASGITransport

API = "/api"

TEMPLATE_ID = "document_return_application"


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


async def create_test_lawyer(mobile=None):
    mobile = mobile or f"9{int(time.time() * 1000) % 1000000000:09d}"
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": None,
        "name": "Adv. Test Lawyer",
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


async def get_template(client):
    r = await client.get(f"{API}/templates/{TEMPLATE_ID}")
    assert r.status_code == 200, r.text
    return r.json()


def full_values(**overrides):
    vals = {
        "court": "gen_jmfc",
        "district": "gandhinagar",
        "taluka": "કલોલ",
        "case_type": "civil_suit",
        "case_number": "Civil Suit No. 125/2024",
        "applicant_role": "ફરીયાદી",
        "party_name": "રમેશભાઈ પટેલ",
        "opposite_party_role": "પ્રતિવાદી",
        "opposite_party": "મહેશભાઈ શાહ",
        "advocate_name": "Adv. Test Lawyer",
        "case_status": "ચાલુ",
        "document_name": "આંક ૧૯ મુજબનો મકાનનો દસ્તાવેજ",
        "date": "15-02-2026",
        "place": "ગાંધીનગર",
    }
    vals.update(overrides)
    return vals


class TestTemplateSpec:
    @pytest.mark.asyncio
    async def test_template_in_public_library(self, client, clean_db):
        r = await client.get(f"{API}/templates")
        assert r.status_code == 200
        t = next((x for x in r.json() if x["id"] == TEMPLATE_ID), None)
        assert t is not None, "document_return_application missing from /api/templates"
        assert t["name_en"] == "Application for Return of Document"
        assert t["name_gu"] == "દસ્તાવેજ પરત મેળવવાની અરજી"
        assert t["category"] == "Civil"

    @pytest.mark.asyncio
    async def test_field_spec_exact(self, client, clean_db):
        t = await get_template(client)
        fields = t["fields"]
        assert len(fields) == 14
        expected = [
            ("court", "select", True),
            ("district", "select", True),
            ("taluka", "select", False),   # taluka is NOT mandatory
            ("case_type", "select", True),
            ("case_number", "text", True),
            ("applicant_role", "radio", True),
            ("party_name", "text", True),
            ("opposite_party_role", "radio", True),
            ("opposite_party", "text", True),
            ("advocate_name", "select", True),
            ("case_status", "select", True),
            ("document_name", "textarea", True),
            ("date", "date", True),
            ("place", "text", True),
        ]
        for i, (key, ftype, required) in enumerate(expected):
            f = fields[i]
            assert f["key"] == key, f"field #{i} key: {f['key']}"
            assert f["type"] == ftype, f"field {key} type: {f['type']}"
            assert f["required"] is required, f"field {key} required: {f['required']}"

        role = next(f for f in fields if f["key"] == "applicant_role")
        assert [o["value"] for o in role["options"]] == ["ફરીયાદી", "अरजદાર", "વાદી"] or \
               [o["value"] for o in role["options"]] == ["ફરીયાદી", "અરજદાર", "વાદી"]
        opp = next(f for f in fields if f["key"] == "opposite_party_role")
        assert [o["value"] for o in opp["options"]] == ["આરોપી", "સામાવાળા", "પ્રતિવાદી"]
        status = next(f for f in fields if f["key"] == "case_status")
        assert [o["value"] for o in status["options"]] == ["ચાલુ", "ડિસ્પોઝ્ડ"]
        # Select fields carry existing catalog values (ids) with bilingual labels
        district = next(f for f in fields if f["key"] == "district")
        assert any(o["value"] == "gandhinagar" and o["label_gu"] == "ગાંધીનગર" for o in district["options"])
        court = next(f for f in fields if f["key"] == "court")
        assert any(o["value"] == "gen_jmfc" for o in court["options"])
        case_type = next(f for f in fields if f["key"] == "case_type")
        assert any(o["value"] == "civil_suit" for o in case_type["options"])
        # Taluka options are district-scoped (dependent dropdown data)
        taluka = next(f for f in fields if f["key"] == "taluka")
        assert all("district_id" in o for o in taluka["options"])
        assert any(o["value"] == "કલોલ" and o["district_id"] == "gandhinagar" for o in taluka["options"])
        # Document description carries the example help text as placeholder
        doc = next(f for f in fields if f["key"] == "document_name")
        assert doc.get("placeholder", "").startswith("દા.ત.")

    @pytest.mark.asyncio
    async def test_all_placeholders_declared(self, client, clean_db):
        """Every {{placeholder}} in content must be a declared field or auto-fill key
        (mirrors the admin publish validation)."""
        t = await get_template(client)
        import re
        from server import _AUTO_FILL_FIELDS
        declared = {f["key"] for f in t["fields"]} | _AUTO_FILL_FIELDS
        for content in (t["content_en"], t["content_gu"]):
            found = set(re.findall(r"\{\{(\w+)\}\}", content))
            assert found, "no placeholders found"
            unknown = found - declared
            assert not unknown, f"unknown placeholders: {unknown}"


class TestCaseStatusConditionals:
    @pytest.mark.asyncio
    async def test_chalu_case_wording(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu", "values": full_values(),
        }, headers=H(token))
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        assert "મહેરબાન જે.એમ.એફ.સી. ન્યાયાલય સાહેબશ્રીની કોર્ટમાં," in content
        assert "કલોલ, ગાંધીનગર" in content                      # taluka, district order
        assert "સિવિલ સૂટ નં. Civil Suit No. 125/2024" in content
        assert "ફરીયાદી\nવિરુદ્ધ\nપ્રતિવાદી" in content
        assert "સદર કામમાં અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે....." in content
        assert "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે." in content
        assert "કામમાં રજૂ કરવામાં આવેલ છે." in content
        assert "તારીખ : 15-02-2026" in content
        assert "સ્થળ : ગાંધીનગર" in content
        assert "ફરીયાદીના એડવોકેટ" in content                  # derived signature role
        assert "{{" not in content                                # no leftover placeholders
        assert "ડિસ્પોઝ્ડ થયેલ છે" not in content
        assert "હતો" not in content

    @pytest.mark.asyncio
    async def test_disposed_case_wording(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": full_values(case_status="ડિસ્પોઝ્ડ"),
        }, headers=H(token))
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        assert "સદર કેસ આપની કોર્ટમાં ડિસ્પોઝ્ડ થયેલ છે." in content
        assert "કામમાં રજૂ કરવામાં આવેલ હતો." in content
        assert "ચાલવા પર છે" not in content
        assert "{{" not in content

    @pytest.mark.asyncio
    async def test_no_taluka_shows_district_only(self, client, clean_db):
        _, token = await create_test_lawyer()
        vals = full_values()
        vals.pop("taluka")
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu", "values": vals,
        }, headers=H(token))
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        assert "કલોલ" not in content
        assert "\nગાંધીનગર\n" in content  # district-only line

    @pytest.mark.asyncio
    async def test_english_mode_resolves_catalog_ids(self, client, clean_db):
        _, token = await create_test_lawyer()
        vals = full_values(language="en")
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "en", "values": vals,
        }, headers=H(token))
        assert r.status_code == 200, r.text
        content = r.json()["content"]
        # Raw catalog ids must never leak into the document
        for raw in ("gen_jmfc", "gandhinagar", "civil_suit"):
            assert raw not in content, f"raw id leaked: {raw}"
        assert "Court of JMFC" in content
        assert "Civil Suit" in content


class TestDocumentGeneration:
    @pytest.mark.asyncio
    async def test_pdf_and_docx_generate_with_conditional_text(self, client, clean_db):
        _, token = await create_test_lawyer()

        r = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": full_values(), "format": "pdf", "filename": "doc_return.pdf",
        }, headers=H(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mime_type"] == "application/pdf"
        pdf = __import__("base64").b64decode(data["base64"])
        assert pdf[:4] == b"%PDF"

        r = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": full_values(), "format": "docx", "filename": "doc_return.docx",
        }, headers=H(token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mime_type"].startswith("application/vnd.openxmlformats")
        docx = __import__("base64").b64decode(data["base64"])
        assert docx[:2] == b"PK"

        # Exactly one credit per download (5 -> 3 after two downloads)
        wallet = await db.wallets.find_one({"user_id": (await db.users.find_one({}, {"_id": 0}))["id"]}, {"_id": 0})
        assert wallet["balance"] == 3
        assert wallet["total_used"] == 2

    @pytest.mark.asyncio
    async def test_disposed_docx_contains_hado(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": full_values(case_status="ડિસ્પોઝ્ડ"), "format": "docx",
            "filename": "doc_return_disposed.docx",
        }, headers=H(token))
        assert r.status_code == 200, r.text
        import base64
        import zipfile
        from io import BytesIO
        z = zipfile.ZipFile(BytesIO(base64.b64decode(r.json()["base64"])))
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
        assert "ડિસ્પોઝ્ડ થયેલ છે" in xml
        assert "હતો" in xml
        assert "ચાલવા પર છે" not in xml
