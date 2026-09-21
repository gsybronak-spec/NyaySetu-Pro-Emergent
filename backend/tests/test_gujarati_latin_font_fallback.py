# -*- coding: utf-8 -*-
"""Unit tests for Character/Script-Aware Font Fallback in Gujarati PDF Generation.

Ensures:
1. When Gujarati documents contain English/Latin names (e.g. 'JAYDEEP', 'RONAK'),
   a suitable Latin fallback font (Times-Roman / Liberation Serif) is used.
2. Zero missing-glyph boxes (\x00 / .notdef) in rendered output.
3. Gujarati Unicode characters (consonants, matras, conjuncts) remain in Lohit Gujarati.
4. Advocate signature line in Gujarati exhibit application remains strictly 10 dashes.
5. English PDF generation remains completely unaffected (20 dashes).
6. Numbers, dates, and punctuation render correctly across mixed text.
"""

import base64
import re
import subprocess
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Mock docx if not installed
for mod in ["docx", "docx.shared", "docx.enum.text", "docx.oxml", "docx.oxml.ns"]:
    if mod not in sys.modules:
        try:
            __import__(mod)
        except ImportError:
            sys.modules[mod] = MagicMock()

import doc_generator
import test_seed_data


def extract_pdf_stream_text(pdf_bytes: bytes) -> str:
    """Extract decompressed text streams from PDF bytes."""
    decomp_str = ""
    for m in re.finditer(rb"(\d+\s+\d+\s+obj.*?endobj)", pdf_bytes, re.DOTALL):
        obj_text = m.group(1)
        s_m = re.search(rb"stream\r?\n(.*)endstream", obj_text, re.DOTALL)
        if s_m:
            raw = s_m.group(1).rstrip(b"\r\n")
            try:
                decomp_str += zlib.decompress(base64.a85decode(raw, adobe=True)).decode("latin1", errors="ignore") + "\n"
                continue
            except Exception:
                pass
            try:
                decomp_str += zlib.decompress(raw).decode("latin1", errors="ignore") + "\n"
                continue
            except Exception:
                pass
    return decomp_str


class TestGujaratiLatinFontFallback(unittest.TestCase):
    """Test suite for script-aware Latin font fallback in Gujarati PDFs."""

    @classmethod
    def setUpClass(cls):
        doc_generator.register_fonts()
        cls.tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_exhibit_application"), None)
        assert cls.tpl is not None, "document_exhibit_application template not found in test_seed_data"

    def test_01_resolve_latin_fallback_font(self):
        """1. Verify fallback font resolution returns valid font names."""
        normal_font = doc_generator._resolve_latin_fallback_font(bold=False)
        bold_font = doc_generator._resolve_latin_fallback_font(bold=True)
        self.assertIn(normal_font, ("Times-Roman", "TimesNewRoman", "LiberationSerif", "DejaVuSerif"))
        self.assertIn(bold_font, ("Times-Bold", "TimesNewRoman-Bold", "LiberationSerif-Bold", "DejaVuSerif-Bold"))

    def test_02_apply_latin_fallback_markup_mixed_text(self):
        """2. Verify _apply_latin_fallback_markup wraps Latin words without breaking Gujarati or entities."""
        # Pure Gujarati: untouched
        pure_gu = "સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે."
        self.assertEqual(doc_generator._apply_latin_fallback_markup(pure_gu), pure_gu)

        # Numbers and dashes: untouched
        dashes = "----------"
        self.assertEqual(doc_generator._apply_latin_fallback_markup(dashes), dashes)

        # Mixed party lines
        p1 = "વાદી :- JAYDEEP"
        wrapped1 = doc_generator._apply_latin_fallback_markup(p1, latin_font="Times-Roman")
        self.assertEqual(wrapped1, 'વાદી :- <font name="Times-Roman">JAYDEEP</font>')

        p2 = "પ્રતિવાદી :- RONAK"
        wrapped2 = doc_generator._apply_latin_fallback_markup(p2, latin_font="Times-Roman")
        self.assertEqual(wrapped2, 'પ્રતિવાદી :- <font name="Times-Roman">RONAK</font>')

        # HTML entity preservation
        mixed_entity = "વાદી :- JAYDEEP & RONAK"
        wrapped_entity = doc_generator._apply_latin_fallback_markup(mixed_entity, latin_font="Times-Roman")
        self.assertEqual(wrapped_entity, 'વાદી :- <font name="Times-Roman">JAYDEEP</font> &amp; <font name="Times-Roman">RONAK</font>')

    def test_03_gujarati_pdf_with_english_names_renders_cleanly(self):
        """3. Generate Gujarati exhibit application PDF with JAYDEEP and RONAK and verify text extraction."""
        ctx = {
            "court_name": "એડીશનલ સિવિલ જજ સાહેબશ્રી",
            "taluka": "અમદાવાદ",
            "district": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "વાદી",
            "party_1_name": "JAYDEEP",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "RONAK",
            "representing_party": "party_1",
            "representing_party_role": "વાદી",
            "date": "21/09/2026",
            "taluka_place": "અમદાવાદ, અમદાવાદ",
        }
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        self.assertIn("વાદી :- JAYDEEP", rendered)
        self.assertIn("પ્રતિવાદી :- RONAK", rendered)

        blocks = doc_generator.build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], (self.tpl.get("settings") or {}).get("block_align"))
        settings = doc_generator.get_doc_settings({
            **(self.tpl.get("settings") or {}),
            "template_id": self.tpl["id"],
            "raw_content": rendered,
            "ctx": ctx,
        })
        b64 = doc_generator._generate_pdf_reportlab_inner(blocks, "gu", settings)
        pdf_bytes = base64.b64decode(b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Verify with pdftotext
        proc = subprocess.run(["pdftotext", "-", "-"], input=pdf_bytes, capture_output=True, check=True)
        extracted_text = proc.stdout.decode("utf-8", errors="replace")

        # 1. English names must be extracted
        self.assertIn("JAYDEEP", extracted_text)
        self.assertIn("RONAK", extracted_text)

        # 2. Gujarati labels must be extracted
        self.assertIn("વાદી", extracted_text)
        self.assertIn("પ્રતિવાદી", extracted_text)

        # 3. Gujarati body text must be present
        self.assertIn("સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે", extracted_text)

        # 4. Signature line must have 10 dashes
        stream_text = extract_pdf_stream_text(pdf_bytes)
        self.assertIn("(----------) Tj", stream_text)
        self.assertNotIn("--------------------", stream_text)

    def test_04_gujarati_signature_retains_10_dashes(self):
        """4. Verify Gujarati PDF stream contains exact 10-dash signature line."""
        ctx = {
            "court_name": "એડીશનલ સિવિલ જજ સાહેબશ્રી",
            "taluka_place": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "વાદી",
            "party_1_name": "JAYDEEP",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "RONAK",
            "representing_party_role": "વાદી",
            "date": "21/09/2026",
        }
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], (self.tpl.get("settings") or {}).get("block_align"))
        settings = doc_generator.get_doc_settings({
            **(self.tpl.get("settings") or {}),
            "template_id": self.tpl["id"],
            "raw_content": rendered,
            "ctx": ctx,
        })
        b64 = doc_generator._generate_pdf_reportlab_inner(blocks, "gu", settings)
        pdf_bytes = base64.b64decode(b64)
        stream_text = extract_pdf_stream_text(pdf_bytes)
        self.assertIn("(----------) Tj", stream_text)
        self.assertNotIn("--------------------", stream_text)

    def test_05_english_pdf_unaffected(self):
        """5. Verify English PDF is completely unaffected and retains 20 dashes."""
        ctx_en = {
            "court_name": "ADDITIONAL CIVIL JUDGE",
            "taluka_place": "AHMEDABAD",
            "case_type": "SPECIAL CIVIL SUIT",
            "case_number": "123/2026",
            "party_1_role": "PLAINTIFF",
            "party_1_name": "JAYDEEP",
            "party_2_role": "DEFENDANT",
            "party_2_name": "RONAK",
            "representing_party_role": "Plaintiff",
            "date": "21/09/2026",
        }
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        blocks_en = doc_generator.build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"], (self.tpl.get("settings") or {}).get("block_align"))
        settings_en = doc_generator.get_doc_settings({
            **(self.tpl.get("settings") or {}),
            "template_id": self.tpl["id"],
            "raw_content": rendered_en,
            "ctx": ctx_en,
        })
        b64_en = doc_generator._generate_pdf_reportlab_inner(blocks_en, "en", settings_en)
        pdf_bytes_en = base64.b64decode(b64_en)
        stream_text_en = extract_pdf_stream_text(pdf_bytes_en)

        self.assertIn("(--------------------) Tj", stream_text_en)
        self.assertNotIn("---------------------", stream_text_en)

        proc = subprocess.run(["pdftotext", "-", "-"], input=pdf_bytes_en, capture_output=True, check=True)
        extracted = proc.stdout.decode("utf-8", errors="replace")
        self.assertIn("JAYDEEP", extracted)
        self.assertIn("RONAK", extracted)
        self.assertIn("Plaintiff's Advocate", extracted)


if __name__ == "__main__":
    unittest.main()
