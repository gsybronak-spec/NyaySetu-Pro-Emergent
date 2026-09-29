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


class TestDDKaravaniArjiTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "dd_karavani_arji"), None)
        self.assertIsNotNone(self.tpl, "dd_karavani_arji template must be present in TEMPLATES")

    def test_01_template_exists_and_active(self):
        """1. Verify template exists, is active, and has canonical metadata."""
        self.assertEqual(self.tpl["id"], "dd_karavani_arji")
        self.assertEqual(self.tpl["name_gu"], "DD કરાવવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Dismissal of Case")
        self.assertEqual(self.tpl.get("category"), "General")
        self.assertTrue(self.tpl.get("is_active"))
        aliases = self.tpl.get("aliases", [])
        self.assertIn("DD કરાવવાની અરજી", aliases)
        self.assertIn("dd karavani arji", aliases)
        self.assertIn("Application for Dismissal of Case", aliases)
        self.assertIn("કેસ ડિસમીસ કરવા બાબત", aliases)

        canonical = server._get_canonical_dd_karavani_arji_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "dd_karavani_arji")

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
            "advocate_for", "dismissal_reason",
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
            "dismissal_reason": "textarea",
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

    def test_07_dismissal_reason_field(self):
        """7. Verify dismissal_reason is textarea with canonical placeholder matching Page 1."""
        f = next(f for f in self.tpl["fields"] if f["key"] == "dismissal_reason")
        self.assertEqual(f["type"], "textarea")
        self.assertFalse(f.get("required"))
        self.assertIn("ફરીયાદી આપ નામદાર કોર્ટ સમક્ષ હાજર રહેતા નથી", f.get("placeholder", ""))

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
            "template_id": "dd_karavani_arji",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_1",
            "dismissal_reason": "પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["place"], "કલોલ, ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "કલોલ, ગાંધીનગર")

    def test_11_taluka_blank_district_only(self):
        """11. Verify place is derived as [District] when taluka is blank."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "district": "ગાંધીનગર",
            "taluka": "",
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "party_1",
            "dismissal_reason": "હવે કોઈ તકરાર બાકી રહેલ ન હોય",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["place"], "ગાંધીનગર")
        self.assertEqual(ctx["taluka_place"], "ગાંધીનગર")

    def test_12_both_taluka_and_district_blank(self):
        """12. Verify place is clean empty string when both taluka and district are blank."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "district": "",
            "taluka": "",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["place"], "")
        self.assertEqual(ctx["taluka_place"], "")

    def test_13_advocate_name_derived_from_advocate_for(self):
        """13. Verify advocate_name resolves to [advocate_for_role] ના એડવોકેટ."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_1",
            "dismissal_reason": "પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["advocate_for_role"], "ફરીયાદી")
        self.assertEqual(ctx["advocate_name"], "ફરીયાદી ના એડવોકેટ")

    def test_14_advocate_name_derived_for_party_2(self):
        """14. Verify advocate_name resolves to accused's advocate when party_2 chosen."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "party_2",
            "dismissal_reason": "હવે કોઈ તકરાર બાકી રહેલ ન હોય",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["advocate_for_role"], "આરોપી")
        self.assertEqual(ctx["advocate_name"], "આરોપી ના એડવોકેટ")

    def test_15_verbatim_text_preservation_including_special_phrase(self):
        """15. Verify verbatim text matching Page 2 of canonical PDF, preserving 'જથી ે'."""
        content_gu = self.tpl["content_gu"]
        # Opening paragraph
        self.assertIn("સદર કામમાં અમો {{advocate_for_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...", content_gu)
        # Paragraph 1
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં {{dismissal_reason}}.", content_gu)
        # Paragraph 2 - Note the exact verbatim source text containing 'જથી ે'
        self.assertIn("વધુમાં {{advocate_for_role}} સદર કેસ ચલાવવામાં રસ ધરાવતા ન હોઈ, જથી ે સદર કેસ ડિસમીસ કરવા સારૂ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", content_gu)
        self.assertIn("જથી ે", content_gu)

    def test_16_verbatim_subject_line(self):
        """16. Verify subject line verbatim: બાબત :- કેસ ડિસ મી સ કરવા બાબત ..."""
        content_gu = self.tpl["content_gu"]
        self.assertIn("બાબત :- કેસ ડિસ મી સ કરવા બાબત ...", content_gu)

    def test_17_court_heading_and_case_line_format(self):
        """17. Verify court heading, mukam, and single-line case format."""
        content_gu = self.tpl["content_gu"]
        self.assertIn("મહેરબાન {{court_name}} સાહેબશ્રીની કોર્ટમાં,", content_gu)
        self.assertIn("મુકામ :- {{place}}", content_gu)
        self.assertIn("{{case_type}} નં. : {{case_number}}", content_gu)

    def test_18_settings_margins_and_sizes(self):
        """18. Verify A4, 4cm left/right, 2cm top/bottom, Lohit Gujarati font, 13pt body, 15pt header."""
        settings = self.tpl.get("settings", {})
        self.assertEqual(settings.get("page_size"), "A4")
        self.assertEqual(settings.get("margin_left_cm"), 4.0)
        self.assertEqual(settings.get("margin_right_cm"), 4.0)
        self.assertEqual(settings.get("margin_top_cm"), 2.0)
        self.assertEqual(settings.get("margin_bottom_cm"), 2.0)
        self.assertEqual(settings.get("font_family"), "Lohit Gujarati")
        self.assertEqual(settings.get("body_font_size"), 13)
        self.assertEqual(settings.get("header_font_size"), 15)

    def test_19_settings_block_align(self):
        """19. Verify block_align configuration contains alignment rules for all sections."""
        settings = self.tpl.get("settings", {})
        ba = settings.get("block_align", [])
        self.assertTrue(isinstance(ba, list) or isinstance(ba, dict))
        if isinstance(ba, list):
            court_rule = next((r for r in ba if "સાહેબશ્રીની કોર્ટમાં" in str(r.get("contains") or "")), None)
            self.assertIsNotNone(court_rule)
            self.assertEqual(court_rule.get("align"), "center")
            self.assertTrue(court_rule.get("bold"))

            mukam_rule = next((r for r in ba if r.get("prefix") == "મુકામ :-"), None)
            self.assertIsNotNone(mukam_rule)
            self.assertEqual(mukam_rule.get("align"), "center")
            self.assertTrue(mukam_rule.get("bold"))

            subject_rule = next((r for r in ba if "બાબત :-" in str(r.get("prefix") or r.get("contains") or "")), None)
            self.assertIsNotNone(subject_rule)
            self.assertEqual(subject_rule.get("align"), "center")
            self.assertTrue(subject_rule.get("bold"))
            self.assertTrue(subject_rule.get("underline"))

    def test_20_render_gujarati_full(self):
        """20. Verify rendering full Gujarati context leaves no unrendered placeholders or None."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "court_name": "પ્રિન્સિપાલ સિવિલ જજ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "૧૨૩૪/૨૦૨૬",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_1",
            "dismissal_reason": "પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય",
            "date": "2026-09-28",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        self.assertIn("મહેરબાન પ્રિન્સિપાલ સિવિલ જજ સાહેબશ્રીની કોર્ટમાં,", rendered)
        self.assertIn("મુકામ :- કલોલ, ગાંધીનગર", rendered)
        self.assertIn("ક્રિમિનલ કેસ નં. : ૧૨૩૪/૨૦૨૬", rendered)
        self.assertIn("ફરીયાદી :- રમેશભાઈ પટેલ", rendered)
        self.assertIn("વિરુદ્ધ", rendered)
        self.assertIn("આરોપી :- સુરેશભાઈ શાહ", rendered)
        self.assertIn("બાબત :- કેસ ડિસ મી સ કરવા બાબત ...", rendered)
        self.assertIn("સદર કામમાં અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...", rendered)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય.", rendered)
        self.assertIn("વધુમાં ફરીયાદી સદર કેસ ચલાવવામાં રસ ધરાવતા ન હોઈ, જથી ે સદર કેસ ડિસમીસ કરવા સારૂ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered)
        self.assertIn("સ્થળ : કલોલ, ગાંધીનગર", rendered)
        self.assertIn("ફરીયાદી ના એડવોકેટ", rendered)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("}}", rendered)
        self.assertNotIn("None", rendered)
        self.assertNotIn("undefined", rendered)

    def test_21_render_english_full(self):
        """21. Verify rendering English context translates roles and reasons appropriately."""
        user = {"advocate_name_en": "Ronak Solanki"}
        values = {
            "template_id": "dd_karavani_arji",
            "court_name": "Principal Civil Judge",
            "district": "Gandhinagar",
            "taluka": "Kalol",
            "case_type": "Criminal Case",
            "case_number": "1234/2026",
            "party_1_role": "complainant",
            "party_1_name": "Rameshbhai Patel",
            "party_2_role": "accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "party_1",
            "dismissal_reason": "પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય",
            "date": "2026-09-28",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "en"))
        rendered = doc_generator.render_template(self.tpl["content_en"], ctx)

        self.assertIn("In the Court of the Hon'ble Principal Civil Judge,", rendered)
        self.assertIn("Place :- Kalol, Gandhinagar", rendered)
        self.assertIn("Criminal Case No. : 1234/2026", rendered)
        self.assertIn("Subject :- Application for Dismissal of Case ...", rendered)
        self.assertIn("a settlement has been arrived at between the parties", rendered)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("}}", rendered)
        self.assertNotIn("None", rendered)

    def test_22_render_with_empty_optionals(self):
        """22. Verify rendering when all optional fields are empty does not crash and leaves no None."""
        user = {}
        values = {"template_id": "dd_karavani_arji"}
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)

        self.assertNotIn("None", rendered)
        self.assertNotIn("undefined", rendered)
        self.assertNotIn("{{", rendered)
        self.assertNotIn("}}", rendered)

    def test_23_dismissal_reason_other_custom(self):
        """23. Verify custom dismissal reason is used when 'અન્ય' is selected."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "dismissal_reason": "અન્ય",
            "dismissal_reason_custom": "બંને પક્ષો સંમત થયા છે",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["dismissal_reason"], "બંને પક્ષો સંમત થયા છે")

    def test_24_pdf_generation_detailed_produces_valid_pdf(self):
        """24. Verify generate_pdf_detailed produces a valid A4 PDF."""
        user = {"advocate_name_gu": "રોનક સોલંકી"}
        values = {
            "template_id": "dd_karavani_arji",
            "court_name": "પ્રિન્સિપાલ સિવિલ જજ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "૧૨૩૪/૨૦૨૬",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "party_1",
            "dismissal_reason": "પક્ષકારો વચ્ચે સમાધાન થઈ ગયેલ હોય",
            "date": "2026-09-28",
        }
        import asyncio
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
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
            template_id="dd_karavani_arji",
            raw_content=rendered,
            ctx=ctx,
        )
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Output must be valid PDF bytes")
        self.assertGreater(len(pdf_bytes), 1000)

    def test_25_pdf_preview_parity_zero_credit_cost(self):
        """25. Verify template can be loaded and preview rendered without deduction."""
        import asyncio
        tpl_found = asyncio.run(server._get_template_by_id("dd_karavani_arji"))
        self.assertIsNotNone(tpl_found)
        self.assertEqual(tpl_found["name_gu"], "DD કરાવવાની અરજી")

    def test_26_deleted_template_ids_does_not_mask_dd_karavani_arji(self):
        """26. Verify dd_karavani_arji is never masked by historical tombstones."""
        import asyncio
        deleted_ids = asyncio.run(server._get_deleted_template_ids())
        self.assertNotIn("dd_karavani_arji", deleted_ids)
        self.assertNotIn("dd_karavani_arji_gu", deleted_ids)
        self.assertNotIn("dd_karavani_arji_en", deleted_ids)

    def test_27_get_catalog_template_order_includes_dd_karavani_arji(self):
        """27. Verify catalog template order includes dd_karavani_arji."""
        import asyncio
        order_res = asyncio.run(server.get_catalog_template_order())
        self.assertIn("template_order", order_res)
        order = order_res["template_order"]
        self.assertTrue(
            "dd_karavani_arji" in order or "dd_karavani_arji_gu" in order or "dd_karavani_arji_en" in order,
            f"dd_karavani_arji must be present in template_order: {order}"
        )

    def test_28_get_published_templates_includes_dd_karavani_arji(self):
        """28. Verify _get_published_templates includes canonical dd_karavani_arji."""
        import asyncio
        server.invalidate_published_templates_cache()
        tpls = asyncio.run(server._get_published_templates())
        found = any(t.get("id") == "dd_karavani_arji" or t.get("template_id") == "dd_karavani_arji" for t in tpls)
        self.assertTrue(found, "dd_karavani_arji must be present in published templates list")


if __name__ == "__main__":
    unittest.main()

