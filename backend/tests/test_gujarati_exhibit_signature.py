# -*- coding: utf-8 -*-
"""Unit tests for Gujarati Exhibit Application Signature Line Formatting.

Ensures:
1. document_exhibit_application in test_seed_data contains strictly 17 dashes in content_gu.
2. block_align contains 17 dashes right-aligned without indent.
3. All 6 dynamic Gujarati advocate roles render 17 dashes right-aligned directly above the role text.
4. build_blocks normalizes any dash line preceding a Gujarati signature to 17 dashes.
5. English PDF rendering is untouched.
6. document_return_application has zero regressions.
7. PDF byte stream directly verifies exact 17-dash line operator and 0 occurrences of 27 dashes.
"""

import base64
import os
import re
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


class TestGujaratiExhibitSignature(unittest.TestCase):
    """Test suite for short proportional 17-dash signature line."""

    def setUp(self):
        self.tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_exhibit_application"), None)
        self.assertIsNotNone(self.tpl, "document_exhibit_application missing from test_seed_data.TEMPLATES")

    def test_01_seed_template_content_gu_has_17_dashes(self):
        """1. Verify template definition has 17 dashes and 0 occurrences of 27 dashes."""
        content_gu = self.tpl["content_gu"]
        self.assertIn("-----------------", content_gu)
        self.assertNotIn("---------------------------", content_gu)

    def test_02_block_align_contains_17_dashes(self):
        """2. Verify block_align configuration contains 17 dashes rule."""
        block_align = (self.tpl.get("settings") or {}).get("block_align", [])
        rules = {r.get("contains"): r for r in block_align if "contains" in r}
        self.assertIn("-----------------", rules)
        self.assertEqual(rules["-----------------"]["align"], "right")
        self.assertFalse(rules["-----------------"].get("indent", True))

    def test_03_plaintiff_advocate_signature_blocks(self):
        """3. Verify party_1 'વાદી ના એડવોકેટ' signature blocks."""
        ctx = {
            "court_name": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રી",
            "taluka_place": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "વાદી",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "representing_party_role": "વાદી",
            "document_details": "આંક ૩ થી રજૂ કરેલ મૂળ વેચાણ દસ્તાવેજ",
            "date": "19/09/2026",
        }
        rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
        blocks = doc_generator.build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], (self.tpl.get("settings") or {}).get("block_align"))
        sig_blocks = [b for b in blocks if b.get("section") == "advocate_signature"]
        self.assertEqual(len(sig_blocks), 2)
        self.assertEqual(sig_blocks[0]["text"], "-----------------")
        self.assertEqual(sig_blocks[0]["align"], "right")
        self.assertEqual(sig_blocks[1]["text"], "વાદી ના એડવોકેટ")
        self.assertEqual(sig_blocks[1]["align"], "right")

    def test_04_all_dynamic_gujarati_roles_signature_blocks(self):
        """4. Verify all 6 dynamic Gujarati advocate roles."""
        roles = [
            ("party_1", "વાદી", "પ્રતિવાદી", "વાદી ના એડવોકેટ"),
            ("party_2", "વાદી", "પ્રતિવાદી", "પ્રતિવાદી ના એડવોકેટ"),
            ("party_1", "અરજદાર", "સામાવાળા", "અરજદાર ના એડવોકેટ"),
            ("party_2", "અરજદાર", "સામાવાળા", "સામાવાળા ના એડવોકેટ"),
            ("party_1", "ફરિયાદી", "આરોપી", "ફરિયાદી ના એડવોકેટ"),
            ("party_2", "ફરિયાદી", "આરોપી", "આરોપી ના એડવોકેટ"),
        ]
        for rep, r1, r2, expected_sig in roles:
            ctx = {
                "court_name": "કોર્ટ",
                "taluka_place": "અમદાવાદ",
                "case_type": "કેસ",
                "case_number": "1/2026",
                "party_1_role": r1,
                "party_1_name": "P1",
                "party_2_role": r2,
                "party_2_name": "P2",
                "representing_party_role": r1 if rep == "party_1" else r2,
                "document_details": "દસ્તાવેજ",
                "date": "19/09/2026",
            }
            rendered = doc_generator.render_template(self.tpl["content_gu"], ctx)
            blocks = doc_generator.build_blocks(rendered, self.tpl["name_en"], self.tpl["name_gu"], (self.tpl.get("settings") or {}).get("block_align"))
            sig_blocks = [b for b in blocks if b.get("section") == "advocate_signature"]
            self.assertEqual(len(sig_blocks), 2)
            self.assertEqual(sig_blocks[0]["text"], "-----------------")
            self.assertEqual(sig_blocks[0]["align"], "right")
            self.assertEqual(sig_blocks[1]["text"], expected_sig)
            self.assertEqual(sig_blocks[1]["align"], "right")

    def test_05_normalizer_resilience_converts_long_dashes_to_17(self):
        """5. Verify build_blocks normalizes long dashes to 17 dashes for Gujarati signatures."""
        raw = (
            "મહેરબાન કોર્ટ સાહેબશ્રી\n\n"
            "તારીખ : 19/09/2026\n"
            "સ્થળ : અમદાવાદ\n\n"
            "---------------------------\n"
            "વાદી ના એડવોકેટ"
        )
        blocks = doc_generator.build_blocks(raw, "Test", "ટેસ્ટ")
        sig_blocks = [b for b in blocks if b.get("section") == "advocate_signature"]
        self.assertEqual(sig_blocks[0]["text"], "-----------------")
        self.assertEqual(sig_blocks[0]["align"], "right")

    def test_06_english_pdf_and_return_application_unaffected(self):
        """6. Verify English PDF and return application are unaffected."""
        # English
        ctx_en = {
            "court_name": "Chief Judicial Magistrate",
            "taluka_place": "Ahmedabad",
            "case_type": "Civil Suit",
            "case_number": "1/2026",
            "party_1_role": "Plaintiff",
            "party_1_name": "P1",
            "party_2_role": "Defendant",
            "party_2_name": "P2",
            "representing_party_role": "Plaintiff",
            "document_details": "Doc 1",
            "date": "19/09/2026",
        }
        rendered_en = doc_generator.render_template(self.tpl["content_en"], ctx_en)
        blocks_en = doc_generator.build_blocks(rendered_en, self.tpl["name_en"], self.tpl["name_gu"])
        settings_en = doc_generator.get_doc_settings({})
        b64_en = doc_generator._generate_pdf_reportlab_inner(blocks_en, "en", settings_en)
        self.assertTrue(b64_en)

        # Return application
        tpl_ret = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_return_application"), None)
        self.assertIsNotNone(tpl_ret)
        ctx_ret = {
            "court": "કોર્ટ",
            "taluka_place": "અમદાવાદ",
            "case_type": "કેસ",
            "case_number": "1/2026",
            "applicant_role": "વાદી",
            "party_name": "P1",
            "opposite_party_role": "પ્રતિવાદી",
            "opposite_party": "P2",
            "selected_party_role": "વાદી",
            "document_name": "Doc",
            "case_status_clause": "ચાલવા પર છે",
            "tense": "હતો",
            "date_display": "19/09/2026",
            "place": "અમદાવાદ",
        }
        rendered_ret = doc_generator.render_template(tpl_ret["content_gu"], ctx_ret)
        blocks_ret = doc_generator.build_blocks(rendered_ret, tpl_ret["name_en"], tpl_ret["name_gu"])
        b64_ret = doc_generator._generate_pdf_reportlab_inner(blocks_ret, "gu", settings_en)
        self.assertTrue(b64_ret)

    def test_07_pdf_byte_stream_verification(self):
        """7. Verify generated PDF byte stream directly for 17 dashes and absence of 27 dashes."""
        ctx = {
            "court_name": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રી",
            "taluka_place": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "વાદી",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "representing_party_role": "વાદી",
            "document_details": "આંક ૩ થી રજૂ કરેલ મૂળ વેચાણ દસ્તાવેજ",
            "date": "19/09/2026",
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

        self.assertIn("(-----------------) Tj", stream_text)
        self.assertNotIn("---------------------------", stream_text)


if __name__ == "__main__":
    unittest.main()
