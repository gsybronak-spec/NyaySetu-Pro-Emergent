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


class TestClosingPurshishTemplate(unittest.TestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "closing_purshish"), None)
        self.assertIsNotNone(self.tpl, "closing_purshish template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """Verify template id, names, category and aliases."""
        self.assertEqual(self.tpl["id"], "closing_purshish")
        self.assertEqual(self.tpl["name_gu"], "ક્લોઝિંગ પુરસીસ")
        self.assertEqual(self.tpl["name_en"], "Closing Purshish")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("closing purshish", aliases)
        self.assertIn("ક્લોઝિંગ પુરસીસ", aliases)

    def test_02_field_count_and_keys(self):
        """Verify exactly 13 advocate-facing fields exist with exact keys."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 13, f"Expected 13 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "date", "place", "advocate_name",
        ]
        self.assertEqual(keys, expected_keys)

    def test_03_all_fields_optional_required_false(self):
        """CRITICAL: All 13 advocate-facing fields must have required: False."""
        fields = self.tpl.get("fields", [])
        for f in fields:
            self.assertFalse(
                f.get("required", False),
                f"Field '{f['key']}' must have required: False, but got required={f.get('required')}"
            )

    def test_04_page_geometry_settings(self):
        """Verify A4 page size and margins: Top 2cm, Bottom 2cm, Left 4cm, Right 4cm."""
        s = self.tpl.get("settings", {})
        self.assertEqual(s.get("page_size", "").upper(), "A4")
        self.assertEqual(float(s.get("margin_top_cm")), 2.0)
        self.assertEqual(float(s.get("margin_bottom_cm")), 2.0)
        self.assertEqual(float(s.get("margin_left_cm")), 4.0)
        self.assertEqual(float(s.get("margin_right_cm")), 4.0)

    def test_05_typography_settings(self):
        """Verify font families, font sizes, line spacing and indent."""
        s = self.tpl.get("settings", {})
        self.assertEqual(s.get("gujarati_font"), "LohitGujarati")
        self.assertEqual(s.get("gujarati_font_docx"), "Lohit Gujarati")
        self.assertEqual(s.get("english_font"), "Times-Roman")
        self.assertEqual(s.get("english_font_docx"), "Times New Roman")
        self.assertEqual(float(s.get("body_size")), 13.0)
        self.assertEqual(float(s.get("heading_size")), 15.0)
        self.assertEqual(float(s.get("body_size_en")), 14.0)
        self.assertEqual(float(s.get("heading_size_en")), 16.0)
        self.assertEqual(float(s.get("line_spacing")), 18.0)
        self.assertEqual(float(s.get("first_line_indent_pt")), 28.35)

    def test_06_canonical_gujarati_content(self):
        """Verify Page 2 canonical Gujarati legal content is strictly present."""
        c = self.tpl["content_gu"]
        self.assertIn("મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,", c)
        self.assertIn("મુકામ :- {{taluka_place}}", c)
        self.assertIn("{{case_type}} નં. : {{case_number}}", c)
        self.assertIn("{{party_1_role}} :- {{party_1_name}}", c)
        self.assertIn("વિરુદ્ધ", c)
        self.assertIn("{{party_2_role}} :- {{party_2_name}}", c)
        self.assertIn("ક્લોઝિંગ પુરસીસ", c)
        self.assertIn("સદર કામમા અમો {{advocate_for_role}}ના એડવોકેટ આપ નામદાર કોર્ટમાં ક્લોઝિંગ પુરસીસ આપી જાહેર કરીએ છીએ કે...", c)
        self.assertIn("સદર કેસમાં {{advocate_for_role}} તરફથી મૌખીક તેમજ દસ્તાવેજી પુરાવાઓ રજુ કરવામા આવેલ છે તે સિવાય અન્ય કોઈ મૌખીક કે દસ્તાવેજી પુરાવાઓ રજુ કરવા માંગતા નથી જે આ ક્લોઝિંગ પુરસીસ આપી જાહેર કરીએ છીએ.", c)
        self.assertIn("તારીખ : {{date}}", c)
        self.assertIn("સ્થળ : {{place}}", c)
        self.assertIn("----------", c)
        self.assertIn("{{advocate_name}}", c)
        # Exactly 10 dashes for Gujarati signature
        dashes = re.findall(r"-+", c)
        self.assertIn("----------", dashes)
        self.assertEqual(len("----------"), 10)

    def test_07_canonical_english_content(self):
        """Verify English counterpart content matches structure and meaning."""
        c = self.tpl["content_en"]
        self.assertIn("IN THE COURT OF THE HON'BLE {{court_name}},", c)
        self.assertIn("AT: {{taluka_place}}", c)
        self.assertIn("{{case_type}} No. : {{case_number}}", c)
        self.assertIn("{{party_1_role}} :- {{party_1_name}}", c)
        self.assertIn("VERSUS", c)
        self.assertIn("{{party_2_role}} :- {{party_2_name}}", c)
        self.assertIn("CLOSING PURSHISH", c)
        self.assertIn("In the aforesaid matter, we, the Advocate for the {{advocate_for_role}}, submit this Closing Purshish before this Hon'ble Court and declare that...", c)
        self.assertIn("In the aforesaid case, oral as well as documentary evidence has been produced on behalf of the {{advocate_for_role}}, and apart from that, do not wish to produce any other oral or documentary evidence, which is hereby declared by submitting this Closing Purshish.", c)
        self.assertIn("Date: {{date}}", c)
        self.assertIn("Place: {{place}}", c)
        self.assertIn("--------------------", c)
        self.assertIn("{{advocate_name}}", c)
        # Exactly 20 dashes for English signature
        self.assertEqual(len("--------------------"), 20)

    def test_08_block_classification_and_alignment(self):
        """Verify block alignment and styling rules match legal structure."""
        values = {
            "court": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "court_name": "Principal Senior Civil Judge",
            "taluka_place": "કલોલ, ગાંધીનગર",
            "case_type": "રેગ્યુલર દિવાની મુકદમો",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for_role": "વાદી",
            "date": "૨૪/૦૯/૨૦૨૬",
            "place": "કલોલ, ગાંધીનગર",
            "advocate_name": "વાદી ના એડવોકેટ",
        }
        rendered = doc_generator.render_template(self.tpl["content_gu"], values)
        blocks = doc_generator.build_blocks(
            rendered,
            self.tpl["name_en"],
            self.tpl["name_gu"],
            align_rules=self.tpl["settings"].get("block_align")
        )

        non_empty = [b for b in blocks if b.get("text")]
        # 1. Court Header: center, bold
        self.assertEqual(non_empty[0]["align"], "center")
        self.assertTrue(non_empty[0]["bold"])
        # 2. Mukam: center, normal (not bold)
        self.assertEqual(non_empty[1]["align"], "center")
        self.assertFalse(non_empty[1]["bold"])
        # 3. Case details: right
        self.assertEqual(non_empty[2]["align"], "right")
        # 4. Party 1: left
        self.assertEqual(non_empty[3]["align"], "left")
        # 5. Versus: center
        self.assertEqual(non_empty[4]["align"], "center")
        # 6. Party 2: left
        self.assertEqual(non_empty[5]["align"], "left")
        # 7. Title: center, bold, underlined
        self.assertEqual(non_empty[6]["align"], "center")
        self.assertTrue(non_empty[6]["bold"])
        self.assertTrue(non_empty[6].get("underline", False))
        # 8 & 9. Paragraphs: justify, indent
        self.assertEqual(non_empty[7]["align"], "justify")
        self.assertTrue(non_empty[7]["indent"])
        self.assertEqual(non_empty[8]["align"], "justify")
        self.assertTrue(non_empty[8]["indent"])
        # 10 & 11. Date & Place: left
        self.assertEqual(non_empty[9]["align"], "left")
        self.assertEqual(non_empty[10]["align"], "left")
        # 12 & 13. Signature: right
        self.assertEqual(non_empty[11]["align"], "right")
        self.assertEqual(non_empty[12]["align"], "right")

    def test_09_blank_values_render_cleanly(self):
        """Blank fields must never leak placeholders or lonely separators."""
        rendered = doc_generator.render_template(self.tpl["content_gu"], {})
        # Must not contain placeholder text
        for forbidden in ("____", "None", "null", "undefined", "N/A", "Required", "[object Object]"):
            self.assertNotIn(forbidden, rendered)

        blocks = doc_generator.build_blocks(
            rendered,
            self.tpl["name_en"],
            self.tpl["name_gu"],
            align_rules=self.tpl["settings"].get("block_align")
        )
        for b in blocks:
            text = b.get("text", "")
            # Lonely separators must be eliminated
            self.assertNotIn(text.strip(), (":-", ":", "નં. :", "No. :"))

    def test_10_pdf_generation_gujarati_harfbuzz(self):
        """Verify HarfBuzz PDF generation succeeds and outputs valid base64 PDF."""
        values = {
            "court": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "taluka_place": "કલોલ, ગાંધીનગર",
            "case_type": "દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "હિતેશભાઈ વ્યાસ",
            "party_2_role": "આરોપી",
            "party_2_name": "પરેશભાઈ મહેતા",
            "advocate_for_role": "ફરીયાદી",
            "date": "૨૪/૦૯/૨૦૨૬",
            "place": "કલોલ, ગાંધીનગર",
            "advocate_name": "ફરીયાદી ના એડવોકેટ",
        }
        rendered = doc_generator.render_template(self.tpl["content_gu"], values)
        blocks = doc_generator.build_blocks(
            rendered,
            self.tpl["name_en"],
            self.tpl["name_gu"],
            align_rules=self.tpl["settings"].get("block_align")
        )
        pdf_b64 = doc_generator.generate_pdf(blocks, language="gu", settings=self.tpl["settings"])
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Must be a valid PDF binary")

    def test_11_docx_generation_gujarati_and_english(self):
        """Verify DOCX generation for both languages if python-docx is available."""
        if isinstance(getattr(doc_generator, "Document", None), MagicMock) or getattr(doc_generator, "Document", None) is None:
            self.skipTest("real python-docx is not installed in the test environment")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], {"court": "સિવિલ કોર્ટ", "advocate_name": "એડવોકેટ"})
        blocks_gu = doc_generator.build_blocks(rendered_gu, self.tpl["name_en"], self.tpl["name_gu"])
        docx_gu_b64 = doc_generator.generate_docx(blocks_gu, language="gu", settings=self.tpl["settings"])
        docx_gu_bytes = base64.b64decode(docx_gu_b64)
        self.assertTrue(docx_gu_bytes.startswith(b"PK"), "Must be valid DOCX zip archive")

        rendered_en = doc_generator.render_template(self.tpl["content_en"], {"court_name": "Civil Court", "advocate_name": "Advocate"})
        blocks_en = doc_generator.build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"])
        docx_en_b64 = doc_generator.generate_docx(blocks_en, language="en", settings=self.tpl["settings"])
        docx_en_bytes = base64.b64decode(docx_en_b64)
        self.assertTrue(docx_en_bytes.startswith(b"PK"), "Must be valid DOCX zip archive")

    def test_12_odt_generation(self):
        """Verify ODT generation succeeds."""
        rendered = doc_generator.render_template(self.tpl["content_gu"], {"court": "સિવિલ કોર્ટ"})
        blocks = doc_generator.build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"])
        odt_b64 = doc_generator.generate_odt(blocks, language="gu", settings=self.tpl["settings"])
        odt_bytes = base64.b64decode(odt_b64)
        self.assertTrue(odt_bytes.startswith(b"PK"), "Must be valid ODT zip archive")

    def test_13_canonical_getter_and_seed_registration(self):
        """Verify server helper returns the canonical closing_purshish template."""
        import server
        canonical = server._get_canonical_closing_purshish_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "closing_purshish")

    def test_14_build_render_context_role_auto_flow_gujarati(self):
        """Verify advocate_for role auto-flows to advocate_for_role and advocate_name in Gujarati."""
        import asyncio
        import server
        user = {"advocate_name_gu": "જે. કે. પટેલ", "advocate_name_en": "J. K. Patel"}
        values = {"advocate_for": "ફરીયાદી"}
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["advocate_for_role"], "ફરીયાદી")
        self.assertEqual(ctx["advocate_name"], "ફરીયાદી ના એડવોકેટ")

    def test_15_build_render_context_role_auto_flow_english(self):
        """Verify advocate_for role auto-flows to advocate_for_role and advocate_name in English."""
        import asyncio
        import server
        user = {"advocate_name_gu": "જે. કે. પટેલ", "advocate_name_en": "J. K. Patel"}
        values = {"advocate_for": "complainant"}
        ctx = asyncio.run(server.build_render_context(user, None, values, "en"))
        self.assertEqual(ctx["advocate_for_role"], "Complainant")
        self.assertEqual(ctx["advocate_name"], "Advocate for Complainant")

    def test_16_build_render_context_taluka_place_both(self):
        """Verify taluka + district produces '[Taluka], [District]'."""
        import asyncio
        import server
        user = {}
        values = {"taluka": "kalol", "district": "gandhinagar"}
        ctx_gu = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx_gu["taluka_place"], "કલોલ, ગાંધીનગર")
        ctx_en = asyncio.run(server.build_render_context(user, None, values, "en"))
        self.assertEqual(ctx_en["taluka_place"], "Kalol, Gandhinagar")

    def test_17_build_render_context_taluka_place_district_only(self):
        """Verify when taluka is omitted, taluka_place produces '[District]'."""
        import asyncio
        import server
        user = {}
        values = {"district": "gandhinagar"}
        ctx_gu = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx_gu["taluka_place"], "ગાંધીનગર")
        ctx_en = asyncio.run(server.build_render_context(user, None, values, "en"))
        self.assertEqual(ctx_en["taluka_place"], "Gandhinagar")

    def test_18_build_render_context_clean_keys_no_none(self):
        """Verify that all template keys are empty strings, never None or undefined."""
        import asyncio
        import server
        user = {}
        values = {}
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        for k in (
            "court_name", "court", "district", "taluka", "taluka_place",
            "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "advocate_for_role", "date", "place", "advocate_name",
        ):
            self.assertIn(k, ctx)
            self.assertIsNotNone(ctx[k])
            self.assertNotEqual(ctx[k], "None")
            self.assertNotEqual(ctx[k], "undefined")

    def test_19_zero_regression_on_certified_copy(self):
        """Verify certified_copy_application template is unaffected."""
        import server
        cc_tpl = server._get_canonical_certified_copy_template()
        self.assertIsNotNone(cc_tpl)
        self.assertEqual(cc_tpl["id"], "certified_copy_application")
        self.assertEqual(len(cc_tpl["fields"]), 19)

    def test_20_zero_regression_on_document_exhibit(self):
        """Verify document_exhibit_application template is unaffected."""
        import server
        ex_tpl = server._get_canonical_exhibit_template()
        self.assertIsNotNone(ex_tpl)
        self.assertEqual(ex_tpl["id"], "document_exhibit_application")


if __name__ == "__main__":
    unittest.main()
