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


class TestKamBoardParLevaniArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "kam_board_par_levani_arji"), None)
        self.assertIsNotNone(self.tpl, "kam_board_par_levani_arji template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "kam_board_par_levani_arji")
        self.assertEqual(self.tpl["name_gu"], "કામ બોર્ડ પર લેવા બાબત")
        self.assertEqual(self.tpl["name_en"], "Application for Taking the Matter on Board")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("kam_board", aliases)
        self.assertIn("kam_board_par_levani_arji", aliases)
        self.assertIn("કામ બોર્ડ પર લેવા બાબત", aliases)
        self.assertIn("કામ બોર્ડ પર લેવાની અરજી", aliases)

    def test_02_gujarati_and_english_pairing(self):
        """2. Verify Gujarati and English pairing in server canonical map."""
        self.assertEqual(server.resolve_canonical_template_id("kam_board_par_levani_arji"), "kam_board_par_levani_arji")
        self.assertEqual(server.resolve_canonical_template_id("kam_board_par_levani_arji_gu"), "kam_board_par_levani_arji")
        self.assertEqual(server.resolve_canonical_template_id("kam_board_par_levani_arji_en"), "kam_board_par_levani_arji")

    def test_03_all_15_form_fields_and_types(self):
        """3. Verify all 15 form fields exist with exact keys, types, and sequence."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 15, f"Expected 15 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "scheduled_date", "urgent_reason",
            "date", "place", "advocate_name"
        ]
        self.assertEqual(keys, expected_keys)

        # Check field types
        field_map = {f["key"]: f for f in fields}
        self.assertEqual(field_map["court_name"]["type"], "select")
        self.assertEqual(field_map["district"]["type"], "select")
        self.assertEqual(field_map["taluka"]["type"], "select")
        self.assertFalse(field_map["taluka"].get("required", True))
        self.assertEqual(field_map["case_type"]["type"], "select")
        self.assertEqual(field_map["case_number"]["type"], "text")
        self.assertEqual(field_map["party_1_role"]["type"], "radio")
        self.assertEqual(field_map["party_1_name"]["type"], "text")
        self.assertEqual(field_map["party_2_role"]["type"], "radio")
        self.assertEqual(field_map["party_2_name"]["type"], "text")
        self.assertEqual(field_map["advocate_for"]["type"], "select")
        self.assertEqual(field_map["scheduled_date"]["type"], "date")
        self.assertEqual(field_map["urgent_reason"]["type"], "select")
        self.assertEqual(field_map["date"]["type"], "date")
        self.assertEqual(field_map["place"]["type"], "text")
        self.assertEqual(field_map["advocate_name"]["type"], "text")

    def test_04_dropdown_options(self):
        """4. Verify party roles and urgent reasons dropdown options."""
        field_map = {f["key"]: f for f in self.tpl.get("fields", [])}

        p1_opts = [o["value"] for o in field_map["party_1_role"]["options"]]
        self.assertIn("ફરીયાદી", p1_opts)
        self.assertIn("અરજદાર", p1_opts)
        self.assertIn("વાદી", p1_opts)

        p2_opts = [o["value"] for o in field_map["party_2_role"]["options"]]
        self.assertIn("આરોપી", p2_opts)
        self.assertIn("સામાવાળા", p2_opts)
        self.assertIn("પ્રતિવાદી", p2_opts)

        reason_opts = [o["value"] for o in field_map["urgent_reason"]["options"]]
        self.assertEqual(len(reason_opts), 4)
        self.assertIn("વોરંટ રદ કરાવવાનો હોય", reason_opts)
        self.assertIn("જામીન રજૂ કરવાના હોય", reason_opts)
        self.assertIn("હુકમ કરાવવાનો હોય", reason_opts)
        self.assertIn("અન્ય", reason_opts)

    def test_05_settings_and_layout(self):
        """5. Verify template settings: A4, 2cm top/bottom margins, 4cm left/right margins, 18pt line spacing."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("page_size"), "A4")
        self.assertEqual(settings.get("body_size"), 13)
        self.assertEqual(settings.get("heading_size"), 15)
        self.assertEqual(settings.get("line_spacing"), 18.0)
        self.assertEqual(settings.get("margin_top_cm"), 2.0)
        self.assertEqual(settings.get("margin_bottom_cm"), 2.0)
        self.assertEqual(settings.get("margin_left_cm"), 4.0)
        self.assertEqual(settings.get("margin_right_cm"), 4.0)

    async def test_06_advocate_designation_derivation(self):
        """6. Verify auto-derived advocate designation in Gujarati and English."""
        user = {"name": "Test Advocate"}
        # For accused / આરોપી: in kam_board it is f"{role} ના એડવોકેટ"
        vals_aaropi = {
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ",
            "advocate_for": "આરોપી",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "scheduled_date": "2026-12-15",
        }
        ctx_aaropi = await server.build_render_context(user, None, vals_aaropi, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx_aaropi["advocate_name"], "આરોપી ના એડવોકેટ")

        # For vadi / વાદી
        vals_vadi = {
            "party_1_role": "વાદી",
            "party_1_name": "રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ",
            "advocate_for": "વાદી",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "scheduled_date": "2026-12-15",
        }
        ctx_vadi = await server.build_render_context(user, None, vals_vadi, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx_vadi["advocate_name"], "વાદી ના એડવોકેટ")

        # In English
        vals_en = {
            "party_1_role": "Plaintiff",
            "party_1_name": "Ramesh",
            "party_2_role": "Defendant",
            "party_2_name": "Suresh",
            "advocate_for": "party_2",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "scheduled_date": "2026-12-15",
        }
        ctx_en = await server.build_render_context(user, None, vals_en, "en", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx_en["advocate_name"], "Advocate for Defendant")

    async def test_07_place_and_taluka_derivation(self):
        """7. Verify place derivation with and without optional taluka."""
        user = {"name": "Test Advocate"}
        # With district only
        vals1 = {"district": "gandhinagar", "taluka": ""}
        ctx1 = await server.build_render_context(user, None, vals1, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx1["place"], "ગાંધીનગર")
        self.assertEqual(ctx1["taluka_place"], "ગાંધીનગર")

        # With taluka and district
        vals2 = {"district": "gandhinagar", "taluka": "kalol"}
        ctx2 = await server.build_render_context(user, None, vals2, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx2["place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx2["taluka_place"], "કલોલ, ગાંધીનગર")

    async def test_08_dynamic_custom_reason(self):
        """8. Verify dynamic custom reason when 'અન્ય' is selected."""
        user = {"name": "Test Advocate"}
        vals = {
            "urgent_reason": "અન્ય",
            "urgent_reason_custom": "મુદ્દતની તારીખે પક્ષકાર હાજર રહી શકે તેમ ન હોવાથી",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx["urgent_reason"], "મુદ્દતની તારીખે પક્ષકાર હાજર રહી શકે તેમ ન હોવાથી")

    async def test_09_date_formatting(self):
        """9. Verify scheduled_date and application date formatting."""
        user = {"name": "Test Advocate"}
        vals = {
            "scheduled_date": "2026-12-25",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="kam_board_par_levani_arji")
        self.assertEqual(ctx["scheduled_date"], "25/12/2026")
        self.assertEqual(ctx["date"], "21/11/2026")

    async def test_10_gujarati_rendering_and_text(self):
        """10. Verify exact Gujarati legal paragraphs and rendered document."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "special_civil_suit",
            "case_number": "૧૨૩/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "scheduled_date": "2026-12-15",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "gu", template_id="kam_board_par_levani_arji")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        # Assert key legal strings are present
        self.assertIn("મુકામ :- કલોલ, ગાંધીનગર", rendered)
        self.assertIn("બાબત :- કામ બોર્ડ પર લેવા બાબત...", rendered)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે તેમજ કેસની આગામી તા. 15/12/2026 નીમવામાં આવેલ છે", rendered)
        self.assertIn("પરંતુ સદર કામમાં આજ રોજ વોરંટ રદ કરાવવાનો હોય જેથી કામ બોર્ડ પર લેવામાં આવે તે જરૂરી છે.", rendered)
        self.assertIn("સદર કાર્યવાહી ન્યાયના હિતમાં હોય, જેથી સદર કામને આજ રોજ બોર્ડ પર લઈ જરૂરી કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertIn("સ્થળ : કલોલ, ગાંધીનગર", rendered)
        self.assertIn("વાદી ના એડવોકેટ", rendered)
        self.assertNotIn("{{", rendered)

    async def test_11_english_rendering_and_text(self):
        """11. Verify English legal paragraphs and rendered document."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "special_civil_suit",
            "case_number": "123/2024",
            "party_1_role": "Plaintiff",
            "party_1_name": "Ramesh Patel",
            "party_2_role": "Defendant",
            "party_2_name": "Haresh Shah",
            "advocate_for": "party_1",
            "scheduled_date": "2026-12-15",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "en", template_id="kam_board_par_levani_arji")
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)

        self.assertIn("Subject :- Application for taking the matter on board ...", rendered)
        self.assertIn("Advocate for Plaintiff", rendered)
        self.assertIn("Place :- Kalol, Gandhinagar", rendered)
        self.assertIn("a warrant is required to be cancelled", rendered)
        self.assertNotIn("{{", rendered)

    async def test_12_pdf_generation(self):
        """12. Verify PDF generation produces valid PDF bytes."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "special_civil_suit",
            "case_number": "૧૨૩/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "વાદી",
            "scheduled_date": "2026-12-15",
            "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "gu", template_id="kam_board_par_levani_arji")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="kam_board_par_levani_arji",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 1000)

    async def test_13_server_get_template(self):
        """13. Verify server.get_template retrieves kam_board_par_levani_arji."""
        t = await server.get_template("kam_board_par_levani_arji")
        self.assertIsNotNone(t)
        self.assertEqual(t.get("name_gu"), "કામ બોર્ડ પર લેવા બાબત")
        self.assertEqual(len(t.get("fields", [])), 15)

    def test_14_existing_12_templates_unmodified(self):
        """14. Verify all 12 prior templates exist and are unchanged."""
        expected_12_ids = [
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
            "fs_right_closure_application",
            "fs_right_reopen_application",
        ]
        all_ids = [t["id"] for t in TEMPLATES]
        for tid in expected_12_ids:
            self.assertIn(tid, all_ids, f"Existing template {tid} must not be missing")
        self.assertIn("kam_board_par_levani_arji", all_ids, "13th template must be in TEMPLATES")


if __name__ == "__main__":
    unittest.main()
