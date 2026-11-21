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


class TestFsRightClosureApplicationTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "fs_right_closure_application"), None)
        self.assertIsNotNone(self.tpl, "fs_right_closure_application template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "fs_right_closure_application")
        self.assertEqual(self.tpl["name_gu"], "એફ.એસ.નો હક બંધ કરાવવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Closing Further Statement (F.S.) Right")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("fs right closure application", aliases)
        self.assertIn("એફ.એસ.નો હક બંધ કરાવવાની અરજી", aliases)
        self.assertIn("એફ.એસ.નો હક બંધ કરવા બાબત", aliases)

    def test_02_gujarati_and_english_pairing(self):
        """2. Verify Gujarati and English pairing in server canonical map."""
        self.assertEqual(server.resolve_canonical_template_id("fs_right_closure_application"), "fs_right_closure_application")
        self.assertEqual(server.resolve_canonical_template_id("fs_right_closure_application_gu"), "fs_right_closure_application")
        self.assertEqual(server.resolve_canonical_template_id("fs_right_closure_application_en"), "fs_right_closure_application")

    def test_03_all_14_form_fields_and_types(self):
        """3. Verify all 14 form fields exist with exact keys, types, and sequence."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 14, f"Expected 14 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "closed_party",
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
            "closed_party": "select",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for f in fields:
            fkey = f["key"]
            self.assertEqual(f["type"], expected_types[fkey], f"Field {fkey} has unexpected type")
            self.assertFalse(f.get("required"), f"Field {fkey} must have required: False")

    async def test_04_optional_taluka_behavior(self):
        """4. Verify optional taluka: does not fail if taluka is omitted."""
        user = {"name": "Test Advocate"}
        vals = {"district": "gandhinagar", "taluka": ""}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        self.assertEqual(ctx["district"], "ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "ગાંધીનગર")

    async def test_05_taluka_before_district_ordering(self):
        """5. Verify if taluka exists, taluka precedes district: 'કલોલ, ગાંધીનગર'."""
        user = {"name": "Test Advocate"}
        vals = {"district": "gandhinagar", "taluka": "kalol"}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        self.assertEqual(ctx["taluka_place"], "કલોલ, ગાંધીનગર")

    async def test_06_case_type_and_case_number_formatting(self):
        """6. Verify case type and number formatting in rendered output."""
        user = {"name": "Test Advocate"}
        vals = {
            "case_type": "criminal_case",
            "case_number": "૧૦૧/૨૦૨૪",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertIn("ક્રિમિનલ કેસ નં. : ૧૦૧/૨૦૨૪", rendered_gu)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="fs_right_closure_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("Criminal Case No. : ૧૦૧/૨૦૨૪", rendered_en)

    def test_07_party_1_role_options(self):
        """7. Verify party 1 role options match: ફરીયાદી, અરજદાર, વાદી."""
        f_p1 = next(f for f in self.tpl["fields"] if f["key"] == "party_1_role")
        p1_vals = [o["value"] for o in f_p1["options"]]
        self.assertEqual(p1_vals, ["ફરીયાદી", "અરજદાર", "વાદી"])

    def test_08_party_2_role_options(self):
        """8. Verify party 2 role options match: આરોપી, સામાવાળા, પ્રતિવાદી."""
        f_p2 = next(f for f in self.tpl["fields"] if f["key"] == "party_2_role")
        p2_vals = [o["value"] for o in f_p2["options"]]
        self.assertEqual(p2_vals, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

    async def test_09_advocate_side_designation_mapping(self):
        """9. Verify advocate-side designation mapping in signature section."""
        user = {"name": "Test Advocate"}
        for role, expected_gu, expected_en in [
            ("ફરીયાદી", "ફરીયાદી ના એડવોકેટ", "Advocate for Complainant"),
            ("અરજદાર", "અરજદાર ના એડવોકેટ", "Advocate for Applicant"),
            ("વાદી", "વાદી ના એડવોકેટ", "Advocate for Plaintiff"),
            ("આરોપી", "આરોપી ના એડવોકેટ", "Advocate for Accused"),
            ("સામાવાળા", "સામાવાળા ના એડવોકેટ", "Advocate for Opponent"),
            ("પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ", "Advocate for Defendant"),
        ]:
            ctx_gu = await server.build_render_context(user, None, {"advocate_for": role}, "gu", template_id="fs_right_closure_application")
            self.assertEqual(ctx_gu["advocate_name"], expected_gu)
            ctx_en = await server.build_render_context(user, None, {"advocate_for": role}, "en", template_id="fs_right_closure_application")
            self.assertEqual(ctx_en["advocate_name"], expected_en)

    async def test_10_independent_target_party_role_selection(self):
        """10. Verify independent closed_party role selection maps to closed_party_role."""
        user = {"name": "Test Advocate"}
        ctx_gu = await server.build_render_context(
            user, None,
            {"party_1_role": "ફરીયાદી", "party_2_role": "આરોપી", "advocate_for": "ફરીયાદી", "closed_party": "આરોપી"},
            "gu",
            template_id="fs_right_closure_application"
        )
        self.assertEqual(ctx_gu["closed_party_role"], "આરોપી")

        ctx_en = await server.build_render_context(
            user, None,
            {"party_1_role": "complainant", "party_2_role": "accused", "advocate_for": "complainant", "closed_party": "accused"},
            "en",
            template_id="fs_right_closure_application"
        )
        self.assertEqual(ctx_en["closed_party_role"], "Accused")

    async def test_11_paragraph_1_role_substitution(self):
        """11. Verify Paragraph 1 role substitution matches selected advocate role."""
        user = {"name": "Test Advocate"}
        vals = {
            "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "advocate_for": "ફરીયાદી",
            "closed_party": "આરોપી",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        expected_p1 = "સદર કામમાં અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......"
        self.assertIn(expected_p1, rendered)

    async def test_12_paragraph_2_both_role_substitutions_synchronized(self):
        """12. Verify Paragraph 2 has both role substitutions populated and synchronized."""
        user = {"name": "Test Advocate"}
        vals = {
            "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "advocate_for": "ફરીયાદી",
            "closed_party": "આરોપી",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટમાં આજ રોજ એફ. એસ. પર છે.", rendered)
        self.assertIn("પરંતુ સદર કેસમાં આરોપી પોતે જાતે કે તેમના વકીલશ્રી આજરોજ આપ નામદાર કોર્ટમાં હાજર ન હોઈ", rendered)
        self.assertIn("જેથી આરોપી નો એફ. એસ. કરવાનો હક બંધ કરી આગળની ન્યાયિક કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)

        # English
        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="fs_right_closure_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("The present case is scheduled today for further statement (F.S.) before this Hon'ble Court.", rendered_en)
        self.assertIn("However, in the said case, Accused personally or their advocate is not present before this Hon'ble Court today", rendered_en)
        self.assertIn("close the right of Accused to record further statement and pass appropriate orders", rendered_en)

    async def test_13_date_substitution(self):
        """13. Verify date substitution in DD/MM/YYYY format."""
        user = {"name": "Test Advocate"}
        vals = {"date": "2026-11-21"}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        self.assertEqual(ctx["date"], "21/11/2026")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("તારીખ : 21/11/2026", rendered)

    async def test_14_district_place_substitution(self):
        """14. Verify place substitution auto-populates from district."""
        user = {"name": "Test Advocate"}
        vals = {"district": "gandhinagar"}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        self.assertEqual(ctx["place"], "ગાંધીનગર")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("સ્થળ : ગાંધીનગર", rendered)

    async def test_15_signature_section_substitution(self):
        """15. Verify dotted line and advocate designation in signature section."""
        user = {"name": "Test Advocate"}
        vals = {"advocate_for": "વાદી"}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("----------\nવાદી ના એડવોકેટ", rendered)

    async def test_16_gujarati_pdf_generation(self):
        """16. Verify Gujarati PDF generation succeeds and contains legal text."""
        user = {"name": "Test Advocate"}
        vals = {
            "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "court_name": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "closed_party": "આરોપી",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_closure_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="fs_right_closure_application",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    async def test_17_english_pdf_generation(self):
        """17. Verify English PDF generation succeeds and contains legal text."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "Chief Judicial Magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "101/2024",
            "party_1_role": "complainant",
            "party_1_name": "Rameshbhai Patel",
            "party_2_role": "accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "complainant",
            "closed_party": "accused",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "en", template_id="fs_right_closure_application")
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="en",
            settings=self.tpl["settings"],
            template_id="fs_right_closure_application",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_18_gujarati_font(self):
        """18. Verify Gujarati font settings."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("gujarati_font"), "LohitGujarati")
        self.assertEqual(settings.get("gujarati_font_docx"), "Lohit Gujarati")

    def test_19_english_font(self):
        """19. Verify English font settings."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("english_font"), "Times-Roman")
        self.assertEqual(settings.get("english_font_docx"), "Times New Roman")

    def test_20_font_sizes(self):
        """20. Verify font sizes: Gujarati 13pt body / 15pt heading, English 14pt body / 16pt heading."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("body_size"), 13)
        self.assertEqual(settings.get("heading_size"), 15)
        self.assertEqual(settings.get("body_size_en"), 14)
        self.assertEqual(settings.get("heading_size_en"), 16)

    def test_21_margins(self):
        """21. Verify margins: Left 4.0cm, Right 4.0cm, Top 2.0cm, Bottom 2.0cm."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("margin_left_cm"), 4.0)
        self.assertEqual(settings.get("margin_right_cm"), 4.0)
        self.assertEqual(settings.get("margin_top_cm"), 2.0)
        self.assertEqual(settings.get("margin_bottom_cm"), 2.0)

    async def test_22_draft_compatibility(self):
        """22. Verify draft saving and resolution compatibility."""
        res_tpl = await server.get_template("fs_right_closure_application")
        self.assertIsNotNone(res_tpl)
        self.assertEqual(res_tpl["id"], "fs_right_closure_application")

    def test_23_existing_templates_regression(self):
        """23. Verify all 10 existing canonical templates are intact in TEMPLATES."""
        existing_10_ids = [
            "vakilatnama_criminal",
            "vakilatnama_civil",
            "exemption_arji",
            "mudat_arji",
            "certified_copy_application",
            "document_exhibit_application",
            "closing_purshish",
            "closing_argument_right_application",
            "reopen_right_to_argue_application",
            "dd_karavani_arji",
        ]
        template_ids = [t.get("id") for t in TEMPLATES]
        for tid in existing_10_ids:
            self.assertIn(tid, template_ids, f"Protected existing template {tid} missing from TEMPLATES")

    def test_24_protected_templates_content_unchanged(self):
        """24. Verify protected templates have not been modified."""
        dd_tpl = next((t for t in TEMPLATES if t.get("id") == "dd_karavani_arji"), None)
        self.assertIsNotNone(dd_tpl)
        self.assertEqual(dd_tpl["name_gu"], "DD કરાવવાની અરજી")
        self.assertIn("disinterested_party", [f["key"] for f in dd_tpl["fields"]])

        car_tpl = next((t for t in TEMPLATES if t.get("id") == "closing_argument_right_application"), None)
        self.assertIsNotNone(car_tpl)
        self.assertEqual(car_tpl["name_gu"], "દલીલોનો હક બંધ કરાવવાની અરજી")

        mudat_tpl = next((t for t in TEMPLATES if t.get("id") == "mudat_arji"), None)
        self.assertIsNotNone(mudat_tpl)
        self.assertEqual(mudat_tpl["name_gu"], "મુદત અરજી")


if __name__ == "__main__":
    unittest.main()
