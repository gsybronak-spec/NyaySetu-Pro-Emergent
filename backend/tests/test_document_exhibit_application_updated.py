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
    "docx", "docx.shared", "docx.enum.text", "docx.oxml", "docx.oxml.ns",
    "google", "google.cloud", "google.cloud.firestore",
    "fastapi", "fastapi.exceptions", "fastapi.responses",
    "fastapi.middleware.cors", "fastapi.middleware.gzip",
    "pydantic", "httpx", "dotenv", "jwt", "bcrypt", "razorpay",
    "cryptography", "cryptography.hazmat", "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.serialization", "cryptography.x509"
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

fastapi_mock = sys.modules["fastapi"]
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

sys.modules["pydantic"].BaseModel = _PydanticBaseModel
sys.modules["pydantic"].Field = lambda *args, **kwargs: None

from test_seed_data import TEMPLATES
import doc_generator
import server


class TestDocumentExhibitApplicationUpdated(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.template_id = "document_exhibit_application"
        self.template = next((t for t in TEMPLATES if t.get("id") == self.template_id), None)
        self.assertIsNotNone(self.template, f"Template {self.template_id} not found in TEMPLATES")
        self.user = {
            "id": "test_user_id",
            "name": "Advocate Test",
            "advocate_name_gu": "એડવોકેટ ટેસ્ટ",
            "advocate_name_en": "Advocate Test",
            "district": "ahmedabad",
            "court": "City Civil Court, Ahmedabad",
        }

    def test_01_template_identity_and_registration(self):
        """Verify template identity, Gujarati/English titles, category, and display order position."""
        self.assertEqual(self.template.get("id"), "document_exhibit_application")
        self.assertEqual(self.template.get("name_gu"), "દસ્તાવેજને આંક પાડવા બાબતની અરજી")
        self.assertEqual(self.template.get("name_en"), "Application for Marking Documents as Exhibits")
        self.assertEqual(self.template.get("category"), "Civil")

        # Verify display order position (#6 -> index 5)
        display_order = server._SETTING_DEFAULTS.get("template_display_order", [])
        self.assertIn("document_exhibit_application", display_order)
        self.assertEqual(display_order.index("document_exhibit_application"), 5)

    def test_02_canonical_resolution_and_aliases(self):
        """Verify resolve_canonical_template_id handles all aliases and variations."""
        expected_aliases = [
            "document_exhibit_application",
            "document_exhibit_application_gu",
            "document_exhibit_application_en",
            "document_exhibit",
            "aanke_padvani_arji",
            "aanke_padvani_arji_gu",
            "aanke_padvani_arji_en",
            "aanke",
            "exhibit",
            "aanke padva",
            "dastavejne aank padva",
            "આંક પાડવાની અરજી",
            "દસ્તાવેજને આંક પાડવા બાબતની અરજી",
            "આંક",
        ]
        for alias in expected_aliases:
            canon = server.resolve_canonical_template_id(alias)
            self.assertEqual(
                canon, "document_exhibit_application",
                f"Alias '{alias}' did not resolve to 'document_exhibit_application', got '{canon}'"
            )

        # Check aliases list in template
        tpl_aliases = self.template.get("aliases", [])
        self.assertIn("આંક પાડવાની અરજી", tpl_aliases)
        self.assertIn("aanke_padvani_arji", tpl_aliases)
        self.assertIn("દસ્તાવેજને આંક પાડવા બાબતની અરજી", tpl_aliases)

    def test_03_fields_count_and_keys_order(self):
        """Verify exactly 16 fields present in exact sequence with proper types."""
        fields = self.template.get("fields", [])
        self.assertEqual(len(fields), 16, f"Expected 16 fields, got {len(fields)}")

        expected_keys = [
            "court_name",
            "district",
            "taluka",
            "case_type",
            "case_number",
            "party_1_role",
            "party_1_name",
            "party_2_role",
            "party_2_name",
            "advocate_for",
            "aank_number",
            "document_index_from",
            "document_index_to",
            "date",
            "place",
            "advocate_name",
        ]
        actual_keys = [f["key"] for f in fields]
        self.assertEqual(actual_keys, expected_keys)

        # Detailed field assertions
        field_dict = {f["key"]: f for f in fields}

        # 1. court_name: select, required=True
        self.assertEqual(field_dict["court_name"]["type"], "select")
        self.assertTrue(field_dict["court_name"]["required"])

        # 2. district: select, required=True
        self.assertEqual(field_dict["district"]["type"], "select")
        self.assertTrue(field_dict["district"]["required"])

        # 3. taluka: select, required=False
        self.assertEqual(field_dict["taluka"]["type"], "select")
        self.assertFalse(field_dict["taluka"]["required"])

        # 4. case_type: select, required=True
        self.assertEqual(field_dict["case_type"]["type"], "select")
        self.assertTrue(field_dict["case_type"]["required"])

        # 5. case_number: text, required=True
        self.assertEqual(field_dict["case_number"]["type"], "text")
        self.assertTrue(field_dict["case_number"]["required"])

        # 6. party_1_role: radio, required=True, includes complainant, applicant, plaintiff
        self.assertEqual(field_dict["party_1_role"]["type"], "radio")
        self.assertTrue(field_dict["party_1_role"]["required"])
        p1_opts = [o["value"] for o in field_dict["party_1_role"]["options"]]
        self.assertIn("વાદી", p1_opts)
        self.assertIn("અરજદાર", p1_opts)
        self.assertIn("ફરીયાદી", p1_opts)

        # 7. party_1_name: text, required=True
        self.assertEqual(field_dict["party_1_name"]["type"], "text")
        self.assertTrue(field_dict["party_1_name"]["required"])

        # 8. party_2_role: radio, required=True, includes accused, opponent, defendant
        self.assertEqual(field_dict["party_2_role"]["type"], "radio")
        self.assertTrue(field_dict["party_2_role"]["required"])
        p2_opts = [o["value"] for o in field_dict["party_2_role"]["options"]]
        self.assertIn("આરોપી", p2_opts)
        self.assertIn("સામાવાળા", p2_opts)
        self.assertIn("પ્રતિવાદી", p2_opts)

        # 9. party_2_name: text, required=True
        self.assertEqual(field_dict["party_2_name"]["type"], "text")
        self.assertTrue(field_dict["party_2_name"]["required"])

        # 10. advocate_for: select, required=True, default="વાદી"
        self.assertEqual(field_dict["advocate_for"]["type"], "select")
        self.assertTrue(field_dict["advocate_for"]["required"])
        self.assertEqual(field_dict["advocate_for"].get("default"), "વાદી")
        adv_opts = [o["value"] for o in field_dict["advocate_for"]["options"]]
        self.assertIn("વાદી", adv_opts)
        self.assertIn("પ્રતિવાદી", adv_opts)
        self.assertIn("અરજદાર", adv_opts)
        self.assertIn("સામાવાળા", adv_opts)
        self.assertIn("ફરીયાદી", adv_opts)
        self.assertIn("આરોપી", adv_opts)

        # 11. aank_number: number, required=False
        self.assertEqual(field_dict["aank_number"]["type"], "number")
        self.assertFalse(field_dict["aank_number"]["required"])

        # 12. document_index_from: number, required=False
        self.assertEqual(field_dict["document_index_from"]["type"], "number")
        self.assertFalse(field_dict["document_index_from"]["required"])

        # 13. document_index_to: number, required=False
        self.assertEqual(field_dict["document_index_to"]["type"], "number")
        self.assertFalse(field_dict["document_index_to"]["required"])

        # 14. date: date, required=True, default="today"
        self.assertEqual(field_dict["date"]["type"], "date")
        self.assertTrue(field_dict["date"]["required"])
        self.assertEqual(field_dict["date"].get("default"), "today")

        # 15. place: text, required=False
        self.assertEqual(field_dict["place"]["type"], "text")
        self.assertFalse(field_dict["place"]["required"])

        # 16. advocate_name: text, required=False
        self.assertEqual(field_dict["advocate_name"]["type"], "text")
        self.assertFalse(field_dict["advocate_name"]["required"])

    async def test_04_build_render_context_with_aank_number(self):
        """Verify build_render_context populates place, aank_number, from/to, and advocate designation."""
        values = {
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "રેગ્યુલર સિવિલ સૂટ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "aank_number": 3,
            "document_index_from": 1,
            "document_index_to": 5,
            "date": "23/11/2026",
        }
        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="document_exhibit_application",
        )
        self.assertEqual(ctx["place"], "સાણંદ, અમદાવાદ")
        self.assertEqual(ctx["taluka_place"], "સાણંદ, અમદાવાદ")
        self.assertEqual(ctx["aank_number"], "3")
        self.assertEqual(ctx["document_index_from"], "1")
        self.assertEqual(ctx["document_index_to"], "5")
        self.assertEqual(ctx["advocate_for_role"], "વાદી")
        self.assertEqual(ctx["advocate_name"], "વાદી ના એડવોકેટ")

    async def test_05_build_render_context_blank_aank_number_fallback(self):
        """Verify empty/zero/null aank_number renders exactly 10 underscores (__________)." """
        # Case A: None
        values_none = {
            "district": "રાજકોટ",
            "advocate_for": "પ્રતિવાદી",
            "aank_number": None,
            "document_index_from": None,
            "document_index_to": None,
        }
        ctx_none = await server.build_render_context(
            user=self.user,
            case=None,
            values=values_none,
            language="gu",
            template_id="document_exhibit_application",
        )
        self.assertEqual(ctx_none["aank_number"], "__________")
        self.assertEqual(ctx_none["document_index_from"], "")
        self.assertEqual(ctx_none["document_index_to"], "")
        self.assertEqual(ctx_none["place"], "રાજકોટ")
        self.assertEqual(ctx_none["advocate_for_role"], "પ્રતિવાદી")
        self.assertEqual(ctx_none["advocate_name"], "પ્રતિવાદી ના એડવોકેટ")

        # Case B: "0" or 0
        values_zero = {"aank_number": 0, "district": "અમદાવાદ", "advocate_for": "વાદી"}
        ctx_zero = await server.build_render_context(
            user=self.user,
            case=None,
            values=values_zero,
            language="gu",
            template_id="document_exhibit_application",
        )
        self.assertEqual(ctx_zero["aank_number"], "__________")

        # Case C: empty string ""
        values_empty = {"aank_number": "", "district": "અમદાવાદ", "advocate_for": "વાદી"}
        ctx_empty = await server.build_render_context(
            user=self.user,
            case=None,
            values=values_empty,
            language="gu",
            template_id="document_exhibit_application",
        )
        self.assertEqual(ctx_empty["aank_number"], "__________")

    async def test_06_build_render_context_english_mode(self):
        """Verify English translation of roles and advocate designation."""
        values = {
            "court_name": "City Civil Court, Ahmedabad",
            "district": "Ahmedabad",
            "taluka": "City",
            "case_type": "Civil Suit",
            "case_number": "101/2024",
            "party_1_role": "Plaintiff",
            "party_1_name": "Ramesh Patel",
            "party_2_role": "Defendant",
            "party_2_name": "Haresh Shah",
            "advocate_for": "Plaintiff",
            "aank_number": 4,
            "document_index_from": 1,
            "document_index_to": 3,
            "date": "23/11/2026",
        }
        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="en",
            template_id="document_exhibit_application",
        )
        self.assertEqual(ctx["place"], "City, Ahmedabad")
        self.assertEqual(ctx["aank_number"], "4")
        self.assertEqual(ctx["document_index_from"], "1")
        self.assertEqual(ctx["document_index_to"], "3")
        self.assertEqual(ctx["advocate_for_role"], "Plaintiff")
        self.assertEqual(ctx["advocate_name"], "Advocate for Plaintiff")

    async def test_07_verbatim_gujarati_draft_content(self):
        """Verify verbatim Gujarati draft content matches Section 3 exactly."""
        values = {
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "રેગ્યુલર સિવિલ સૂટ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "aank_number": 3,
            "document_index_from": 1,
            "document_index_to": 5,
            "date": "23/11/2026",
        }
        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="document_exhibit_application",
        )
        rendered = doc_generator.render_template(self.template["content_gu"], ctx)

        # Subject verification
        self.assertIn("બાબત :- દસ્તાવેજને આંક પાડવા બાબત...", rendered)

        # Opening sentence verification
        self.assertIn("સદર કામમાં અમો વાદીના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...", rendered)

        # Main body paragraph verbatim
        expected_body = (
            "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. "
            "સદર કેસમાં અમો વાદીએ દસ્તાવેજી પુરાવા લીસ્ટથી અસલ દસ્તાવેજ / ઓનલાઈન અસલ નકલ "
            "આંક 3 ના પુરાવા લિસ્ટથી અનુક્રમ નં. 1 થી 5 રજુ કરેલ છે કે જેને જુબાનીમાં રીફર કરેલ છે "
            "અને કેસના ન્યાયિક નિર્ણય માટે જરૂરી છે. તેમજ સદર દસ્તાવેજને પુરાવા તરીકે રેકર્ડ પર લેવા "
            "ન્યાયના હિતમાં હોઈ, સદર દસ્તાવેજને રેકર્ડ પર લઈ તેને આંક આપી પુરાવામાં વંચાણે લેવા મહેરબાની કરશોજી."
        )
        self.assertIn(expected_body, rendered)

        # Signature verification: 10 dashes and advocate designation
        self.assertIn("----------", rendered)
        self.assertIn("વાદી ના એડવોકેટ", rendered)

    async def test_08_verbatim_gujarati_draft_blank_aank(self):
        """Verify draft rendering when aank_number is omitted uses 10 underscores."""
        values = {
            "court_name": "સિવિલ જજ",
            "district": "વડોદરા",
            "case_type": "સિવિલ સૂટ",
            "case_number": "૪૨/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "અ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "બ",
            "advocate_for": "વાદી",
            "date": "23/11/2026",
        }
        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="document_exhibit_application",
        )
        rendered = doc_generator.render_template(self.template["content_gu"], ctx)
        self.assertIn("આંક __________ ના પુરાવા લિસ્ટથી", rendered)

    async def test_09_block_align_and_geometry(self):
        """Verify block alignments and layout settings."""
        settings = self.template.get("settings", {})
        self.assertEqual(settings.get("page_size"), "A4")
        self.assertEqual(settings.get("margin_top_cm"), 2.0)
        self.assertEqual(settings.get("margin_bottom_cm"), 2.0)
        self.assertEqual(settings.get("margin_left_cm"), 4.0)
        self.assertEqual(settings.get("margin_right_cm"), 4.0)

        values = {
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "રેગ્યુલર સિવિલ સૂટ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "aank_number": 3,
            "document_index_from": 1,
            "document_index_to": 5,
            "date": "23/11/2026",
        }
        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="document_exhibit_application",
        )
        rendered = doc_generator.render_template(self.template["content_gu"], ctx)
        align_rules = (self.template.get("settings") or {}).get("block_align")
        blocks = doc_generator.build_blocks(rendered, align_rules=align_rules)

        # Title block
        title_block = next((b for b in blocks if "બાબત :- દસ્તાવેજને આંક પાડવા બાબત..." in b["text"]), None)
        self.assertIsNotNone(title_block, "Title block must be found")
        self.assertEqual(title_block["align"], "center")
        self.assertTrue(title_block["bold"])
        self.assertTrue(title_block["underline"])

        # Main body paragraph
        main_body = next((b for b in blocks if "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે" in b["text"]), None)
        self.assertIsNotNone(main_body, "Main body block must be found")
        self.assertEqual(main_body["align"], "justify")
        self.assertFalse(main_body["underline"], "Main body paragraph MUST NOT be underlined")
        self.assertFalse(main_body["bold"], "Main body paragraph MUST NOT be bold")
        self.assertTrue(main_body["indent"], "Main body paragraph MUST have first-line indent")

    async def test_10_pdf_generation_gujarati_and_english(self):
        """Verify PDF generation succeeds and returns valid PDF bytes for both Gujarati and English."""
        values = {
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "રેગ્યુલર સિવિલ સૂટ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "aank_number": 3,
            "document_index_from": 1,
            "document_index_to": 5,
            "date": "23/11/2026",
        }

        # Gujarati PDF
        ctx_gu = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="document_exhibit_application",
        )
        rendered_gu = doc_generator.render_template(self.template["content_gu"], ctx_gu)
        align_rules_gu = (self.template.get("settings") or {}).get("block_align")
        blocks_gu = doc_generator.build_blocks(rendered_gu, align_rules=align_rules_gu)
        pdf_b64_gu = doc_generator.generate_pdf(
            blocks_gu,
            language="gu",
            settings=self.template.get("settings"),
            template_id="document_exhibit_application",
        )
        self.assertIsInstance(pdf_b64_gu, str)
        pdf_bytes_gu = base64.b64decode(pdf_b64_gu)
        self.assertTrue(pdf_bytes_gu.startswith(b"%PDF-"), "Generated Gujarati file is not a valid PDF")
        self.assertGreater(len(pdf_bytes_gu), 500)

        # English PDF
        values_en = {
            "court_name": "Principal Senior Civil Judge",
            "district": "Ahmedabad",
            "taluka": "Sanand",
            "case_type": "Regular Civil Suit",
            "case_number": "101/2024",
            "party_1_role": "Plaintiff",
            "party_1_name": "Ramesh Patel",
            "party_2_role": "Defendant",
            "party_2_name": "Haresh Shah",
            "advocate_for": "Plaintiff",
            "aank_number": 3,
            "document_index_from": 1,
            "document_index_to": 5,
            "date": "23/11/2026",
        }
        ctx_en = await server.build_render_context(
            user=self.user,
            case=None,
            values=values_en,
            language="en",
            template_id="document_exhibit_application",
        )
        rendered_en = doc_generator.render_template(self.template["content_en"], ctx_en)
        align_rules_en = (self.template.get("settings") or {}).get("block_align")
        blocks_en = doc_generator.build_blocks(rendered_en, align_rules=align_rules_en)
        pdf_b64_en = doc_generator.generate_pdf(
            blocks_en,
            language="en",
            settings=self.template.get("settings"),
            template_id="document_exhibit_application",
        )
        self.assertIsInstance(pdf_b64_en, str)
        pdf_bytes_en = base64.b64decode(pdf_b64_en)
        self.assertTrue(pdf_bytes_en.startswith(b"%PDF-"), "Generated English file is not a valid PDF")
        self.assertGreater(len(pdf_bytes_en), 500)


if __name__ == "__main__":
    unittest.main()
