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


class TestWarrantRadKarvaniArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "warrant_rad_karvani_arji"), None)
        self.assertIsNotNone(self.tpl, "warrant_rad_karvani_arji template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "warrant_rad_karvani_arji")
        self.assertEqual(self.tpl["name_gu"], "વોરંટ રદ કરાવવા બાબત")
        self.assertEqual(self.tpl["name_en"], "Application for Cancellation of Warrant")
        self.assertEqual(self.tpl.get("category"), "Criminal")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("warrant_rad", aliases)
        self.assertIn("warrant_rad_karvani_arji", aliases)
        self.assertIn("વોરંટ રદ કરાવવા બાબત", aliases)
        self.assertIn("વોરંટ રદ કરવાની અરજી", aliases)

    def test_02_gujarati_and_english_pairing(self):
        """2. Verify Gujarati and English pairing in server canonical map."""
        self.assertEqual(server.resolve_canonical_template_id("warrant_rad_karvani_arji"), "warrant_rad_karvani_arji")
        self.assertEqual(server.resolve_canonical_template_id("warrant_rad_karvani_arji_gu"), "warrant_rad_karvani_arji")
        self.assertEqual(server.resolve_canonical_template_id("warrant_rad_karvani_arji_en"), "warrant_rad_karvani_arji")

    def test_03_all_16_form_fields_and_types(self):
        """3. Verify all form fields exist with exact keys, types, and sequence."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 16, f"Expected 16 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "warrant_date", "absence_reason", "absence_reason_custom",
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
        self.assertEqual(field_map["warrant_date"]["type"], "date")
        self.assertEqual(field_map["absence_reason"]["type"], "select")
        self.assertEqual(field_map["date"]["type"], "date")
        self.assertEqual(field_map["place"]["type"], "text")
        self.assertEqual(field_map["advocate_name"]["type"], "text")

    def test_04_dropdown_options(self):
        """4. Verify party roles, complete 6 individual advocate party roles, and absence reasons dropdown options."""
        field_map = {f["key"]: f for f in self.tpl.get("fields", [])}

        p1_opts = [o["value"] for o in field_map["party_1_role"]["options"]]
        self.assertIn("ફરીયાદી", p1_opts)
        self.assertIn("અરજદાર", p1_opts)
        self.assertIn("વાદી", p1_opts)

        p2_opts = [o["value"] for o in field_map["party_2_role"]["options"]]
        self.assertIn("આરોપી", p2_opts)
        self.assertIn("સામાવાળા", p2_opts)
        self.assertIn("પ્રતિવાદી", p2_opts)

        # FIX 1: Verify complete 6 individual party roles for advocate_for
        adv_opts = [o["value"] for o in field_map["advocate_for"]["options"]]
        expected_adv_roles = ["આરોપી", "સામાવાળા", "પ્રતિવાદી", "ફરીયાદી", "અરજદાર", "વાદી"]
        self.assertEqual(adv_opts, expected_adv_roles, f"Expected {expected_adv_roles}, got {adv_opts}")
        self.assertEqual(field_map["advocate_for"].get("default"), "આરોપી")
        self.assertNotIn("source", field_map["advocate_for"])

        # FIX 2: Verify grammatically corrected phrasing for all 6 absence reasons (without 'કારણોસર' in dropdown)
        reason_opts = [o["value"] for o in field_map["absence_reason"]["options"]]
        expected_reasons = [
            "અભ્યાસ અર્થે બહારગામ ગયેલ હોવાના",
            "માંદગીના",
            "વ્યવસાય અર્થે બહારગામ ગયેલ હોવાના",
            "સામાજીક કામમાં રોકાયેલ હોવાના",
            "સગા-સબંધીમાં કોઈ સગાનું અવસાન થયેલ હોવાના",
            "અન્ય",
        ]
        self.assertEqual(reason_opts, expected_reasons, f"Expected {expected_reasons}, got {reason_opts}")

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

    async def test_06_advocate_designation_and_accused_role(self):
        """6. Verify all 6 individual advocate party roles and accused_name_role."""
        user = {"name": "Test Advocate"}

        # Test all 6 individual roles in Gujarati
        roles_gu_expected = [
            ("આરોપી", "આરોપી ના એડવોકેટ"),
            ("સામાવાળા", "સામાવાળા ના એડવોકેટ"),
            ("પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ"),
            ("ફરીયાદી", "ફરીયાદી ના એડવોકેટ"),
            ("અરજદાર", "અરજદાર ના એડવોકેટ"),
            ("વાદી", "વાદી ના એડવોકેટ"),
        ]
        for role_val, expected_desig in roles_gu_expected:
            vals = {
                "party_1_role": "ફરીયાદી",
                "party_1_name": "રમેશભાઈ",
                "party_2_role": "આરોપી",
                "party_2_name": "સુરેશભાઈ",
                "advocate_for": role_val,
                "absence_reason": "માંદગીના",
                "warrant_date": "2026-12-15",
            }
            ctx = await server.build_render_context(user, None, vals, "gu", template_id="warrant_rad_karvani_arji")
            self.assertEqual(ctx["advocate_name"], expected_desig, f"Failed for role {role_val}")
            self.assertEqual(ctx["advocate_for_role"], role_val)

        # Test all 6 roles in English
        roles_en_expected = [
            ("આરોપી", "Advocate for Accused", "Accused"),
            ("સામાવાળા", "Advocate for Opponent", "Opponent"),
            ("પ્રતિવાદી", "Advocate for Defendant", "Defendant"),
            ("ફરીયાદી", "Advocate for Complainant", "Complainant"),
            ("અરજદાર", "Advocate for Applicant", "Applicant"),
            ("વાદી", "Advocate for Plaintiff", "Plaintiff"),
        ]
        for role_val, expected_desig_en, expected_role_en in roles_en_expected:
            vals_en = {
                "party_1_role": "Complainant",
                "party_1_name": "Ramesh",
                "party_2_role": "Accused",
                "party_2_name": "Suresh",
                "advocate_for": role_val,
                "absence_reason": "Illness",
                "warrant_date": "2026-12-15",
            }
            ctx_en = await server.build_render_context(user, None, vals_en, "en", template_id="warrant_rad_karvani_arji")
            self.assertEqual(ctx_en["advocate_name"], expected_desig_en, f"Failed for role {role_val} in EN")
            self.assertEqual(ctx_en["advocate_for_role"], expected_role_en)

    async def test_07_place_and_taluka_derivation(self):
        """7. Verify place derivation with and without optional taluka."""
        user = {"name": "Test Advocate"}
        # With district only
        vals1 = {"district": "gandhinagar", "taluka": ""}
        ctx1 = await server.build_render_context(user, None, vals1, "gu", template_id="warrant_rad_karvani_arji")
        self.assertEqual(ctx1["place"], "ગાંધીનગર")
        self.assertEqual(ctx1["taluka_place"], "ગાંધીનગર")

        # With taluka and district
        vals2 = {"district": "gandhinagar", "taluka": "kalol"}
        ctx2 = await server.build_render_context(user, None, vals2, "gu", template_id="warrant_rad_karvani_arji")
        self.assertEqual(ctx2["place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx2["taluka_place"], "કલોલ, ગાંધીનગર")

    async def test_08_dynamic_custom_reason(self):
        """8. Verify dynamic custom reason when 'અન્ય' is selected."""
        user = {"name": "Test Advocate"}
        vals = {
            "absence_reason": "અન્ય",
            "absence_reason_custom": "ટ્રેન મોડી હોવાના કારણે સમયસર પહોંચી શકાયેલ ન હોઈ",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="warrant_rad_karvani_arji")
        self.assertEqual(ctx["absence_reason"], "ટ્રેન મોડી હોવાના કારણે સમયસર પહોંચી શકાયેલ ન હોઈ")

    async def test_09_date_formatting(self):
        """9. Verify warrant_date and application date formatting."""
        user = {"name": "Test Advocate"}
        vals = {
            "warrant_date": "2026-12-25",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="warrant_rad_karvani_arji")
        self.assertEqual(ctx["warrant_date"], "25/12/2026")
        self.assertEqual(ctx["date"], "21/11/2026")

    async def test_10_gujarati_rendering_and_text(self):
        """10. Verify exact Gujarati legal paragraphs and rendered document."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "૪૫૬/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "આરોપી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "આરોપી",
            "warrant_date": "2026-12-15",
            "absence_reason": "માંદગીના",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "gu", template_id="warrant_rad_karvani_arji")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        # Assert key legal strings from authoritative PDF are present
        self.assertIn("મુકામ :- કલોલ, ગાંધીનગર", rendered)
        self.assertIn("બાબત :- વોરંટ રદ કરાવવા બાબત...", rendered)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે તેમજ કેસની આગામી તા. 15/12/2026 નિમવામાં આવેલ છે.", rendered)
        self.assertIn("અમોના અસીલ માંદગીના કારણોસર આપ નામદાર કોર્ટમાં હાજર રહી શકેલ ન હોઈ, જેથી અમોના અસીલ પર વોરંટ કાઢવામાં આવેલ છે.", rendered)
        self.assertIn("વધુમાં, ગેરહાજર રહેવાનો કોઈ દુર્ભાવ કે આપ નામદાર કોર્ટની કાર્યવાહીમાં વિલંબ કરવાનો આશય નથી", rendered)
        self.assertIn("જેથી સદર આરોપી વિરુદ્ધ કાઢવામાં આવેલ વોરંટ રદ કરી કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertIn("સ્થળ : કલોલ, ગાંધીનગર", rendered)
        self.assertIn("આરોપી ના એડવોકેટ", rendered)
        self.assertNotIn("કારણોસર કારણોસર", rendered)
        self.assertNotIn("{{", rendered)

        # Verify all 6 absence reason options produce grammatically correct combined wording with paragraph
        all_reasons = [
            ("અભ્યાસ અર્થે બહારગામ ગયેલ હોવાના", "અભ્યાસ અર્થે બહારગામ ગયેલ હોવાના કારણોસર"),
            ("માંદગીના", "માંદગીના કારણોસર"),
            ("વ્યવસાય અર્થે બહારગામ ગયેલ હોવાના", "વ્યવસાય અર્થે બહારગામ ગયેલ હોવાના કારણોસર"),
            ("સામાજીક કામમાં રોકાયેલ હોવાના", "સામાજીક કામમાં રોકાયેલ હોવાના કારણોસર"),
            ("સગા-સબંધીમાં કોઈ સગાનું અવસાન થયેલ હોવાના", "સગા-સબંધીમાં કોઈ સગાનું અવસાન થયેલ હોવાના કારણોસર"),
            ("અન્ય", "અન્ય કારણોસર"),
        ]
        for opt_val, expected_combined in all_reasons:
            s_val = dict(sample_values, absence_reason=opt_val)
            ctx_r = await server.build_render_context(user, None, s_val, "gu", template_id="warrant_rad_karvani_arji")
            rend_r = doc_generator.render_template(self.tpl["content_gu"], ctx_r)
            self.assertIn(expected_combined, rend_r, f"Expected '{expected_combined}' in rendered text for '{opt_val}'")
            self.assertNotIn("કારણોસર કારણોસર", rend_r, f"Duplicate 'કારણોસર કારણોસર' found for reason {opt_val}")
            self.assertNotIn("{{", rend_r)

        # Also verify custom text functionality for અન્ય
        s_val_custom = dict(sample_values, absence_reason="અન્ય", absence_reason_custom="ટ્રાફિકમાં ફસાઈ ગયેલ હોવાના")
        ctx_custom = await server.build_render_context(user, None, s_val_custom, "gu", template_id="warrant_rad_karvani_arji")
        rend_custom = doc_generator.render_template(self.tpl["content_gu"], ctx_custom)
        self.assertIn("ટ્રાફિકમાં ફસાઈ ગયેલ હોવાના કારણોસર", rend_custom)
        self.assertNotIn("કારણોસર કારણોસર", rend_custom)

    async def test_11_english_rendering_and_text(self):
        """11. Verify English legal paragraphs and rendered document."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "456/2024",
            "party_1_role": "Complainant",
            "party_1_name": "Ramesh Patel",
            "party_2_role": "Accused",
            "party_2_name": "Haresh Shah",
            "advocate_for": "party_2",
            "warrant_date": "2026-12-15",
            "absence_reason": "Illness",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "en", template_id="warrant_rad_karvani_arji")
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)

        self.assertIn("Subject :- Application for Cancellation of Warrant", rendered)
        self.assertIn("Advocate for Accused", rendered)
        self.assertIn("Place :- Kalol, Gandhinagar", rendered)
        self.assertIn("cancel the warrant issued against the said Accused", rendered)
        self.assertNotIn("{{", rendered)

    async def test_12_pdf_generation(self):
        """12. Verify PDF generation produces valid PDF bytes."""
        user = {"name": "Test Advocate"}
        sample_values = {
            "court_name": "principal_senior_civil_judge",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "૪૫૬/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "પટેલ રમેશભાઈ",
            "party_2_role": "આરોપી",
            "party_2_name": "શાહ હરેશભાઈ",
            "advocate_for": "આરોપી",
            "warrant_date": "2026-12-15",
            "absence_reason": "માંદગીના",
            "date": "2026-11-21",
        }
        ctx = await server.build_render_context(user, None, sample_values, "gu", template_id="warrant_rad_karvani_arji")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="warrant_rad_karvani_arji",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated file must start with PDF header %PDF-")
        self.assertGreater(len(pdf_bytes), 1000, "Generated PDF must be non-empty and well-sized")

    async def test_13_server_get_template(self):
        """13. Verify server.get_template retrieves warrant_rad_karvani_arji."""
        t = await server.get_template("warrant_rad_karvani_arji")
        self.assertIsNotNone(t)
        self.assertEqual(t.get("name_gu"), "વોરંટ રદ કરાવવા બાબત")
        self.assertEqual(t.get("name_en"), "Application for Cancellation of Warrant")

    def test_14_existing_13_templates_unmodified(self):
        """14. Verify all 13 prior templates exist and are unchanged."""
        expected_13_ids = [
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
            "kam_board_par_levani_arji",
        ]
        all_ids = [t["id"] for t in TEMPLATES]
        for tid in expected_13_ids:
            self.assertIn(tid, all_ids, f"Existing template {tid} must not be missing")
        self.assertIn("warrant_rad_karvani_arji", all_ids, "14th template must be in TEMPLATES")


if __name__ == "__main__":
    unittest.main()
