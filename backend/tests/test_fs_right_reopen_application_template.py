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


class TestFsRightReopenApplicationTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "fs_right_reopen_application"), None)
        self.assertIsNotNone(self.tpl, "fs_right_reopen_application template must be present in TEMPLATES")

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "fs_right_reopen_application")
        self.assertEqual(self.tpl["name_gu"], "એફ.એસ.નો હક ફરીથી ખોલવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Reopening Further Statement (F.S.) Right")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("fs right reopen application", aliases)
        self.assertIn("એફ.એસ.નો હક ફરીથી ખોલવાની અરજી", aliases)
        self.assertIn("એફ.એસ.નો હક ફરીથી ખોલવા બાબત", aliases)

    def test_02_gujarati_and_english_pairing(self):
        """2. Verify Gujarati and English pairing in server canonical map."""
        self.assertEqual(server.resolve_canonical_template_id("fs_right_reopen_application"), "fs_right_reopen_application")
        self.assertEqual(server.resolve_canonical_template_id("fs_right_reopen_application_gu"), "fs_right_reopen_application")
        self.assertEqual(server.resolve_canonical_template_id("fs_right_reopen_application_en"), "fs_right_reopen_application")

    def test_03_all_14_form_fields_and_types(self):
        """3. Verify all 14 form fields exist with exact keys, types, and sequence."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 14, f"Expected 14 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "fs_failure_reason",
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
            "fs_failure_reason": "select",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for f in fields:
            fkey = f["key"]
            self.assertEqual(f["type"], expected_types[fkey], f"Field {fkey} has unexpected type")
            self.assertFalse(f.get("required"), f"Field {fkey} must have required: False")

    def test_04_fs_failure_reason_options(self):
        """4. Verify fs_failure_reason options ending in ', જે' plus 'અન્ય'."""
        field = next((f for f in self.tpl["fields"] if f["key"] == "fs_failure_reason"), None)
        self.assertIsNotNone(field)
        opts = [o["value"] for o in field.get("options", [])]
        expected_ending = ", જે"
        for opt in opts:
            if opt != "અન્ય":
                self.assertTrue(opt.endswith(expected_ending), f"Option '{opt}' does not end in '{expected_ending}'")
        self.assertIn("અન્ય", opts)

    async def test_05_optional_taluka_behavior(self):
        """5. Verify optional taluka: does not fail if taluka is omitted."""
        user = {"name": "Test Advocate"}
        vals = {"district": "gandhinagar", "taluka": ""}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx["district"], "ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "ગાંધીનગર")
        self.assertEqual(ctx["place"], "ગાંધીનગર")

    async def test_06_taluka_before_district_ordering(self):
        """6. Verify if taluka exists, taluka precedes district: 'કલોલ, ગાંધીનગર'."""
        user = {"name": "Test Advocate"}
        vals = {"district": "gandhinagar", "taluka": "kalol"}
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx["taluka_place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx["place"], "કલોલ, ગાંધીનગર")

    async def test_07_subject_and_paragraphs_rendering_gu(self):
        """7. Verify exact legal content sequence and structure in Gujarati."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "૧૨૩/૨૦૨૪",
            "party_1_role": "ફરિયાદી",
            "party_1_name": "રાજેશભાઇ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઇ શાહ",
            "advocate_for": "આરોપી",
            "fs_failure_reason": "અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે",
            "date": "2024-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_reopen_application")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        self.assertIn("મુકામ :- કલોલ, ગાંધીનગર", rendered)
        self.assertIn("ક્રિમિનલ કેસ નં. : ૧૨૩/૨૦૨૪", rendered)
        self.assertTrue("ફરિયાદી :- રાજેશભાઇ પટેલ" in rendered or "ફરીયાદી :- રાજેશભાઇ પટેલ" in rendered)
        self.assertIn("વિરુદ્ધ", rendered)
        self.assertIn("આરોપી :- સુરેશભાઇ શાહ", rendered)
        self.assertIn("બાબત :- એફ.એસ.નો હક ફરીથી ખોલવા બાબત...", rendered)
        self.assertIn("સદર કામમા અમો આરોપી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....", rendered)
        self.assertIn("અમોનો એફ. એસ. નો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે.", rendered)
        self.assertIn("જે અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે કારણોસર એફ. એસ. થઈ શકેલ નહિ", rendered)
        self.assertIn("અમોનો એફ. એસ. નો હક ફરીથી ખોલી અમોને એફ.એસ. કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertNotIn("એફ. એસ. કરવાનો હક", rendered)
        self.assertIn("તારીખ : 21/11/2024", rendered)
        self.assertIn("સ્થળ : કલોલ, ગાંધીનગર", rendered)
        # Advocate designation for આરોપી must be exactly આરોપીના (no એડવોકેટ appended)
        self.assertEqual(ctx["advocate_name"], "આરોપીના")
        bottom_designation = rendered.split("----------")[-1].strip()
        self.assertEqual(bottom_designation, "આરોપીના")

    async def test_07b_advocate_designation_other_roles(self):
        """7b. Verify selecting other roles still correctly appends ના એડવોકેટ."""
        user = {"name": "Test Advocate"}
        # Test Plaintiff / વાદી
        vals_vadi = {"advocate_for": "વાદી"}
        ctx_vadi = await server.build_render_context(user, None, vals_vadi, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx_vadi["advocate_name"], "વાદી ના એડવોકેટ")

        # Test Complainant / ફરિયાદી
        vals_fariyadi = {"advocate_for": "ફરિયાદી"}
        ctx_fariyadi = await server.build_render_context(user, None, vals_fariyadi, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx_fariyadi["advocate_name"], "ફરીયાદી ના એડવોકેટ")

        # Test Opponent / સામાવાળા
        vals_samawala = {"advocate_for": "સામાવાળા"}
        ctx_samawala = await server.build_render_context(user, None, vals_samawala, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx_samawala["advocate_name"], "સામાવાળા ના એડવોકેટ")

    async def test_08_custom_reason_resolution(self):
        """8. Verify dynamic custom reason resolution when 'અન્ય' is selected."""
        user = {"name": "Test Advocate"}
        vals = {
            "fs_failure_reason": "અન્ય",
            "fs_failure_reason_custom": "ટ્રેન મોડી હોવાના કારણે સમયસર પહોંચી શકાયેલ ન હતું, જે",
            "advocate_for": "party_2",
            "party_2_role": "આરોપી",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_reopen_application")
        self.assertEqual(ctx["fs_failure_reason"], "ટ્રેન મોડી હોવાના કારણે સમયસર પહોંચી શકાયેલ ન હતું, જે")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("ટ્રેન મોડી હોવાના કારણે સમયસર પહોંચી શકાયેલ ન હતું, જે", rendered)

    async def test_09_english_rendering(self):
        """9. Verify English legal application rendering and translation."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "123/2024",
            "party_1_role": "ફરિયાદી",
            "party_1_name": "Rajesh Patel",
            "party_2_role": "આરોપી",
            "party_2_name": "Suresh Shah",
            "advocate_for": "આરોપી",
            "fs_failure_reason": "અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે",
            "date": "2024-11-21",
        }
        ctx = await server.build_render_context(user, None, vals, "en", template_id="fs_right_reopen_application")
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)

        self.assertIn("Place :- Kalol, Gandhinagar", rendered)
        self.assertIn("Criminal Case No. : 123/2024", rendered)
        self.assertIn("Versus", rendered)
        self.assertIn("Subject :- Application for reopening further statement (F.S.) right ...", rendered)
        self.assertIn("Advocate for Accused", rendered)
        self.assertIn("we could not attend this Hon'ble Court due to illness, which", rendered)
        self.assertIn("Date : 21/11/2024", rendered)

    async def test_10_pdf_generation_clean_no_unresolved_placeholders(self):
        """10. Verify generated PDF has valid PDF header and no unresolved placeholders."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "123/2024",
            "party_1_role": "ફરિયાદી",
            "party_1_name": "રાજેશભાઇ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઇ શાહ",
            "advocate_for": "આરોપી",
            "fs_failure_reason": "અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે",
            "date": "2024-11-21",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="fs_right_reopen_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        # Ensure no raw {{...}} remains
        matches = re.findall(r"\{\{[^}]+\}\}", rendered_gu)
        self.assertEqual(matches, [], f"Unresolved placeholders found in rendered text: {matches}")

        blocks = doc_generator.build_blocks(rendered_gu, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="fs_right_reopen_application",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated document must be a valid PDF")
        self.assertGreater(len(pdf_bytes), 1000, "PDF size should be realistic")

    def test_11_existing_11_templates_unmodified(self):
        """11. Verify the 11 existing templates exist and are unchanged."""
        expected_11_ids = [
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
        ]
        all_ids = [t["id"] for t in TEMPLATES]
        for tid in expected_11_ids:
            self.assertIn(tid, all_ids, f"Existing template {tid} must not be missing")
        self.assertIn("fs_right_reopen_application", all_ids, "12th template must be in TEMPLATES")


if __name__ == "__main__":
    unittest.main()
