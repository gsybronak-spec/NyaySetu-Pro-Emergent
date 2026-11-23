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


class TestWarrantNoHathBidoApvaniArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "warrant_no_hath_bido_apvani_arji"), None)
        self.assertIsNotNone(self.tpl, "warrant_no_hath_bido_apvani_arji template must be present in TEMPLATES")
        self.user = {"name": "Test Advocate", "advocate_name_gu": "ટેસ્ટ એડવોકેટ", "advocate_name_en": "Test Advocate"}

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "warrant_no_hath_bido_apvani_arji")
        self.assertEqual(self.tpl["name_gu"], "સમન્સ / વોરંટનો હાથબીડો આપવા બાબત")
        self.assertEqual(self.tpl["name_en"], "Application for Issuance of Summons/Warrant Service Process")
        self.assertEqual(self.tpl.get("category"), "Criminal")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("warrant_hathbido", aliases)
        self.assertIn("hathbido", aliases)
        self.assertIn("direct_service", aliases)
        self.assertIn("સમન્સ / વોરંટનો હાથબીડો આપવા બાબત", aliases)

    def test_02_canonical_resolution(self):
        """2. Verify canonical ID aliases and language variants resolution."""
        for cand in [
            "warrant_no_hath_bido_apvani_arji",
            "warrant_no_hath_bido_apvani_arji_gu",
            "warrant_no_hath_bido_apvani_arji_en",
            "warrant_hathbido",
            "hathbido",
            "direct_service",
            "સમન્સ / વોરંટનો હાથબીડો આપવા બાબત",
            "સમન્સ / વોરંટનો હાથબીડો આપવા બાબતની અરજી",
            "હાથબીડો",
            "સમન્સ હાથબીડો",
            "વોરંટ હાથબીડો",
        ]:
            self.assertEqual(
                server.resolve_canonical_template_id(cand),
                "warrant_no_hath_bido_apvani_arji",
                f"Failed to resolve {cand} to warrant_no_hath_bido_apvani_arji",
            )

    def test_03_display_order_position_18(self):
        """3. Verify template is at position #18 in template_display_order."""
        order = server._SETTING_DEFAULTS.get("template_display_order", [])
        self.assertIn("warrant_no_hath_bido_apvani_arji", order)
        idx = order.index("warrant_no_hath_bido_apvani_arji")
        self.assertEqual(idx, 17, f"Expected position 18 (index 17), found {idx + 1}")
        self.assertEqual(order[16], "samadhan_purshish", "Preceding template should be samadhan_purshish")

    def test_04_form_fields_schema(self):
        """4. Verify the 15 standard form fields are defined and sequenced correctly."""
        fields = self.tpl.get("fields", [])
        field_keys = [f["key"] for f in fields]
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
            "process_type",
            "advocate_for",
            "process_person",
            "date",
            "place",
            "advocate_name",
        ]
        self.assertEqual(field_keys, expected_keys)

        # Verify process_type field
        pt_field = next(f for f in fields if f["key"] == "process_type")
        self.assertEqual(pt_field["type"], "radio")
        self.assertEqual(pt_field.get("default"), "સમન્સ")
        pt_vals = [o["value"] for o in pt_field["options"]]
        self.assertEqual(pt_vals, ["સમન્સ", "વોરંટ"])

        # Verify process_person field
        pp_field = next(f for f in fields if f["key"] == "process_person")
        self.assertEqual(pp_field["type"], "select")
        pp_vals = [o["value"] for o in pp_field["options"]]
        self.assertIn("આરોપી", pp_vals)
        self.assertIn("સામાવાળા", pp_vals)
        self.assertIn("પ્રતિવાદી", pp_vals)
        self.assertIn("ફરીયાદી", pp_vals)
        self.assertIn("અરજદાર", pp_vals)
        self.assertIn("વાદી", pp_vals)

    async def test_05_gujarati_context_and_draft_summons(self):
        """5. Verify Gujarati draft rendering with process_type = સમન્સ."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "હસમુખભાઈ મોહનભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "ભરતભાઈ નારણભાઈ પરમાર",
            "process_type": "સમન્સ",
            "advocate_for": "ફરીયાદી",
            "process_person": "આરોપી",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="warrant_no_hath_bido_apvani_arji",
        )

        self.assertEqual(ctx["taluka_place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx["place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx["process_type"], "સમન્સ")
        self.assertEqual(ctx["process_person"], "આરોપી")
        self.assertEqual(ctx["advocate_for_role"], "ફરીયાદી")
        self.assertEqual(ctx["advocate_name"], "ફરીયાદી ના એડવોકેટ")

        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("મહેરબાન ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટ સાહેબશ્રીની કોર્ટમાં,", rendered)
        self.assertIn("મુકામ :- કલોલ, ગાંધીનગર", rendered)
        self.assertIn("ફોજદારી કેસ નં. : 1234/2026", rendered)
        self.assertIn("ફરીયાદી :- હસમુખભાઈ મોહનભાઈ પટેલ", rendered)
        self.assertIn("વિરુદ્ધ", rendered)
        self.assertIn("આરોપી :- ભરતભાઈ નારણભાઈ પરમાર", rendered)
        self.assertIn("બાબત :- સમન્સનો હાથબીડો આપવા બાબત...", rendered)
        self.assertIn("સદર કામમાં અમો ફરીયાદીના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે .....", rendered)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે.", rendered)
        self.assertIn("સદર કેસમાં આરોપીને બજવણી માટે સમન્સ ઇશ્યુ કરવામાં આવેલ છે", rendered)
        self.assertIn("સદર સમન્સની બજવણી કરાવવા માટે સમન્સનો જરૂરી હાથબીડો આપી બજવણી કરાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertIn("તારીખ : 23/11/2026", rendered)
        self.assertIn("સ્થળ : કલોલ, ગાંધીનગર", rendered)
        self.assertIn("ફરીયાદી ના એડવોકેટ", rendered)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("}}", rendered)

    async def test_06_gujarati_context_and_draft_warrant(self):
        """6. Verify Gujarati draft rendering with process_type = વોરંટ."""
        values = {
            "court_name": "પ્રિન્સિપાલ સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "5678/2026",
            "party_1_role": "અરજદાર",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "સામાવાળા",
            "party_2_name": "વિષ્ણુભાઈ પ્રજાપતિ",
            "process_type": "વોરંટ",
            "advocate_for": "અરજદાર",
            "process_person": "સામાવાળા",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="warrant_no_hath_bido_apvani_arji",
        )

        self.assertEqual(ctx["process_type"], "વોરંટ")
        self.assertEqual(ctx["process_person"], "સામાવાળા")
        self.assertEqual(ctx["advocate_name"], "અરજદાર ના એડવોકેટ")

        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("બાબત :- વોરંટનો હાથબીડો આપવા બાબત...", rendered)
        self.assertIn("સદર કામમાં અમો અરજદારના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે .....", rendered)
        self.assertIn("સદર કેસમાં સામાવાળાને બજવણી માટે વોરંટ ઇશ્યુ કરવામાં આવેલ છે", rendered)
        self.assertIn("સદર વોરંટની બજવણી કરાવવા માટે વોરંટનો જરૂરી હાથબીડો આપી બજવણી કરાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertNotIn("{{", rendered)

    async def test_07_english_context_and_draft(self):
        """7. Verify English draft rendering."""
        values = {
            "court_name": "Chief Judicial Magistrate",
            "district": "Gandhinagar",
            "taluka": "Kalol",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "Complainant",
            "party_1_name": "Hasmukhbhai Mohanbhai Patel",
            "party_2_role": "Accused",
            "party_2_name": "Bharatbhai Naranbhai Parmar",
            "process_type": "Warrant",
            "advocate_for": "Complainant",
            "process_person": "Accused",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="en",
            template_id="warrant_no_hath_bido_apvani_arji",
        )

        self.assertEqual(ctx["process_type"], "Warrant")
        self.assertEqual(ctx["process_person"], "Accused")
        self.assertEqual(ctx["advocate_name"], "Advocate for Complainant")

        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        self.assertIn("IN THE COURT OF THE HON'BLE Chief Judicial Magistrate,", rendered)
        self.assertIn("AT: Kalol, Gandhinagar", rendered)
        self.assertIn("Criminal Case No. : 1234/2026", rendered)
        self.assertIn("SUBJECT: APPLICATION FOR ISSUANCE OF Warrant SERVICE PROCESS / HAND DELIVERY...", rendered)
        self.assertIn("In the above matter, we, the advocate for Complainant, most respectfully submit before this Hon'ble Court that:", rendered)
        self.assertIn("In the said case, Warrant has been issued for service upon Accused", rendered)
        self.assertIn("Advocate for Complainant", rendered)
        self.assertNotIn("{{", rendered)

    async def test_08_block_align_and_no_body_underline(self):
        """8. Verify that title is centered/bold/underlined and body paragraphs are NOT underlined and properly justified."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "હસમુખભાઈ મોહનભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "ભરતભાઈ નારણભાઈ પરમાર",
            "process_type": "સમન્સ",
            "advocate_for": "ફરીયાદી",
            "process_person": "આરોપી",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="warrant_no_hath_bido_apvani_arji",
        )
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        align_rules = (self.tpl.get("settings") or {}).get("block_align")
        blocks = doc_generator.build_blocks(rendered, align_rules=align_rules)

        # Title block
        title_block = next((b for b in blocks if "હાથબીડો આપવા બાબત" in b["text"]), None)
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

    async def test_09_pdf_generation(self):
        """9. Verify clean PDF generation without error."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "હસમુખભાઈ મોહનભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "ભરતભાઈ નારણભાઈ પરમાર",
            "process_type": "સમન્સ",
            "advocate_for": "ફરીયાદી",
            "process_person": "આરોપી",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="gu",
            template_id="warrant_no_hath_bido_apvani_arji",
        )
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        align_rules = (self.tpl.get("settings") or {}).get("block_align")
        blocks = doc_generator.build_blocks(rendered, align_rules=align_rules)
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl.get("settings"),
            template_id="warrant_no_hath_bido_apvani_arji",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Output must be valid PDF bytes")
        self.assertGreater(len(pdf_bytes), 1000)
        art_path = Path("/home/court/.gemini/antigravity/brain/e73c87ff-99de-4a10-8aa0-68da9c24e83b/live_deployed_warrant_no_hath_bido_apvani_arji_gu.pdf")
        with open(art_path, "wb") as f:
            f.write(pdf_bytes)

    async def test_10_english_pdf_generation(self):
        """10. Verify clean English PDF generation."""
        values = {
            "court_name": "Chief Judicial Magistrate",
            "district": "Gandhinagar",
            "taluka": "Kalol",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "Complainant",
            "party_1_name": "Hasmukhbhai Mohanbhai Patel",
            "party_2_role": "Accused",
            "party_2_name": "Bharatbhai Naranbhai Parmar",
            "process_type": "Warrant",
            "advocate_for": "Complainant",
            "process_person": "Accused",
            "date": "23/11/2026",
        }

        ctx = await server.build_render_context(
            user=self.user,
            case=None,
            values=values,
            language="en",
            template_id="warrant_no_hath_bido_apvani_arji",
        )
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        align_rules = (self.tpl.get("settings") or {}).get("block_align")
        blocks = doc_generator.build_blocks(rendered, align_rules=align_rules)
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="en",
            settings=self.tpl.get("settings"),
            template_id="warrant_no_hath_bido_apvani_arji",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Output must be valid PDF bytes")
        self.assertGreater(len(pdf_bytes), 1000)
        art_path = Path("/home/court/.gemini/antigravity/brain/e73c87ff-99de-4a10-8aa0-68da9c24e83b/live_deployed_warrant_no_hath_bido_apvani_arji_en.pdf")
        with open(art_path, "wb") as f:
            f.write(pdf_bytes)


if __name__ == "__main__":
    unittest.main()

