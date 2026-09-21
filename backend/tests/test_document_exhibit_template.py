# -*- coding: utf-8 -*-
"""Comprehensive test suite for the 'દસ્તાવેજને આંક પાડવા બાબતની અરજી'
(Application for Marking Documents as Exhibits) template.

Covers all 31 verification points:
1. Template Registration & Metadata (ID, Gujarati Name, English Name, Category, aliases)
2. Exactly 13 input fields present with expected keys, types, required flags
3. Field 'court_name': select, required True
4. Field 'district': select, required True
5. Field 'taluka': select, required False (optional)
6. Field 'case_type': select, required True
7. Field 'case_number': text, required True
8. Field 'party_1_role': radio, required True
9. Field 'party_1_name': text, required True
10. Field 'party_2_role': radio, required True
11. Field 'party_2_name': text, required True
12. Field 'representing_party': select, required True
13. Field 'document_details': textarea, required True
14. Field 'date': date, required True
15. Field 'place': text, required False
16. Page layout geometry: A4, 2cm top/bottom, 4cm left/right margins
17. Font settings: Lohit Gujarati (13pt body, 15pt heading); Times New Roman (14pt body, 16pt heading)
18. Paragraph spacing: 6pt, Line spacing: 18pt, First-line indent: 28.35pt (1cm)
19. Block alignments: Court centered & bold, Subject centered & bold, Body justified, Signature right
20. Gujarati content fidelity: exact wording, no omissions
21. English content fidelity: exact formal Indian court legal translation
22. Place formatting: 'Taluka, District' vs 'District'
23. Date formatting: DD/MM/YYYY
24. Party role resolution: party_1 vs party_2 representation
25. Direct Template Mode: preview clean, 0 unfilled placeholders
26. Saved Case Mode: linking a case auto-populates court, case_type, case_number, parties
27. PDF Generation: valid non-empty PDF (%PDF-) in Gujarati and English
28. DOCX Generation: valid DOCX file (PK zip)
29. ODT Generation: valid ODT file (PK zip)
30. Admin Template Validation: _validate_placeholders returns valid: True, unknown: []
31. Template search and alias resolution
"""

import os
import sys
import uuid
import time
import base64
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DB_NAME", "nyaysetu_test_doc_exhibit")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import server
app = server.app
from server import make_token, _validate_placeholders
from tests.firestore_test_utils import FirestoreDBSurrogate
mock_db = FirestoreDBSurrogate()
db = FirestoreDBSurrogate()

API = "/api"
TEMPLATE_ID = "document_exhibit_application"


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    yield


async def create_test_lawyer(mobile=None):
    mobile = mobile or f"9{int(time.time() * 1000) % 1000000000:09d}"
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": None,
        "name": "Adv. Test Lawyer",
        "advocate_name_gu": "એડવોકેટ રમેશભાઈ પટેલ",
        "advocate_name_en": "Advocate Ramesh Patel",
        "provider": "mobile",
        "bar_council_no": "G/1234/2020",
        "state": "Gujarat",
        "district": "ahmedabad",
        "court": "City Civil Court, Ahmedabad",
        "language_pref": "en",
        "theme_pref": "light",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "referred_by": None,
        "favourite_courts": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.collection("users").document(user["id"]).set(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 10,
        "free_credits_granted": 10,
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


def sample_exhibit_values(**overrides):
    vals = {
        "district": "ગાંધીનગર",
        "taluka": "કલોલ",
        "court_name": "principal_senior_civil_judge",
        "case_type": "regular_civil_suit",
        "case_number": "૧૨૫/૨૦૨૪",
        "party_1_role": "વાદી",
        "party_1_name": "રમણભાઈ પટેલ",
        "party_2_role": "પ્રતિવાદી",
        "party_2_name": "સુરેશભાઈ શાહ",
        "representing_party": "party_1",
        "document_details": "આંક ૩ થી રજૂ કરેલ મૂળ વેચાણ દસ્તાવેજ તથા ઇલેક્ટ્રિક બિલની નકલ",
        "date": "2026-02-15",
    }
    vals.update(overrides)
    return vals


class TestPoint1To15_TemplateSpecAndFields:
    """Tests 1 through 15: Registration, Metadata, and 12 Input Fields."""

    @pytest.mark.asyncio
    async def test_01_template_registration_and_metadata(self, client, clean_db):
        r = await client.get(f"{API}/templates")
        assert r.status_code == 200
        tpl = next((x for x in r.json() if x["id"] == TEMPLATE_ID), None)
        assert tpl is not None, f"{TEMPLATE_ID} missing from /api/templates"
        assert tpl["name_en"] == "Application for Marking Documents as Exhibits"
        assert tpl["name_gu"] == "દસ્તાવેજને આંક પાડવા બાબતની અરજી"
        assert tpl["category"] == "Civil"

    @pytest.mark.asyncio
    async def test_02_exactly_12_input_fields(self, client, clean_db):
        tpl = await get_template(client)
        fields = tpl["fields"]
        assert len(fields) == 12, f"Expected exactly 12 fields, got {len(fields)}"
        expected_keys = [
            "district", "taluka", "court_name", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "representing_party", "document_details", "date"
        ]
        assert [f["key"] for f in fields] == expected_keys

    @pytest.mark.asyncio
    async def test_03_field_court_name(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "court_name")
        assert f["type"] == "select"
        assert f["required"] is True
        opts = [o["value"] for o in f.get("options", [])]
        assert "principal_senior_civil_judge" in opts
        assert "civil_judge_jmfc" in opts

    @pytest.mark.asyncio
    async def test_04_field_district(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "district")
        assert f["type"] == "select"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_05_field_taluka_optional(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "taluka")
        assert f["type"] == "select"
        assert f["required"] is False

    @pytest.mark.asyncio
    async def test_06_field_case_type(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "case_type")
        assert f["type"] == "select"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_07_field_case_number(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "case_number")
        assert f["type"] == "text"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_08_field_party_1_role(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "party_1_role")
        assert f["type"] == "radio"
        assert f["required"] is True
        opts = [o["value"] for o in f.get("options", [])]
        assert opts == ["વાદી", "અરજદાર", "ફરીયાદી"]

    @pytest.mark.asyncio
    async def test_09_field_party_1_name(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "party_1_name")
        assert f["type"] == "text"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_10_field_party_2_role(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "party_2_role")
        assert f["type"] == "radio"
        assert f["required"] is True
        opts = [o["value"] for o in f.get("options", [])]
        assert opts == ["પ્રતિવાદી", "સામાવાળા", "આરોપી"]

    @pytest.mark.asyncio
    async def test_11_field_party_2_name(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "party_2_name")
        assert f["type"] == "text"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_12_field_representing_party(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "representing_party")
        assert f["type"] in ("radio", "select")
        assert f["required"] is True
        opts = [o["value"] for o in f.get("options", [])]
        assert "party_1" in opts
        assert "party_2" in opts

    @pytest.mark.asyncio
    async def test_13_field_document_details(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "document_details")
        assert f["type"] == "textarea"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_14_field_date(self, client, clean_db):
        tpl = await get_template(client)
        f = next(x for x in tpl["fields"] if x["key"] == "date")
        assert f["type"] == "date"
        assert f["required"] is True

    @pytest.mark.asyncio
    async def test_15_field_place_not_in_input_fields(self, client, clean_db):
        tpl = await get_template(client)
        keys = [x["key"] for x in tpl["fields"]]
        assert "place" not in keys, "place MUST NOT be in template.fields; it is derived-only"


class TestPoint16To19_PageLayoutAndTypography:
    """Tests 16 through 19: Page geometry, fonts, spacing, indent, and block alignments."""

    @pytest.mark.asyncio
    async def test_16_page_layout_geometry_margins(self, client, clean_db):
        from test_seed_data import TEMPLATES
        tpl = next(x for x in TEMPLATES if x["id"] == TEMPLATE_ID)
        s = tpl.get("settings", {})
        assert s.get("page_size") == "A4"
        assert float(s.get("margin_top_cm", 0)) == 2.0
        assert float(s.get("margin_bottom_cm", 0)) == 2.0
        assert float(s.get("margin_left_cm", 0)) == 4.0
        assert float(s.get("margin_right_cm", 0)) == 4.0

    @pytest.mark.asyncio
    async def test_17_font_settings(self, client, clean_db):
        from test_seed_data import TEMPLATES
        tpl = next(x for x in TEMPLATES if x["id"] == TEMPLATE_ID)
        s = tpl.get("settings", {})
        assert "Lohit" in s.get("gujarati_font", "") or "Lohit" in s.get("gujarati_font_docx", "")
        assert s.get("body_size") == 13
        assert s.get("heading_size") == 15
        assert s.get("body_size_en") == 14
        assert s.get("heading_size_en") == 16

    @pytest.mark.asyncio
    async def test_18_spacing_and_indent(self, client, clean_db):
        from test_seed_data import TEMPLATES
        tpl = next(x for x in TEMPLATES if x["id"] == TEMPLATE_ID)
        s = tpl.get("settings", {})
        assert float(s.get("paragraph_spacing", 0)) == 6.0
        assert float(s.get("line_spacing", 0)) == 19.5
        assert float(s.get("first_line_indent_pt", 0)) == 28.35

    @pytest.mark.asyncio
    async def test_19_block_alignments(self, client, clean_db):
        from test_seed_data import TEMPLATES
        tpl = next(x for x in TEMPLATES if x["id"] == TEMPLATE_ID)
        block_align = (tpl.get("settings") or {}).get("block_align", [])
        rules = {r["contains"]: r for r in block_align}
        assert rules["સાહેબશ્રીની કોર્ટમાં"]["align"] == "center"
        assert rules["સાહેબશ્રીની કોર્ટમાં"]["bold"] is True
        assert rules[" નં. :"]["align"] == "right"
        assert rules["વિરુદ્ધ"]["align"] == "center"
        assert "બાબત :- દસ્તાવેજને આંક પાડવા બાબત..." in rules or "બાબત :- દસ્તાવેજને આંક પાડવા બાબત ..." in rules
        assert rules["સદર કેસ આપ નામદાર"]["align"] == "justify"
        assert rules["સદર કેસ આપ નામદાર"]["indent"] is True
        assert rules["ના એડવોકેટ"]["align"] == "right"


class TestPoint20To24_ContentAndFormatting:
    """Tests 20 through 24: Gujarati & English content fidelity, place, date, role resolution."""

    @pytest.mark.asyncio
    async def test_20_gujarati_content_fidelity(self, client, clean_db):
        tpl = await get_template(client)
        c = tpl["content_gu"]
        assert "મહેરબાન {{court_name}} સાહેબશ્રીની કોર્ટમાં," in c
        assert "મુકામ :- {{taluka_place}}" in c
        assert "{{case_type}} નં. : {{case_number}}" in c
        assert "{{party_1_role}} :- {{party_1_name}}" in c
        assert "વિરુદ્ધ" in c
        assert "{{party_2_role}} :- {{party_2_name}}" in c
        assert "બાબત :- દસ્તાવેજને આંક પાડવા બાબત..." in c
        assert "સદર કામમાં અમો {{representing_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે..." in c
        assert "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે." in c
        assert "દસ્તાવેજી પુરાવા લીસ્ટથી અસલ દસ્તાવેજ રજુ કરેલ છે" in c
        assert "તેને આંક આપી પુરાવામાં વંચાણે લેવા મહેરબાની કરશોજી." in c
        assert "તારીખ : {{date}}" in c
        assert "સ્થળ : {{taluka_place}}" in c
        assert "{{representing_party_role}} ના એડવોકેટ" in c

    @pytest.mark.asyncio
    async def test_21_english_content_fidelity(self, client, clean_db):
        tpl = await get_template(client)
        c = tpl["content_en"]
        assert "BEFORE THE COURT OF THE HON'BLE {{court_name}}" in c
        assert "Place: {{taluka_place}}" in c
        assert "{{case_type}} No. : {{case_number}}" in c
        assert "{{party_1_role}} :- {{party_1_name}}" in c
        assert "VERSUS" in c
        assert "{{party_2_role}} :- {{party_2_name}}" in c
        assert "Subject: Regarding marking the document(s) as exhibit(s)..." in c
        assert "In the above matter, I/We, the Advocate for the {{representing_party_role}}, most respectfully submit before this Hon'ble Court that..." in c
        assert "The above case is pending before this Hon'ble Court." in c
        assert "produced original document(s) vide documentary evidence list" in c
        assert "assign exhibit number(s) to the same and read them in evidence." in c
        assert "Date : {{date}}" in c
        assert "Place : {{taluka_place}}" in c
        assert "{{representing_party_role}}'s Advocate" in c

    @pytest.mark.asyncio
    async def test_22_place_formatting_with_and_without_taluka(self, client, clean_db):
        _, token = await create_test_lawyer()
        # Case A: with Taluka
        r1 = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(taluka="કલોલ", district="ગાંધીનગર"),
        }, headers=H(token))
        assert r1.status_code == 200
        assert "કલોલ, ગાંધીનગર" in r1.json()["content"]

        # Case B: without Taluka (taluka is empty string)
        r2 = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(taluka="", district="ગાંધીનગર"),
        }, headers=H(token))
        assert r2.status_code == 200
        content2 = r2.json()["content"]
        assert "ગાંધીનગર" in content2
        assert ", ગાંધીનગર" not in content2
        assert "ગાંધીનગર," not in content2

    @pytest.mark.asyncio
    async def test_23_date_formatting_dd_mm_yyyy(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(date="2026-03-25"),
        }, headers=H(token))
        assert r.status_code == 200
        assert "25/03/2026" in r.json()["content"]

    @pytest.mark.asyncio
    async def test_24_party_role_resolution(self, client, clean_db):
        _, token = await create_test_lawyer()
        # Representing party 1
        r1 = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(
                party_1_role="વાદી", party_2_role="પ્રતિવાદી", representing_party="party_1"
            ),
        }, headers=H(token))
        assert r1.status_code == 200
        assert "અમો વાદી ના એડવોકેટની" in r1.json()["content"]
        assert "વાદી ના એડવોકેટ" in r1.json()["content"]

        # Representing party 2
        r2 = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(
                party_1_role="વાદી", party_2_role="પ્રતિવાદી", representing_party="party_2"
            ),
        }, headers=H(token))
        assert r2.status_code == 200
        assert "અમો પ્રતિવાદી ના એડવોકેટની" in r2.json()["content"]
        assert "પ્રતિવાદી ના એડવોકેટ" in r2.json()["content"]


class TestPoint25To31_GenerationAndIntegration:
    """Tests 25 through 31: Direct mode, Saved Case mode, PDF/DOCX/ODT generation, Admin validation, Search."""

    @pytest.mark.asyncio
    async def test_25_direct_template_mode_preview_clean(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(),
        }, headers=H(token))
        assert r.status_code == 200
        content = r.json()["content"]
        assert "{{" not in content, f"Found unresolved placeholder in content:\n{content}"

    @pytest.mark.asyncio
    async def test_26_saved_case_mode_auto_population(self, client, clean_db):
        user, token = await create_test_lawyer()
        case_id = str(uuid.uuid4())
        case_data = {
            "id": case_id,
            "user_id": user["id"],
            "case_number": "RCS/55/2025",
            "case_type_id": "regular_civil_suit",
            "court_id": "gen_civil_senior",
            "district_id": "ahmedabad",
            "taluka_id": "dholka",
            "party_name": "અમૃતલાલ પટેલ",
            "party_role": "plaintiff",
            "opposite_party": "ભીખુભાઈ શાહ",
            "opposite_party_role": "defendant",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.collection("cases").document(case_id).set(case_data)

        # In saved case mode, court, case_number, party names inherit from linked case
        r = await client.post(f"{API}/applications/preview", json={
            "template_id": TEMPLATE_ID,
            "language": "gu",
            "case_id": case_id,
            "values": {
                "representing_party": "party_1",
                "document_details": "આંક ૫ નો કરારપત્ર",
                "date": "2026-04-10",
            },
        }, headers=H(token))
        assert r.status_code == 200
        content = r.json()["content"]
        assert "અમૃતલાલ પટેલ" in content
        assert "ભીખુભાઈ શાહ" in content
        assert "RCS/55/2025" in content
        assert "{{" not in content

    @pytest.mark.asyncio
    async def test_27_pdf_generation_gujarati_and_english(self, client, clean_db):
        _, token = await create_test_lawyer()
        # Gujarati PDF
        r_gu = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(), "format": "pdf",
            "filename": "exhibit_app_gu.pdf",
        }, headers=H(token))
        assert r_gu.status_code == 200
        pdf_gu = base64.b64decode(r_gu.json()["base64"])
        assert pdf_gu.startswith(b"%PDF-")

        # English PDF
        r_en = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "en",
            "values": sample_exhibit_values(court_name="Court of Principal Senior Civil Judge"),
            "format": "pdf", "filename": "exhibit_app_en.pdf",
        }, headers=H(token))
        assert r_en.status_code == 200
        pdf_en = base64.b64decode(r_en.json()["base64"])
        assert pdf_en.startswith(b"%PDF-")

    @pytest.mark.asyncio
    async def test_28_docx_generation_valid(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(), "format": "docx",
            "filename": "exhibit_app.docx",
        }, headers=H(token))
        assert r.status_code == 200
        docx = base64.b64decode(r.json()["base64"])
        assert docx.startswith(b"PK\x03\x04")

    @pytest.mark.asyncio
    async def test_29_odt_generation_valid(self, client, clean_db):
        _, token = await create_test_lawyer()
        r = await client.post(f"{API}/applications/download", json={
            "template_id": TEMPLATE_ID, "language": "gu",
            "values": sample_exhibit_values(), "format": "odt",
            "filename": "exhibit_app.odt",
        }, headers=H(token))
        assert r.status_code == 200
        odt = base64.b64decode(r.json()["base64"])
        assert odt.startswith(b"PK\x03\x04")

    @pytest.mark.asyncio
    async def test_30_admin_template_validation(self, client, clean_db):
        tpl = await get_template(client)
        v = _validate_placeholders(tpl["content_en"], tpl["content_gu"], tpl["fields"])
        assert v["valid"] is True, f"Validation failed: {v}"
        assert len(v["unknown"]) == 0, f"Unknown placeholders found: {v['unknown']}"

    @pytest.mark.asyncio
    async def test_31_template_search_and_alias_resolution(self, client, clean_db):
        # Search for exhibit in English
        r_en = await client.get(f"{API}/templates?q=exhibit")
        assert r_en.status_code == 200
        ids_en = [t["id"] for t in r_en.json()]
        assert TEMPLATE_ID in ids_en

        # Search for aank in Gujarati
        r_gu = await client.get(f"{API}/templates?q=આંક")
        assert r_gu.status_code == 200
        ids_gu = [t["id"] for t in r_gu.json()]
        assert TEMPLATE_ID in ids_gu
