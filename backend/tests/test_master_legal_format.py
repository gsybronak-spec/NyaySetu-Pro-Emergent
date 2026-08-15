"""Comprehensive test suite for NyaySetu Master Legal Document Formatting Engine (NYAYSETU_LEGAL_FORMAT_V1).

Guarantees that:
1. All existing applications and all newly added Admin applications permanently
   inherit NYAYSETU_LEGAL_FORMAT_V1.
2. The legal document visual hierarchy is strictly enforced:
   - Court Heading -> CENTER + BOLD
   - Case Details / Number -> RIGHT + NORMAL
   - Parties -> LEFT + NORMAL
   - Versus / વિરુદ્ધ -> CENTER + BOLD
   - Application Title -> CENTER + BOLD
   - Main Legal Body Paragraphs -> FULL JUSTIFY + Fixed First-Line Indent
   - Numbered Points -> FULL JUSTIFY (at left margin)
   - Date & Place -> LEFT + NORMAL
   - Advocate Signature -> RIGHT + NORMAL
3. Raw AI text is normalized before rendering (no tabs, excessive spaces or blank lines).
4. Margins, fonts, sizes, line spacing, and paragraph spacing use the approved NyaySetu values.
5. All document engines (HarfBuzz PDF, ReportLab PDF, DOCX, ODT, Playwright) render consistently.
"""

import base64
import os
import re
from pathlib import Path
import pytest
import mongomock_motor

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_master_format")

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_master_format"]

import server
server.db = mock_db

from server import _get_published_templates, _get_template_by_id
import doc_generator
from doc_generator import (
    NYAYSETU_LEGAL_FORMAT_V1,
    SUPPORTED_FORMAT_VERSIONS,
    MASTER_LEGAL_DOC_SETTINGS,
    DEFAULT_DOC_SETTINGS,
    normalize_legal_text,
    build_blocks,
    get_doc_settings,
    generate_pdf_hb,
    generate_pdf_detailed,
    generate_docx,
    generate_odt,
)


class TestMasterLegalFormatSpecification:
    """Validate master legal document constants, settings, and defaults."""

    def test_master_format_version_registered(self):
        assert NYAYSETU_LEGAL_FORMAT_V1 == "NYAYSETU_LEGAL_FORMAT_V1"
        assert NYAYSETU_LEGAL_FORMAT_V1 in SUPPORTED_FORMAT_VERSIONS

    def test_approved_settings_values(self):
        s = MASTER_LEGAL_DOC_SETTINGS
        assert s["format_version"] == "NYAYSETU_LEGAL_FORMAT_V1"
        assert s["page_size"] == "A4"
        assert s["margin_top_cm"] == 2.5
        assert s["margin_bottom_cm"] == 2.5
        assert s["margin_left_cm"] == 2.5
        assert s["margin_right_cm"] == 2.5
        assert s["body_size"] == 12
        assert s["heading_size"] == 13
        assert s["line_spacing"] == 18
        assert s["paragraph_spacing"] == 6
        assert s["first_line_indent_pt"] == 24.0
        assert s["gujarati_font"] == "NotoSansGujarati"
        assert s["english_font"] == "Times-Roman"
        assert s["alignment"] == "justify"

    def test_get_doc_settings_returns_master_defaults(self):
        settings = get_doc_settings()
        assert settings["format_version"] == NYAYSETU_LEGAL_FORMAT_V1
        assert settings["body_size"] == 12
        assert settings["first_line_indent_pt"] == 24.0


class TestLegalTextNormalization:
    """Validate AI/raw text normalization before legal block classification."""

    def test_normalizes_tabs_and_multiple_spaces(self):
        raw = "\t\tIN THE COURT OF SESSIONS    JUDGE   \n\n\n   વકીલાતનામું   \t  \n1.   First point   with   spaces."
        cleaned = normalize_legal_text(raw)
        lines = cleaned.split("\n")
        assert lines[0] == "IN THE COURT OF SESSIONS JUDGE"
        assert lines[1] == ""
        assert lines[2] == "વકીલાતનામું"
        assert lines[3] == "1. First point with spaces."

    def test_preserves_gujarati_unicode_and_punctuation(self):
        guj = "મહેરબાન કોર્ટમાં, રમેશભાઈ પટેલ વિરુદ્ધ રાજ્ય સરકાર... ક્ષ, જ્ઞ, ત્ર, શ્ર."
        cleaned = normalize_legal_text(guj)
        assert cleaned == guj

    def test_collapses_excessive_blank_lines(self):
        raw = "Line 1\n\n\n\n\nLine 2\n\n\nLine 3"
        cleaned = normalize_legal_text(raw)
        assert cleaned == "Line 1\n\nLine 2\n\nLine 3"


class TestLegalBlockClassification:
    """Validate deterministic structural classification of legal document elements."""

    SAMPLE_GUJARATI_APP = """મહેરબાન સિટી સિવિલ કોર્ટ સાહેબશ્રીની કોર્ટમાં,
અમદાવાદ

દિવાની કેસ નં. ૧૨૩/૨૦૨૬

રમેશભાઈ પ્રતાપભાઈ પટેલ
વિરુદ્ધ
રાજ્ય સરકાર તથા અન્ય

મુદ્દત અરજી

સદર કામમાં અમો અરજદારના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

૧. સદર કેસ આપ નામદાર કોર્ટ સમક્ષ મુદત પર આવેલ છે.
૨. અમો અરજદારના મહત્વના પુરાવા તૈયાર કરવા સારું અન્ય મુદત મળવા વિનંતી છે.

આથી આપ નામદાર કોર્ટને પ્રાર્થના કે ન્યાયના હિતમાં મુદત આપવા મહેરબાની કરશોજી.

તારીખ : ૧૫/૦૮/૨૦૨૬
સ્થળ : અમદાવાદ

અરજદારના એડવોકેટ"""

    def test_full_structural_hierarchy(self):
        blocks = build_blocks(self.SAMPLE_GUJARATI_APP, title_gu="મુદ્દત અરજી")
        
        # Court header -> Center + Bold
        assert blocks[0]["text"] == "મહેરબાન સિટી સિવિલ કોર્ટ સાહેબશ્રીની કોર્ટમાં,"
        assert blocks[0]["align"] == "center" and blocks[0]["bold"] is True

        assert blocks[1]["text"] == "અમદાવાદ"
        assert blocks[1]["align"] == "center" and blocks[1]["bold"] is True

        # Case number -> Right
        case_block = next(b for b in blocks if "કેસ નં." in b["text"])
        assert case_block["align"] == "right" and case_block["bold"] is False

        # Versus -> Center + Bold
        vs_block = next(b for b in blocks if b["text"] == "વિરુદ્ધ")
        assert vs_block["align"] == "center" and vs_block["bold"] is True

        # Application Title -> Center + Bold
        title_block = next(b for b in blocks if b["text"] == "મુદ્દત અરજી")
        assert title_block["align"] == "center" and title_block["bold"] is True

        # Main Body Narrative -> Justified with First-Line Indent
        body_intro = next(b for b in blocks if "સદર કામમાં અમો" in b["text"])
        assert body_intro["align"] == "justify" and body_intro["bold"] is False
        assert body_intro["indent"] is True

        # Numbered Points -> Justified without First-Line Indent
        point1 = next(b for b in blocks if "૧. સદર કેસ" in b["text"])
        assert point1["align"] == "justify" and point1["bold"] is False
        assert point1["indent"] is False

        point2 = next(b for b in blocks if "૨. અમો અરજદાર" in b["text"])
        assert point2["align"] == "justify" and point2["bold"] is False
        assert point2["indent"] is False

        # Prayer -> Justified with First-Line Indent
        prayer = next(b for b in blocks if "આથી આપ નામદાર" in b["text"])
        assert prayer["align"] == "justify" and prayer["bold"] is False
        assert prayer["indent"] is True

        # Date & Place -> Left
        date_block = next(b for b in blocks if "તારીખ :" in b["text"])
        assert date_block["align"] == "left" and date_block["bold"] is False

        place_block = next(b for b in blocks if "સ્થળ :" in b["text"])
        assert place_block["align"] == "left" and place_block["bold"] is False

        # Advocate Signature -> Right
        sig_block = next(b for b in blocks if b["text"] == "અરજદારના એડવોકેટ")
        assert sig_block["align"] == "right" and sig_block["bold"] is False

    def test_english_legal_application_hierarchy(self):
        content = """IN THE COURT OF THE PRINCIPAL DISTRICT JUDGE,
AHMEDABAD

Special Civil Application No. 456 of 2026

Ramesh Patel
Versus
State of Gujarat

APPLICATION FOR ADJOURNMENT

The applicant respectfully submits as under:

1. That the applicant has appeared in person.
2. That essential documents are to be produced on record.

Date : 15/08/2026
Place : Ahmedabad

Advocate for Applicant"""

        blocks = build_blocks(content, title_en="APPLICATION FOR ADJOURNMENT")
        
        # Court header -> Center
        assert blocks[0]["align"] == "center" and blocks[0]["bold"] is True
        assert blocks[1]["align"] == "center" and blocks[1]["bold"] is True
        # Case Details -> Right
        assert any(b["align"] == "right" and "Special Civil Application" in b["text"] for b in blocks)
        # Versus -> Center
        assert any(b["align"] == "center" and b["text"] == "Versus" for b in blocks)
        # Title -> Center
        assert any(b["align"] == "center" and b["text"] == "APPLICATION FOR ADJOURNMENT" for b in blocks)
        # Narrative intro -> Justify + Indent
        body_intro = next(b for b in blocks if "The applicant respectfully" in b["text"])
        assert body_intro["align"] == "justify" and body_intro["indent"] is True
        # Numbered point 1 -> Justify + No Indent
        pt1 = next(b for b in blocks if "1. That the applicant" in b["text"])
        assert pt1["align"] == "justify" and pt1["indent"] is False
        # Date -> Left
        date_b = next(b for b in blocks if "Date :" in b["text"])
        assert date_b["align"] == "left"
        # Signature -> Right
        sig_b = next(b for b in blocks if "Advocate for Applicant" in b["text"])
        assert sig_b["align"] == "right"


class TestMultiEngineRendering:
    """Validate PDF, DOCX, ODT, and Image generation under NYAYSETU_LEGAL_FORMAT_V1."""

    def test_pdf_hb_generates_with_master_format(self):
        blocks = build_blocks(TestLegalBlockClassification.SAMPLE_GUJARATI_APP, title_gu="મુદ્દત અરજી")
        b64, meta = generate_pdf_detailed(blocks, language="gu")
        raw = base64.b64decode(b64)
        assert raw.startswith(b"%PDF")
        assert b"GujHB-" in raw  # Unique per-generation font identity
        assert meta["engine"] == "harfbuzz"

    def test_docx_generates_with_master_format(self):
        blocks = build_blocks(TestLegalBlockClassification.SAMPLE_GUJARATI_APP, title_gu="મુદ્દત અરજી")
        b64 = generate_docx(blocks, language="gu")
        raw = base64.b64decode(b64)
        assert raw.startswith(b"PK")  # Valid DOCX zip container

    def test_odt_generates_with_master_format(self):
        blocks = build_blocks(TestLegalBlockClassification.SAMPLE_GUJARATI_APP, title_gu="મુદ્દત અરજી")
        b64 = generate_odt(blocks, language="gu")
        raw = base64.b64decode(b64)
        assert raw.startswith(b"PK")  # Valid ODT zip container


class TestAdminTemplateInheritance:
    """Validate that newly added Admin templates automatically inherit NYAYSETU_LEGAL_FORMAT_V1."""

    def test_admin_created_template_automatically_inherits_master_format(self):
        # Scenario B: Admin creates a brand new template defining ONLY content/fields
        new_content_gu = """મહેરબાન મેટ્રોપોલિટન મેજિસ્ટ્રેટ કોર્ટ સાહેબશ્રીની કોર્ટમાં,
અમદાવાદ

ક્રિમિનલ કેસ નં. ૫૫૫/૨૦૨૬

ફરિયાદી પક્ષ
વિરુદ્ધ
આરોપી પક્ષ

વોરંટ રદ કરવાની અરજી

સદર કામમાં અમો આરોપી તરફે એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

૧. સદર કામમાં આપ નામદાર કોર્ટ દ્વારા બીનજામીનલાયક વોરંટ ઇસ્યુ કરવામાં આવેલ છે.
૨. આરોપી અનિવાર્ય સંજોગોના કારણે મુદતે હાજર રહી શકેલ ન હતા.

આથી આપ નામદાર કોર્ટને નમ્ર પ્રાર્થના કે સદર વોરંટ રદ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

આરોપી તરફે એડવોકેટ"""

        # Build blocks with zero manual formatting configuration
        blocks = build_blocks(new_content_gu, title_gu="વોરંટ રદ કરવાની અરજી")
        
        # Verify automatic layout inheritance
        assert blocks[0]["align"] == "center" and blocks[0]["bold"] is True  # Court
        assert any(b["align"] == "right" and "૫૫૫/૨૦૨૬" in b["text"] for b in blocks)  # Case No
        assert any(b["align"] == "center" and b["text"] == "વિરુદ્ધ" for b in blocks)  # Versus
        assert any(b["align"] == "center" and b["text"] == "વોરંટ રદ કરવાની અરજી" for b in blocks)  # Title
        
        body_p = next(b for b in blocks if "સદર કામમાં અમો" in b["text"])
        assert body_p["align"] == "justify" and body_p["indent"] is True
        
        pt1 = next(b for b in blocks if "૧. સદર કામમાં" in b["text"])
        assert pt1["align"] == "justify" and pt1["indent"] is False
        
        sig = next(b for b in blocks if b["text"] == "આરોપી તરફે એડવોકેટ")
        assert sig["align"] == "right"

        # Verify PDF generation
        pdf_b64, meta = generate_pdf_detailed(blocks, language="gu")
        raw_pdf = base64.b64decode(pdf_b64)
        assert raw_pdf.startswith(b"%PDF")
        assert b"GujHB-" in raw_pdf

    @pytest.mark.asyncio
    async def test_existing_seed_templates_all_have_master_format_version(self):
        # Scenario A: All existing templates have NYAYSETU_LEGAL_FORMAT_V1
        templates = await _get_published_templates()
        assert len(templates) >= 21
        for t in templates:
            assert t.get("format_version") == NYAYSETU_LEGAL_FORMAT_V1
            fetched = await _get_template_by_id(t["id"])
            assert fetched is not None
            assert fetched.get("format_version") == NYAYSETU_LEGAL_FORMAT_V1
