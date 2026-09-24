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


class TestClosingArgumentRightApplicationTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "closing_argument_right_application"), None)
        self.assertIsNotNone(self.tpl, "closing_argument_right_application template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """Verify template id, names, category and aliases."""
        self.assertEqual(self.tpl["id"], "closing_argument_right_application")
        self.assertEqual(self.tpl["name_gu"], "દલીલોનો હક બંધ કરાવવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Closing the Right to Make Arguments")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("closing argument right application", aliases)
        self.assertIn("દલીલોનો હક બંધ કરાવવાની અરજી", aliases)
        self.assertIn("દલીલોનો હક બંધ કરવા બાબત", aliases)

    def test_02_field_count_and_keys(self):
        """Verify exactly 15 advocate-facing fields exist with exact keys and order."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 15, f"Expected 15 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "closed_party", "duration_status",
            "date", "place", "advocate_name",
        ]
        self.assertEqual(keys, expected_keys)

    def test_03_field_types(self):
        """Verify types of all 15 fields."""
        type_map = {f["key"]: f.get("type") for f in self.tpl.get("fields", [])}
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
            "closed_party": "select",
            "duration_status": "radio",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for k, expected_type in expected_types.items():
            self.assertEqual(type_map.get(k), expected_type, f"Field {k} should have type {expected_type}")

    def test_04_all_advocate_fields_optional(self):
        """Verify ALL 15 advocate-facing fields have required: False."""
        for f in self.tpl.get("fields", []):
            self.assertFalse(f.get("required"), f"Field {f['key']} must have required: False")

    def test_05_role_options(self):
        """Verify party role options match requirements."""
        f_p1 = next(f for f in self.tpl["fields"] if f["key"] == "party_1_role")
        p1_vals = [o["value"] for o in f_p1["options"]]
        self.assertEqual(p1_vals, ["ફરીયાદી", "અરજદાર", "વાદી"])

        f_p2 = next(f for f in self.tpl["fields"] if f["key"] == "party_2_role")
        p2_vals = [o["value"] for o in f_p2["options"]]
        self.assertEqual(p2_vals, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

        f_dur = next(f for f in self.tpl["fields"] if f["key"] == "duration_status")
        dur_vals = [o["value"] for o in f_dur["options"]]
        self.assertEqual(dur_vals, ["ઘણી મુદ્દતથી", "આજ દિન સુધી"])

    async def test_06_advocate_for_dynamic_role_resolution(self):
        """Verify Advocate For dynamically sets advocate_for_role and advocate designation."""
        user = {"name": "Test Advocate", "advocate_name_gu": "પરીક્ષણ એડવોકેટ", "advocate_name_en": "Test Advocate"}
        vals_gu = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "ફરીયાદી",
        }
        ctx_gu = await server.build_render_context(user, None, vals_gu, "gu", template_id="closing_argument_right_application")
        self.assertEqual(ctx_gu["advocate_for_role"], "ફરીયાદી")
        self.assertIn("ફરીયાદી ના એડવોકેટ", ctx_gu["advocate_name"])

        # English
        vals_en = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "complainant",
            "party_2_role": "accused",
            "advocate_for": "complainant",
        }
        ctx_en = await server.build_render_context(user, None, vals_en, "en", template_id="closing_argument_right_application")
        self.assertEqual(ctx_en["advocate_for_role"], "Complainant")
        self.assertIn("Advocate for Complainant", ctx_en["advocate_name"])

    async def test_07_closed_party_dynamic_role_resolution(self):
        """Verify closed_party dynamically maps to closed_party_role in both languages."""
        user = {"name": "Test Advocate"}
        # Gujarati
        vals_gu = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "closed_party": "પ્રતિવાદી",
        }
        ctx_gu = await server.build_render_context(user, None, vals_gu, "gu", template_id="closing_argument_right_application")
        self.assertEqual(ctx_gu["closed_party_role"], "પ્રતિવાદી")

        # English
        vals_en = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "plaintiff",
            "party_2_role": "defendant",
            "advocate_for": "plaintiff",
            "closed_party": "defendant",
        }
        ctx_en = await server.build_render_context(user, None, vals_en, "en", template_id="closing_argument_right_application")
        self.assertEqual(ctx_en["closed_party_role"], "Defendant")

    async def test_08_paragraph_1_and_2_substitutions(self):
        """Verify verbatim paragraph role substitutions in rendered text."""
        user = {"name": "Test Advocate"}
        vals = {
            "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "court_name": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "101/2024",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "closed_party": "આરોપી",
            "date": "2026-09-24",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="closing_argument_right_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        # Paragraph 1
        expected_p1 = "સદર કામમાં અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે....."
        self.assertIn(expected_p1, rendered)

        # Paragraph 2
        self.assertIn("સદર કેસમાં આરોપી પોતે જાતે કે તેમના વકીલશ્રી આજરોજ આપ નામદાર કોર્ટમા હાજર ન હોઈ", rendered)
        self.assertIn("જેથી આરોપી નો દલીલો કરવાનો હક બંધ કરી આગળની ન્યાયિક કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)

        # English
        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="closing_argument_right_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("In the present matter, we, the Advocate for Complainant, respectfully submit before this Hon'ble Court that...", rendered_en)
        self.assertIn("in the said case, Accused personally or their advocate is not present before this Hon'ble Court today", rendered_en)
        self.assertIn("therefore this Hon'ble Court may be pleased to close the right of Accused to make arguments", rendered_en)

    def test_09_party_alignment_indent_zero(self):
        """Verify Party 1 and Party 2 have identical left alignment and zero paragraph indent."""
        rendered = """મહેરબાન ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,
મુકામ :- ગાંધીનગર

ક્રિમિનલ કેસ નં. : ૧૦૧/૨૦૨૪

ફરીયાદી :- રમેશભાઈ પટેલ
વિરુદ્ધ
આરોપી :- સુરેશભાઈ શાહ

બાબત :- દલીલોનો હક બંધ કરવા બાબત...

સદર કામમાં અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....
"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        p1_block = next((b for b in blocks if "ફરીયાદી :-" in b["text"]), None)
        p2_block = next((b for b in blocks if "આરોપી :-" in b["text"]), None)
        vs_block = next((b for b in blocks if b["text"] == "વિરુદ્ધ"), None)

        self.assertIsNotNone(p1_block)
        self.assertIsNotNone(p2_block)
        self.assertIsNotNone(vs_block)

        self.assertEqual(p1_block["align"], "left")
        self.assertEqual(p2_block["align"], "left")
        self.assertFalse(p1_block["indent"], "Party 1 must have indent == False")
        self.assertFalse(p2_block["indent"], "Party 2 must have indent == False")
        self.assertEqual(vs_block["align"], "center")

    def test_10_subject_formatting(self):
        """Verify Subject is center aligned, bold, and underlined."""
        rendered = """બાબત :- દલીલોનો હક બંધ કરવા બાબત..."""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        subj_block = blocks[0]
        self.assertEqual(subj_block["align"], "center")
        self.assertTrue(subj_block["bold"])
        self.assertTrue(subj_block.get("underline"))

    def test_11_court_and_mukam_heading_formatting(self):
        """Verify Court Name and Mukam are centered and bold."""
        rendered = """મહેરબાન ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,
મુકામ :- ગાંધીનગર"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        court_b = blocks[0]
        mukam_b = blocks[1]
        self.assertEqual(court_b["align"], "center")
        self.assertTrue(court_b["bold"])
        self.assertEqual(mukam_b["align"], "center")
        self.assertTrue(mukam_b["bold"])

    def test_12_typography_and_margins_settings(self):
        """Verify exact typography, font sizes, and margins."""
        s = self.tpl["settings"]
        self.assertEqual(s["page_size"], "A4")
        self.assertEqual(s["margin_left_cm"], 4.0)
        self.assertEqual(s["margin_right_cm"], 4.0)
        self.assertEqual(s["margin_top_cm"], 2.0)
        self.assertEqual(s["margin_bottom_cm"], 2.0)
        self.assertEqual(s["gujarati_font"], "LohitGujarati")
        self.assertEqual(s["english_font"], "Times-Roman")
        self.assertEqual(s["body_size"], 13)
        self.assertEqual(s["heading_size"], 15)
        self.assertEqual(s["body_size_en"], 14)
        self.assertEqual(s["heading_size_en"], 16)

    def test_13_signature_dashes(self):
        """Verify signature line has exactly 10 dashes in Gujarati and 20 dashes in English."""
        # Gujarati doc
        rendered_gu = "તારીખ : 24/09/2026\nસ્થળ : ગાંધીનગર\n\n----------\nફરીયાદી ના એડવોકેટ"
        blocks_gu = doc_generator.build_blocks(rendered_gu)
        dash_b_gu = next(b for b in blocks_gu if "-" in b["text"])
        self.assertEqual(dash_b_gu["text"], "----------")
        self.assertEqual(len(dash_b_gu["text"]), 10)
        self.assertEqual(dash_b_gu["align"], "right")

        # English doc
        rendered_en = "Date: 24/09/2026\nPlace: Gandhinagar\n\n--------------------\nAdvocate for Complainant"
        blocks_en = doc_generator.build_blocks(rendered_en)
        dash_b_en = next(b for b in blocks_en if "-" in b["text"])
        self.assertEqual(dash_b_en["text"], "--------------------")
        self.assertEqual(len(dash_b_en["text"]), 20)
        self.assertEqual(dash_b_en["align"], "right")

    async def test_14_blank_fields_no_block_and_no_leakage(self):
        """Verify blank optional fields do not block and do not leak broken tags."""
        server.validate_template_requirements(self.tpl, {}, "gu")
        server.validate_template_requirements(self.tpl, {}, "en")

        user = {"name": ""}
        ctx_gu = await server.build_render_context(user, None, {}, "gu", template_id="closing_argument_right_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)

        self.assertNotIn("None", rendered_gu)
        self.assertNotIn("null", rendered_gu)
        self.assertNotIn("undefined", rendered_gu)
        self.assertNotIn("{{", rendered_gu)
        self.assertNotIn("}}", rendered_gu)

        ctx_en = await server.build_render_context(user, None, {}, "en", template_id="closing_argument_right_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertNotIn("None", rendered_en)
        self.assertNotIn("null", rendered_en)
        self.assertNotIn("undefined", rendered_en)
        self.assertNotIn("{{", rendered_en)
        self.assertNotIn("}}", rendered_en)

    async def test_15_taluka_place_logic(self):
        """Verify Taluka auto-resolves to 'Taluka, District' when present, or District only when blank."""
        user = {"name": "Test Advocate"}
        # Both taluka and district
        ctx1 = await server.build_render_context(user, None, {"district": "gandhinagar", "taluka": "kalol"}, "gu", template_id="closing_argument_right_application")
        self.assertEqual(ctx1["taluka_place"], "કલોલ, ગાંધીનગર")

        # District only
        ctx2 = await server.build_render_context(user, None, {"district": "gandhinagar", "taluka": ""}, "gu", template_id="closing_argument_right_application")
        self.assertEqual(ctx2["taluka_place"], "ગાંધીનગર")

    async def test_16_saved_case_immutability(self):
        """Verify generating application from Saved Case does not mutate original Saved Case."""
        user = {"name": "Test Advocate"}
        orig_case = {
            "id": "case_123",
            "court_name": "principal_senior_civil_judge",
            "case_number": "999/2024",
            "district": "ahmedabad",
            "party_name": "Test Plaintiff",
            "opposite_party": "Test Defendant",
            "party_role": "વાદી",
            "opposite_party_role": "પ્રતિવાદી",
        }
        case_copy = dict(orig_case)
        vals = {"case_number": "999/2024", "advocate_for": "વાદી", "closed_party": "પ્રતિવાદી"}
        ctx = await server.build_render_context(user, case_copy, vals, "gu", template_id="closing_argument_right_application")
        self.assertEqual(orig_case, case_copy, "Saved case dictionary must not be mutated!")

    async def test_17_multi_format_generation(self):
        """Verify Gujarati PDF, English PDF, DOCX, and ODT generation work without error."""
        user = {"name": "Test Advocate"}
        vals = {
            "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
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
            "closed_party": "આરોપી",
            "date": "2026-09-24",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="closing_argument_right_application")
        blocks_gu = doc_generator.build_blocks(
            doc_generator.render_template(self.tpl["content_gu"], ctx_gu),
            align_rules=self.tpl["settings"].get("block_align")
        )

        # PDF Gujarati
        pdf_gu = doc_generator.generate_pdf(blocks_gu, "gu", self.tpl["settings"])
        self.assertTrue(len(pdf_gu) > 100)

        # PDF English
        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="closing_argument_right_application")
        blocks_en = doc_generator.build_blocks(
            doc_generator.render_template(self.tpl["content_en"], ctx_en),
            align_rules=self.tpl["settings"].get("block_align")
        )
        pdf_en = doc_generator.generate_pdf(blocks_en, "en", self.tpl["settings"])
        self.assertTrue(len(pdf_en) > 100)

        # DOCX
        doc_cls = getattr(doc_generator, "Document", None)
        if doc_cls is not None and not isinstance(doc_cls, MagicMock):
            docx_b64 = doc_generator.generate_docx(blocks_gu, "gu", self.tpl["settings"])
            self.assertTrue(len(docx_b64) > 100)

        # ODT
        odt_b64 = doc_generator.generate_odt(blocks_gu, "gu", self.tpl["settings"])
        self.assertTrue(len(odt_b64) > 100)

    def test_18_canonical_template_getter(self):
        """Verify server canonical getter returns closing_argument_right_application."""
        canonical = server._get_canonical_closing_argument_right_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "closing_argument_right_application")


if __name__ == "__main__":
    unittest.main()
