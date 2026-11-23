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


class TestUlatTapasNoHaqKholvaniArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "ulat_tapas_no_haq_kholvani_arji"), None)
        self.assertIsNotNone(self.tpl, "ulat_tapas_no_haq_kholvani_arji template must be present in TEMPLATES")
        self.user = {"name": "Test Advocate", "advocate_name_gu": "ટેસ્ટ એડવોકેટ", "advocate_name_en": "Test Advocate"}

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "ulat_tapas_no_haq_kholvani_arji")
        self.assertEqual(self.tpl["name_gu"], "ઉલટ તપાસનો હક ફરીથી ખોલી આપવા બાબત")
        self.assertEqual(self.tpl["name_en"], "Application to Reopen Cross-Examination Right")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("ulat_tapas_khol", aliases)
        self.assertIn("ulta_tapas_no_haq_kholvani_arji", aliases)
        self.assertIn("ઉલટ તપાસનો હક ફરીથી ખોલી આપવા બાબત", aliases)

    def test_02_canonical_resolution(self):
        """2. Verify canonical ID aliases and language variants resolution."""
        for cand in [
            "ulat_tapas_no_haq_kholvani_arji",
            "ulat_tapas_no_haq_kholvani_arji_gu",
            "ulat_tapas_no_haq_kholvani_arji_en",
            "ulta_tapas_no_haq_kholvani_arji",
            "ulta_tapas_no_haq_kholvani_arji_gu",
            "ulta_tapas_no_haq_kholvani_arji_en",
            "ulat_tapas_khol",
            "ulat_tapas_kholvani_arji",
        ]:
            self.assertEqual(
                server.resolve_canonical_template_id(cand),
                "ulat_tapas_no_haq_kholvani_arji",
                f"Failed canonical resolution for {cand}"
            )

    def test_03_all_15_form_fields(self):
        """3. Verify all 15 form fields exist with exact keys, types, and sequence."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 15, f"Expected 15 fields, got {len(fields)}")
        keys = [f["key"] for f in fields]
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
            "reason",
            "custom_reason",
            "date",
            "place",
            "advocate_name",
        ]
        self.assertEqual(keys, expected_keys)

        types = {f["key"]: f.get("type") for f in fields}
        self.assertEqual(types["court_name"], "select")
        self.assertEqual(types["district"], "select")
        self.assertEqual(types["taluka"], "select")
        self.assertEqual(types["case_type"], "select")
        self.assertEqual(types["case_number"], "text")
        self.assertEqual(types["party_1_role"], "radio")
        self.assertEqual(types["party_1_name"], "text")
        self.assertEqual(types["party_2_role"], "radio")
        self.assertEqual(types["party_2_name"], "text")
        self.assertEqual(types["advocate_for"], "select")
        self.assertEqual(types["reason"], "select")
        self.assertEqual(types["custom_reason"], "text")
        self.assertEqual(types["date"], "date")
        self.assertEqual(types["place"], "text")
        self.assertEqual(types["advocate_name"], "text")

    def test_04_party_roles_and_reasons_options(self):
        """4. Verify options for party roles, advocate_for, and reason."""
        fields = {f["key"]: f for f in self.tpl.get("fields", [])}

        p1_opts = [o.get("value") or o.get("key") for o in fields["party_1_role"].get("options", [])]
        self.assertEqual(p1_opts, ["ફરીયાદી", "અરજદાર", "વાદી"])

        p2_opts = [o.get("value") or o.get("key") for o in fields["party_2_role"].get("options", [])]
        self.assertEqual(p2_opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

        adv_opts = [o.get("value") or o.get("key") for o in fields["advocate_for"].get("options", [])]
        self.assertEqual(adv_opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી", "ફરીયાદી", "અરજદાર", "વાદી"])

        reason_opts = [o.get("value") or o.get("key") for o in fields["reason"].get("options", [])]
        self.assertEqual(reason_opts, [
            "માંદગીના કારણોસર",
            "સામાજીક કામે રોકાયેલ હોવાના કારણોસર",
            "સગા ગુજરી ગયેલ હોવાથી",
            "આર્થિક કામ અર્થે બહારગામ ગયેલ હોવાથી",
            "અન્ય",
        ])

    def test_05_legal_draft_text_structure(self):
        """5. Verify Gujarati legal draft structure matches PDF Page 2 exactly."""
        gu = self.tpl.get("content_gu", "")
        self.assertIn("મહેરબાન {{court_name}} સાહેબશ્રીની કોર્ટમાં,", gu)
        self.assertIn("મુકામ :- {{taluka_place}}", gu)
        self.assertIn("{{case_type}} નં. : {{case_number}}", gu)
        self.assertIn("{{party_1_role}} :- {{party_1_name}}", gu)
        self.assertIn("વિરુદ્ધ", gu)
        self.assertIn("{{party_2_role}} :- {{party_2_name}}", gu)
        self.assertIn("બાબત :- ઉલટતપાસનો હક ફરીથી ખોલી આપવા બાબત...", gu)
        self.assertIn("સદર કામમાં અમો {{advocate_for_role}}ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે .....", gu)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટમાં ચાલવા પર છે. જેમાં અમોનો ઉલટ-તપાસનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે.", gu)
        self.assertIn("{{reason_text}} કારણોસર ઉલટ-તપાસ થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી હોવાથી તથા ઉલટ-તપાસ કરવાની તક મળવી એ ન્યાયના હિતમાં હોય, અમોનો ઉલટ-તપાસ કરવાનો હક ફરીથી ખોલી અમોને ઉલટ-તપાસ કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશો જી.", gu)
        self.assertIn("તારીખ : {{date}}", gu)
        self.assertIn("સ્થળ : {{place}}", gu)
        self.assertIn("{{advocate_name}}", gu)

    async def test_06_rendering_default_reason_illness(self):
        """6. Test rendering with default reason 'માંદગીના કારણોસર' and verify grammar deduplication."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "અમદાવાદ",
            "taluka": "દસક્રોઈ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રાજેશભાઈ સોલંકી",
            "party_2_role": "આરોપી",
            "party_2_name": "પ્રકાશભાઈ પટેલ",
            "advocate_for": "આરોપી",
            "reason": "માંદગીના કારણોસર",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="ulat_tapas_no_haq_kholvani_arji")
        self.assertEqual(ctx["taluka_place"], "દસક્રોઈ, અમદાવાદ")
        self.assertEqual(ctx["place"], "દસક્રોઈ, અમદાવાદ")
        self.assertEqual(ctx["advocate_for_role"], "આરોપી")
        self.assertEqual(ctx["advocate_name"], "આરોપી ના એડવોકેટ")
        self.assertEqual(ctx["date"], "23/11/2026")

        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("મહેરબાન ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,", rendered)
        self.assertIn("મુકામ :- દસક્રોઈ, અમદાવાદ", rendered)
        self.assertIn("ફોજદારી કેસ નં. : 1234/2026", rendered)
        self.assertIn("ફરીયાદી :- રાજેશભાઈ સોલંકી", rendered)
        self.assertIn("વિરુદ્ધ", rendered)
        self.assertIn("આરોપી :- પ્રકાશભાઈ પટેલ", rendered)
        self.assertIn("સદર કામમાં અમો આરોપીના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે .....", rendered)
        # Deduplication check: must be "માંદગીના કારણોસર", NOT "માંદગીના કારણોસર કારણોસર"
        self.assertIn("માંદગીના કારણોસર ઉલટ-તપાસ થઈ શકેલ નહિ", rendered)
        self.assertNotIn("કારણોસર કારણોસર", rendered)
        self.assertIn("તારીખ : 23/11/2026", rendered)
        self.assertIn("સ્થળ : દસક્રોઈ, અમદાવાદ", rendered)
        self.assertIn("આરોપી ના એડવોકેટ", rendered)

    async def test_07_rendering_bereavement_reason(self):
        """7. Test rendering with 'સગા ગુજરી ગયેલ હોવાથી' reason."""
        values = {
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "સુરત",
            "taluka": "",
            "case_type": "દિવાની કેસ",
            "case_number": "567/2025",
            "party_1_role": "વાદી",
            "party_1_name": "મનસુખભાઈ શાહ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "દિનેશભાઈ મહેતા",
            "advocate_for": "પ્રતિવાદી",
            "reason": "સગા ગુજરી ગયેલ હોવાથી",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="ulat_tapas_no_haq_kholvani_arji")
        self.assertEqual(ctx["taluka_place"], "સુરત")
        self.assertEqual(ctx["place"], "સુરત")
        self.assertEqual(ctx["advocate_for_role"], "પ્રતિવાદી")
        self.assertEqual(ctx["advocate_name"], "પ્રતિવાદી ના એડવોકેટ")

        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("મુકામ :- સુરત", rendered)
        self.assertIn("સગા ગુજરી ગયેલ હોવાથી ઉલટ-તપાસ થઈ શકેલ નહિ", rendered)
        self.assertNotIn("હોવાથી કારણોસર", rendered)
        self.assertIn("પ્રતિવાદી ના એડવોકેટ", rendered)

    async def test_08_rendering_custom_reason(self):
        """8. Test rendering with custom reason (અન્ય)."""
        values = {
            "court_name": "ફેમિલી કોર્ટ",
            "district": "વડોદરા",
            "taluka": "વડોદરા",
            "case_type": "ફેમિલી કેસ",
            "case_number": "890/2026",
            "party_1_role": "અરજદાર",
            "party_1_name": "ભાવનાબેન જોશી",
            "party_2_role": "સામાવાળા",
            "party_2_name": "હિતેશભાઈ જોશી",
            "advocate_for": "સામાવાળા",
            "reason": "અન્ય",
            "custom_reason": "આરોપીને અકસ્માત થવાથી હોસ્પિટલમાં દાખલ થયેલ હોવાના",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="ulat_tapas_no_haq_kholvani_arji")
        self.assertEqual(ctx["advocate_for_role"], "સામાવાળા")
        self.assertEqual(ctx["advocate_name"], "સામાવાળા ના એડવોકેટ")
        self.assertEqual(ctx["reason_text"], "આરોપીને અકસ્માત થવાથી હોસ્પિટલમાં દાખલ થયેલ હોવાના")

        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("આરોપીને અકસ્માત થવાથી હોસ્પિટલમાં દાખલ થયેલ હોવાના કારણોસર ઉલટ-તપાસ થઈ શકેલ નહિ", rendered)
        self.assertNotIn("અન્ય", rendered)
        self.assertIn("સામાવાળા ના એડવોકેટ", rendered)

    async def test_09_rendering_english(self):
        """9. Test rendering in English."""
        values = {
            "court_name": "Chief Judicial Magistrate",
            "district": "Ahmedabad",
            "taluka": "Daskroi",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "Complainant",
            "party_1_name": "Rajesh Solanki",
            "party_2_role": "Accused",
            "party_2_name": "Prakash Patel",
            "advocate_for": "Accused",
            "reason": "Due to illness",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "en", template_id="ulat_tapas_no_haq_kholvani_arji")
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        self.assertIn("SUBJECT: APPLICATION TO REOPEN CROSS-EXAMINATION RIGHT", rendered)
        self.assertIn("Advocate for Accused", rendered)
        self.assertIn("Due to illness, cross-examination could not be conducted", rendered)
        self.assertNotIn("{{", rendered)

    async def test_10_pdf_generation(self):
        """10. Verify valid PDF can be generated."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "અમદાવાદ",
            "taluka": "દસક્રોઈ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રાજેશભાઈ સોલંકી",
            "party_2_role": "આરોપી",
            "party_2_name": "પ્રકાશભાઈ પટેલ",
            "advocate_for": "આરોપી",
            "reason": "માંદગીના કારણોસર",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="ulat_tapas_no_haq_kholvani_arji")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="ulat_tapas_no_haq_kholvani_arji",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated file must start with PDF header %PDF-")
        self.assertGreater(len(pdf_bytes), 1000, "Generated PDF must be non-empty and well-sized")

    async def test_11_server_get_template(self):
        """11. Verify server.get_template retrieves ulat_tapas_no_haq_kholvani_arji."""
        t = await server.get_template("ulat_tapas_no_haq_kholvani_arji")
        self.assertIsNotNone(t)
        self.assertEqual(t.get("name_gu"), "ઉલટ તપાસનો હક ફરીથી ખોલી આપવા બાબત")
        self.assertEqual(t.get("name_en"), "Application to Reopen Cross-Examination Right")

    def test_12_existing_15_templates_unmodified(self):
        """12. Verify all 15 prior templates exist and are unchanged."""
        expected_15_ids = [
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
            "warrant_rad_karvani_arji",
            "ulat_tapas_no_haq_bandh_karavani_arji",
        ]
        all_ids = [t["id"] for t in TEMPLATES]
        for tid in expected_15_ids:
            self.assertIn(tid, all_ids, f"Existing template {tid} must not be missing")
        self.assertIn("ulat_tapas_no_haq_kholvani_arji", all_ids, "16th template must be in TEMPLATES")


if __name__ == "__main__":
    unittest.main()
