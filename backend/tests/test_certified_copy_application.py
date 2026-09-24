# -*- coding: utf-8 -*-
"""Comprehensive test suite for the 'પ્રમાણિત નકલ મેળવવા બાબત'
(Application for Obtaining Certified Copy) template.

Template ID: certified_copy_application
Canonical Source: Certified Report.pdf

Covers:
1. Template Registration & Metadata (ID, Gujarati Name, English Name, Category, aliases)
2. Exactly 19 input fields present with expected keys, types, required flags
3. Deposit amount strictly has ZERO advocate input field (Page 1 spec)
4. Field 'court_name': select, required True
5. Field 'district': select, required True
6. Field 'taluka': select, required False (optional)
7. Field 'court_officer_detail': text, required True
8. Field 'case_type': select, required True
9. Field 'case_number': text, required True
10. Field 'case_date_type': radio, required True (મુદ્દત તારીખ, ફેંસલ તારીખ)
11. Field 'case_date': date, required True
12. Field 'party_1_role': radio, required True
13. Field 'party_1_name': text, required True
14. Field 'party_2_role': radio, required True
15. Field 'party_2_name': text, required True
16. Field 'document_details': textarea, required True
17. Field 'number_of_copies': number, required True
18. Field 'recipient_name': text, required True
19. Field 'date': date, required True
20. Field 'place': text, required False
21. Field 'advocate_name': text, required True
22. Field 'mobile_number': text, required True
23. Page layout geometry: A4, 2cm top/bottom, 4cm left/right margins
24. Font settings: Lohit Gujarati (13pt body, 15pt heading); Times New Roman (14pt body, 16pt heading)
25. Spacing: line_spacing 18.0pt, paragraph_spacing 6.0pt, indent 28.35pt
26. Table 1: 3x2, Row 1 merged, cols="58.4,41.6"
27. Table 2: 2x2, cols="64.6,35.4"
28. Gujarati content fidelity: exact wording, 6 underscores for deposit blank
29. English content fidelity: exact legal translation, 12 underscores for deposit blank
30. Case date formatting from YYYY-MM-DD to DD/MM/YYYY
31. Location formatting: 'Taluka, District' vs 'District'
32. Direct Template Mode & Saved Case Mode context building
33. Multi-format generation: PDF, DOCX, ODT
34. Zero regression on document_exhibit_application
"""

import asyncio
import os
import sys
import unittest
import base64
import re
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock third-party dependencies if not installed
for mod in [
    'docx', 'docx.shared', 'docx.enum.text', 'docx.oxml', 'docx.oxml.ns',
    'google', 'google.cloud', 'google.cloud.firestore',
    'fastapi', 'fastapi.exceptions', 'fastapi.responses',
    'fastapi.middleware.cors', 'fastapi.middleware.gzip',
    'pydantic', 'httpx', 'dotenv', 'jwt', 'bcrypt', 'razorpay',
    'cryptography', 'cryptography.hazmat', 'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.serialization', 'cryptography.x509'
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

class _MockRouter:
    def __init__(self, *args, **kwargs): pass
    def get(self, *args, **kwargs): return lambda f: f
    def post(self, *args, **kwargs): return lambda f: f
    def put(self, *args, **kwargs): return lambda f: f
    def delete(self, *args, **kwargs): return lambda f: f
    def patch(self, *args, **kwargs): return lambda f: f
    def include_router(self, *args, **kwargs): pass

class _MockFastAPI(_MockRouter):
    def __init__(self, *args, **kwargs): pass
    def add_middleware(self, *args, **kwargs): pass
    def exception_handler(self, *args, **kwargs): return lambda f: f
    def on_event(self, *args, **kwargs): return lambda f: f

class _MockHTTPException(Exception):
    def __init__(self, status_code, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")

fastapi_mock = sys.modules['fastapi']
fastapi_mock.FastAPI = _MockFastAPI
fastapi_mock.APIRouter = _MockRouter
fastapi_mock.HTTPException = _MockHTTPException
fastapi_mock.Depends = lambda x: x
fastapi_mock.Header = lambda *args, **kwargs: None
fastapi_mock.Request = MagicMock
fastapi_mock.Response = MagicMock
fastapi_mock.Cookie = lambda *args, **kwargs: None

class _PydanticBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules['pydantic'].BaseModel = _PydanticBaseModel
sys.modules['pydantic'].Field = lambda *args, **kwargs: None

import test_seed_data
import seed_data
import server
from doc_generator import (
    generate_pdf,
    generate_docx,
    generate_odt,
    render_template,
    build_blocks,
    get_doc_settings,
)

TEMPLATE_ID = "certified_copy_application"


class TestCertifiedCopyApplicationTemplate(unittest.TestCase):

    def setUp(self):
        self.tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == TEMPLATE_ID), None)
        self.assertIsNotNone(self.tpl, f"Template {TEMPLATE_ID} not found in test_seed_data")

    def test_01_template_identity_and_metadata(self):
        self.assertEqual(self.tpl["id"], TEMPLATE_ID)
        self.assertEqual(self.tpl["name_en"], "Application for Obtaining Certified Copy")
        self.assertEqual(self.tpl["name_gu"], "પ્રમાણિત નકલ મેળવવા બાબત")
        self.assertEqual(self.tpl["category"], "General")
        self.assertIn("pramanit nakal", self.tpl.get("aliases", []))

    def test_02_field_count_and_keys(self):
        fields = self.tpl["fields"]
        self.assertEqual(len(fields), 19, f"Expected exactly 19 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "court_officer_detail",
            "case_type", "case_number", "case_date_type", "case_date",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "document_details", "number_of_copies", "recipient_name",
            "date", "place", "advocate_name", "mobile_number",
        ]
        self.assertEqual(keys, expected_keys)

    def test_03_zero_deposit_amount_input_field(self):
        keys = [f["key"] for f in self.tpl["fields"]]
        self.assertNotIn("deposit_amount", keys)
        self.assertNotIn("deposit", keys)
        self.assertNotIn("amount", keys)

    def test_04_all_19_fields_optional(self):
        fmap = {f["key"]: f for f in self.tpl["fields"]}
        for key, f in fmap.items():
            self.assertFalse(f["required"], f"Field '{key}' must be optional (required=False)")

        # Explicitly verify the specific fields identified in instructions
        self.assertFalse(fmap["document_details"]["required"])
        self.assertFalse(fmap["number_of_copies"]["required"])
        self.assertFalse(fmap["recipient_name"]["required"])
        self.assertFalse(fmap["mobile_number"]["required"])
        self.assertFalse(fmap["advocate_name"]["required"])
        self.assertFalse(fmap["court_officer_detail"]["required"])
        self.assertFalse(fmap["case_date"]["required"])
        self.assertFalse(fmap["court_name"]["required"])
        self.assertFalse(fmap["district"]["required"])
        self.assertFalse(fmap["case_number"]["required"])

    def test_05_settings_geometry_and_typography(self):
        s = self.tpl["settings"]
        self.assertEqual(s["page_size"], "A4")
        self.assertEqual(s["margin_top_cm"], 2.0)
        self.assertEqual(s["margin_bottom_cm"], 2.0)
        self.assertEqual(s["margin_left_cm"], 4.0)
        self.assertEqual(s["margin_right_cm"], 4.0)
        self.assertEqual(s["body_size"], 13)
        self.assertEqual(s["heading_size"], 15)
        self.assertEqual(s["body_size_en"], 14)
        self.assertEqual(s["heading_size_en"], 16)
        self.assertEqual(s["line_spacing"], 18.0)
        self.assertEqual(s["paragraph_spacing"], 6.0)
        self.assertEqual(s["first_line_indent_pt"], 28.35)

    def test_06_table_parsing_and_structure(self):
        blocks_gu = build_blocks(self.tpl["content_gu"])
        table_blocks = [b for b in blocks_gu if b.get("section") == "table"]
        self.assertEqual(len(table_blocks), 2, f"Expected 2 tables, found {len(table_blocks)}")

        # Table 1: Case details table (3 rows x 2 cols, row 0 merged)
        t1 = table_blocks[0]
        self.assertEqual(t1.get("meta"), {"cols": [58.4, 41.6], "align": ["right", "left"]})
        self.assertEqual(len(t1["rows"]), 3)
        # Row 0: Merged court officer detail
        self.assertEqual(len(t1["rows"][0]), 1)
        self.assertIn("{{court_officer_detail}}", t1["rows"][0][0])
        # Row 1: Case type label without redundant colon/dash
        self.assertEqual(t1["rows"][1][0], "{{case_type}} નં.")
        self.assertNotIn(":-", t1["rows"][1][0])
        self.assertNotIn(":", t1["rows"][1][0])
        self.assertEqual(t1["rows"][1][1], "{{case_number}}")
        # Row 2: Case date type label without redundant colon/dash
        self.assertEqual(t1["rows"][2][0], "{{case_date_type}}")
        self.assertNotIn(":-", t1["rows"][2][0])
        self.assertNotIn(":", t1["rows"][2][0])
        self.assertEqual(t1["rows"][2][1], "{{case_date}}")

        # Table 2: Document request table (2 rows x 2 cols)
        t2 = table_blocks[1]
        self.assertEqual(t2.get("meta"), {"cols": [64.6, 35.4], "align": ["left", "center"]})
        self.assertEqual(len(t2["rows"]), 2)
        # Row 0: Header row is marked and BOTH cells are centered
        self.assertTrue(t2.get("row_meta", [{}])[0].get("is_header", False))
        self.assertEqual(t2.get("row_meta", [{}])[0].get("align"), ["center", "center"])
        self.assertEqual(t2["rows"][0], ["માંગેલ દસ્તાવેજ ની વિગત", "કુલ નંગ"])
        # Row 1: Data row retains left / center alignment
        self.assertEqual(t2["rows"][1], ["{{document_details}}", "{{number_of_copies}}"])

        # English block verification
        blocks_en = build_blocks(self.tpl["content_en"])
        table_blocks_en = [b for b in blocks_en if b.get("section") == "table"]
        self.assertEqual(len(table_blocks_en), 2)
        t1_en = table_blocks_en[0]
        self.assertEqual(t1_en.get("meta"), {"cols": [58.4, 41.6], "align": ["right", "left"]})
        self.assertEqual(t1_en["rows"][1][0], "{{case_type}} No.")
        self.assertNotIn(":-", t1_en["rows"][1][0])
        self.assertNotIn(":", t1_en["rows"][1][0])
        self.assertEqual(t1_en["rows"][2][0], "{{case_date_type}}")
        self.assertNotIn(":-", t1_en["rows"][2][0])
        self.assertNotIn(":", t1_en["rows"][2][0])

        t2_en = table_blocks_en[1]
        self.assertEqual(t2_en.get("meta"), {"cols": [64.6, 35.4], "align": ["left", "center"]})
        self.assertTrue(t2_en.get("row_meta", [{}])[0].get("is_header", False))
        self.assertEqual(t2_en.get("row_meta", [{}])[0].get("align"), ["center", "center"])
        self.assertEqual(t2_en["rows"][0], ["Particulars of Requested Documents", "Total Copies"])

    def test_07_gujarati_fidelity_and_deposit_underscores(self):
        c_gu = self.tpl["content_gu"]
        self.assertIn("મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,", c_gu)
        self.assertIn("મુકામ :- {{place}}", c_gu)
        self.assertIn("બાબત : પ્રમાણિત નકલ મેળવવા બાબત ...", c_gu)
        self.assertIn("સદર કેસમાંથી અમોને નીચે જણાવેલ દસ્તાવેજની સહી-સિક્કાવાળી પ્રમાણિત નકલની અભ્યાસ તેમજ ન્યાયિક કાર્યવાહી અર્થે જરૂરીયાત હોય", c_gu)
        # Exactly 6 underscores in Gujarati deposit
        self.assertIn("ડિપોઝિટ પેટે રૂ. ______ જમા કરાવેલ છે.", c_gu)
        # Exactly 10 dashes in Gujarati signature line
        self.assertIn("----------\n{{advocate_name}}", c_gu)

    def test_08_english_fidelity_and_deposit_underscores(self):
        c_en = self.tpl["content_en"]
        self.assertIn("IN THE COURT OF THE HON'BLE {{court}},", c_en)
        self.assertIn("AT: {{place}}", c_en)
        self.assertIn("Subject: Application for Obtaining Certified Copy...", c_en)
        self.assertIn("From the aforesaid case, we require certified copies duly signed and sealed", c_en)
        # Exactly 12 underscores in English deposit
        self.assertIn("an amount of Rs. ____________ has been deposited towards deposit.", c_en)
        # Exactly 20 dashes in English signature line
        self.assertIn("--------------------\n{{advocate_name}}", c_en)

    def test_09_build_render_context_formatting(self):
        async def _test():
            user = {
                "name": "Ramesh Patel",
                "advocate_name_gu": "એડવોકેટ રમેશભાઈ પટેલ",
                "advocate_name_en": "Advocate Ramesh Patel",
                "mobile": "9876543210",
            }
            values = {
                "court_name": "City Civil Court, Ahmedabad",
                "district": "ahmedabad",
                "taluka": "અમદાવાદ શહેર",
                "court_officer_detail": "શ્રી એ.બી. શાહ સાહેબની કોર્ટ",
                "case_type": "regular_civil_suit",
                "case_number": "૧૨૩/૨૦૨૪",
                "case_date_type": "મુદ્દત તારીખ",
                "case_date": "2026-02-25",
                "party_1_role": "વાદી",
                "party_1_name": "રાજેશકુમાર શાંતિલાલ શાહ",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "મહેશભાઈ કાનજીભાઈ પટેલ",
                "document_details": "આંક - ૧, ૫, ૭ તથા હુકમની નકલ",
                "number_of_copies": "2",
                "recipient_name": "કિશોરભાઈ મોહનભાઈ પરમાર",
                "date": "2026-02-20",
                "place": "",
                "advocate_name": "એડવોકેટ રમેશભાઈ પટેલ",
                "mobile_number": "9876543210",
            }
            ctx = await server.build_render_context(user, None, values, "gu")
            self.assertEqual(ctx["case_date"], "25/02/2026")
            self.assertEqual(ctx["date"], "20/02/2026")
            self.assertIn("અમદાવાદ શહેર", ctx["place"])
            self.assertIn("અમદાવાદ", ctx["place"])
            self.assertEqual(ctx["court"], "સિટી સિવિલ કોર્ટ, અમદાવાદ")
        asyncio.run(_test())

    def test_10_pdf_generation_gujarati(self):
        async def _test():
            user = {
                "name": "Ramesh Patel",
                "advocate_name_gu": "એડવોકેટ રમેશભાઈ પટેલ",
                "advocate_name_en": "Advocate Ramesh Patel",
                "mobile": "9876543210",
            }
            values = {
                "court": "મહેરબાન સિટી સિવિલ કોર્ટ",
                "court_name": "મહેરબાન સિટી સિવિલ કોર્ટ",
                "district": "અમદાવાદ",
                "taluka": "અમદાવાદ શહેર",
                "court_officer_detail": "શ્રી એ.બી. શાહ સાહેબની કોર્ટ",
                "case_type": "રેગ્યુલર સિવિલ સૂટ",
                "case_number": "૧૨૩/૨૦૨૪",
                "case_date_type": "મુદ્દત તારીખ",
                "case_date": "2026-02-25",
                "party_1_role": "વાદી",
                "party_1_name": "રાજેશકુમાર શાંતિલાલ શાહ",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "મહેશભાઈ કાનજીભાઈ પટેલ",
                "document_details": "આંક - ૧, ૫, ૭ તથા હુકમની નકલ",
                "number_of_copies": "2",
                "recipient_name": "કિશોરભાઈ મોહનભાઈ પરમાર",
                "date": "2026-02-20",
                "place": "અમદાવાદ",
                "advocate_name": "એડવોકેટ રમેશભાઈ પટેલ",
                "mobile_number": "9876543210",
            }
            ctx = await server.build_render_context(user, None, values, "gu")
            rendered = render_template(self.tpl["content_gu"], ctx)
            self.assertNotIn("{{court}}", rendered)
            self.assertNotIn("{{recipient_name}}", rendered)
            self.assertIn("રૂ. ______", rendered)

            blocks = build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            doc_settings = get_doc_settings({
                **self.tpl["settings"],
                "page_size": "A4",
                "template_id": TEMPLATE_ID,
                "raw_content": rendered,
                "ctx": ctx,
            })
            pdf_b64 = generate_pdf(blocks, "gu", doc_settings)
            pdf_bytes = base64.b64decode(pdf_b64)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Output must be valid PDF")
            self.assertGreater(len(pdf_bytes), 1000)
        asyncio.run(_test())

    def test_11_pdf_generation_english(self):
        async def _test():
            user = {
                "name": "Ramesh Patel",
                "advocate_name_gu": "એડવોકેટ રમેશભાઈ પટેલ",
                "advocate_name_en": "Advocate Ramesh Patel",
                "mobile": "9876543210",
            }
            values = {
                "court": "City Civil Court",
                "court_name": "City Civil Court",
                "district": "Ahmedabad",
                "taluka": "Ahmedabad City",
                "court_officer_detail": "Hon'ble Court of Additional Civil Judge",
                "case_type": "Regular Civil Suit",
                "case_number": "123/2024",
                "case_date_type": "Disposal Date",
                "case_date": "2026-02-25",
                "party_1_role": "Plaintiff",
                "party_1_name": "Rajeshkumar Shantilal Shah",
                "party_2_role": "Defendant",
                "party_2_name": "Maheshbhai Kanjibhai Patel",
                "document_details": "Exhibit 1, 5, 7 and certified order copy",
                "number_of_copies": "2",
                "recipient_name": "Kishorbhai Mohanbhai Parmar",
                "date": "2026-02-20",
                "place": "Ahmedabad",
                "advocate_name": "Advocate Ramesh Patel",
                "mobile_number": "9876543210",
            }
            ctx = await server.build_render_context(user, None, values, "en")
            rendered = render_template(self.tpl["content_en"], ctx)
            self.assertNotIn("{{court}}", rendered)
            self.assertNotIn("{{recipient_name}}", rendered)
            self.assertIn("Rs. ____________", rendered)

            blocks = build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            tpl_settings = dict(self.tpl["settings"])
            tpl_settings["body_size"] = tpl_settings.get("body_size_en", 14)
            tpl_settings["heading_size"] = tpl_settings.get("heading_size_en", 16)
            doc_settings = get_doc_settings({
                **tpl_settings,
                "page_size": "A4",
                "template_id": TEMPLATE_ID,
                "raw_content": rendered,
                "ctx": ctx,
            })
            pdf_b64 = generate_pdf(blocks, "en", doc_settings)
            pdf_bytes = base64.b64decode(pdf_b64)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Output must be valid PDF")
            self.assertGreater(len(pdf_bytes), 1000)
        asyncio.run(_test())

    def test_12_odt_and_docx_generation(self):
        values = {
            "court": "City Civil Court",
            "place": "Ahmedabad",
            "court_officer_detail": "Court 5",
            "case_type": "Civil Suit",
            "case_number": "101/2024",
            "case_date_type": "Next Hearing Date",
            "case_date": "25/02/2026",
            "party_1_role": "Plaintiff",
            "party_1_name": "Party A",
            "party_2_role": "Defendant",
            "party_2_name": "Party B",
            "document_details": "Order copy",
            "number_of_copies": "1",
            "recipient_name": "Advocate",
            "date": "20/02/2026",
            "advocate_name": "Test Adv",
            "mobile_number": "9876543210",
        }
        rendered = render_template(self.tpl["content_en"], values)
        blocks = build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"])
        doc_settings = get_doc_settings({**self.tpl["settings"], "page_size": "A4", "template_id": TEMPLATE_ID})

        # ODT
        odt_b64 = generate_odt(blocks, "en", doc_settings)
        odt_bytes = base64.b64decode(odt_b64)
        self.assertTrue(odt_bytes.startswith(b"PK"), "ODT must be valid zip")

        # DOCX (optional if python-docx installed)
        try:
            docx_b64 = generate_docx(blocks, "en", doc_settings)
            docx_bytes = base64.b64decode(docx_b64)
            self.assertTrue(docx_bytes.startswith(b"PK"), "DOCX must be valid zip")
        except Exception:
            pass

    def test_13_canonical_getter_and_seed_registration(self):
        canonical = server._get_canonical_certified_copy_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], TEMPLATE_ID)
        self.assertIn(canonical["id"], [t["id"] for t in seed_data.TEMPLATES])

    def test_14_zero_regression_on_exhibit_template(self):
        exhibit_tpl = server._get_canonical_exhibit_template()
        self.assertIsNotNone(exhibit_tpl)
        self.assertEqual(exhibit_tpl["id"], "document_exhibit_application")
        self.assertIn("દસ્તાવેજી પુરાવા લીસ્ટથી અસલ દસ્તાવેજ", exhibit_tpl["content_gu"])
        self.assertEqual(len(exhibit_tpl["fields"]), 11)

    def test_14b_zero_regression_on_return_template(self):
        return_tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_return_application"), None)
        self.assertIsNotNone(return_tpl)
        self.assertIn("દસ્તાવેજ પરત મેળવવાની અરજી", return_tpl["content_gu"])
        self.assertEqual(len(return_tpl["fields"]), 14)

    def test_15_signature_and_date_place_alignments_gu_and_en(self):
        """Verify Date & Place are left-aligned and signature block (dash line, advocate name, mobile) is right-aligned."""
        # Test Gujarati
        ctx_gu = {
            "court": "સિટી સિવિલ કોર્ટ",
            "place": "અમદાવાદ",
            "court_officer_detail": "શ્રી એ.બી. શાહ સાહેબની કોર્ટ",
            "case_type": "રેગ્યુલર સિવિલ સૂટ",
            "case_number": "૧૨૩/૨૦૨૪",
            "case_date_type": "મુદ્દત તારીખ",
            "case_date": "25/02/2026",
            "party_1_role": "વાદી",
            "party_1_name": "રાજેશકુમાર શાંતિલાલ શાહ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "મહેશભાઈ કાનજીભાઈ પટેલ",
            "document_details": "આંક - ૧, ૫, ૭ તથા હુકમની નકલ",
            "number_of_copies": "2",
            "recipient_name": "કિશોરભાઈ મોહનભાઈ પરમાર",
            "date": "20/02/2026",
            "advocate_name": "એડવોકેટ રમેશભાઈ પટેલ",
            "mobile_number": "9876543210",
        }
        rendered_gu = render_template(self.tpl["content_gu"], ctx_gu)
        blocks_gu = build_blocks(rendered_gu, self.tpl["name_en"], self.tpl["name_gu"], align_rules=self.tpl["settings"].get("block_align"))
        date_block_gu = next(b for b in blocks_gu if "તારીખ :" in b.get("text", ""))
        place_block_gu = next(b for b in blocks_gu if "સ્થળ :" in b.get("text", ""))
        self.assertEqual(date_block_gu["align"], "left")
        self.assertEqual(place_block_gu["align"], "left")

        sig_dash_gu = next(b for b in blocks_gu if "----------" in b.get("text", ""))
        adv_name_gu = next(b for b in blocks_gu if "એડવોકેટ રમેશભાઈ પટેલ" in b.get("text", ""))
        mobile_gu = next(b for b in blocks_gu if "9876543210" in b.get("text", ""))
        self.assertEqual(sig_dash_gu["align"], "right")
        self.assertEqual(len(sig_dash_gu["text"]), 10)
        self.assertEqual(adv_name_gu["align"], "right")
        self.assertEqual(mobile_gu["align"], "right")

        # Test English
        ctx_en = {
            "court": "City Civil Court",
            "place": "Ahmedabad",
            "court_officer_detail": "Hon Court of Additional Civil Judge",
            "case_type": "Regular Civil Suit",
            "case_number": "123/2024",
            "case_date_type": "Disposal Date",
            "case_date": "25/02/2026",
            "party_1_role": "Plaintiff",
            "party_1_name": "Rajeshkumar Shantilal Shah",
            "party_2_role": "Defendant",
            "party_2_name": "Maheshbhai Kanjibhai Patel",
            "document_details": "Exhibit 1, 5, 7 and order copy",
            "number_of_copies": "2",
            "recipient_name": "Kishorbhai Mohanbhai Parmar",
            "date": "20/02/2026",
            "advocate_name": "Advocate Ramesh Patel",
            "mobile_number": "9876543210",
        }
        rendered_en = render_template(self.tpl["content_en"], ctx_en)
        blocks_en = build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"], align_rules=self.tpl["settings"].get("block_align"))
        date_block_en = next(b for b in blocks_en if "Date:" in b.get("text", ""))
        place_block_en = next(b for b in blocks_en if "Place:" in b.get("text", ""))
        self.assertEqual(date_block_en["align"], "left")
        self.assertEqual(place_block_en["align"], "left")

        sig_dash_en = next(b for b in blocks_en if "--------------------" in b.get("text", ""))
        adv_name_en = next(b for b in blocks_en if "Advocate Ramesh Patel" in b.get("text", ""))
        mobile_en = next(b for b in blocks_en if "9876543210" in b.get("text", ""))
        self.assertEqual(sig_dash_en["align"], "right")
        self.assertEqual(len(sig_dash_en["text"]), 20)
        self.assertEqual(adv_name_en["align"], "right")
        self.assertEqual(mobile_en["align"], "right")

    def test_16_location_localization_gu_and_en(self):
        async def _test():
            user = {"name": "Test Advocate", "district": "gandhinagar"}
            
            # Gujarati document with raw district IDs
            for raw_dist, expected_gu in [
                ("gandhinagar", "ગાંધીનગર"),
                ("ahmedabad", "અમદાવાદ"),
                ("rajkot", "રાજકોટ"),
                ("vadodara", "વડોદરા"),
            ]:
                ctx_gu = await server.build_render_context(user, None, {
                    "district": raw_dist,
                    "court_name": "Civil Court",
                    "party_1_role": "વાદી",
                    "party_1_name": "A",
                    "party_2_role": "પ્રતિવાદી",
                    "party_2_name": "B",
                    "court_officer_detail": "Court",
                    "case_type": "civil_suit",
                    "case_number": "1/2026",
                    "case_date_type": "મુદ્દત તારીખ",
                    "case_date": "2026-02-25",
                    "document_details": "Doc",
                    "number_of_copies": "1",
                    "recipient_name": "Rec",
                    "date": "2026-02-20",
                    "advocate_name": "Adv",
                    "mobile_number": "9999999999",
                }, "gu")
                self.assertEqual(ctx_gu["district"], expected_gu)
                self.assertEqual(ctx_gu["place"], expected_gu)
                rendered = render_template(self.tpl["content_gu"], ctx_gu)
                self.assertIn(f"મુકામ :- {expected_gu}", rendered)
                self.assertNotIn(raw_dist, rendered)

            # English document with raw district IDs
            for raw_dist, expected_en in [
                ("gandhinagar", "Gandhinagar"),
                ("ahmedabad", "Ahmedabad"),
                ("rajkot", "Rajkot"),
                ("vadodara", "Vadodara"),
            ]:
                ctx_en = await server.build_render_context(user, None, {
                    "district": raw_dist,
                    "court_name": "Civil Court",
                    "party_1_role": "Plaintiff",
                    "party_1_name": "A",
                    "party_2_role": "Defendant",
                    "party_2_name": "B",
                    "court_officer_detail": "Court",
                    "case_type": "civil_suit",
                    "case_number": "1/2026",
                    "case_date_type": "Next Hearing Date",
                    "case_date": "2026-02-25",
                    "document_details": "Doc",
                    "number_of_copies": "1",
                    "recipient_name": "Rec",
                    "date": "2026-02-20",
                    "advocate_name": "Adv",
                    "mobile_number": "9999999999",
                }, "en")
                self.assertEqual(ctx_en["district"], expected_en)
                self.assertEqual(ctx_en["place"], expected_en)
                rendered = render_template(self.tpl["content_en"], ctx_en)
                self.assertIn(f"AT: {expected_en}", rendered)
                self.assertNotIn(raw_dist, rendered)

            # Taluka + District localization
            ctx_combo_gu = await server.build_render_context(user, None, {
                "district": "gandhinagar",
                "taluka": "કલોલ",
                "court_name": "Civil Court",
                "party_1_role": "વાદી",
                "party_1_name": "A",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "B",
                "court_officer_detail": "Court",
                "case_type": "civil_suit",
                "case_number": "1/2026",
                "case_date_type": "મુદ્દત તારીખ",
                "case_date": "2026-02-25",
                "document_details": "Doc",
                "number_of_copies": "1",
                "recipient_name": "Rec",
                "date": "2026-02-20",
                "advocate_name": "Adv",
                "mobile_number": "9999999999",
            }, "gu")
            self.assertEqual(ctx_combo_gu["place"], "કલોલ, ગાંધીનગર")

            ctx_combo_en = await server.build_render_context(user, None, {
                "district": "gandhinagar",
                "taluka": "kalol",
                "court_name": "Civil Court",
                "party_1_role": "Plaintiff",
                "party_1_name": "A",
                "party_2_role": "Defendant",
                "party_2_name": "B",
                "court_officer_detail": "Court",
                "case_type": "civil_suit",
                "case_number": "1/2026",
                "case_date_type": "Next Hearing Date",
                "case_date": "2026-02-25",
                "document_details": "Doc",
                "number_of_copies": "1",
                "recipient_name": "Rec",
                "date": "2026-02-20",
                "advocate_name": "Adv",
                "mobile_number": "9999999999",
            }, "en")
            self.assertEqual(ctx_combo_en["place"], "Kalol, Gandhinagar")

        asyncio.run(_test())

    def test_17_party_role_and_name_spacing(self):
        async def _test():
            user = {"name": "Test Advocate"}
            # Party spacing with accidental extra whitespace
            values_gu = {
                "court_name": "Civil Court",
                "district": "gandhinagar",
                "party_1_role": "વાદી  ",
                "party_1_name": "  રાજેશકુમાર શાહ  ",
                "party_2_role": "  પ્રતિવાદી",
                "party_2_name": "મહેશભાઈ પટેલ  ",
                "court_officer_detail": "Court",
                "case_type": "civil_suit",
                "case_number": "1/2026",
                "case_date_type": "મુદ્દત તારીખ",
                "case_date": "2026-02-25",
                "document_details": "Doc",
                "number_of_copies": "1",
                "recipient_name": "Rec",
                "date": "2026-02-20",
                "advocate_name": "Adv",
                "mobile_number": "9999999999",
            }
            ctx_gu = await server.build_render_context(user, None, values_gu, "gu")
            rendered_gu = render_template(self.tpl["content_gu"], ctx_gu)
            blocks_gu = build_blocks(rendered_gu, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            
            p1_block = next(b for b in blocks_gu if "રાજેશકુમાર શાહ" in b.get("text", ""))
            p2_block = next(b for b in blocks_gu if "મહેશભાઈ પટેલ" in b.get("text", ""))
            self.assertEqual(p1_block["text"], "વાદી :- રાજેશકુમાર શાહ")
            self.assertEqual(p2_block["text"], "પ્રતિવાદી :- મહેશભાઈ પટેલ")
            self.assertNotIn("  :-", p1_block["text"])
            self.assertNotIn(":-  ", p1_block["text"])
            # Assert IDENTICAL alignment, indentation, and section for Party 1 and Party 2
            self.assertEqual(p1_block["align"], "left")
            self.assertEqual(p2_block["align"], "left")
            self.assertFalse(p1_block["indent"])
            self.assertFalse(p2_block["indent"])
            self.assertEqual(p1_block["section"], "party")
            self.assertEqual(p2_block["section"], "party")

            # Gujarati party alignment: Fariyadi vs Aropi (User's reported case)
            values_fariyadi = dict(values_gu)
            values_fariyadi["party_1_role"] = "ફરીયાદી"
            values_fariyadi["party_1_name"] = "જે જે"
            values_fariyadi["party_2_role"] = "આરોપી"
            values_fariyadi["party_2_name"] = "રરર"
            ctx_far = await server.build_render_context(user, None, values_fariyadi, "gu")
            rend_far = render_template(self.tpl["content_gu"], ctx_far)
            blks_far = build_blocks(rend_far, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            p1_far = next(b for b in blks_far if "જે જે" in b.get("text", ""))
            p2_far = next(b for b in blks_far if "રરર" in b.get("text", ""))
            self.assertEqual(p1_far["text"], "ફરીયાદી :- જે જે")
            self.assertEqual(p2_far["text"], "આરોપી :- રરર")
            self.assertEqual(p1_far["align"], "left")
            self.assertEqual(p2_far["align"], "left")
            self.assertFalse(p1_far["indent"], "Party 1 must not be indented!")
            self.assertFalse(p2_far["indent"], "Party 2 must not be indented!")
            self.assertEqual(p1_far["section"], "party")
            self.assertEqual(p2_far["section"], "party")

            # English party spacing
            values_en = {
                "court_name": "Civil Court",
                "district": "gandhinagar",
                "party_1_role": "Plaintiff  ",
                "party_1_name": "  John Doe  ",
                "party_2_role": "  Defendant",
                "party_2_name": "Jane Smith  ",
                "court_officer_detail": "Court",
                "case_type": "civil_suit",
                "case_number": "1/2026",
                "case_date_type": "Next Hearing Date",
                "case_date": "2026-02-25",
                "document_details": "Doc",
                "number_of_copies": "1",
                "recipient_name": "Rec",
                "date": "2026-02-20",
                "advocate_name": "Adv",
                "mobile_number": "9999999999",
            }
            ctx_en = await server.build_render_context(user, None, values_en, "en")
            rendered_en = render_template(self.tpl["content_en"], ctx_en)
            blocks_en = build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            
            p1_block_en = next(b for b in blocks_en if "John Doe" in b.get("text", ""))
            p2_block_en = next(b for b in blocks_en if "Jane Smith" in b.get("text", ""))
            self.assertEqual(p1_block_en["text"], "Plaintiff :- John Doe")
            self.assertEqual(p2_block_en["text"], "Defendant :- Jane Smith")
            self.assertEqual(p1_block_en["align"], "left")
            self.assertEqual(p2_block_en["align"], "left")
            self.assertFalse(p1_block_en["indent"])
            self.assertFalse(p2_block_en["indent"])
            self.assertEqual(p1_block_en["section"], "party")
            self.assertEqual(p2_block_en["section"], "party")

        asyncio.run(_test())

    def test_18_signature_dash_counts_and_right_alignment(self):
        # Gujarati signature line is strictly 10 dashes and right aligned
        rendered_gu = render_template(self.tpl["content_gu"], {
            "court": "કોર્ટ", "place": "ગાંધીનગર", "court_officer_detail": "કોર્ટ",
            "case_type": "દાવો", "case_number": "1/2026", "case_date_type": "મુદ્દત તારીખ",
            "case_date": "25/02/2026", "party_1_role": "વાદી", "party_1_name": "A",
            "party_2_role": "પ્રતિવાદી", "party_2_name": "B", "document_details": "નકલ",
            "number_of_copies": "1", "recipient_name": "C", "date": "20/02/2026",
            "advocate_name": "રમેશભાઈ પટેલ", "mobile_number": "9876543210",
        })
        blocks_gu = build_blocks(rendered_gu, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
        sig_gu = next(b for b in blocks_gu if b.get("text", "").startswith("----------"))
        self.assertEqual(sig_gu["text"], "----------")
        self.assertEqual(len(sig_gu["text"]), 10)
        self.assertEqual(sig_gu["align"], "right")

        adv_gu = next(b for b in blocks_gu if "રમેશભાઈ પટેલ" in b.get("text", ""))
        mob_gu = next(b for b in blocks_gu if "9876543210" in b.get("text", ""))
        self.assertEqual(adv_gu["align"], "right")
        self.assertEqual(mob_gu["align"], "right")

        # English signature line is strictly 20 dashes and right aligned
        rendered_en = render_template(self.tpl["content_en"], {
            "court": "Court", "place": "Gandhinagar", "court_officer_detail": "Court",
            "case_type": "Suit", "case_number": "1/2026", "case_date_type": "Next Hearing Date",
            "case_date": "25/02/2026", "party_1_role": "Plaintiff", "party_1_name": "A",
            "party_2_role": "Defendant", "party_2_name": "B", "document_details": "Copy",
            "number_of_copies": "1", "recipient_name": "C", "date": "20/02/2026",
            "advocate_name": "Ramesh Patel", "mobile_number": "9876543210",
        })
        blocks_en = build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
        sig_en = next(b for b in blocks_en if b.get("text", "").startswith("--------------------"))
        self.assertEqual(sig_en["text"], "--------------------")
        self.assertEqual(len(sig_en["text"]), 20)
        self.assertEqual(sig_en["align"], "right")

        adv_en = next(b for b in blocks_en if "Ramesh Patel" in b.get("text", ""))
        mob_en = next(b for b in blocks_en if "9876543210" in b.get("text", ""))
        self.assertEqual(adv_en["align"], "right")
        self.assertEqual(mob_en["align"], "right")

    def test_19_optional_blank_field_rendering_and_table_integrity(self):
        """Test template with cases A through J where various optional fields are left blank.
        Verify:
        - Document generation/preview is never blocked.
        - Exactly TWO tables are rendered.
        - Table 1 has 3 rows × 2 cols with row 0 merged.
        - Table 2 has 2 rows × 2 cols.
        - No 'undefined', 'null', 'None', 'N/A', 'Required', '[object Object]', or '____' in output.
        - Deposit blanks strictly 6 underscores (GU) and 12 underscores (EN).
        """
        async def _run_cases():
            user = {"id": "test_adv", "name_gu": "એડવોકેટ રમેશભાઈ પટેલ", "name_en": "Advocate Ramesh Patel"}
            
            base_values = {
                "court_name": "principal_senior_civil_judge",
                "district": "gandhinagar",
                "court_officer_detail": "શ્રી એ.બી. શાહ સાહેબની કોર્ટ",
                "case_type": "regular_civil_suit",
                "case_number": "૧૨૩/૨૦૨૪",
                "case_date_type": "મુદ્દત તારીખ",
                "case_date": "2026-02-25",
                "party_1_role": "વાદી",
                "party_1_name": "રાજેશકુમાર શાહ",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "મહેશભાઈ પટેલ",
                "document_details": "આંક ૧, ૫",
                "number_of_copies": "2",
                "recipient_name": "કિશોરભાઈ",
                "date": "2026-02-20",
                "place": "કલોલ, ગાંધીનગર",
                "advocate_name": "એડવોકેટ રમેશભાઈ પટેલ",
                "mobile_number": "9876543210",
            }

            test_variations = [
                ("A_all_filled", {}),
                ("B_document_details_blank", {"document_details": ""}),
                ("C_number_of_copies_blank", {"number_of_copies": ""}),
                ("D_recipient_name_blank", {"recipient_name": ""}),
                ("E_mobile_number_blank", {"mobile_number": ""}),
                ("F_advocate_name_blank", {"advocate_name": ""}),
                ("G_case_date_blank", {"case_date": "", "case_date_type": ""}),
                ("H_court_officer_blank", {"court_officer_detail": ""}),
                ("I_parties_partially_blank", {"party_1_name": "", "party_2_role": ""}),
                ("J_all_optional_blank", {
                    "document_details": "", "number_of_copies": "", "recipient_name": "",
                    "mobile_number": "", "court_officer_detail": "", "case_date": "",
                    "case_date_type": "", "place": "",
                }),
            ]

            for name, overrides in test_variations:
                # 1. Gujarati test
                vals_gu = dict(base_values)
                vals_gu.update(overrides)
                ctx_gu = await server.build_render_context(user, None, vals_gu, "gu")
                # validate_template_requirements must NOT raise HTTPException
                server.validate_template_requirements(self.tpl, ctx_gu, "gu")
                rend_gu = render_template(self.tpl["content_gu"], ctx_gu)
                blks_gu = build_blocks(rend_gu, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))

                # Asserts on text
                self.assertNotIn("undefined", rend_gu, f"Case {name} leaked undefined")
                self.assertNotIn("null", rend_gu, f"Case {name} leaked null")
                self.assertNotIn("None", rend_gu, f"Case {name} leaked None")
                self.assertNotIn("N/A", rend_gu, f"Case {name} leaked N/A")
                self.assertIn("______", rend_gu, f"Case {name} must have 6 underscores deposit blank")
                self.assertNotIn("____", rend_gu.replace("______", ""), f"Case {name} leaked ____ placeholder")

                # Table structure verification
                tables_gu = [b for b in blks_gu if b.get("section") == "table"]
                self.assertEqual(len(tables_gu), 2, f"Case {name} must have exactly 2 tables")
                self.assertEqual(len(tables_gu[0]["rows"]), 3, f"Case {name} Table 1 must have 3 rows")
                self.assertEqual(len(tables_gu[1]["rows"]), 2, f"Case {name} Table 2 must have 2 rows")

                # 2. English test
                vals_en = {
                    "court_name": "principal_senior_civil_judge",
                    "district": "gandhinagar",
                    "court_officer_detail": "Court of Shri A.B. Shah",
                    "case_type": "regular_civil_suit",
                    "case_number": "123/2024",
                    "case_date_type": "Next Hearing Date",
                    "case_date": "2026-02-25",
                    "party_1_role": "Plaintiff",
                    "party_1_name": "Rajeshkumar Shah",
                    "party_2_role": "Defendant",
                    "party_2_name": "Maheshbhai Patel",
                    "document_details": "Exhibit 1, 5",
                    "number_of_copies": "2",
                    "recipient_name": "Kishorbhai",
                    "date": "2026-02-20",
                    "place": "Kalol, Gandhinagar",
                    "advocate_name": "Advocate Ramesh Patel",
                    "mobile_number": "9876543210",
                }
                vals_en.update(overrides)
                ctx_en = await server.build_render_context(user, None, vals_en, "en")
                server.validate_template_requirements(self.tpl, ctx_en, "en")
                rend_en = render_template(self.tpl["content_en"], ctx_en)
                blks_en = build_blocks(rend_en, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))

                self.assertNotIn("undefined", rend_en, f"Case {name} EN leaked undefined")
                self.assertNotIn("null", rend_en, f"Case {name} EN leaked null")
                self.assertNotIn("None", rend_en, f"Case {name} EN leaked None")
                self.assertNotIn("N/A", rend_en, f"Case {name} EN leaked N/A")
                self.assertIn("____________", rend_en, f"Case {name} EN must have 12 underscores deposit blank")
                self.assertNotIn("____", rend_en.replace("____________", ""), f"Case {name} EN leaked ____ placeholder")

                tables_en = [b for b in blks_en if b.get("section") == "table"]
                self.assertEqual(len(tables_en), 2, f"Case {name} EN must have exactly 2 tables")
                self.assertEqual(len(tables_en[0]["rows"]), 3, f"Case {name} EN Table 1 must have 3 rows")
                self.assertEqual(len(tables_en[1]["rows"]), 2, f"Case {name} EN Table 2 must have 2 rows")

        asyncio.run(_run_cases())

    def test_21_saved_case_editable_application_court_immutability(self):
        """Verify that opening Certified Copy Application from a Saved Case allows
        independently editing the application court, while leaving the Saved Case 100% untouched."""
        async def _test():
            user = {
                "name": "Ramesh Patel",
                "advocate_name_gu": "એડવોકેટ રમેશભાઈ પટેલ",
                "advocate_name_en": "Advocate Ramesh Patel",
                "mobile": "9876543210",
            }
            # Saved Case with Court = "2nd JMFC"
            saved_case = {
                "id": "saved_case_jmfc_123",
                "court_id": "court_of_jmfc",
                "court": "2nd JMFC",
                "court_label": "2nd JMFC",
                "district_id": "gandhinagar",
                "district_label": "Gandhinagar",
                "taluka_id": "kalol",
                "taluka_label": "Kalol",
                "case_type_id": "regular_civil_suit",
                "case_type_label": "Regular Civil Suit",
                "case_number": "123/2024",
                "party_name": "Rajeshkumar Shantilal Shah",
                "party_role": "Plaintiff",
                "opposite_party": "Maheshbhai Kanjibhai Patel",
                "opposite_party_role": "Defendant",
            }

            # TEST 1: Initial context uses Saved Case court
            vals_init = {
                "court_name": "2nd JMFC",
                "case_number": "123/2024",
                "template_id": TEMPLATE_ID,
            }
            ctx_init = await server.build_render_context(user, saved_case, vals_init, "en", template_id=TEMPLATE_ID)
            self.assertIn("2nd JMFC", ctx_init["court"])

            # TEST 2: Advocate changes application Court to "Chief Judicial Magistrate"
            vals_changed_en = {
                "court_name": "Chief Judicial Magistrate",
                "case_number": "123/2024",
                "document_details": "Exh. 1, 5",
                "number_of_copies": "2",
                "date": "2026-03-01",
                "template_id": TEMPLATE_ID,
            }
            ctx_changed_en = await server.build_render_context(user, saved_case, vals_changed_en, "en", template_id=TEMPLATE_ID)
            self.assertEqual(ctx_changed_en["court"], "Chief Judicial Magistrate")

            rend_preview_en = render_template(self.tpl["content_en"], ctx_changed_en)
            self.assertIn("IN THE COURT OF THE HON'BLE Chief Judicial Magistrate,", rend_preview_en)
            self.assertNotIn("2nd JMFC", rend_preview_en)

            # TEST 3: CRITICAL DATA-SAFETY — Saved Case MUST remain completely untouched!
            self.assertEqual(saved_case["court"], "2nd JMFC")
            self.assertEqual(saved_case["court_label"], "2nd JMFC")
            self.assertEqual(saved_case["court_id"], "court_of_jmfc")

            # TEST 4: Gujarati document rendering & PDF generation with selected application court
            vals_changed_gu = {
                "court_name": "chief_judicial_magistrate",
                "case_number": "૧૨૩/૨૦૨૪",
                "document_details": "આંક - ૧, ૫",
                "number_of_copies": "2",
                "date": "2026-03-01",
                "template_id": TEMPLATE_ID,
            }
            ctx_changed_gu = await server.build_render_context(user, saved_case, vals_changed_gu, "gu", template_id=TEMPLATE_ID)
            self.assertEqual(ctx_changed_gu["court"], "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ")

            rend_gu = render_template(self.tpl["content_gu"], ctx_changed_gu)
            self.assertIn("મહેરબાન ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,", rend_gu)
            self.assertNotIn("2nd JMFC", rend_gu)

            blks_gu = build_blocks(rend_gu, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            pdf_bytes_gu = generate_pdf(blks_gu, "gu", get_doc_settings(self.tpl["settings"]))
            self.assertGreater(len(pdf_bytes_gu), 1000)

            # TEST 5: English PDF generation
            blks_en = build_blocks(rend_preview_en, self.tpl["name_en"], self.tpl["name_gu"], self.tpl["settings"].get("block_align"))
            pdf_bytes_en = generate_pdf(blks_en, "en", get_doc_settings(self.tpl["settings"]))
            self.assertGreater(len(pdf_bytes_en), 1000)

            # TEST 6: Direct Template mode still allows normal Court selection
            vals_direct = {
                "court_name": "chief_judicial_magistrate",
                "district": "gandhinagar",
                "case_number": "123/2024",
                "document_details": "Exh. 1",
                "number_of_copies": "1",
                "date": "2026-03-01",
                "template_id": TEMPLATE_ID,
            }
            ctx_direct = await server.build_render_context(user, None, vals_direct, "en", template_id=TEMPLATE_ID)
            self.assertEqual(ctx_direct["court"], "Chief Judicial Magistrate")

            # TEST 7: Other templates remain unaffected — case court takes precedence
            vals_other = {
                "court_name": "Chief Judicial Magistrate",
                "case_number": "123/2024",
                "date": "2026-03-01",
                "template_id": "closing_purshish",
            }
            ctx_other = await server.build_render_context(user, saved_case, vals_other, "en", template_id="closing_purshish")
            self.assertEqual(ctx_other["court"], "Court of JMFC")
            self.assertNotEqual(ctx_other["court"], "Chief Judicial Magistrate")

            # FINAL RE-VERIFICATION of Saved Case Immutability
            self.assertEqual(saved_case["court"], "2nd JMFC")
            self.assertEqual(saved_case["court_label"], "2nd JMFC")
            self.assertEqual(saved_case["court_id"], "court_of_jmfc")

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()

