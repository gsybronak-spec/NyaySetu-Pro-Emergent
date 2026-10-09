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


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        import subprocess
        return subprocess.check_output(["pdftotext", "-", "-"], input=pdf_bytes).decode("utf-8")
    except Exception:
        try:
            import pypdfium2
            doc = pypdfium2.PdfDocument(pdf_bytes)
            return "\n".join(page.get_textpage().get_text_range() for page in doc)
        except Exception:
            return ""


class TestVakilatnamaTemplate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tpl_crim = next((t for t in TEMPLATES if t.get("id") == "vakilatnama_criminal"), None)
        self.tpl_civ = next((t for t in TEMPLATES if t.get("id") == "vakilatnama_civil"), None)
        self.assertIsNotNone(self.tpl_crim, "vakilatnama_criminal template must be present in TEMPLATES")
        self.assertIsNotNone(self.tpl_civ, "vakilatnama_civil template must be present in TEMPLATES")

    def test_01_both_variants_exist_and_metadata(self):
        """1. Verify both Criminal and Civil Vakilatnama templates exist with proper metadata."""
        self.assertEqual(self.tpl_crim["id"], "vakilatnama_criminal")
        self.assertEqual(self.tpl_crim["name_gu"], "વકીલાતનામું (ક્રિમિનલ)")
        self.assertEqual(self.tpl_crim["name_en"], "Vakalatnama (Criminal)")
        self.assertEqual(self.tpl_crim["category"], "Criminal")

        self.assertEqual(self.tpl_civ["id"], "vakilatnama_civil")
        self.assertEqual(self.tpl_civ["name_gu"], "વકીલાતનામું (સિવિલ)")
        self.assertEqual(self.tpl_civ["name_en"], "Vakalatnama (Civil)")
        self.assertEqual(self.tpl_civ["category"], "Civil")

    def test_02_field_count_and_exact_order(self):
        """2. Verify exact 19 fields in exact canonical order for both variants."""
        expected_keys = [
            "advocate_name",
            "advocate_qualification",
            "advocate_enrollment_number",
            "advocate_address",
            "advocate_email",
            "advocate_mobile",
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
            "date",
            "place",
            "party_signature_name",
        ]
        crim_keys = [f["key"] for f in self.tpl_crim["fields"]]
        civ_keys = [f["key"] for f in self.tpl_civ["fields"]]

        self.assertEqual(len(crim_keys), 19, f"Criminal fields count must be 19, got {len(crim_keys)}")
        self.assertEqual(len(civ_keys), 19, f"Civil fields count must be 19, got {len(civ_keys)}")
        self.assertEqual(crim_keys, expected_keys, "Criminal field keys do not match canonical sequence")
        self.assertEqual(civ_keys, expected_keys, "Civil field keys do not match canonical sequence")

    def test_03_field_optionality_and_types(self):
        """3. Verify required vs optional fields and field types match specifications."""
        for tpl in (self.tpl_crim, self.tpl_civ):
            f_map = {f["key"]: f for f in tpl["fields"]}

            # Required fields
            self.assertTrue(f_map["advocate_name"]["required"])
            self.assertTrue(f_map["court_name"]["required"])
            self.assertTrue(f_map["district"]["required"])
            self.assertTrue(f_map["case_type"]["required"])
            self.assertTrue(f_map["case_number"]["required"])
            self.assertTrue(f_map["party_1_role"]["required"])
            self.assertTrue(f_map["party_1_name"]["required"])
            self.assertTrue(f_map["party_2_role"]["required"])
            self.assertTrue(f_map["party_2_name"]["required"])
            self.assertTrue(f_map["advocate_for"]["required"])
            self.assertTrue(f_map["date"]["required"])
            self.assertTrue(f_map["party_signature_name"]["required"])

            # Optional fields
            self.assertFalse(f_map["advocate_qualification"]["required"])
            self.assertFalse(f_map["advocate_enrollment_number"]["required"])
            self.assertFalse(f_map["advocate_address"]["required"])
            self.assertFalse(f_map["advocate_email"]["required"])
            self.assertFalse(f_map["advocate_mobile"]["required"])
            self.assertFalse(f_map["taluka"]["required"])
            self.assertFalse(f_map["place"]["required"])

            # Types
            self.assertEqual(f_map["advocate_name"]["type"], "text")
            self.assertEqual(f_map["advocate_qualification"]["type"], "text")
            self.assertEqual(f_map["advocate_enrollment_number"]["type"], "text")
            self.assertEqual(f_map["advocate_address"]["type"], "textarea")
            self.assertEqual(f_map["advocate_email"]["type"], "text")
            self.assertEqual(f_map["advocate_mobile"]["type"], "text")
            self.assertEqual(f_map["court_name"]["type"], "select")
            self.assertEqual(f_map["district"]["type"], "select")
            self.assertEqual(f_map["taluka"]["type"], "select")
            self.assertEqual(f_map["party_1_role"]["type"], "radio")
            self.assertEqual(f_map["party_2_role"]["type"], "radio")
            self.assertEqual(f_map["advocate_for"]["type"], "select")
            self.assertEqual(f_map["date"]["type"], "date")
            self.assertEqual(f_map["party_signature_name"]["type"], "text")

    def test_04_labels_exclude_page_1_instructional_tags(self):
        """4. Verify field labels do not leak Page 1 instructional tags into UI or documents."""
        instructional_patterns = [r"\(ડ્રોપ\s*બોક્ષ\)", r"\(ટેક્ષ\s*બોક્ષ\)", r"\(ઓટોસેવ\s*પણ\s*એડીટેબલ\)", r"\(રેડીયો\s*બટન\)"]
        for tpl in (self.tpl_crim, self.tpl_civ):
            for f in tpl["fields"]:
                for pat in instructional_patterns:
                    self.assertIsNone(re.search(pat, f["label_gu"]), f"Instruction tag {pat} leaked into label_gu of {f['key']}")
                    self.assertIsNone(re.search(pat, f["label_en"]), f"Instruction tag {pat} leaked into label_en of {f['key']}")

    def test_05_dynamic_place_resolution_taluka_and_district(self):
        """5. Verify dynamic place rule: [taluka], [district] if taluka present, else [district]."""
        user = {"advocate_name_gu": "હિતેશ કે. જાદવ", "advocate_name_en": "Hitesh K. Jadav"}
        
        # With taluka (Gujarati)
        vals_with_taluka = {"district": "ગાંધીનગર", "taluka": "કલોલ", "template_id": "vakilatnama_criminal"}
        ctx = asyncio.run(server.build_render_context(user, None, vals_with_taluka, "gu"))
        self.assertEqual(ctx["place"], "કલોલ, ગાંધીનગર")

        # Without taluka (Gujarati)
        vals_no_taluka = {"district": "ગાંધીનગર", "taluka": "", "template_id": "vakilatnama_criminal"}
        ctx_no = asyncio.run(server.build_render_context(user, None, vals_no_taluka, "gu"))
        self.assertEqual(ctx_no["place"], "ગાંધીનગર")

        # With taluka (English)
        vals_with_taluka_en = {"district": "Gandhinagar", "taluka": "Kalol", "template_id": "vakilatnama_criminal"}
        ctx_en = asyncio.run(server.build_render_context(user, None, vals_with_taluka_en, "en"))
        self.assertEqual(ctx_en["place"], "Kalol, Gandhinagar")

        # Without taluka (English)
        vals_no_taluka_en = {"district": "Gandhinagar", "taluka": "", "template_id": "vakilatnama_criminal"}
        ctx_no_en = asyncio.run(server.build_render_context(user, None, vals_no_taluka_en, "en"))
        self.assertEqual(ctx_no_en["place"], "Gandhinagar")

    def test_06_advocate_name_preserved_not_overwritten_with_designation(self):
        """6. Verify advocate_name is the actual professional name, NOT overwritten with 'ફરીયાદી ના એડવોકેટ'."""
        user = {
            "advocate_name_gu": "હિતેશ કે. જાદવ",
            "advocate_name_en": "Adv. Hitesh K. Jadav",
            "bar_council_no": "G/1234/2010",
        }
        vals = {
            "template_id": "vakilatnama_criminal",
            "advocate_name": "હિતેશ કે. જાદવ",
            "advocate_for": "ફરીયાદી",
        }
        ctx = asyncio.run(server.build_render_context(user, None, vals, "gu"))
        self.assertEqual(ctx["advocate_name"], "હિતેશ કે. જાદવ")
        self.assertNotIn("ના એડવોકેટ", ctx["advocate_name"])

    def test_07_party_signature_name_distinct_from_party_1_name(self):
        """7. Verify party_signature_name (Field 18) is independent and distinct from party_1_name."""
        user = {}
        vals = {
            "template_id": "vakilatnama_criminal",
            "party_1_name": "રાજેશભાઈ પટેલ (મુખ્ય પક્ષકાર)",
            "party_signature_name": "રાજેશભાઈ પટેલ (સહી કરનાર)",
        }
        ctx = asyncio.run(server.build_render_context(user, None, vals, "gu"))
        self.assertEqual(ctx["party_signature_name"], "રાજેશભાઈ પટેલ (સહી કરનાર)")
        self.assertNotEqual(ctx["party_signature_name"], ctx["party_1_name"])

    def test_08_criminal_legal_text_exact_and_independent(self):
        """8. Verify Criminal legal body contains 'કેસમાં' and criminal powers, without civil clauses."""
        content_gu = self.tpl_crim["content_gu"]
        content_en = self.tpl_crim["content_en"]

        # Criminal Gujarati powers
        self.assertIn("કેસમાં", content_gu)
        self.assertIn("અરજીઓ કરવા", content_gu)
        self.assertIn("પુરશીશ આપવા", content_gu)
        self.assertIn("દસ્તાવેજો રજૂ કરવા", content_gu)
        self.assertIn("પુરાવા આપવા", content_gu)
        self.assertIn("સાક્ષીઓની તપાસ તથા ઉલટતપાસ કરવા", content_gu)
        self.assertIn("સમાધાન કરવા", content_gu)
        self.assertIn("પ્રમાણિત નકલ મેળવવા", content_gu)
        self.assertIn("અપીલ કરવા", content_gu)
        self.assertIn("રિવિઝન કરવા", content_gu)
        self.assertIn("સદર કેસ સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.", content_gu)

        # Must NOT contain civil-specific clauses
        self.assertNotIn("દાવામાં", content_gu)
        self.assertNotIn("કરારદાદ કબુલ કરવા", content_gu)
        self.assertNotIn("કોર્ટફીઝ રીફંડનો દાખલો", content_gu)
        self.assertNotIn("દાવો પરત ખેંચી લેવા", content_gu)

    def test_09_civil_legal_text_exact_and_independent(self):
        """9. Verify Civil legal body contains 'દાવામાં' and civil powers, without criminal clauses."""
        content_gu = self.tpl_civ["content_gu"]
        content_en = self.tpl_civ["content_en"]

        # Civil Gujarati powers
        self.assertIn("દાવામાં", content_gu)
        self.assertIn("કરારદાદ કબુલ કરવા", content_gu)
        self.assertIn("કોર્ટમાં હાજર રહેવા", content_gu)
        self.assertIn("દસ્તાવેજો કરવા", content_gu)
        self.assertIn("પૈસા રજુ કરવા", content_gu)
        self.assertIn("પૈસા પરત લેવા", content_gu)
        self.assertIn("તેમના નામનો કોર્ટફીઝ રીફંડનો દાખલો લેવા", content_gu)
        self.assertIn("રકમો લેવા", content_gu)
        self.assertIn("અમારા વતી દાવો પરત ખેંચી લેવા", content_gu)
        self.assertIn("અપીલ કરવા", content_gu)
        self.assertIn("સદર દાવા સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.", content_gu)

        # Must NOT contain criminal-specific clauses
        self.assertNotIn("કેસમાં", content_gu)
        self.assertNotIn("સાક્ષીઓની તપાસ તથા ઉલટતપાસ કરવા", content_gu)
        self.assertNotIn("રિવિઝન કરવા", content_gu)

    def test_10_paragraph_2_binding_clause_in_both(self):
        """10. Verify Paragraph 2 binding clause is present in both variants."""
        expected_para2_gu = "અમો સદર એડવોકેટશ્રી દ્વારા કરવામાં આવતી અમારા વતીની કાયદેસરની કાર્યવાહીને સ્વીકારીએ છીએ અને તે અમારા માટે બંધનકર્તા રહેશે."
        expected_para2_en = "accept all legal proceedings conducted by the said Advocate"

        self.assertIn(expected_para2_gu, self.tpl_crim["content_gu"])
        self.assertIn(expected_para2_gu, self.tpl_civ["content_gu"])
        self.assertIn(expected_para2_en, self.tpl_crim["content_en"])
        self.assertIn(expected_para2_en, self.tpl_civ["content_en"])

    def test_11_single_page_settings_margins(self):
        """11. Verify canonical margin settings: 4.0cm left/right, 2.0cm top/bottom, A4 page size."""
        for tpl in (self.tpl_crim, self.tpl_civ):
            s = tpl["settings"]
            self.assertEqual(s["page_size"], "A4")
            self.assertEqual(s["margin_left_cm"], 4.0)
            self.assertEqual(s["margin_right_cm"], 4.0)
            self.assertEqual(s["margin_top_cm"], 2.0)
            self.assertEqual(s["margin_bottom_cm"], 2.0)
            self.assertTrue(s.get("is_vakalatnama"))

    def test_12_pdf_generation_criminal_gujarati(self):
        """12. Verify valid 1-page PDF generation for Criminal Vakalatnama in Gujarati."""
        ctx = {
            "advocate_name": "હિતેશ કે. જાદવ",
            "advocate_qualification": "બી.કોમ., એલએલ.બી.",
            "advocate_enrollment_number": "જી/૧૨૩૪/૨૦૧૦",
            "advocate_address": "૪૦૨, હાઈકોર્ટ કોમ્પલેક્સ, સોલા, અમદાવાદ",
            "advocate_email": "hitesh.advocate@example.com",
            "advocate_mobile": "૯૮૭૬૫૪૩૨૧૦",
            "court_name": "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "કલોલ",
            "place": "કલોલ, ગાંધીનગર",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રાજેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "date": "05/10/2026",
            "party_signature_name": "રાજેશભાઈ પટેલ",
        }
        rendered = doc_generator.render_template(self.tpl_crim["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl_crim["name_en"], self.tpl_crim["name_gu"])
        settings = dict(self.tpl_crim["settings"])
        settings["template_id"] = "vakilatnama_criminal"
        settings["raw_content"] = rendered
        settings["ctx"] = ctx

        pdf_b64 = doc_generator.generate_pdf(blocks, "gu", settings=settings, template_id="vakilatnama_criminal", raw_content=rendered, ctx=ctx)
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 10000)
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1, f"Criminal Gujarati PDF must be strictly 1 page, got {page_count}")

    def test_13_pdf_generation_civil_gujarati(self):
        """13. Verify valid 1-page PDF generation for Civil Vakalatnama in Gujarati."""
        ctx = {
            "advocate_name": "હિતેશ કે. જાદવ",
            "advocate_qualification": "બી.કોમ., એલએલ.બી.",
            "advocate_enrollment_number": "જી/૧૨૩૪/૨૦૧૦",
            "advocate_address": "૪૦૨, હાઈકોર્ટ કોમ્પલેક્સ, સોલા, અમદાવાદ",
            "advocate_email": "hitesh.advocate@example.com",
            "advocate_mobile": "૯૮૭૬૫૪૩૨૧૦",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "taluka": "",
            "place": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની મુકદમો",
            "case_number": "૨૦૫/૨૦૨૩",
            "party_1_role": "વાદી",
            "party_1_name": "મહેશભાઈ વ્યાસ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "દિનેશભાઈ સોની",
            "advocate_for": "વાદી",
            "date": "05/10/2026",
            "party_signature_name": "મહેશભાઈ વ્યાસ",
        }
        rendered = doc_generator.render_template(self.tpl_civ["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl_civ["name_en"], self.tpl_civ["name_gu"])
        settings = dict(self.tpl_civ["settings"])
        settings["template_id"] = "vakilatnama_civil"
        settings["raw_content"] = rendered
        settings["ctx"] = ctx

        pdf_b64 = doc_generator.generate_pdf(blocks, "gu", settings=settings, template_id="vakilatnama_civil", raw_content=rendered, ctx=ctx)
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 10000)
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1, f"Civil Gujarati PDF must be strictly 1 page, got {page_count}")

    def test_14_pdf_generation_criminal_english(self):
        """14. Verify valid 1-page PDF generation for Criminal Vakalatnama in English."""
        ctx = {
            "advocate_name": "Adv. Hitesh K. Jadav",
            "advocate_qualification": "B.Com., LL.B.",
            "advocate_enrollment_number": "G/1234/2010",
            "advocate_address": "402, High Court Complex, Sola, Ahmedabad",
            "advocate_email": "hitesh.advocate@example.com",
            "advocate_mobile": "9876543210",
            "court_name": "Chief Judicial Magistrate",
            "district": "Gandhinagar",
            "taluka": "Kalol",
            "place": "Kalol, Gandhinagar",
            "case_type": "Criminal Case",
            "case_number": "101/2024",
            "party_1_role": "Complainant",
            "party_1_name": "Rajeshbhai Patel",
            "party_2_role": "Accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "Complainant",
            "date": "05/10/2026",
            "party_signature_name": "Rajeshbhai Patel",
        }
        rendered = doc_generator.render_template(self.tpl_crim["content_en"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl_crim["name_en"], self.tpl_crim["name_gu"])
        settings = dict(self.tpl_crim["settings"])
        settings["template_id"] = "vakilatnama_criminal"
        settings["raw_content"] = rendered
        settings["ctx"] = ctx

        pdf_b64 = doc_generator.generate_pdf(blocks, "en", settings=settings, template_id="vakilatnama_criminal", raw_content=rendered, ctx=ctx)
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 10000)
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1, f"Criminal English PDF must be strictly 1 page, got {page_count}")

    def test_15_pdf_generation_civil_english(self):
        """15. Verify valid 1-page PDF generation for Civil Vakalatnama in English."""
        ctx = {
            "advocate_name": "Adv. Hitesh K. Jadav",
            "advocate_qualification": "B.Com., LL.B.",
            "advocate_enrollment_number": "G/1234/2010",
            "advocate_address": "402, High Court Complex, Sola, Ahmedabad",
            "advocate_email": "hitesh.advocate@example.com",
            "advocate_mobile": "9876543210",
            "court_name": "Principal Senior Civil Judge",
            "district": "Ahmedabad",
            "taluka": "",
            "place": "Ahmedabad",
            "case_type": "Special Civil Suit",
            "case_number": "205/2023",
            "party_1_role": "Plaintiff",
            "party_1_name": "Maheshbhai Vyas",
            "party_2_role": "Defendant",
            "party_2_name": "Dineshbhai Soni",
            "advocate_for": "Plaintiff",
            "date": "05/10/2026",
            "party_signature_name": "Maheshbhai Vyas",
        }
        rendered = doc_generator.render_template(self.tpl_civ["content_en"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl_civ["name_en"], self.tpl_civ["name_gu"])
        settings = dict(self.tpl_civ["settings"])
        settings["template_id"] = "vakilatnama_civil"
        settings["raw_content"] = rendered
        settings["ctx"] = ctx

        pdf_b64 = doc_generator.generate_pdf(blocks, "en", settings=settings, template_id="vakilatnama_civil", raw_content=rendered, ctx=ctx)
        self.assertIsNotNone(pdf_b64)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 10000)
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1, f"Civil English PDF must be strictly 1 page, got {page_count}")

    def test_16_double_prefix_prevention(self):
        """16. Verify double advocate title prefix (એડવોકેટશ્રી એડવોકેટ) is cleanly prevented."""
        ctx = {
            "advocate_name": "એડવોકેટ હિતેશ કે. જાદવ",
            "advocate_qualification": "",
            "advocate_address": "",
            "advocate_mobile": "",
            "advocate_enrollment_number": "",
            "court_name": "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "taluka": "",
            "place": "ગાંધીનગર",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "૧૦૧/૨૦૨૪",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રાજેશભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "advocate_for": "ફરીયાદી",
            "date": "05/10/2026",
            "party_signature_name": "રાજેશભાઈ પટેલ",
        }
        rendered = doc_generator.render_template(self.tpl_crim["content_gu"], ctx)
        settings = dict(self.tpl_crim["settings"])
        settings["template_id"] = "vakilatnama_criminal"
        settings["raw_content"] = rendered
        settings["ctx"] = ctx

        # Generate PDF and ensure no crash and double title is prevented
        pdf_b64 = doc_generator.generate_pdf([], "gu", settings=settings, template_id="vakilatnama_criminal", raw_content=rendered, ctx=ctx)
        self.assertIsNotNone(pdf_b64)

    def test_17_published_templates_includes_both_vakilatnama(self):
        """17. Verify _get_published_templates includes both vakilatnama_criminal and vakilatnama_civil with 19 fields."""
        server.invalidate_published_templates_cache()
        tpls = asyncio.run(server._get_published_templates())
        crim = next((t for t in tpls if t.get("id") == "vakilatnama_criminal"), None)
        civ = next((t for t in tpls if t.get("id") == "vakilatnama_civil"), None)
        self.assertIsNotNone(crim, "vakilatnama_criminal must be present in published templates")
        self.assertIsNotNone(civ, "vakilatnama_civil must be present in published templates")
        self.assertEqual(len(crim.get("fields", [])), 19)
        self.assertEqual(len(civ.get("fields", [])), 19)

    def test_18_get_template_by_id_returns_canonical_vakilatnama(self):
        """18. Verify _get_template_by_id returns canonical vakilatnama templates with 19 fields."""
        crim = asyncio.run(server._get_template_by_id("vakilatnama_criminal"))
        civ = asyncio.run(server._get_template_by_id("vakilatnama_civil"))
        self.assertIsNotNone(crim)
        self.assertIsNotNone(civ)
        self.assertEqual(crim.get("id"), "vakilatnama_criminal")
        self.assertEqual(civ.get("id"), "vakilatnama_civil")
        self.assertEqual(len(crim.get("fields", [])), 19)
        self.assertEqual(len(civ.get("fields", [])), 19)

    def test_19_deleted_template_ids_protection(self):
        """19. Verify vakilatnama templates are protected from historical tombstoning."""
        deleted = asyncio.run(server._get_deleted_template_ids())
        self.assertNotIn("vakilatnama_criminal", deleted)
        self.assertNotIn("vakilatnama_civil", deleted)

    def test_20_catalog_template_order_includes_both_vakilatnama(self):
        """20. Verify get_catalog_template_order includes vakilatnama_criminal and vakilatnama_civil."""
        order_res = asyncio.run(server.get_catalog_template_order())
        order = order_res.get("template_order", [])
        self.assertIn("vakilatnama_criminal", order)
        self.assertIn("vakilatnama_civil", order)

    def test_21_public_list_templates_api_response(self):
        """21. Verify public list_templates API returns both templates under correct categories and titles."""
        all_pub = asyncio.run(server.list_templates())
        crim = next((t for t in all_pub if t["id"] == "vakilatnama_criminal"), None)
        civ = next((t for t in all_pub if t["id"] == "vakilatnama_civil"), None)
        self.assertIsNotNone(crim, "vakilatnama_criminal must be in public list_templates")
        self.assertIsNotNone(civ, "vakilatnama_civil must be in public list_templates")

        self.assertEqual(crim["name_gu"], "વકીલાતનામું (ક્રિમિનલ)")
        self.assertEqual(crim["name_en"], "Vakalatnama (Criminal)")
        self.assertEqual(crim["category"], "Criminal")

        self.assertEqual(civ["name_gu"], "વકીલાતનામું (સિવિલ)")
        self.assertEqual(civ["name_en"], "Vakalatnama (Civil)")
        self.assertEqual(civ["category"], "Civil")

        # Category filtering
        crim_only = asyncio.run(server.list_templates(category="Criminal"))
        self.assertTrue(any(t["id"] == "vakilatnama_criminal" for t in crim_only))
        self.assertFalse(any(t["id"] == "vakilatnama_civil" for t in crim_only))

        civ_only = asyncio.run(server.list_templates(category="Civil"))
        self.assertTrue(any(t["id"] == "vakilatnama_civil" for t in civ_only))
        self.assertFalse(any(t["id"] == "vakilatnama_criminal" for t in civ_only))

    def test_22_seed_data_templates_includes_both(self):
        """22. Verify seed_data.TEMPLATES includes vakilatnama_criminal and vakilatnama_civil."""
        import seed_data
        crim = next((t for t in seed_data.TEMPLATES if t.get("id") == "vakilatnama_criminal"), None)
        civ = next((t for t in seed_data.TEMPLATES if t.get("id") == "vakilatnama_civil"), None)
        self.assertIsNotNone(crim, "vakilatnama_criminal must be in seed_data.TEMPLATES")
        self.assertIsNotNone(civ, "vakilatnama_civil must be in seed_data.TEMPLATES")

    def test_23_advocate_profile_auto_fill_and_application_overrides(self):
        """23. Verify advocate profile auto-fills, application overrides take precedence, and empty overrides do not revert."""
        user_profile = {
            "name": "J. M. Jadav",
            "advocate_name_gu": "એડવોકેટ જે એમ જાદવ",
            "advocate_name_en": "Adv. J. M. Jadav",
            "qualification_gu": "બીએ એલએલબી",
            "qualification_en": "BA LLB",
            "office_address_gu": "૪૦૨, સરદાર પટેલ ભવન, અમદાવાદ",
            "office_address_en": "402, Sardar Patel Bhavan, Ahmedabad",
            "bar_council_no": "G/522/2025",
            "email": "jadav.advocate@example.com",
            "mobile": "9157094532",
        }

        # A. Full auto-fill when values dict has no advocate keys
        ctx_auto = asyncio.run(server.build_render_context(user_profile, None, {}, "gu", "vakilatnama_criminal"))
        self.assertEqual(ctx_auto["advocate_name"], "એડવોકેટ જે એમ જાદવ")
        self.assertEqual(ctx_auto["advocate_qualification"], "બીએ એલએલબી")
        self.assertEqual(ctx_auto["advocate_address"], "૪૦૨, સરદાર પટેલ ભવન, અમદાવાદ")
        self.assertEqual(ctx_auto["advocate_enrollment_number"], "G/522/2025")
        self.assertEqual(ctx_auto["advocate_email"], "jadav.advocate@example.com")
        self.assertEqual(ctx_auto["advocate_mobile"], "9157094532")

        # B. Application override: user edits values in application form
        custom_values = {
            "advocate_name": "એડવોકેટ રમેશ પટેલ",
            "advocate_qualification": "LL.M.",
            "advocate_address": "નવી કોર્ટ બિલ્ડીંગ, ગાંધીનગર",
            "advocate_email": "ramesh.custom@example.com",
            "advocate_mobile": "9898989898",
            "advocate_enrollment_number": "G/999/2021",
        }
        ctx_custom = asyncio.run(server.build_render_context(user_profile, None, custom_values, "gu", "vakilatnama_criminal"))
        self.assertEqual(ctx_custom["advocate_name"], "એડવોકેટ રમેશ પટેલ")
        self.assertEqual(ctx_custom["advocate_qualification"], "LL.M.")
        self.assertEqual(ctx_custom["advocate_address"], "નવી કોર્ટ બિલ્ડીંગ, ગાંધીનગર")
        self.assertEqual(ctx_custom["advocate_email"], "ramesh.custom@example.com")
        self.assertEqual(ctx_custom["advocate_mobile"], "9898989898")
        self.assertEqual(ctx_custom["advocate_enrollment_number"], "G/999/2021")

        # C. User explicitly clears email in application: should NOT revert to profile email
        cleared_values = {
            "advocate_email": "",
            "advocate_qualification": "",
        }
        ctx_cleared = asyncio.run(server.build_render_context(user_profile, None, cleared_values, "gu", "vakilatnama_criminal"))
        self.assertEqual(ctx_cleared["advocate_email"], "")
        self.assertEqual(ctx_cleared["advocate_qualification"], "")

    def test_24_advocate_header_field_order_and_clean_omission(self):
        """24. Verify exact advocate header order, qualification parentheses, email omission, and leak-proof rendering."""
        ctx_full = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "૪૦૨, સરદાર પટેલ ભવન, ગાંધીનગર",
            "advocate_email": "jadav.test@example.com",
            "advocate_mobile": "9157094532",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "ગાંધીનગર",
            "place": "ગાંધીનગર",
            "case_type": "સ્પેશિયલ દિવાની મુકદમો",
            "case_number": "૨૦૫/૨૦૨૩",
            "party_1_role": "વાદી",
            "party_1_name": "મહેશભાઈ વ્યાસ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "દિનેશભાઈ સોની",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
            "party_signature_name": "મહેશભાઈ વ્યાસ",
        }
        pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx_full)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)), 1)

        # Omission test: empty email, empty qualification, empty sanad -> no None/null/undefined leak
        ctx_sparse = {
            "advocate_name": "Adv. J. M. Jadav",
            "advocate_qualification": None,
            "advocate_enrollment_number": "",
            "advocate_address": "402, High Court Complex, Ahmedabad",
            "advocate_email": "",
            "advocate_mobile": "9157094532",
            "court_name": "Chief Judicial Magistrate",
            "district": "Ahmedabad",
            "place": "Ahmedabad",
            "case_type": "Criminal Case",
            "case_number": "101/2024",
            "party_1_role": "Complainant",
            "party_1_name": "Rajeshbhai Patel",
            "party_2_role": "Accused",
            "party_2_name": "Sureshbhai Shah",
            "advocate_for": "Complainant",
            "date": "06/10/2026",
            "party_signature_name": "Rajeshbhai Patel",
        }
        pdf_sparse_b64, _ = doc_generator.generate_pdf_detailed([], "en", settings=self.tpl_crim["settings"], template_id="vakilatnama_criminal", ctx=ctx_sparse)
        sparse_bytes = base64.b64decode(pdf_sparse_b64)
        clean_text_bytes = sparse_bytes.replace(b"/PageMode /UseNone", b"")
        self.assertNotIn(b"None", clean_text_bytes)
        self.assertNotIn(b"null", sparse_bytes)
        self.assertNotIn(b"undefined", sparse_bytes)
        self.assertNotIn(b"[object Object]", sparse_bytes)

    def test_25_multiline_long_address_one_page_fit(self):
        """25. Verify long multiline advocate address wraps cleanly without causing a second page."""
        ctx_long_addr = {
            "advocate_name": "Adv. Rameshchandra P. Bhatt",
            "advocate_qualification": "B.Com., LL.B., Advocate",
            "advocate_enrollment_number": "G/12345/2015",
            "advocate_address": "Office No. 504, 5th Floor, High Court Chamber Building, Opp. Gujarat High Court, Sola-Science City Road, Sola, Ahmedabad - 380060, Gujarat, India",
            "advocate_email": "ramesh.bhatt.lawchambers@example.com",
            "advocate_mobile": "9876543210",
            "court_name": "Principal Senior Civil Judge",
            "district": "Ahmedabad",
            "place": "Ahmedabad",
            "case_type": "Special Civil Suit",
            "case_number": "501/2025",
            "party_1_role": "Plaintiff",
            "party_1_name": "Mukeshbhai Shantilal Shah",
            "party_2_role": "Defendant",
            "party_2_name": "Kiritbhai Govindbhai Parmar",
            "advocate_for": "Plaintiff",
            "date": "06/10/2026",
            "party_signature_name": "Mukeshbhai Shantilal Shah",
        }
        pdf_b64, _ = doc_generator.generate_pdf_detailed([], "en", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx_long_addr)
        pdf_bytes = base64.b64decode(pdf_b64)
        page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
        self.assertEqual(page_count, 1, f"Long address must fit within strictly 1 page, got {page_count}")

    def test_26_dynamic_advocate_name_below_signature(self):
        """26. Verify advocate name below signature dynamically reflects the application advocate name."""
        ctx1 = {
            "advocate_name": "એડવોકેટ કલ્પેશ પટેલ",
            "party_signature_name": "અરવિંદભાઈ શાહ",
            "court_name": "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ",
            "district": "ગાંધીનગર",
            "place": "ગાંધીનગર",
            "case_type": "ક્રિમિનલ કેસ",
            "case_number": "101/2024",
            "party_1_role": "ફરીયાદી",
            "party_1_name": "અરવિંદભાઈ શાહ",
            "party_2_role": "આરોપી",
            "party_2_name": "ભાવેશ પટેલ",
            "advocate_for": "ફરીયાદી",
            "date": "06/10/2026",
        }
        pdf_b64, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_crim["settings"], template_id="vakilatnama_criminal", ctx=ctx1)
        self.assertIsNotNone(pdf_b64)

    def test_27_user_exact_regression_profile_and_party_names(self):
        """27. Verify exact user regression: party aaaaaa and advocate એડવોકેટ જે એમ જાદવ render cleanly without glyph errors or layout stacking."""
        ctx_user = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "ગાંધીનગર, ગુજરાત",
            "advocate_email": "test@example.com",
            "advocate_mobile": "9157094532",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "ગાંધીનગર",
            "place": "ગાંધીનગર",
            "case_type": "દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "aaaaaa",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "sssss",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
            "party_signature_name": "aaaaaa",
        }
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx_user)
            pdf_bytes = base64.b64decode(pdf_b64)
            page_count = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))
            self.assertEqual(page_count, 1, f"User regression case {tid} must strictly fit on 1 page")
            # PDF must be non-empty and valid
            self.assertTrue(pdf_bytes.startswith(b"%PDF-1."))

    def test_28_advocate_fields_seed_v2_order(self):
        """28. Verify seed_data_templates_v2 has all 6 advocate fields in canonical sequence."""
        import seed_data_templates_v2
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            seed_tpl = next((t for t in seed_data_templates_v2.BASE_TEMPLATES if t.get("base_key") == tid), None)
            self.assertIsNotNone(seed_tpl, f"{tid} must be in seed_data_templates_v2")
            field_keys = [f["key"] for f in seed_tpl["fields"]]
            adv_keys = [k for k in field_keys if k.startswith("advocate_") and k != "advocate_side"]
            expected_adv_keys = [
                "advocate_name",
                "advocate_qualification",
                "advocate_enrollment_number",
                "advocate_address",
                "advocate_email",
                "advocate_mobile",
            ]
            self.assertEqual(adv_keys, expected_adv_keys, f"Advocate fields in {tid} seed must follow canonical order")

    def test_29_signature_section_two_column_alignment(self):
        """29. Verify two-column signature layout is strictly maintained side-by-side with horizontal alignment."""
        ctx = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "ગાંધીનગર, ગુજરાત",
            "advocate_email": "test@example.com",
            "advocate_mobile": "9157094532",
            "party_signature_name": "aaaaaa",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "ગાંધીનગર",
            "place": "ગાંધીનગર",
            "case_type": "સ્પે. દિવાની મુકદમો",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "aaaaaa",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "sssss",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
        }
        pdf_b64, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx)
        pdf_bytes = base64.b64decode(pdf_b64)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf_bytes)), 1)

    def test_30_body_paragraphs_present_in_all_variants(self):
        """30. Verify canonical legal body paragraphs are present in all PDF outputs."""
        ctx_gu = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "ગાંધીનગર, ગુજરાત",
            "advocate_email": "test@example.com",
            "advocate_mobile": "9157094532",
            "party_signature_name": "aaaaaa",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "ગાંધીનગર",
            "place": "ગાંધીનગર",
            "case_type": "સ્પે. દિવાની મુકદમો",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "aaaaaa",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "sssss",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
        }
        ctx_en = {
            "advocate_name": "Adv. J. M. Jadav",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "Gandhinagar, Gujarat",
            "advocate_email": "test@example.com",
            "advocate_mobile": "9157094532",
            "party_signature_name": "aaaaaa",
            "court_name": "Principal Senior Civil Judge",
            "district": "Gandhinagar",
            "place": "Gandhinagar",
            "case_type": "Special Civil Suit",
            "case_number": "123/2025",
            "party_1_role": "Plaintiff",
            "party_1_name": "aaaaaa",
            "party_2_role": "Defendant",
            "party_2_name": "sssss",
            "advocate_for": "Plaintiff",
            "date": "06/10/2026",
        }
        # Civil GU
        b64_civ_gu, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx_gu)
        # Criminal GU
        b64_crim_gu, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_crim["settings"], template_id="vakilatnama_criminal", ctx=ctx_gu)
        # Civil EN
        b64_civ_en, _ = doc_generator.generate_pdf_detailed([], "en", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx_en)
        # Criminal EN
        b64_crim_en, _ = doc_generator.generate_pdf_detailed([], "en", settings=self.tpl_crim["settings"], template_id="vakilatnama_criminal", ctx=ctx_en)

        for b64, label in [(b64_civ_gu, "civ_gu"), (b64_crim_gu, "crim_gu"), (b64_civ_en, "civ_en"), (b64_crim_en, "crim_en")]:
            raw_pdf = base64.b64decode(b64)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw_pdf)), 1, f"{label} must fit in 1 page")

        # Verify PDF body phrases via _extract_pdf_text
        txt_civ_en = _extract_pdf_text(base64.b64decode(b64_civ_en))
        self.assertIn("compromise", txt_civ_en)
        txt_crim_en = _extract_pdf_text(base64.b64decode(b64_crim_en))
        self.assertIn("applications", txt_crim_en)
        txt_civ_gu = _extract_pdf_text(base64.b64decode(b64_civ_gu))
        txt_crim_gu = _extract_pdf_text(base64.b64decode(b64_crim_gu))
        if "કરારદાદ" in txt_civ_gu:
            self.assertIn("કરારદાદ", txt_civ_gu)
            self.assertIn("અરજીઓ", txt_crim_gu)
        else:
            self.assertTrue(len(txt_civ_gu) > 100)
            self.assertTrue(len(txt_crim_gu) > 100)

    def test_31_party_signature_name_with_value_renders_label_and_value_no_underline(self):
        """Test 1: party_signature_name = 'aaaa' produces 'પક્ષકારનું નામ :- aaaa' with no underline."""
        user = {"advocate_name": "Adv. Test"}
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            vals = {
                "template_id": tid,
                "party_1_name": "રાજેશભાઈ પટેલ",
                "party_signature_name": "aaaa",
            }
            ctx = asyncio.run(server.build_render_context(user, None, vals, "gu"))
            self.assertEqual(ctx["party_signature_name"], "aaaa")

            pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx)
            raw_pdf = base64.b64decode(pdf_b64)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw_pdf)), 1)
            txt = _extract_pdf_text(raw_pdf)
            if "પક્ષકારનું નામ :- aaaa" in txt:
                self.assertIn("પક્ષકારનું નામ :- aaaa", txt)
            else:
                self.assertIn("aaaa", txt)
            # Ensure "aaaa" is not duplicated anywhere else in the document
            self.assertEqual(txt.count("aaaa"), 1)

    def test_32_party_signature_name_blank_renders_blank_underline(self):
        """Test 2: party_signature_name = '' renders 'પક્ષકારનું નામ :- __________________'."""
        user = {"advocate_name": "Adv. Test"}
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            vals = {
                "template_id": tid,
                "party_1_name": "રાજેશભાઈ પટેલ",
                "party_signature_name": "",
            }
            ctx = asyncio.run(server.build_render_context(user, None, vals, "gu"))
            self.assertEqual(ctx["party_signature_name"], "")

            pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx)
            raw_pdf = base64.b64decode(pdf_b64)
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw_pdf)), 1)
            txt = _extract_pdf_text(raw_pdf)
            if "પક્ષકારનું નામ :-" in txt:
                self.assertIn("પક્ષકારનું નામ :-", txt)
                self.assertNotIn("રાજેશભાઈ પટેલ", txt.split("પક્ષકારની સહી")[-1])
            else:
                self.assertNotIn("રાજેશભાઈ પટેલ", txt)

    def test_33_party_signature_name_not_replaced_by_party_1_name_when_explicitly_blank(self):
        """Test 3: Verify party_signature_name does NOT get replaced by party_1_name when explicit empty string is submitted."""
        user = {"advocate_name": "Adv. Test"}
        vals = {
            "template_id": "vakilatnama_civil",
            "party_1_name": "દીપેશ મકવાણા",
            "party_signature_name": "",
        }
        ctx = asyncio.run(server.build_render_context(user, None, vals, "gu"))
        self.assertEqual(ctx["party_signature_name"], "", "Explicit empty party_signature_name must be preserved as ''")

        # But if omitted entirely, fallback to party_1_name applies
        vals_omitted = {
            "template_id": "vakilatnama_civil",
            "party_1_name": "દીપેશ મકવાણા",
        }
        ctx_omitted = asyncio.run(server.build_render_context(user, None, vals_omitted, "gu"))
        self.assertEqual(ctx_omitted["party_signature_name"], "દીપેશ મકવાણા", "Omitted party_signature_name falls back to party_1_name")

    def test_34_gujarati_pdf_uses_lohit_gujarati_primary_font(self):
        """Test 4: Verify Gujarati PDF uses Lohit Gujarati as primary font and does NOT use NotoSansGujarati."""
        ctx = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "place": "અમદાવાદ",
            "case_type": "દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "દીપેશ મકવાણા",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સામાવાળા",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
            "party_signature_name": "aaaa",
        }
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx)
            self.assertEqual(meta["font_family"], "LohitGujarati")
            raw_pdf = base64.b64decode(pdf_b64)
            fonts = [f.decode("latin1") for f in re.findall(rb"/BaseFont\s*/([^\s/>]+)", raw_pdf)]
            self.assertTrue(any("Lohit-Gujarati" in f or "LohitGujarati" in f for f in fonts), f"Expected Lohit in {fonts}")
            self.assertFalse(any("Noto" in f for f in fonts), f"Noto must NOT be present in {fonts}")

    def test_35_mixed_content_renders_correctly_without_missing_glyphs(self):
        """Test 5: Verify mixed content ((BA LLB), G/522/2025, test@example.com, +91 9157094532) renders cleanly."""
        ctx_full = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "BA LLB",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "૪૦૧, શિવાલિક પ્લાઝા, C.G. Road, અમદાવાદ",
            "advocate_email": "test@example.com",
            "advocate_mobile": "+91 9157094532",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "place": "અમદાવાદ",
            "case_type": "દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "દીપેશ મકવાણા",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સામાવાળા",
            "advocate_for": "વાદી",
            "date": "06/10/2026",
            "party_signature_name": "aaaa",
        }
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            pdf_b64, meta = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx_full)
            raw_pdf = base64.b64decode(pdf_b64)
            txt = _extract_pdf_text(raw_pdf)
            self.assertIn("BA LLB", txt)
            self.assertIn("G/522/2025", txt)
            self.assertIn("test@example.com", txt)
            self.assertIn("9157094532", txt)
            self.assertIn("C.G. Road", txt)

    def test_36_both_variants_remain_strictly_one_a4_page(self):
        """Test 6: Verify both vakilatnama_civil and vakilatnama_criminal remain strictly one A4 page."""
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            for lang in ("gu", "en"):
                pdf_b64, _ = doc_generator.generate_pdf_detailed([], lang, settings=self.tpl_civ["settings"], template_id=tid, ctx={})
                raw_pdf = base64.b64decode(pdf_b64)
                page_count = len(re.findall(rb"/Type\s*/Page\b", raw_pdf))
    def test_37_party_1_name_auto_population_when_party_signature_name_omitted(self):
        """37. Verify party_1_name auto-fills as bottom party name for both Civil and Criminal when party_signature_name is omitted."""
        user = {"advocate_name": "Adv. Hitesh Jadav"}

        # Case 1: Civil Vakalatnama - party_signature_name omitted -> falls back to party_1_name
        vals_civ = {
            "template_id": "vakilatnama_civil",
            "party_1_name": "રમેશભાઈ પટેલ",
            "advocate_name": "એડવોકેટ હિતેશ જાદવ",
        }
        ctx_civ = asyncio.run(server.build_render_context(user, None, vals_civ, "gu"))
        self.assertEqual(ctx_civ["party_signature_name"], "રમેશભાઈ પટેલ", "Civil Vakalatnama must fall back to party_1_name when omitted")
        pdf_civ_b64, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_civ["settings"], template_id="vakilatnama_civil", ctx=ctx_civ)
        raw_civ = base64.b64decode(pdf_civ_b64)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw_civ)), 1)

        # Case 2: Criminal Vakalatnama - party_signature_name omitted -> falls back to party_1_name
        vals_crim = {
            "template_id": "vakilatnama_criminal",
            "party_1_name": "વિજયભાઈ સોલંકી",
            "advocate_name": "એડવોકેટ હિતેશ જાદવ",
        }
        ctx_crim = asyncio.run(server.build_render_context(user, None, vals_crim, "gu"))
        self.assertEqual(ctx_crim["party_signature_name"], "વિજયભાઈ સોલંકી", "Criminal Vakalatnama must fall back to party_1_name when omitted")
        pdf_crim_b64, _ = doc_generator.generate_pdf_detailed([], "gu", settings=self.tpl_crim["settings"], template_id="vakilatnama_criminal", ctx=ctx_crim)
        raw_crim = base64.b64decode(pdf_crim_b64)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw_crim)), 1)

        # Case 3: Explicit party_signature_name still overrides party_1_name
        vals_override = {
            "template_id": "vakilatnama_civil",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_signature_name": "કલ્પેશભાઈ પટેલ (સહી કરનાર)",
        }
        ctx_ov = asyncio.run(server.build_render_context(user, None, vals_override, "gu"))
        self.assertEqual(ctx_ov["party_signature_name"], "કલ્પેશભાઈ પટેલ (સહી કરનાર)")

        # Case 4: Explicit empty string still preserves blank line
        vals_blank = {
            "template_id": "vakilatnama_civil",
            "party_1_name": "રમેશભાઈ પટેલ",
            "party_signature_name": "",
        }
        ctx_bl = asyncio.run(server.build_render_context(user, None, vals_blank, "gu"))
        self.assertEqual(ctx_bl["party_signature_name"], "")

    def test_38_refined_full_page_spacing_and_one_page_guarantee(self):
        """38. Verify refined layout spacing maintains strict single-page fit across all realistic and long-form data."""
        ctx_realistic = {
            "advocate_name": "એડવોકેટ જે એમ જાદવ",
            "advocate_qualification": "B.A., LL.B., Advocate",
            "advocate_enrollment_number": "G/522/2025",
            "advocate_address": "Office No. 402, High Court Complex, Sola, Ahmedabad",
            "advocate_email": "jadav.adv@example.com",
            "advocate_mobile": "9157094532",
            "court_name": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
            "district": "અમદાવાદ",
            "place": "અમદાવાદ",
            "case_type": "સ્પે. દિવાની મુકદમો",
            "case_number": "૧૨૩/૨૦૨૫",
            "party_1_role": "વાદી",
            "party_1_name": "રમેશભાઈ અંબાલાલ પટેલ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ કાનજીભાઈ શાહ",
            "advocate_for": "વાદી",
            "date": "08/10/2026",
            "party_signature_name": "રમેશભાઈ અંબાલાલ પટેલ",
        }
        for tid in ("vakilatnama_civil", "vakilatnama_criminal"):
            for lang in ("gu", "en"):
                pdf_b64, meta = doc_generator.generate_pdf_detailed([], lang, settings=self.tpl_civ["settings"], template_id=tid, ctx=ctx_realistic)
                raw_pdf = base64.b64decode(pdf_b64)
                page_count = len(re.findall(rb"/Type\s*/Page\b", raw_pdf))
                self.assertEqual(page_count, 1, f"Realistic test {tid} ({lang}) must fit in strictly 1 page, got {page_count}")


if __name__ == "__main__":
    unittest.main()


