"""Comprehensive automated test suite for NyaySetu Pro Application Field Architecture,
Single-Application / No-Case Workflow, and Language-Aware Drafting.
"""

import os
import sys
import base64
import pytest
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from seed_data_templates_v2 import TEMPLATES_V2
from server import (
    ROLE_MAP,
    _ROLE_CANONICAL_LOOKUP,
    resolve_party_role_label,
    format_advocate_name,
    build_render_context,
)
from doc_generator import (
    render_template,
    build_blocks,
    generate_pdf,
    generate_docx,
    generate_odt,
    generate_document_images,
    rasterize_pdf_pages,
    _pdf_bytes_from_b64,
)


@pytest.fixture
def mock_user_bilingual():
    return {
        "id": "u_test_advocate",
        "name": "Ronak Solanki",
        "advocate_name_en": "Adv. Ronak Solanki",
        "advocate_name_gu": "એડવોકેટ રોનક સોલંકી",
        "district": "ahmedabad",
        "court": "City Civil Court, Ahmedabad",
    }


@pytest.fixture
def mock_case_civil():
    return {
        "id": "c_test_civil_1",
        "user_id": "u_test_advocate",
        "case_number": "101/2026",
        "district_id": "ahmedabad",
        "taluka_id": "ahmedabad_city",
        "court_id": "gen_jmfc",
        "case_type_id": "civil_suit",
        "party_name": "Rameshbhai Patel",
        "opposite_party": "Rajeshkumar Shah",
        "party_role": "plaintiff",
        "opposite_party_role": "defendant",
    }


@pytest.fixture
def mock_case_criminal():
    return {
        "id": "c_test_crim_1",
        "user_id": "u_test_advocate",
        "case_number": "505/2026",
        "district_id": "gandhinagar",
        "taluka_id": "kalol",
        "court_id": "gen_sessions",
        "case_type_id": "crim_bail",
        "party_name": "Suresh Patel",
        "opposite_party": "State of Gujarat",
        "party_role": "applicant",
        "opposite_party_role": "opponent",
    }


# Test 1: All 21 templates load successfully and have date as the last field
def test_all_21_templates_structure():
    assert len(TEMPLATES_V2) == 21
    template_ids = [t["id"] for t in TEMPLATES_V2]
    expected_ids = [
        "aanke_padvani_arji", "certified_report", "dd_karavani_arji", "document_return",
        "document_on_record", "closing_purshish", "hazari_mafi_arji", "fs_haq_bandh",
        "fs_haq_khol", "jamin_bond", "kam_board", "mudat_arji", "saaxi_summons",
        "samadhan_purshish", "ulat_tapas_bandh", "ulat_tapas_khol", "undertaking",
        "vakilatnama_civil", "vakilatnama_criminal", "warrant_hathbido", "warrant_rad"
    ]
    for eid in expected_ids:
        assert eid in template_ids, f"Missing template: {eid}"

    for t in TEMPLATES_V2:
        fields = t["fields"]
        assert len(fields) > 0, f"Template {t['id']} has no fields"
        last_field = fields[-1]
        assert last_field["key"] == "date", f"Template {t['id']} last field is not date (got {last_field['key']})"


# Test 2 & 3: Party role resolution for Gujarati and English
def test_party_role_bilingual_resolution():
    roles = ["plaintiff", "defendant", "applicant", "opponent", "complainant", "accused"]
    for r in roles:
        gu_label = resolve_party_role_label(r, language="gu")
        en_label = resolve_party_role_label(r, language="en")
        assert gu_label == ROLE_MAP[r]["gu"]
        assert en_label == ROLE_MAP[r]["en"]
        assert gu_label != en_label

    # Legacy strings normalization
    assert resolve_party_role_label("વાદી", language="en") == "Plaintiff"
    assert resolve_party_role_label("Plaintiff", language="gu") == "વાદી"
    assert resolve_party_role_label("આરોપી", language="en") == "Accused"
    assert resolve_party_role_label("Accused", language="gu") == "આરોપી"


# Test 4 & 5: English never receives Gujarati role labels and vice versa
def test_strict_language_role_isolation():
    gu_labels = [ROLE_MAP[k]["gu"] for k in ROLE_MAP]
    en_labels = [ROLE_MAP[k]["en"] for k in ROLE_MAP]

    for k in ROLE_MAP:
        resolved_en = resolve_party_role_label(k, "en")
        resolved_gu = resolve_party_role_label(k, "gu")

        assert resolved_en not in gu_labels
        assert resolved_gu not in en_labels


# Test 6 & 7: Bilingual advocate name formatting and resolution
def test_advocate_bilingual_formatting(mock_user_bilingual):
    assert format_advocate_name("Ronak Solanki", language="en") == "Adv. Ronak Solanki"
    assert format_advocate_name("Adv. Ronak Solanki", language="en") == "Adv. Ronak Solanki"
    assert format_advocate_name("રોનક સોલંકી", language="gu") == "એડવોકેટ રોનક સોલંકી"
    assert format_advocate_name("એડવોકેટ રોનક સોલંકી", language="gu") == "એડવોકેટ રોનક સોલંકી"


@pytest.mark.asyncio
async def test_build_render_context_bilingual_advocate(mock_user_bilingual):
    # Gujarati context
    ctx_gu = await build_render_context(mock_user_bilingual, None, {}, language="gu")
    assert ctx_gu["advocate_name"] == "એડવોકેટ રોનક સોલંકી"

    # English context
    ctx_en = await build_render_context(mock_user_bilingual, None, {}, language="en")
    assert ctx_en["advocate_name"] == "Adv. Ronak Solanki"


# Test 8: Case-first mode inherits all common details
@pytest.mark.asyncio
async def test_case_first_mode_inheritance(mock_user_bilingual, mock_case_civil):
    ctx = await build_render_context(mock_user_bilingual, mock_case_civil, {}, language="gu")
    assert ctx["case_number"] == "101/2026"
    assert ctx["party_name"] == "Rameshbhai Patel"
    assert ctx["opposite_party"] == "Rajeshkumar Shah"
    assert ctx["party_role"] == "વાદી"
    assert ctx["opposite_party_role"] == "પ્રતિવાદી"
    assert "party_line" in ctx
    assert ctx["party_line"] == "વાદી Rameshbhai Patel"


# Test 9: No-Case mode dynamic base fields resolution
@pytest.mark.asyncio
async def test_no_case_mode_resolution(mock_user_bilingual):
    no_case_values = {
        "district": "ahmedabad",
        "taluka": "daskroi",
        "court": "JMFC Court, Ahmedabad",
        "case_type": "civil_suit",
        "case_number": "999/2026",
        "party_name": "Arvindbhai Patel",
        "party_role": "applicant",
        "opposite_party": "Bhavik Shah",
        "opposite_party_role": "opponent",
        "advocate_name": "Adv. Ronak Solanki",
        "date": "2026-08-15",
    }
    # In English
    ctx_en = await build_render_context(mock_user_bilingual, None, no_case_values, language="en")
    assert ctx_en["party_role"] == "Applicant"
    assert ctx_en["opposite_party_role"] == "Opponent"
    assert ctx_en["case_number"] == "999/2026"
    assert ctx_en["date_display"] == "15/08/2026"

    # In Gujarati
    ctx_gu = await build_render_context(mock_user_bilingual, None, no_case_values, language="gu")
    assert ctx_gu["party_role"] == "અરજદાર"
    assert ctx_gu["opposite_party_role"] == "સામાવાળા"


# Test 10: Conditional "Other" fields replacement and zero leakage
@pytest.mark.asyncio
async def test_conditional_other_replacement(mock_user_bilingual):
    values = {
        "reason": "other",
        "reason_other": "તબિયત અસ્વસ્થ હોવાના કારણે",
        "absence_reason": "other",
        "absence_reason_other": "અગત્યના સરકારી કામે બહારગામ હોવાથી",
    }
    ctx = await build_render_context(mock_user_bilingual, None, values, language="gu")
    assert ctx["reason"] == "તબિયત અસ્વસ્થ હોવાના કારણે"
    assert ctx["absence_reason"] == "અગત્યના સરકારી કામે બહારગામ હોવાથી"
    assert "other" not in ctx["reason"]
    assert "other" not in ctx["absence_reason"]


# Test 11: Taluka optional behavior
@pytest.mark.asyncio
async def test_taluka_optional_behavior(mock_user_bilingual):
    # With taluka
    ctx_with = await build_render_context(mock_user_bilingual, None, {"district": "ગાંધીનગર", "taluka": "કલોલ"}, language="gu")
    assert ctx_with["taluka_place"] == "કલોલ, ગાંધીનગર"

    # Without taluka
    ctx_without = await build_render_context(mock_user_bilingual, None, {"district": "ગાંધીનગર", "taluka": ""}, language="gu")
    assert ctx_without["taluka_place"] == "ગાંધીનગર"
    assert "None" not in ctx_without["taluka_place"]
    assert "null" not in ctx_without["taluka_place"]


# Test 12: Jamin Bond Case No. vs Crime Reg. No. resolution
@pytest.mark.asyncio
async def test_jamin_bond_case_or_crime(mock_user_bilingual):
    # Case number present
    ctx_case = await build_render_context(mock_user_bilingual, None, {"case_number": "123/2026"}, language="gu")
    assert ctx_case["case_or_crime"] == "કેસ નં. 123/2026"

    # Only Crime Reg. No. present
    ctx_crime = await build_render_context(mock_user_bilingual, None, {"crime_reg_number": "I-CR 45/2026"}, language="gu")
    assert ctx_crime["case_or_crime"] == "ગુન્હા રજી. નં. I-CR 45/2026"

    # In English
    ctx_en = await build_render_context(mock_user_bilingual, None, {"case_number": "123/2026"}, language="en")
    assert ctx_en["case_or_crime"] == "Case No. 123/2026"


# Test 13-16: End-to-end multi-engine document generation (PDF, DOCX, ODT, PNG)
@pytest.mark.asyncio
async def test_all_document_formats_generation(mock_user_bilingual, mock_case_civil):
    template = next(t for t in TEMPLATES_V2 if t["id"] == "mudat_arji")
    ctx = await build_render_context(mock_user_bilingual, mock_case_civil, {"reason": "માંદગીના"}, language="gu")

    content = render_template(template["content_gu"], ctx)
    blocks = build_blocks(content, title_gu=template.get("name_gu", ""))

    # 1. PDF
    pdf_b64 = generate_pdf(blocks, language="gu", settings=template.get("settings"))
    assert isinstance(pdf_b64, str)
    pdf_bytes = _pdf_bytes_from_b64(pdf_b64)
    assert pdf_bytes.startswith(b"%PDF")

    # 2. DOCX
    docx_b64 = generate_docx(blocks, language="gu", settings=template.get("settings"))
    assert isinstance(docx_b64, str)
    docx_bytes = base64.b64decode(docx_b64)
    assert len(docx_bytes) > 500

    # 3. ODT
    odt_b64 = generate_odt(blocks, language="gu", settings=template.get("settings"))
    assert isinstance(odt_b64, str)
    odt_bytes = base64.b64decode(odt_b64)
    assert len(odt_bytes) > 500

    # 4. PNG
    png_pages = rasterize_pdf_pages(pdf_bytes)
    assert len(png_pages) >= 1
    assert png_pages[0].startswith(b"\x89PNG\r\n\x1a\n")


# Test 17: All 21 templates generate successfully without template error
@pytest.mark.asyncio
async def test_all_21_templates_generation_smoke(mock_user_bilingual, mock_case_civil):
    for t in TEMPLATES_V2:
        ctx = await build_render_context(mock_user_bilingual, mock_case_civil, {}, language="gu")
        content = render_template(t["content_gu"], ctx)
        blocks = build_blocks(content, title_gu=t.get("name_gu", ""))
        pdf_b64 = generate_pdf(blocks, language="gu", settings=t.get("settings"))
        pdf_bytes = _pdf_bytes_from_b64(pdf_b64)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
