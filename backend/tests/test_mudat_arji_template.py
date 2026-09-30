# -*- coding: utf-8 -*-
import os
import re
import unittest
import base64
import io
import sys
import asyncio
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


class TestMudatArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "mudat_arji"), None)
        self.assertIsNotNone(self.tpl, "mudat_arji template must be present in TEMPLATES")

    def test_01_template_exists_and_active(self):
        """1. Verify template exists, is active, and has canonical metadata."""
        self.assertEqual(self.tpl["id"], "mudat_arji")
        self.assertEqual(self.tpl["name_gu"], "મુદત અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Adjournment")
        self.assertEqual(self.tpl.get("category"), "General")
        self.assertTrue(self.tpl.get("is_active"))
        aliases = self.tpl.get("aliases", [])
        self.assertIn("મુદત અરજી", aliases)
        self.assertIn("mudat arji", aliases)
        self.assertIn("Adjournment Application", aliases)
        self.assertIn("Application for Adjournment", aliases)

        canonical = server._get_canonical_mudat_arji_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "mudat_arji")

    def test_02_field_count_is_exactly_15(self):
        """2. Verify template has exactly 15 advocate-facing fields."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 15, f"Expected exactly 15 fields, found {len(fields)}")

    def test_03_field_order_and_canonical_types(self):
        """3. Verify exact field keys, sequence, and types matching Page 1 of canonical PDF."""
        fields = self.tpl.get("fields", [])
        expected_fields = [
            ("court_name", "select"),
            ("district", "select"),
            ("taluka", "select"),
            ("case_type", "select"),
            ("case_number", "text"),
            ("party_1_role", "radio"),
            ("party_1_name", "text"),
            ("party_2_role", "radio"),
            ("party_2_name", "text"),
            ("advocate_for", "select"),
            ("adjournment_reason", "select"),
            ("other_adjournment_reason", "textarea"),
            ("date", "date"),
            ("place", "text"),
            ("advocate_name", "text"),
        ]
        self.assertEqual(len(fields), len(expected_fields))
        for i, (expected_key, expected_type) in enumerate(expected_fields):
            f = fields[i]
            self.assertEqual(f.get("key"), expected_key, f"Field index {i} mismatch: expected {expected_key}, got {f.get('key')}")
            self.assertEqual(f.get("type"), expected_type, f"Field type mismatch for {expected_key}: expected {expected_type}, got {f.get('type')}")

    def test_04_party_roles_options(self):
        """4. Verify radio options for party 1 and party 2 roles."""
        fields_dict = {f["key"]: f for f in self.tpl.get("fields", [])}
        p1 = fields_dict.get("party_1_role")
        p2 = fields_dict.get("party_2_role")

        p1_opts = [o.get("value", o) if isinstance(o, dict) else o for o in p1.get("options", [])]
        p2_opts = [o.get("value", o) if isinstance(o, dict) else o for o in p2.get("options", [])]

        self.assertEqual(p1_opts, ["ફરીયાદી", "અરજદાર", "વાદી"])
        self.assertEqual(p2_opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

    def test_05_adjournment_reason_options(self):
        """5. Verify exact 8 adjournment reason options matching Page 1."""
        fields_dict = {f["key"]: f for f in self.tpl.get("fields", [])}
        reason_field = fields_dict.get("adjournment_reason")
        self.assertIsNotNone(reason_field)
        opts = [o.get("value", o) if isinstance(o, dict) else o for o in reason_field.get("options", [])]
        expected_reasons = [
            "અનિવાર્ય સંજોગોના",
            "પુરાવા તૈયાર કરવાના બાકી હોવાના",
            "કેસ વિશે પુરતો અભ્યાસ કરવાનો બાકી હોવાના",
            "બહારગામ ગયેલ હોવાના",
            "માંદગીના",
            "સામાજીક કાર્યોમા રોકાયેલ હોવાના",
            "બીજી કોર્ટમાં રોકાયેલ હોવાના",
            "અન્ય",
        ]
        self.assertEqual(opts, expected_reasons)

    def test_06_exact_verbatim_content_gu(self):
        """6. Verify exact Gujarati legal wording in content_gu matching Page 2."""
        c = self.tpl.get("content_gu", "")
        # Subject line
        self.assertIn("બાબત :- મુદ્દત આપવા બાબત...", c)
        # Paragraph 1
        self.assertIn("સદર કામમાં અમો {{advocate_for_role}}ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......", c)
        # Paragraph 2
        p2_expected = (
            "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેની મુદ્દત આજ રોજની છે પરંતુ સદર કામમાં "
            "અમો આજરોજ {{adjournment_reason}} કારણોસર ન્યાયિક કાર્યવાહી આજરોજ પુરતી આગળ ચલાવી શકીએ તેમ ન હોઈ, "
            "સદરહુ કામમાં આજરોજ કેસ આગળ ન ચલાવવા ન્યાયના હિતમાં એક મુદ્દત આપી યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી."
        )
        self.assertIn(p2_expected, c)

    def test_07_layout_and_typography_settings(self):
        """7. Verify layout and typography settings match canonical court rules."""
        s = self.tpl.get("settings", {})
        self.assertEqual(s.get("page_size"), "A4")
        self.assertAlmostEqual(s.get("margin_left_cm"), 4.0, delta=0.05)
        self.assertAlmostEqual(s.get("margin_right_cm"), 4.0, delta=0.05)
        self.assertAlmostEqual(s.get("margin_top_cm"), 2.0, delta=0.05)
        self.assertAlmostEqual(s.get("margin_bottom_cm"), 2.0, delta=0.05)

        self.assertEqual(s.get("font_family"), "Lohit Gujarati")
        self.assertEqual(s.get("gujarati_font_docx"), "Lohit Gujarati")
        self.assertEqual(s.get("english_font_docx"), "Times New Roman")
        self.assertEqual(s.get("body_size"), 13)
        self.assertEqual(s.get("heading_size"), 15)
        self.assertEqual(s.get("body_size_en"), 14)
        self.assertEqual(s.get("heading_size_en"), 16)
        self.assertEqual(s.get("line_spacing"), 18.0)
        self.assertEqual(s.get("paragraph_spacing"), 6.0)
        self.assertAlmostEqual(s.get("first_line_indent_pt"), 28.35, delta=0.05)

    def test_08_build_render_context_dynamic_place_with_taluka(self):
        """8. Verify dynamic place derivation with taluka and district."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "અમદાવાદ",
            "taluka": "દસક્રોઈ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_1",
            "adjournment_reason": "માંદગીના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx.get("place"), "દસક્રોઈ, અમદાવાદ")
        self.assertEqual(ctx.get("advocate_for_role"), "ફરીયાદી")
        self.assertEqual(ctx.get("advocate_name"), "ફરીયાદી ના એડવોકેટ")

    def test_09_build_render_context_dynamic_place_without_taluka(self):
        """9. Verify dynamic place derivation without taluka defaults to district."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "પ્રિન્સિપાલ સીનીયર સીવીલ જજ સાહેબની કોર્ટ",
            "district": "સુરત",
            "taluka": "",
            "case_type": "સ્પેશિયલ દિવાની મુકદ્દમો",
            "case_number": "૫૫/૨૦૨૪",
            "party_1_role": "વાદી",
            "party_1_name": "કિરીટભાઈ મહેતા",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "હસમુખભાઈ પ્રજાપતિ",
            "advocate_for": "party_1",
            "adjournment_reason": "બહારગામ ગયેલ હોવાના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx.get("place"), "સુરત")
        self.assertEqual(ctx.get("advocate_for_role"), "વાદી")
        self.assertEqual(ctx.get("advocate_name"), "વાદી ના એડવોકેટ")

    def test_10_build_render_context_advocate_designation(self):
        """10. Verify advocate designation matches selected party role."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "રાજકોટ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૨૦૨/૨૦૨૪",
            "party_1_role": "અરજદાર",
            "party_1_name": "અરજદાર પક્ષ",
            "party_2_role": "સામાવાળા",
            "party_2_name": "સામાવાળા પક્ષ",
            "advocate_for": "party_2",
            "adjournment_reason": "અનિવાર્ય સંજોગોના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx.get("advocate_for_role"), "સામાવાળા")
        self.assertEqual(ctx.get("advocate_name"), "સામાવાળા ના એડવોકેટ")

    def test_11_build_render_context_predefined_reason(self):
        """11. Verify predefined reason flows properly in Gujarati and maps to English."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "અમદાવાદ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "adjournment_reason": "માંદગીના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx_gu = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx_gu.get("adjournment_reason"), "માંદગીના")

        ctx_en = asyncio.run(server.build_render_context(user, None, raw_vals, "en"))
        self.assertEqual(ctx_en.get("adjournment_reason"), "illness")

    def test_12_build_render_context_custom_reason(self):
        """12. Verify custom reason when 'અન્ય' is selected."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "અમદાવાદ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "adjournment_reason": "અન્ય",
            "other_adjournment_reason": "પક્ષકારો વચ્ચે સમાધાનની વાતચીત ચાલી રહેલ હોવાના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx_gu = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx_gu.get("adjournment_reason"), "પક્ષકારો વચ્ચે સમાધાનની વાતચીત ચાલી રહેલ હોવાના")

    def test_13_build_render_context_leak_prevention_switch_away_from_custom(self):
        """13. Verify custom reason is cleared/ignored if user switches back to predefined reason."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "અમદાવાદ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "adjournment_reason": "બહારગામ ગયેલ હોવાના",
            "other_adjournment_reason": "પક્ષકારો વચ્ચે સમાધાનની વાતચીત ચાલી રહેલ હોવાના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx_gu = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        self.assertEqual(ctx_gu.get("adjournment_reason"), "બહારગામ ગયેલ હોવાના")

    def test_14_pdf_generation_gujarati(self):
        """14. Verify full Gujarati PDF generation succeeds and outputs valid PDF."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "ચીફ જ્યુડીશ્યલ મેજીસ્ટ્રેટ સાહેબની કોર્ટ",
            "district": "અમદાવાદ",
            "taluka": "દસક્રોઈ",
            "case_type": "ક્રિમીનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "adjournment_reason": "માંદગીના",
            "date": "૩૦/૦૯/૨૦૨૬",
        }
        ctx = asyncio.run(server.build_render_context(user, None, raw_vals, "gu"))
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(
            rendered,
            self.tpl["name_en"],
            self.tpl["name_gu"],
            self.tpl.get("settings", {}).get("block_align"),
        )
        pdf_b64, meta = doc_generator.generate_pdf_detailed(
            blocks,
            language="gu",
            settings=self.tpl.get("settings"),
            template_id="mudat_arji",
            raw_content=rendered,
            ctx=ctx,
        )
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_15_pdf_generation_english(self):
        """15. Verify full English PDF generation succeeds and outputs valid PDF."""
        user = {"advocate_name_en": "Ronak Solanki"}
        raw_vals = {
            "template_id": "mudat_arji",
            "court_name": "Court of Chief Judicial Magistrate",
            "district": "Ahmedabad",
            "taluka": "Daskroi",
            "case_type": "Criminal Case",
            "case_number": "101/2024",
            "party_1_role": "Complainant",
            "party_1_name": "Rameshbhai Patel",
            "party_2_role": "Accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "party_2",
            "adjournment_reason": "illness",
            "date": "30/09/2026",
        }
        ctx = asyncio.run(server.build_render_context(user, None, raw_vals, "en"))
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        blocks = doc_generator.build_blocks(
            rendered,
            self.tpl["name_en"],
            self.tpl["name_gu"],
            self.tpl.get("settings", {}).get("block_align"),
        )
        pdf_b64, meta = doc_generator.generate_pdf_detailed(
            blocks,
            language="en",
            settings=self.tpl.get("settings"),
            template_id="mudat_arji",
            raw_content=rendered,
            ctx=ctx,
        )
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 1000)

    def test_16_deleted_template_ids_protection(self):
        """16. Verify mudat_arji is protected from tombstoning."""
        deleted = asyncio.run(server._get_deleted_template_ids())
        self.assertNotIn("mudat_arji", deleted)

    def test_17_published_templates_includes_mudat_arji(self):
        """17. Verify _get_published_templates includes mudat_arji."""
        published = asyncio.run(server._get_published_templates())
        m = next((t for t in published if t.get("id") == "mudat_arji"), None)
        self.assertIsNotNone(m)
        self.assertEqual(len(m.get("fields", [])), 15)

    def test_18_get_template_by_id_heals_mudat_arji(self):
        """18. Verify _get_template_by_id heals and returns mudat_arji."""
        t = asyncio.run(server._get_template_by_id("mudat_arji"))
        self.assertIsNotNone(t)
        self.assertEqual(t.get("id"), "mudat_arji")
        self.assertEqual(len(t.get("fields", [])), 15)

    def test_19_english_content_fidelity(self):
        """19. Verify English content matches court standards for Adjournment Application."""
        c = self.tpl.get("content_en", "")
        self.assertIn("Subject :- Application for Adjournment ...", c)
        self.assertIn("Advocate for {{advocate_for_role}}", c)
        self.assertIn("{{adjournment_reason}}", c)
        self.assertIn("grant an adjournment", c)


if __name__ == "__main__":
    unittest.main()
