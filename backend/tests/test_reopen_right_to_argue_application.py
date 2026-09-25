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


class TestReopenRightToArgueApplicationTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl = next((t for t in TEMPLATES if t.get("id") == "reopen_right_to_argue_application"), None)
        self.assertIsNotNone(self.tpl, "reopen_right_to_argue_application template must be present in TEMPLATES")

    def test_01_template_exists_and_active(self):
        """1. Verify template exists, is active, and has canonical metadata."""
        self.assertEqual(self.tpl["id"], "reopen_right_to_argue_application")
        self.assertEqual(self.tpl["name_gu"], "દલીલો કરવા નો હક ફરીથી ખોલાવવાની અરજી")
        self.assertEqual(self.tpl["name_en"], "Application for Reopening the Right to Make Arguments")
        self.assertEqual(self.tpl.get("category"), "General")
        self.assertTrue(self.tpl.get("is_active"))
        aliases = self.tpl.get("aliases", [])
        self.assertIn("દલીલો કરવા નો હક ફરીથી ખોલાવવાની અરજી", aliases)
        self.assertIn("reopen right to argue application", aliases)

        canonical = server._get_canonical_reopen_right_to_argue_template()
        self.assertIsNotNone(canonical)
        self.assertEqual(canonical["id"], "reopen_right_to_argue_application")

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
            "advocate_for", "argument_failure_reason",
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
            "argument_failure_reason": "select",
            "date": "date",
            "place": "text",
            "advocate_name": "text",
        }
        for f in fields:
            self.assertEqual(f["type"], expected_types[f["key"]], f"Field {f['key']} has unexpected type {f['type']}")

    def test_04_all_fields_optional_required_false(self):
        """4. Verify all 14 fields have required: False."""
        for f in self.tpl.get("fields", []):
            self.assertFalse(f.get("required"), f"Field {f['key']} must have required: False")

    def test_05_party_roles_radio_options(self):
        """5. Verify Party 1 & 2 roles are radio buttons with canonical options."""
        p1 = next(f for f in self.tpl["fields"] if f["key"] == "party_1_role")
        self.assertEqual(p1["type"], "radio")
        p1_opts = [o["value"] for o in p1.get("options", [])]
        self.assertEqual(p1_opts, ["ફરીયાદી", "અરજદાર", "વાદી"])

        p2 = next(f for f in self.tpl["fields"] if f["key"] == "party_2_role")
        self.assertEqual(p2["type"], "radio")
        p2_opts = [o["value"] for o in p2.get("options", [])]
        self.assertEqual(p2_opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

    def test_06_canonical_reason_dropdown_options(self):
        """6. Verify argument_failure_reason dropdown has the exact 7 canonical choices."""
        reason_field = next(f for f in self.tpl["fields"] if f["key"] == "argument_failure_reason")
        self.assertEqual(reason_field["type"], "select")
        opts = [o["value"] for o in reason_field.get("options", [])]
        expected_opts = [
            "દલીલો તૈયાર ન હોવાના",
            "અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે",
            "અમો સામાજીક કામે રોકાયેલ હોવાના કારણોસર આપ નામદાર કોર્ટમા આવી શકીએ તેમ ન હતા, જે",
            "આરોપીના સગા ગુજરી ગયેલ, જે",
            "આરોપીને વ્યવસાયના કામ અર્થે વિદેશ જવાનુ થયેલ, જે",
            "આરોપી બીજા ગુન્હાના કામ અર્થે જેલમાં હોય, જે",
            "અન્ય",
        ]
        self.assertEqual(opts, expected_opts)
        self.assertEqual(len(opts), 7)
        for o in reason_field.get("options", []):
            self.assertEqual(o["label_gu"], o["value"])
            self.assertEqual(o["label_en"], o["value"])

    async def test_07_taluka_district_mukam_logic(self):
        """7. Verify District -> Mukam/Place auto-fill logic: place directly synchronizes with district."""
        user = {"name": "Test Advocate"}
        ctx_gn = await server.build_render_context(
            user, None, {"district": "gandhinagar"}, "gu", template_id="reopen_right_to_argue_application"
        )
        self.assertEqual(ctx_gn["district"], "ગાંધીનગર")
        self.assertEqual(ctx_gn["place"], "ગાંધીનગર")

        ctx_ahm = await server.build_render_context(
            user, None, {"district": "ahmedabad"}, "gu", template_id="reopen_right_to_argue_application"
        )
        self.assertEqual(ctx_ahm["district"], "અમદાવાદ")
        self.assertEqual(ctx_ahm["place"], "અમદાવાદ")

        ctx_blank = await server.build_render_context(
            user, None, {"district": ""}, "gu", template_id="reopen_right_to_argue_application"
        )
        self.assertEqual(ctx_blank["district"], "")
        self.assertEqual(ctx_blank["place"], "")

    def test_08_court_name_formatting(self):
        """8. Verify Court Name is centered, bold, 15pt GU / 16pt EN."""
        rules = self.tpl["settings"].get("block_align", [])
        court_rule = next((r for r in rules if r.get("contains") == "સાહેબશ્રીની કોર્ટમાં" or r.get("contains") == "In the Court of the Hon'ble"), None)
        self.assertIsNotNone(court_rule)
        self.assertEqual(court_rule["align"], "center")
        self.assertTrue(court_rule["bold"])
        self.assertEqual(self.tpl["settings"]["heading_size"], 15)
        self.assertEqual(self.tpl["settings"]["heading_size_en"], 16)

    def test_09_mukam_line_formatting(self):
        """9. Verify Mukam line is centered, regular body (bold: False), 13pt GU / 14pt EN."""
        rules = self.tpl["settings"].get("block_align", [])
        mukam_rule = next((r for r in rules if r.get("prefix") == "મુકામ :-" or r.get("prefix") == "Place :-"), None)
        self.assertIsNotNone(mukam_rule)
        self.assertEqual(mukam_rule["align"], "center")
        self.assertFalse(mukam_rule["bold"])
        self.assertEqual(self.tpl["settings"]["body_size"], 13)
        self.assertEqual(self.tpl["settings"]["body_size_en"], 14)

    def test_10_case_details_right_aligned(self):
        """10. Verify Case Details line is right-aligned."""
        rules = self.tpl["settings"].get("block_align", [])
        case_rule = next((r for r in rules if "નં. :" in r.get("contains", "") or "No. :" in r.get("contains", "")), None)
        self.assertIsNotNone(case_rule)
        self.assertEqual(case_rule["align"], "right")

    def test_11_party_1_and_party_2_left_aligned(self):
        """11. Verify Party 1 & Party 2 are left-aligned with zero first-line indent."""
        rendered = """મહેરબાન ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રીની કોર્ટમાં,

મુકામ :- ગાંધીનગર

ક્રિમિનલ કેસ નં. : ૧૦૧/૨૦૨૪

ફરીયાદી :- રમેશભાઈ પટેલ

વિરુદ્ધ

આરોપી :- સુરેશભાઈ શાહ

બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત ...
"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        p1_block = next((b for b in blocks if "ફરીયાદી :-" in b["text"]), None)
        p2_block = next((b for b in blocks if "આરોપી :-" in b["text"]), None)
        self.assertIsNotNone(p1_block)
        self.assertIsNotNone(p2_block)
        self.assertEqual(p1_block["align"], "left")
        self.assertEqual(p2_block["align"], "left")
        self.assertFalse(p1_block.get("indent", False))
        self.assertFalse(p2_block.get("indent", False))

    def test_12_versus_separator_centered(self):
        """12. Verify 'વિરુદ્ધ' / 'Versus' separator is centered."""
        rendered = "વિરુદ્ધ"
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks[0]["align"], "center")

        rendered_en = "Versus"
        blocks_en = doc_generator.build_blocks(rendered_en, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks_en[0]["align"], "center")

    def test_13_subject_center_bold_underlined(self):
        """13. Verify Subject is center aligned, bold, and underlined."""
        rendered = "બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત ..."
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        self.assertEqual(blocks[0]["align"], "center")
        self.assertTrue(blocks[0]["bold"])
        self.assertTrue(blocks[0].get("underline"))

    def test_14_exact_subject_text_verbatim(self):
        """14. Verify exact verbatim subject line from canonical Page 2."""
        self.assertIn("બાબત :- દલીલો કરવા નો હક ફરીથી ખોલવા બાબત ...", self.tpl["content_gu"])
        self.assertIn("Subject :- Application for reopening the right to make arguments ...", self.tpl["content_en"])

    async def test_15_paragraph_1_verbatim_canonical_text(self):
        """15. Verify verbatim legal text for Paragraph 1 matching Page 2 of canonical PDF."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "ફરીયાદી",
            "party_2_role": "આરોપી",
            "advocate_for": "ફરીયાદી",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertIn("સદર કામમા અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....", rendered_gu)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("In the said matter, we, the Advocate for Complainant, humbly submit before this Hon'ble Court that.....", rendered_en)

    async def test_16_paragraph_2_verbatim_canonical_text(self):
        """16. Verify verbatim legal text for Paragraph 2 preserving exact source wording."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "દલીલો તૈયાર ન હોવાના",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટમાં દલીલો પર છે. જેમા અમોનો દલીલો કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે.", rendered_gu)
        self.assertIn("જે દલીલો તૈયાર ન હોવાના કારણોસર દલીલો થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી હોવાથી તથા દલીલો કરવાની તક મળવીએ ન્યાયના હિતમા હોય, અમોનો દલીલો કરવાનો હક ફરીથી ખોલી અમોને દલીલો કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.", rendered_gu)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertIn("The said case is pending before this Hon'ble Court for arguments. Wherein our right to make arguments has been closed by this Hon'ble Court.", rendered_en)
        self.assertIn("As arguments could not be made due to the reason that arguments were not prepared, and as the said reason is reasonable and getting an opportunity to make arguments is in the interest of justice, it is prayed to be pleased to pass appropriate order reopening our right to make arguments and granting us an opportunity to make arguments.", rendered_en)

    def test_17_paragraphs_indent_and_justified(self):
        """17. Verify paragraphs are justified with 1-tab first line indent."""
        rendered = """સદર કામમા અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટમાં દલીલો પર છે. જેમા અમોનો દલીલો કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે. જે દલીલો તૈયાર ન હોવાના કારણોસર દલીલો થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી હોવાથી તથા દલીલો કરવાની તક મળવીએ ન્યાયના હિતમા હોય, અમોનો દલીલો કરવાનો હક ફરીથી ખોલી અમોને દલીલો કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી."""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        non_spacers = [b for b in blocks if b.get("section") != "spacer"]
        self.assertEqual(non_spacers[0]["align"], "justify")
        self.assertTrue(non_spacers[0].get("indent"))
        self.assertEqual(non_spacers[1]["align"], "justify")
        self.assertTrue(non_spacers[1].get("indent"))

    async def test_18_reason_other_with_conditional_text(self):
        """18. Verify selecting 'અન્ય' with custom text populates paragraph cleanly without permanent 15th field."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અન્ય",
            "argument_failure_reason_custom": "મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx["argument_failure_reason"], "મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("જે મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના કારણોસર દલીલો થઈ શકેલ નહિ", rendered)
        self.assertNotIn("અન્ય", rendered)

    async def test_19_reason_other_blank_fallback(self):
        """19. Verify selecting 'અન્ય' without custom text falls back cleanly without crashing."""
        user = {"name": "Test Advocate"}
        vals = {
            "party_1_role": "વાદી",
            "party_2_role": "પ્રતિવાદી",
            "advocate_for": "વાદી",
            "argument_failure_reason": "અન્ય",
            "argument_failure_reason_custom": "",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx["argument_failure_reason"], "અન્ય")
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("જે અન્ય કારણોસર દલીલો થઈ શકેલ નહિ", rendered)

    def test_20_date_and_place_left_aligned(self):
        """20. Verify Date and Place blocks are left-aligned."""
        rendered = """તારીખ : 25/09/2026

સ્થળ : કલોલ, ગાંધીનગર"""
        blocks = doc_generator.build_blocks(rendered, align_rules=self.tpl["settings"].get("block_align"))
        date_b = next(b for b in blocks if "તારીખ :" in b["text"])
        place_b = next(b for b in blocks if "સ્થળ :" in b["text"])
        self.assertEqual(date_b["align"], "left")
        self.assertEqual(place_b["align"], "left")

    def test_21_signature_dashes_count(self):
        """21. Verify signature dashes: exactly 10 dashes GU, 20 dashes EN."""
        rendered_gu = """તારીખ : 25/09/2026

સ્થળ : કલોલ, ગાંધીનગર

----------

ફરીયાદી ના એડવોકેટ"""
        blocks_gu = doc_generator.build_blocks(rendered_gu, align_rules=self.tpl["settings"].get("block_align"))
        dash_b_gu = next(b for b in blocks_gu if "-" in b["text"])
        self.assertEqual(dash_b_gu["text"], "----------")
        self.assertEqual(len(dash_b_gu["text"]), 10)
        self.assertEqual(dash_b_gu["align"], "right")

        rendered_en = """Date : 25/09/2026

Place : Kalol, Gandhinagar

--------------------

Advocate for Complainant"""
        blocks_en = doc_generator.build_blocks(rendered_en, align_rules=self.tpl["settings"].get("block_align"))
        dash_b_en = next(b for b in blocks_en if "-" in b["text"])
        self.assertEqual(dash_b_en["text"], "--------------------")
        self.assertEqual(len(dash_b_en["text"]), 20)
        self.assertEqual(dash_b_en["align"], "right")

    async def test_22_advocate_name_auto_derives_from_advocate_for(self):
        """22. Verify advocate designation auto-derives from advocate_for."""
        user = {"name": "Test Advocate", "advocate_name_gu": "પરીક્ષણ એડવોકેટ", "advocate_name_en": "Test Advocate"}
        role_pairs = [
            ("ફરીયાદી", "ફરીયાદી ના એડવોકેટ"),
            ("આરોપી", "આરોપી ના એડવોકેટ"),
            ("અરજદાર", "અરજદાર ના એડવોકેટ"),
            ("સામાવાળા", "સામાવાળા ના એડવોકેટ"),
            ("વાદી", "વાદી ના એડવોકેટ"),
            ("પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ"),
        ]
        for role, expected_desig in role_pairs:
            ctx = await server.build_render_context(user, None, {"advocate_for": role}, "gu", template_id="reopen_right_to_argue_application")
            self.assertEqual(ctx["advocate_name"], expected_desig, f"advocate_for={role} must derive {expected_desig}")

        # English
        role_pairs_en = [
            ("complainant", "Advocate for Complainant"),
            ("accused", "Advocate for Accused"),
            ("applicant", "Advocate for Applicant"),
            ("opponent", "Advocate for Opponent"),
            ("plaintiff", "Advocate for Plaintiff"),
            ("defendant", "Advocate for Defendant"),
        ]
        for role, expected_desig in role_pairs_en:
            ctx = await server.build_render_context(user, None, {"advocate_for": role}, "en", template_id="reopen_right_to_argue_application")
            self.assertEqual(ctx["advocate_name"], expected_desig, f"advocate_for={role} must derive {expected_desig}")

        # Empty/unselected
        ctx_empty = await server.build_render_context(user, None, {"advocate_for": ""}, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(ctx_empty["advocate_name"], "")

    def test_23_margins_a4_4cm_lr_2cm_tb(self):
        """23. Verify margins are A4, 4cm L/R, 2cm T/B."""
        s = self.tpl["settings"]
        self.assertEqual(s["page_size"], "A4")
        self.assertEqual(s["margin_left_cm"], 4.0)
        self.assertEqual(s["margin_right_cm"], 4.0)
        self.assertEqual(s["margin_top_cm"], 2.0)
        self.assertEqual(s["margin_bottom_cm"], 2.0)

    def test_24_fonts_and_sizes_gu_and_en(self):
        """24. Verify fonts and sizes: Lohit Gujarati (13pt body, 15pt heading) / Times New Roman (14pt body, 16pt heading)."""
        s = self.tpl["settings"]
        self.assertEqual(s["gujarati_font"], "LohitGujarati")
        self.assertEqual(s["english_font"], "Times-Roman")
        self.assertEqual(s["body_size"], 13)
        self.assertEqual(s["heading_size"], 15)
        self.assertEqual(s["body_size_en"], 14)
        self.assertEqual(s["heading_size_en"], 16)

    async def test_25_blank_fields_non_blocking_preview(self):
        """25. Verify all blank fields allow preview without validation errors."""
        server.validate_template_requirements(self.tpl, {}, "gu")
        server.validate_template_requirements(self.tpl, {}, "en")
        user = {"name": ""}
        ctx_gu = await server.build_render_context(user, None, {}, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertTrue(len(rendered_gu) > 50)

    async def test_26_blank_fields_no_ugly_placeholders(self):
        """26. Verify blank fields never leak 'undefined', 'null', 'None', 'N/A', or {{field}}."""
        user = {"name": ""}
        ctx_gu = await server.build_render_context(user, None, {}, "gu", template_id="reopen_right_to_argue_application")
        rendered_gu = doc_generator.render_template(self.tpl["content_gu"], ctx_gu)
        self.assertNotIn("None", rendered_gu)
        self.assertNotIn("null", rendered_gu)
        self.assertNotIn("undefined", rendered_gu)
        self.assertNotIn("N/A", rendered_gu)
        self.assertNotIn("[object Object]", rendered_gu)
        self.assertNotIn("{{", rendered_gu)
        self.assertNotIn("}}", rendered_gu)

        ctx_en = await server.build_render_context(user, None, {}, "en", template_id="reopen_right_to_argue_application")
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        self.assertNotIn("None", rendered_en)
        self.assertNotIn("null", rendered_en)
        self.assertNotIn("undefined", rendered_en)
        self.assertNotIn("N/A", rendered_en)
        self.assertNotIn("[object Object]", rendered_en)
        self.assertNotIn("{{", rendered_en)
        self.assertNotIn("}}", rendered_en)

    async def test_27_pdf_generation_valid(self):
        """27. Verify PDF generation produces non-empty bytes for both Gujarati and English."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "taluka": "kalol",
            "case_type": "criminal_case",
            "case_number": "101/2024",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "argument_failure_reason": "દલીલો તૈયાર ન હોવાના",
            "date": "2026-09-25",
            "place": "કલોલ, ગાંધીનગર",
        }
        ctx_gu = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        blocks_gu = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_gu"], ctx_gu), align_rules=self.tpl["settings"].get("block_align"))
        pdf_gu = doc_generator.generate_pdf(blocks_gu, "gu", self.tpl["settings"])
        self.assertTrue(len(pdf_gu) > 100)

        ctx_en = await server.build_render_context(user, None, vals, "en", template_id="reopen_right_to_argue_application")
        blocks_en = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_en"], ctx_en), align_rules=self.tpl["settings"].get("block_align"))
        pdf_en = doc_generator.generate_pdf(blocks_en, "en", self.tpl["settings"])
        self.assertTrue(len(pdf_en) > 100)

    async def test_28_docx_and_odt_generation_valid(self):
        """28. Verify DOCX and ODT export work without error."""
        user = {"name": "Test Advocate"}
        vals = {
            "court_name": "chief_judicial_magistrate",
            "district": "gandhinagar",
            "party_1_role": "વાદી",
            "party_1_name": "રમેશભાઈ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ",
            "advocate_for": "વાદી",
            "argument_failure_reason": "આરોપીના દાદા ગુજરી ગયેલ હોવાના",
        }
        ctx = await server.build_render_context(user, None, vals, "gu", template_id="reopen_right_to_argue_application")
        blocks = doc_generator.build_blocks(doc_generator.render_template(self.tpl["content_gu"], ctx), align_rules=self.tpl["settings"].get("block_align"))

        doc_cls = getattr(doc_generator, "Document", None)
        if doc_cls is not None and not isinstance(doc_cls, MagicMock):
            docx_b64 = doc_generator.generate_docx(blocks, "gu", self.tpl["settings"])
            self.assertTrue(len(docx_b64) > 100)

        odt_b64 = doc_generator.generate_odt(blocks, "gu", self.tpl["settings"])
        self.assertTrue(len(odt_b64) > 100)

    async def test_29_saved_case_mode_unmodified(self):
        """29. Verify Saved Case record is not modified when rendering application."""
        user = {"name": "Test Advocate"}
        orig_case = {
            "id": "case_999",
            "court_name": "chief_judicial_magistrate",
            "case_number": "555/2024",
            "district": "gandhinagar",
            "party_name": "Test Complainant",
            "opposite_party": "Test Accused",
            "party_role": "ફરીયાદી",
            "opposite_party_role": "આરોપી",
        }
        case_copy = dict(orig_case)
        vals = {"argument_failure_reason": "આરોપીના દાદા ગુજરી ગયેલ હોવાના", "advocate_for": "ફરીયાદી"}
        ctx = await server.build_render_context(user, case_copy, vals, "gu", template_id="reopen_right_to_argue_application")
        self.assertEqual(orig_case, case_copy, "Original Saved Case dict must remain completely untouched")

    def test_30_zero_regression_other_templates(self):
        """30. Verify other existing templates remain untouched and valid."""
        other_ids = ["closing_argument_right_application", "closing_purshish", "certified_copy_application"]
        for tid in other_ids:
            tpl = next((t for t in TEMPLATES if t.get("id") == tid), None)
            self.assertIsNotNone(tpl, f"Template {tid} must exist in TEMPLATES")
            self.assertTrue(len(tpl.get("fields", [])) > 0, f"Template {tid} must have fields")

    async def test_31_user_tests_a_through_h(self):
        """31. Verify all 8 explicitly mandated tests A through H from user specification."""
        user = {"name": "Test Advocate"}

        # TEST A: Select advocate_for = ફરીયાદી
        ctx_a = await server.build_render_context(user, None, {"advocate_for": "ફરીયાદી"}, "gu", template_id="reopen_right_to_argue_application")
        rendered_a = doc_generator.render_template(self.tpl["content_gu"], ctx_a)
        self.assertIn("સદર કામમા અમો ફરીયાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....", rendered_a)

        # TEST B: Select advocate_for = વાદી
        ctx_b = await server.build_render_context(user, None, {"advocate_for": "વાદી"}, "gu", template_id="reopen_right_to_argue_application")
        rendered_b = doc_generator.render_template(self.tpl["content_gu"], ctx_b)
        self.assertIn("સદર કામમા અમો વાદી ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....", rendered_b)

        # TEST C: Select reason = દલીલો તૈયાર ન હોવાના (Option 1)
        ctx_c = await server.build_render_context(
            user, None,
            {"argument_failure_reason": "દલીલો તૈયાર ન હોવાના"},
            "gu",
            template_id="reopen_right_to_argue_application"
        )
        rendered_c = doc_generator.render_template(self.tpl["content_gu"], ctx_c)
        self.assertIn("જે દલીલો તૈયાર ન હોવાના કારણોસર દલીલો થઈ શકેલ નહિ", rendered_c)

        # TEST C2: Select reason = અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે (Option 2)
        ctx_c2 = await server.build_render_context(
            user, None,
            {"argument_failure_reason": "અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે"},
            "gu",
            template_id="reopen_right_to_argue_application"
        )
        rendered_c2 = doc_generator.render_template(self.tpl["content_gu"], ctx_c2)
        self.assertIn("જે અમો માંદગીના કારણોસર આપ નામદાર કોર્ટમાં આવી શકીએ તેમ ન હતા, જે કારણોસર દલીલો થઈ શકેલ નહિ", rendered_c2)

        # TEST D: Select reason = આરોપીના સગા ગુજરી ગયેલ, જે
        ctx_d = await server.build_render_context(user, None, {"argument_failure_reason": "આરોપીના સગા ગુજરી ગયેલ, જે"}, "gu", template_id="reopen_right_to_argue_application")
        rendered_d = doc_generator.render_template(self.tpl["content_gu"], ctx_d)
        self.assertIn("જે આરોપીના સગા ગુજરી ગયેલ, જે કારણોસર દલીલો થઈ શકેલ નહિ", rendered_d)

        # TEST E: Select "અન્ય", Enter "મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના"
        ctx_e = await server.build_render_context(
            user, None,
            {"argument_failure_reason": "અન્ય", "argument_failure_reason_custom": "મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના"},
            "gu",
            template_id="reopen_right_to_argue_application"
        )
        rendered_e = doc_generator.render_template(self.tpl["content_gu"], ctx_e)
        self.assertIn("જે મારા પિતાશ્રી હોસ્પિટલમાં દાખલ થયેલ હોવાના કારણોસર દલીલો થઈ શકેલ નહિ", rendered_e)
        self.assertNotIn("અન્ય", rendered_e)

        # TEST F: Select District = ગાંધીનગર -> lower Mukam/Place: ગાંધીનગર
        ctx_f = await server.build_render_context(user, None, {"district": "ગાંધીનગર"}, "gu", template_id="reopen_right_to_argue_application")
        rendered_f = doc_generator.render_template(self.tpl["content_gu"], ctx_f)
        self.assertEqual(ctx_f["district"], "ગાંધીનગર")
        self.assertEqual(ctx_f["place"], "ગાંધીનગર")
        self.assertIn("મુકામ :- ગાંધીનગર", rendered_f)
        self.assertIn("સ્થળ : ગાંધીનગર", rendered_f)

        # TEST G: Change District = અમદાવાદ -> lower Mukam/Place: અમદાવાદ
        ctx_g = await server.build_render_context(user, None, {"district": "અમદાવાદ"}, "gu", template_id="reopen_right_to_argue_application")
        rendered_g = doc_generator.render_template(self.tpl["content_gu"], ctx_g)
        self.assertEqual(ctx_g["district"], "અમદાવાદ")
        self.assertEqual(ctx_g["place"], "અમદાવાદ")
        self.assertIn("મુકામ :- અમદાવાદ", rendered_g)
        self.assertIn("સ્થળ : અમદાવાદ", rendered_g)

        # TEST H: Clear District -> lower Mukam/Place becomes blank
        ctx_h = await server.build_render_context(user, None, {"district": ""}, "gu", template_id="reopen_right_to_argue_application")
        rendered_h = doc_generator.render_template(self.tpl["content_gu"], ctx_h)
        self.assertEqual(ctx_h["district"], "")
        self.assertEqual(ctx_h["place"], "")
        self.assertIn("મુકામ :- ", rendered_h)
        self.assertIn("સ્થળ : ", rendered_h)


if __name__ == "__main__":
    unittest.main()
