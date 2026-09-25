# -*- coding: utf-8 -*-
import os
import re
import unittest
import base64
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

from test_seed_data import TEMPLATES
import doc_generator
import server


class TestReopenRightToArgueApplicationTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "reopen_right_to_argue_application"), None)
        self.assertIsNotNone(self.tpl, "reopen_right_to_argue_application template must be present in TEMPLATES")

    def test_01_template_exists_and_active(self):
        """1. Verify template exists, is active, and has canonical metadata."""
        self.assertEqual(self.tpl["id"], "reopen_right_to_argue_application")
        self.assertEqual(self.tpl["name_gu"], "દલીલો કરવા નો હક ફરીથી ખોલાવવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Reopening the Right to Make Arguments")
        self.assertEqual(self.tpl.get("category"), "General")
        self.assertTrue(self.tpl.get("is_active"))
        aliases = self.tpl.get("aliases", [])
        self.assertIn("દલીલો કરવા નો હક ફરીથી ખોલાવવાની અરજી", aliases)
        self.assertIn("reopen right to argue application", aliases)

        # Check server canonical getter
        canonical = server._get_canonical_reopen_right_to_argue_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "reopen_right_to_argue_application")

    def test_02_field_count_is_exactly_14(self):
        """2. Verify template has exactly 14 advocate-facing fields."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 14, f"Expected exactly 14 fields, found {len(fields)}")

    def test_03_field_order_and_types(self):
        """3. Verify exact field keys, sequence, and types."""
        fields = self.tpl.get("fields", [])
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "argument_failure_reason",
            "date", "place", "advocate_name",
        ]
        self.assertEqual(keys, expected_keys)

        expected_types = {
            "court_name": "select",
            "district": "select",
            "taluka": "select",
            "case_type": "select",
            "case_number": "text",
            "party_1_role": "radio",
            "party_1_name": "text",
            "party_2_role": "radio",
            "party_2_name": "text",
            "advocate_for": "select",
            "argument_failure_reason": "select",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for f in fields:
            self.assertEqual(f["type"], expected_types[f["key"]], f"Field {f['key']} has unexpected type {f['type']}")

    def test_04_all_fields_optional_required_false(self):
        """4. Verify every field has required: False."""
        for f in self.tpl.get("fields", []):
            self.assertFalse(f.get("required"), f"Field {f['key']} must have required: False")

    def test_05_court_name_formatting(self):
        """5. Verify Court Name is centered, bold, 15pt GU / 16pt EN."""
        rules = self.tpl["settings"].get("block_align", [])
        court_rule = next((r for r in rules if r.get("contains") == "કોર્ટમાં" or r.get("contains") == "IN THE COURT OF"), None)
        self.assertIsNotNone(court_rule)
        self.assertEqual(court_rule["align"], "center")
        self.assertTrue(court_rule["bold"])
        self.assertEqual(self.tpl["settings"]["heading_size"], 15)
        self.assertEqual(self.tpl["settings"]["heading_size_en"], 16)

    def test_06_mukam_line_formatting(self):
        """6. Verify Mukam line is centered, regular body (bold: False), 13pt GU / 14pt EN."""
        rules = self.tpl["settings"].get("block_align", [])
        mukam_rule = next((r for r in rules if r.get("prefix") == "મુકામ :-" or r.get("prefix") == "At :-"), None)
        self.assertIsNotNone(mukam_rule)
        self.assertEqual(mukam_rule["align"], "center")
        self.assertFalse(mukam_rule["bold"])
        self.assertEqual(self.tpl["settings"]["body_size"], 13)
        self.assertEqual(self.tpl["settings"]["body_size_en"], 14)

    def test_07_case_details_right_aligned(self):
        """7. Verify Case Details line is right-aligned."""
        rules = self.tpl["settings"].get("block_align", [])
        case_rule = next((r for r in rules if "કેસ નં." in r.get("contains", "") or "Case No." in r.get("contains", "")), None)
        self.assertIsNotNone(case_rule)
        self.assertEqual(case_rule["align"], "right")

    def test_08_party_1_and_party_2_left_aligned(self):
        """8. Verify Party 1 & Party 2 are left-aligned with zero first-line indent."""
        rendered = """મહેરબાન ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,
મુકામ :- ગાંધીનગર

ક્રિમિનલ કેસ નં. : ૧૦૧/૨૦૨૪

ફરીયાદી :- રમેશભાઈ પટેલ
વિરુદ્ધ
આરોપી :- સુરેશભાઈ શાહ

બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત...
"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        p1_block = next((b for b in blocks if "ફરીયાદી :-" in b["text"]), None)
        p2_block = next((b for b in blocks if "આરોપી :-" in b["text"]), None)
        self.assertIsNotNone(p1_block)
        self.assertIsNotNone(p2_block)
        self.assertEqual(p1_block["align"], "left")
        self.assertEqual(p2_block["align"], "left")
        self.assertFalse(p1_block.get("indent", False))
        self.assertFalse(p2_block.get("indent", False))

    def test_09_versus_separator_centered(self):
        """9. Verify 'વિરુદ્ધ' / 'VERSUS' separator is centered."""
        rendered = "વિરુદ્ધ"
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks[0]["align"], "center")

        rendered_en = "VERSUS"
        blocks_en = doc_generator.build_blocks(rendered_en, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks_en[0]["align"], "center")

    def test_10_subject_center_bold_underlined(self):
        """10. Verify Subject is center aligned, bold, and underlined."""
        rendered = "બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત..."
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks[0]["align"], "center")
        self.assertTrue(blocks[0]["bold"])
        self.assertTrue(blocks[0].get("underline"))

    def test_11_subject_text_verbatim(self):
        """11. Verify exact verbatim subject line."""
        self.assertIn("બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત...", self.tpl["content_gu"])
        self.assertIn("Subject :- Regarding reopening of the right to make arguments...", self.tpl["content_en"])

    async def test_12_paragraph_1_verbatim(self):
        """12. Verify verbatim legal text for Paragraph 1."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "ફરીયાદી",
            "argument_failure_reason": "અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertIn("સદર કામે અમો ફરીયાદી ના એડવોકેટ ની આપ નામદાર કોર્ટ ને નમ્ર અરજ છે કે,", rendered_gu)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("In the present matter, we, the Advocate for Complainant, respectfully submit before this Hon'ble Court that,", rendered_en)

    async def test_13_paragraph_2_verbatim(self):
        """13. Verify verbatim legal text for Paragraph 2, preserving exact source wording."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "ફરીયાદી",
            "argument_failure_reason": "અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertIn("સદર કામ આજ રોજ દલીલ ઉપર મુકરર થયેલ હોય પરંતુ અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય", rendered_gu)
        self.assertIn("જમા ે અમોનો દલીલો કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે.", rendered_gu)
        self.assertIn("જેથી ન્યાય ના હિત માં અમોને દલીલો કરવા નો હક ફરીથી ખોલી આપવા મહેરબાની કરશો જી.", rendered_gu)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("The present matter has been fixed today for arguments, however,", rendered_en)
        self.assertIn("due to which our right to make arguments has been closed by this Hon'ble Court.", rendered_en)
        self.assertIn("Therefore, in the interest of justice, this Hon'ble Court may be pleased to reopen our right to make arguments.", rendered_en)

    def test_14_paragraph_indent_and_justified(self):
        """14. Verify paragraphs are justified with 1-tab first line indent."""
        rendered = """સદર કામે અમો ફરીયાદી ના એડવોકેટ ની આપ નામદાર કોર્ટ ને નમ્ર અરજ છે કે,

સદર કામ આજ રોજ દલીલ ઉપર મુકરર થયેલ હોય પરંતુ..."""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        non_spacers = [b for b in blocks if b.get("section") != "spacer"]
        self.assertEqual(non_spacers[0]["align"], "justify")
        self.assertTrue(non_spacers[0].get("indent"))
        self.assertEqual(non_spacers[1]["align"], "justify")
        self.assertTrue(non_spacers[1].get("indent"))

    def test_15_reason_dropdown_has_7_options(self):
        """15. Verify argument_failure_reason dropdown has exactly 7 canonical options."""
        reason_field = next(f for f in self.tpl["fields"] if f["key"] == "argument_failure_reason")
        opts = reason_field.get("options", [])
        self.assertEqual(len(opts), 7)
        vals = [o["value"] for o in opts]
        expected_opts = [
            "અમો વકીલશ્રી અન્ય કોર્ટના રોકાણના કારણે હાજર રહી શકેલ ન હોય",
            "અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય",
            "અમો વકીલશ્રી અંગત કામ સબબ બહારગામ ગયેલ હોય",
            "અમો પક્ષકાર બીમારીના કારણે હાજર રહી શકેલ ન હોય",
            "અમો પક્ષકાર અંગત કામ સબબ બહારગામ ગયેલ હોય",
            "અમો પક્ષકાર અન્ય કોર્ટના રોકાણના કારણે હાજર રહી શકેલ ન હોય",
            "અન્ય",
        ]
        self.assertEqual(vals, expected_opts)

    async def test_16_reason_selection_renders_correctly(self):
        """16. Verify standard reason selection renders properly in document."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અમો વકીલશ્રી અંગત કામ સબબ બહારગામ ગયેલ હોય",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("પરંતુ અમો વકીલશ્રી અંગત કામ સબબ બહારગામ ગયેલ હોય, જમા ે અમોનો દલીલો કરવાનો હક", rendered)

    async def test_17_reason_other_with_custom_text(self):
        """17. Verify selecting 'અન્ય' with custom reason replaces placeholder properly."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અન્ય",
            "argument_failure_reason_custom": "અમો વકીલશ્રીનું ટ્રેન મોડી પડવાના કારણે પહોંચી શકાયું ન હોય",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx["argument_failure_reason"], "અમો વકીલશ્રીનું ટ્રેન મોડી પડવાના કારણે પહોંચી શકાયું ન હોય")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("પરંતુ અમો વકીલશ્રીનું ટ્રેન મોડી પડવાના કારણે પહોંચી શકાયું ન હોય, જમા ે", rendered)
        self.assertNotIn("અન્ય,", rendered)

    async def test_18_reason_other_blank_fallback(self):
        """18. Verify selecting 'અન્ય' without custom text falls back cleanly without crashing."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અન્ય",
            "argument_failure_reason_custom": "",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx["argument_failure_reason"], "અન્ય")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("પરંતુ અન્ય, જમા ે અમોનો દલીલો કરવાનો હક", rendered)

    async def test_19_taluka_optional_in_place_default(self):
        """19. Verify taluka optional in place derivation: with taluka -> taluka, district; without taluka -> district."""
        user = {"name": "Test Advocate"}
        # With taluka
        ctx_with = await server.build_render_context(user, None, {"district": "gandhinagar", "taluka": "kalol"}, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx_with["taluka_place"], "કલોલ, ગાંધીનગર")

        # Without taluka
        ctx_without = await server.build_render_context(user, None, {"district": "gandhinagar", "taluka": ""}, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx_without["taluka_place"], "ગાંધીનગર")

    def test_20_date_and_place_left_aligned(self):
        """20. Verify Date and Place blocks are left-aligned."""
        rendered = """તારીખ : 25/09/2026
મુકામ :- ગાંધીનગર"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        date_b = next(b for b in blocks if "તારીખ" in b["text"])
        self.assertEqual(date_b["align"], "left")

    def test_21_signature_dashes_count(self):
        """21. Verify signature dashes: exactly 10 dashes GU, 20 dashes EN."""
        rendered_gu = """તારીખ : 25/09/2026
મુકામ :- ગાંધીનગર

----------
ફરીયાદી ના એડવોકેટ"""
        blocks_gu = doc_generator.build_blocks(rendered_gu, align_rules=self.tpl["settings"].get("block_align"))
        dash_b_gu = next(b for b in blocks_gu if "-" in b["text"] and not "મુકામ" in b["text"])
        self.assertEqual(dash_b_gu["text"], "----------")
        self.assertEqual(len(dash_b_gu["text"]), 10)
        self.assertEqual(dash_b_gu["align"], "right")

        rendered_en = """Date: 25/09/2026
Place: Gandhinagar

--------------------
Advocate for Complainant"""
        blocks_en = doc_generator.build_blocks(rendered_en, align_rules=self.tpl["settings"].get("block_align"))
        dash_b_en = next(b for b in blocks_en if "-" in b["text"])
        self.assertEqual(dash_b_en["text"], "--------------------")
        self.assertEqual(len(dash_b_en["text"]), 20)
        self.assertEqual(dash_b_en["align"], "right")

    async def test_22_advocate_name_auto_derives_from_advocate_for(self):
        """22. Verify advocate designation auto-derives from advocate_for."""
        user = {"name": "Test Advocate", "advocate_name_gu": "પરીક્ષણ એડવોકેટ", "advocate_name_en": "Test Advocate"}
        role_pairs = [
            ("ફરીયાદી", "ફરીયાદી ના એડવોકેટ"),
            ("આરોપી", "આરોપી ના એડવોકેટ"),
            ("અરજદાર", "અરજદાર ના એડવોકેટ"),
            ("સામાવાળા", "સામાવાળા ના એડવોકેટ"),
            ("વાદી", "વાદી ના એડવોકેટ"),
            ("પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ"),
        ]
        for role, expected_desig in role_pairs:
            ctx = await server.build_render_context(user, None, {"advocate_for": role}, "gu", template_id="reopen_right_to_argue_application")
            self.assertEqual(ctx["advocate_name"], expected_desig, f"advocate_for={role} must derive {expected_desig}")

        # English
        role_pairs_en = [
            ("complainant", "Advocate for Complainant"),
            ("accused", "Advocate for Accused"),
            ("applicant", "Advocate for Applicant"),
            ("opponent", "Advocate for Opponent"),
            ("plaintiff", "Advocate for Plaintiff"),
            ("defendant", "Advocate for Defendant"),
        ]
        for role, expected_desig in role_pairs_en:
            ctx = await server.build_render_context(user, None, {"advocate_for": role}, "en", template_id="reopen_right_to_argue_application")
            self.assertEqual(ctx["advocate_name"], expected_desig, f"advocate_for={role} must derive {expected_desig}")

        # Empty/unselected
        ctx_empty = await server.build_render_context(user, None, {"advocate_for": ""}, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx_empty["advocate_name"], "")

    def test_23_margins_a4_4cm_lr_2cm_tb(self):
        """23. Verify margins are A4, 4cm L/R, 2cm T/B."""
        s = self.tpl["settings"]
        self.assertEqual(s["page_size"], "A4")
        self.assertEqual(s["margin_left_cm"], 4.0)
        self.assertEqual(s["margin_right_cm"], 4.0)
        self.assertEqual(s["margin_top_cm"], 2.0)
        self.assertEqual(s["margin_bottom_cm"], 2.0)

    def test_24_fonts_lohit_gujarati_and_times_new_roman(self):
        """24. Verify fonts: Lohit Gujarati / Times-Roman."""
        s = self.tpl["settings"]
        self.assertEqual(s["gujarati_font"], "LohitGujarati")
        self.assertEqual(s["english_font"], "Times-Roman")

    async def test_25_blank_fields_non_blocking_preview(self):
        """25. Verify all blank fields allow preview without validation errors."""
        server.validate_template_requirements(self.tpl, {}, "gu")
        server.validate_template_requirements(self.tpl, {}, "en")
        user = {"name": ""}
        ctx_gu = await server.build_render_context(user, None, {}, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertTrue(len(rendered_gu) > 50)

    async def test_26_blank_fields_no_ugly_placeholders(self):
        """26. Verify blank fields never leak 'undefined', 'null', 'None', 'N/A', or {{field}}."""
        user = {"name": ""}
        ctx_gu = await server.build_render_context(user, None, {}, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertNotIn("None", rendered_gu)
        self.assertNotIn("null", rendered_gu)
        self.assertNotIn("undefined", rendered_gu)
        self.assertNotIn("N/A", rendered_gu)
        self.assertNotIn("[object Object]", rendered_gu)
        self.assertNotIn("{{", rendered_gu)
        self.assertNotIn("}}", rendered_gu)

        ctx_en = await server.build_render_context(user, None, {}, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertNotIn("None", rendered_en)
        self.assertNotIn("null", rendered_en)
        self.assertNotIn("undefined", rendered_en)
        self.assertNotIn("N/A", rendered_en)
        self.assertNotIn("[object Object]", rendered_en)
        self.assertNotIn("{{", rendered_en)
        self.assertNotIn("}}", rendered_en)

    async def test_27_pdf_generation_valid(self):
        """27. Verify PDF generation produces non-empty bytes for both Gujarati and English."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "101/2024",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "argument_failure_reason": "અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય",
            "date": "2026-09-25",
            "place": "કલોલ, ગાંધીનગર",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        blocks_gu = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_gu"], ctx_gu), align_rules=self.tpl["settings"].get("block_align"))
        pdf_gu = doc_generator.generate_pdf(blocks_gu, "gu", self.tpl["settings"])
        self.assertTrue(len(pdf_gu) > 100)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        blocks_en = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_en"], ctx_en), align_rules=self.tpl["settings"].get("block_align"))
        pdf_en = doc_generator.generate_pdf(blocks_en, "en", self.tpl["settings"])
        self.assertTrue(len(pdf_en) > 100)

    async def test_28_docx_and_odt_generation_valid(self):
        """28. Verify DOCX and ODT export work without error."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "વાદી",
            "party_1_name": "રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અમો વકીલશ્રી અંગત કામ સબબ બહારગામ ગયેલ હોય",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        blocks = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_gu"], ctx), align_rules=self.tpl["settings"].get("block_align"))

        doc_cls = getattr(doc_generator, "Document", None)
        if doc_cls is not None and not isinstance(doc_cls, MagicMock):
            docx_b64 = doc_generator.generate_docx(blocks, "gu", self.tpl["settings"])
            self.assertTrue(len(docx_b64) > 100)

        odt_b64 = doc_generator.generate_odt(blocks, "gu", self.tpl["settings"])
        self.assertTrue(len(odt_b64) > 100)

    async def test_29_saved_case_mode_unmodified(self):
        """29. Verify Saved Case record is not modified when rendering application."""
        user = {"name": "Test Advocate"}
        orig_case = {
            "id": "case_999",
            "court_name": "chief_judicial_magistrate",
            "case_number": "555/2024",
            "district": "gandhinagar",
            "party_name": "Test Complainant",
            "opposite_party": "Test Accused",
            "party_role": "ફરીયાદી",
            "opposite_party_role": "આરોપી",
        }
        case_copy = dict(orig_case)
        vals = {"argument_failure_reason": "અમો વકીલશ્રી બીમારીના કારણે હાજર રહી શકેલ ન હોય", "advocate_for": "ફરીયાદી"}
        ctx = await server.build_render_context(user, case_copy, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(orig_case, case_copy, "Original Saved Case dict must remain completely untouched")

    def test_30_zero_regression_other_templates(self):
        """30. Verify other existing templates remain untouched and valid."""
        other_ids = ["closing_argument_right_application", "closing_purshish", "certified_copy_application"]
        for tid in other_ids:
            tpl = next((t for t in TEMPLATES if t.get("id") == tid), None)
            self.assertIsNotNone(tpl, f"Template {tid} must exist in TEMPLATES")
            self.assertTrue(len(tpl.get("fields", [])) > 0, f"Template {tid} must have fields")


if __name__ == "__main__":
    unittest.main()
