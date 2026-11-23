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


class TestSamadhanPurshishTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "samadhan_purshish"), None)
        self.assertIsNotNone(self.tpl, "samadhan_purshish template must be present in TEMPLATES")
        self.user = {"name": "Test Advocate", "advocate_name_gu": "ટેસ્ટ એડવોકેટ", "advocate_name_en": "Test Advocate"}

    def test_01_template_identity_and_names(self):
        """1. Verify template ID registration and identity."""
        self.assertEqual(self.tpl["id"], "samadhan_purshish")
        self.assertEqual(self.tpl["name_gu"], "સમાધાન પુરસીસ")
        self.assertEqual(self.tpl["name_en"], "Settlement Purshish / Settlement Memo")
        self.assertEqual(self.tpl.get("category"), "General")
        aliases = self.tpl.get("aliases", [])
        self.assertIn("samadhan", aliases)
        self.assertIn("compromise_purshish", aliases)
        self.assertIn("settlement_purshish", aliases)
        self.assertIn("settlement_memo", aliases)
        self.assertIn("સમાધાન પુરસીસ", aliases)

    def test_02_canonical_resolution(self):
        """2. Verify canonical ID aliases and language variants resolution."""
        for cand in [
            "samadhan_purshish",
            "samadhan_purshish_gu",
            "samadhan_purshish_en",
            "samadhan",
            "compromise_purshish",
            "settlement_purshish",
            "settlement_memo",
            "સમાધાન પુરસીસ",
            "સમાધાન પુરશીસ",
        ]:
            self.assertEqual(
                server.resolve_canonical_template_id(cand),
                "samadhan_purshish",
                f"Failed canonical resolution for {cand}"
            )

    def test_03_fields_structure(self):
        """3. Verify 13 standard fields structure and configurations."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 13, f"Expected 13 fields, got {len(fields)}")
        field_keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "date", "place", "advocate_name"
        ]
        self.assertEqual(field_keys, expected_keys)

        # Check party_1_role options
        p1 = next(f for f in fields if f["key"] == "party_1_role")
        p1_opts = [o.get("value") or o for o in p1.get("options", [])]
        self.assertIn("ફરીયાદી", p1_opts)
        self.assertIn("અરજદાર", p1_opts)
        self.assertIn("વાદી", p1_opts)

        # Check party_2_role options
        p2 = next(f for f in fields if f["key"] == "party_2_role")
        p2_opts = [o.get("value") or o for o in p2.get("options", [])]
        self.assertIn("આરોપી", p2_opts)
        self.assertIn("સામાવાળા", p2_opts)
        self.assertIn("પ્રતિવાદી", p2_opts)

        # Check advocate_for options
        adv_for = next(f for f in fields if f["key"] == "advocate_for")
        adv_opts = [o.get("value") or o for o in adv_for.get("options", [])]
        self.assertIn("ફરીયાદી", adv_opts)
        self.assertIn("અરજદાર", adv_opts)
        self.assertIn("વાદી", adv_opts)
        self.assertIn("આરોપી", adv_opts)
        self.assertIn("સામાવાળા", adv_opts)
        self.assertIn("પ્રતિવાદી", adv_opts)

        # Check date, place, advocate_name
        self.assertFalse(next(f for f in fields if f["key"] == "date")["required"])
        self.assertFalse(next(f for f in fields if f["key"] == "place")["required"])
        self.assertFalse(next(f for f in fields if f["key"] == "advocate_name")["required"])

    def test_04_display_order_and_unmasking(self):
        """4. Verify template order is position #17 and unmasked from deleted_ids."""
        order = server._SETTING_DEFAULTS.get("template_display_order", [])
        self.assertIn("samadhan_purshish", order)
        self.assertEqual(order[16], "samadhan_purshish", "samadhan_purshish must be at display position #17 (0-indexed 16)")

    async def test_05_gujarati_draft_rendering(self):
        """5. Verify exact legal Gujarati draft text renders properly."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "અમદાવાદ",
            "taluka": "",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ કાંતિભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ બાબુભાઈ શાહ",
            "advocate_for": "આરોપી",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="samadhan_purshish")
        draft_text = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ", draft_text)
        self.assertIn("મુકામ :- અમદાવાદ", draft_text)
        self.assertIn("ફોજદારી કેસ નં. : 1234/2026", draft_text)
        self.assertIn("ફરીયાદી :- રમેશભાઈ કાંતિભાઈ પટેલ", draft_text)
        self.assertIn("વિરુદ્ધ", draft_text)
        self.assertIn("આરોપી :- સુરેશભાઈ બાબુભાઈ શાહ", draft_text)
        self.assertIn("સમાધાન પુરસીસ", draft_text)
        self.assertIn("સદર કામમા અમો આરોપીના એડવોકેટ આપ નામદાર કોર્ટમાં પુરસીસ થી જાહેર કરીએ છીએ કે .....", draft_text)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે.", draft_text)
        self.assertIn("સદર કેસના પક્ષકારો વચ્ચે પરસ્પર સમાધાન થયેલ છે.", draft_text)
        self.assertIn("બંને પક્ષકારોએ પોતાની સ્વતંત્ર ઇચ્છાથી તથા કોઈપણ જાતના દબાણ, ધાકધમકી કે લાલચ વગર સમાધાન કરેલ છે અને સમાધાન મુજબ આગળની કાર્યવાહી કરવા બંને પક્ષકારો સંમત છે.", draft_text)
        self.assertIn("સદર સમાધાન પુરસીસ રેકોર્ડ પર લઈ યોગ્ય કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશો જી.", draft_text)
        self.assertIn("તારીખ : 23/11/2026", draft_text)
        self.assertIn("સ્થળ : અમદાવાદ", draft_text)
        self.assertIn("આરોપી ના એડવોકેટ", draft_text)

    async def test_06_english_draft_rendering(self):
        """6. Verify English draft text renders properly."""
        values = {
            "court_name": "Court of Additional Chief Judicial Magistrate",
            "district": "Ahmedabad",
            "taluka": "",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "Complainant",
            "party_1_name": "Rameshbhai K. Patel",
            "party_2_role": "Accused",
            "party_2_name": "Sureshbhai B. Shah",
            "advocate_for": "Accused",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "en", template_id="samadhan_purshish")
        draft_text = doc_generator.render_template(self.tpl["content_en"], ctx)
        self.assertIn("SETTLEMENT PURSHISH / MEMO", draft_text)
        self.assertIn("Complainant :- Rameshbhai K. Patel", draft_text)
        self.assertIn("Accused :- Sureshbhai B. Shah", draft_text)
        self.assertIn("An amicable settlement has been arrived at between the parties to the said case", draft_text)
        self.assertIn("Advocate for Accused", draft_text)

    async def test_07_build_render_context_taluka_district(self):
        """7. Verify build_render_context place formatting for District and Taluka."""
        values = {
            "district": "અમદાવાદ",
            "taluka": "દસ્ક્રોઈ",
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "case_type": "દીવાની કેસ",
            "case_number": "567/2026",
            "party_1_role": "વાદી",
            "party_1_name": "પક્ષકાર ૧",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "પક્ષકાર ૨",
            "advocate_for": "વાદી",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="samadhan_purshish")
        self.assertEqual(ctx["place"], "દસ્ક્રોઈ, અમદાવાદ")
        self.assertEqual(ctx["taluka_place"], "દસ્ક્રોઈ, અમદાવાદ")
        self.assertEqual(ctx["advocate_for_role"], "વાદી")
        self.assertEqual(ctx["advocate_name"], "વાદી ના એડવોકેટ")

    async def test_08_advocate_designation_mapping(self):
        """8. Verify advocate designation mapping for all roles."""
        for role, expected_gu, expected_en in [
            ("ફરીયાદી", "ફરીયાદી ના એડવોકેટ", "Advocate for Complainant"),
            ("અરજદાર", "અરજદાર ના એડવોકેટ", "Advocate for Applicant"),
            ("વાદી", "વાદી ના એડવોકેટ", "Advocate for Plaintiff"),
            ("આરોપી", "આરોપી ના એડવોકેટ", "Advocate for Accused"),
            ("સામાવાળા", "સામાવાળા ના એડવોકેટ", "Advocate for Opponent"),
            ("પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ", "Advocate for Defendant"),
        ]:
            val = {
                "district": "રાજકોટ",
                "court_name": "સિવિલ કોર્ટ",
                "case_type": "દીવાની કેસ",
                "case_number": "999/2026",
                "party_1_role": "વાદી",
                "party_1_name": "વાદી ૧",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "પ્રતિવાદી ૧",
                "advocate_for": role,
                "date": "2026-11-23",
            }
            ctx_gu = await server.build_render_context(self.user, None, val, "gu", template_id="samadhan_purshish")
            self.assertEqual(ctx_gu["advocate_name"], expected_gu)

            ctx_en = await server.build_render_context(self.user, None, val, "en", template_id="samadhan_purshish")
            self.assertEqual(ctx_en["advocate_name"], expected_en)

    async def test_09_pdf_generation(self):
        """9. Verify PDF generation executes without errors and generates valid PDF."""
        values = {
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ સાહેબશ્રીની કોર્ટ",
            "district": "અમદાવાદ",
            "taluka": "સાણંદ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "1234/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "હસમુખભાઈ મોહનભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "ભરતભાઈ નારણભાઈ પરમાર",
            "advocate_for": "આરોપી",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="samadhan_purshish")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(
            blocks,
            language="gu",
            settings=self.tpl["settings"],
            template_id="samadhan_purshish",
        )
        self.assertIsInstance(pdf_b64, str)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated file must start with PDF header %PDF-")
        self.assertGreater(len(pdf_bytes), 1000, "Generated PDF must be non-empty and well-sized")

    async def test_10_api_get_template_by_id(self):
        """10. Verify server._get_template_by_id returns canonical template."""
        res = await server._get_template_by_id("samadhan_purshish")
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], "samadhan_purshish")
        self.assertEqual(res["name_gu"], "સમાધાન પુરસીસ")
        self.assertEqual(len(res["fields"]), 13)

        # Check aliases
        res_alias = await server._get_template_by_id("samadhan")
        self.assertIsNotNone(res_alias)
        self.assertEqual(res_alias["id"], "samadhan_purshish")

    def test_11_preservation_of_all_16_existing_templates(self):
        """11. Verify all previous 16 templates are preserved in TEMPLATES."""
        all_ids = [t.get("id") for t in TEMPLATES]
        expected_16 = [
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
            "ulat_tapas_no_haq_kholvani_arji",
        ]
        for tid in expected_16:
            self.assertIn(tid, all_ids, f"Template {tid} missing from TEMPLATES")
        self.assertIn("samadhan_purshish", all_ids)

    async def test_12_clean_cleanup_placeholders(self):
        """12. Verify doc_generator cleans unreplaced placeholders."""
        values = {
            "court_name": "કોર્ટ",
            "district": "અમદાવાદ",
            "taluka": "",
            "case_type": "કેસ",
            "case_number": "1/2026",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "નામ ૧",
            "party_2_role": "આરોપી",
            "party_2_name": "નામ ૨",
            "advocate_for": "આરોપી",
            "date": "2026-11-23",
        }
        ctx = await server.build_render_context(self.user, None, values, "gu", template_id="samadhan_purshish")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("}}", rendered)


if __name__ == "__main__":
    unittest.main()
