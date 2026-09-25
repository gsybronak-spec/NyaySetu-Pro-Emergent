# -*- coding: utf-8 -*-
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


class TestExemptionArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "exemption_arji"), None)
        self.assertIsNotNone(self.tpl, "exemption_arji template must be present in TEMPLATES")

    def test_01_template_exists_and_active(self):
        """1. Verify template exists, is active, and has canonical metadata."""
        self.assertEqual(self.tpl["id"], "exemption_arji")
        self.assertEqual(self.tpl["name_gu"], "હાજરી મુક્તિ આપવા બાબત... (એક્ઝામ્પ્શન રીપોર્ટ)")
        self.assertEqual(self.tpl["name_en"], "Application for Exemption from Personal Appearance (Exemption Report)")
        self.assertEqual(self.tpl.get("category"), "Criminal")
        self.assertTrue(self.tpl.get("is_active"))
        aliases = self.tpl.get("aliases", [])
        self.assertIn("હાજરી મુક્તિ આપવા બાબત... (એક્ઝામ્પ્શન રીપોર્ટ)", aliases)
        self.assertIn("exemption arji", aliases)

        canonical = server._get_canonical_exemption_arji_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "exemption_arji")

    def test_02_field_count_is_exactly_14(self):
        """2. Verify template has exactly 14 advocate-facing fields."""
        fields = self.tpl.get("fields", [])
        self.assertEqual(len(fields), 14, f"Expected exactly 14 fields, found {len(fields)}")

    def test_03_field_order_and_canonical_types(self):
        """3. Verify exact field keys, sequence, and types matching Page 1 of canonical PDF."""
        fields = self.tpl.get("fields", [])
        keys = [f["key"] for f in fields]
        expected_keys = [
            "court_name", "district", "taluka", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "advocate_for", "absence_reason",
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
            "absence_reason": "select",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for f in fields:
            self.assertEqual(f["type"], expected_types[f["key"]], f"Field {f['key']} type mismatch")

    def test_04_all_14_fields_have_required_false(self):
        """4. Verify all 14 fields have required: False."""
        for f in self.tpl["fields"]:
            self.assertFalse(f.get("required"), f"Field {f['key']} must have required=False")

    def test_05_party_1_role_options(self):
        """5. Verify party_1_role options: ફરીયાદી, અરજદાર, વાદી."""
        f = next(f for f in self.tpl["fields"] if f["key"] == "party_1_role")
        opts = [o["label_gu"] if isinstance(o, dict) else o for o in f["options"]]
        self.assertEqual(opts, ["ફરીયાદી", "અરજદાર", "વાદી"])

    def test_06_party_2_role_options(self):
        """6. Verify party_2_role options: આરોપી, સામાવાળા, પ્રતિવાદી."""
        f = next(f for f in self.tpl["fields"] if f["key"] == "party_2_role")
        opts = [o["label_gu"] if isinstance(o, dict) else o for o in f["options"]]
        self.assertEqual(opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

    def test_07_absence_reason_dropdown_options(self):
        """7. Verify absence_reason has exactly 6 canonical options character-for-character."""
        f = next(f for f in self.tpl["fields"] if f["key"] == "absence_reason")
        opts = [o["label_gu"] if isinstance(o, dict) else o for o in f["options"]]
        expected_options = [
            "અનિવાર્ય સંજોગોના",
            "બહારગામ ગયેલ હોવાના",
            "માંદગીના",
            "સામાજીક કાર્યોમા રોકાયેલ હોવાના",
            "બીજી કોર્ટમા પણ મુદ્દત હોય જેથી બીજી કોર્ટમા ગયેલ હોવાના",
            "અન્ય",
        ]
        self.assertEqual(len(opts), 6)
        self.assertEqual(opts, expected_options)

    def test_08_advocate_for_options(self):
        """8. Verify advocate_for options include party roles."""
        f = next(f for f in self.tpl["fields"] if f["key"] == "advocate_for")
        vals = [o["value"] for o in f["options"]]
        self.assertTrue("આરોપી" in vals or "party_2" in vals)
        self.assertTrue("ફરીયાદી" in vals or "party_1" in vals)

    def test_09_place_and_advocate_name_readonly(self):
        """9. Verify place and advocate_name have readonly=True."""
        f_place = next(f for f in self.tpl["fields"] if f["key"] == "place")
        f_adv = next(f for f in self.tpl["fields"] if f["key"] == "advocate_name")
        self.assertTrue(f_place.get("readonly"))
        self.assertTrue(f_adv.get("readonly"))

    def test_10_taluka_place_both_present(self):
        """10. Verify place is derived as [Taluka], [District] when both are present."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_2",
            "absence_reason": "માંદગીના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "કલોલ, ગાંધીનગર")

    def test_11_taluka_blank_district_only(self):
        """11. Verify place is derived as [District] when taluka is blank."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "district": "ગાંધીનગર",
            "taluka": "",
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "party_1",
            "absence_reason": "અનિવાર્ય સંજોગોના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["place"], "ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "ગાંધીનગર")

    def test_12_advocate_for_party_2_accused_auto_flow(self):
        """12. Verify advocate_for role auto-flow for party_2 (આરોપી)."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "district": "ગાંધીનગર",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_2",
            "absence_reason": "માંદગીના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["advocate_for_role"], "આરોપી")
        self.assertEqual(ctx["advocate_name"], "આરોપી ના એડવોકેટ")

    def test_13_advocate_for_party_1_complainant_auto_flow(self):
        """13. Verify advocate_for role auto-flow for party_1 (ફરીયાદી)."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "district": "અમદાવાદ",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_1",
            "absence_reason": "બહારગામ ગયેલ હોવાના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["advocate_for_role"], "ફરીયાદી")
        self.assertEqual(ctx["advocate_name"], "ફરીયાદી ના એડવોકેટ")

    def test_14_absence_reason_custom_substitution(self):
        """14. Verify custom absence reason substitutes correctly when 'અન્ય' is selected."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "district": "સુરત",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_2",
            "absence_reason": "અન્ય",
            "absence_reason_custom": "ટ્રેન મોડી પડવાના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["absence_reason"], "ટ્રેન મોડી પડવાના")

    def test_15_absence_reason_english_mapping(self):
        """15. Verify Gujarati absence reasons map to English legal phrasing in English context."""
        user = {"advocate_name_en": "Ronak Solanki"}
        values = {
            "template_id": "exemption_arji",
            "district": "Gandhinagar",
            "party_1_role": "complainant",
            "party_2_role": "accused",
            "advocate_for": "party_2",
            "absence_reason": "અનિવાર્ય સંજોગોના",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "en"))
        self.assertEqual(ctx["absence_reason"], "unavoidable circumstances")
        self.assertEqual(ctx["advocate_for_role"], "Accused")
        self.assertEqual(ctx["advocate_name"], "Advocate for Accused")

    def test_16_canonical_gujarati_body_content(self):
        """16. Verify exact Gujarati legal wording in content_gu."""
        content_gu = self.tpl["content_gu"]
        self.assertIn("બાબત :- હાજરી મુક્તિ આપવા બાબત... (એક્ઝામ્પ્શન રીપોર્ટ)", content_gu)
        self.assertIn("સદર કામમાં અમો {{advocate_for_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...", content_gu)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેની મુદ્દત આજ રોજની છે પરંતુ સદર કામના {{advocate_for_role}} આજરોજ {{absence_reason}} કારણોસર આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકે તેમ નથી. જેથી આજના દિવસ પૂરતી {{advocate_for_role}}ની વ્યક્તિગત હાજરી માફ રાખી સદર કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", content_gu)
        self.assertIn("મહેરબાન {{court_name}} સાહેબશ્રીની કોર્ટમાં,", content_gu)
        self.assertIn("મુકામ :- {{place}}", content_gu)
        self.assertIn("તારીખ : {{date}}", content_gu)
        self.assertIn("સ્થળ : {{place}}", content_gu)
        self.assertIn("----------", content_gu)

    def test_17_page_settings_and_typography(self):
        """17. Verify margins 4cm/4cm/2cm/2cm, A4 size, and typography."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("page_size"), "A4")
        self.assertEqual(settings.get("margin_left_cm"), 4.0)
        self.assertEqual(settings.get("margin_right_cm"), 4.0)
        self.assertEqual(settings.get("margin_top_cm"), 2.0)
        self.assertEqual(settings.get("margin_bottom_cm"), 2.0)

    def test_18_render_full_gujarati_document(self):
        """18. Verify end-to-end Gujarati document generation (PDF bytes returned)."""
        user = {"advocate_name_gu": "રોનક એ. સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "૧૨૩૪/૨૦૨૬",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "મહેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "absence_reason": "માંદગીના",
            "date": "25/09/2026",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu", template_id="exemption_arji"))
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(blocks, "gu", self.tpl["settings"])
        self.assertIsNotNone(pdf_b64)
        self.assertGreater(len(pdf_b64), 100)
        raw_pdf = base64.b64decode(pdf_b64)
        self.assertTrue(raw_pdf.startswith(b"%PDF"))

    def test_19_render_full_english_document(self):
        """19. Verify end-to-end English document generation (PDF bytes returned)."""
        user = {"advocate_name_en": "Ronak A. Solanki"}
        values = {
            "template_id": "exemption_arji",
            "court_name": "Chief Judicial Magistrate",
            "district": "Gandhinagar",
            "taluka": "Kalol",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "complainant",
            "party_1_name": "Maheshbhai Patel",
            "party_2_role": "accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "party_2",
            "absence_reason": "બહારગામ ગયેલ હોવાના",
            "date": "25/09/2026",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "en", template_id="exemption_arji"))
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        pdf_b64 = doc_generator.generate_pdf(blocks, "en", self.tpl["settings"])
        self.assertIsNotNone(pdf_b64)
        self.assertGreater(len(pdf_b64), 100)
        raw_pdf = base64.b64decode(pdf_b64)
        self.assertTrue(raw_pdf.startswith(b"%PDF"))

    def test_20_docx_generation(self):
        """20. Verify DOCX document generation."""
        user = {"advocate_name_gu": "રોનક એ. સોલંકી"}
        values = {
            "template_id": "exemption_arji",
            "court_name": "ચીફ જ્યુડીશીયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ફોજદારી કેસ",
            "case_number": "૧૨૩૪/૨૦૨૬",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "મહેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_2",
            "absence_reason": "માંદગીના",
            "date": "25/09/2026",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu", template_id="exemption_arji"))
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        doc_cls = getattr(doc_generator, "Document", None)
        if doc_cls is not None and not isinstance(doc_cls, MagicMock):
            docx_b64 = doc_generator.generate_docx(blocks, "gu", self.tpl["settings"])
            self.assertIsNotNone(docx_b64)
            self.assertGreater(len(docx_b64), 100)


if __name__ == '__main__':
    unittest.main()
