"""Regression: unique embedded-font identity per generated PDF.

Android PDF viewers cache embedded fonts keyed by the PDF-level font name.
ReportLab's SUBSETN(n) is a FIXED function, so every document embedded its
Lohit subset as /AAAAAA+Lohit-Gujarati even though each document carried a
different glyph->code mapping. Opening PDF #2 after PDF #1 then reuses PDF #1's
cached glyph mapping -> corrupted/malformed Gujarati on the 2nd+ download.

These tests assert that every generated PDF has a DISTINCT font identity while
remaining structurally consistent (BaseFont == FontName, ToUnicode present,
Widths present, font embedded) and that sequential generation in one process
never reuses an identity.
"""

import base64
import io
import re
import unittest

import pymupdf

from doc_generator import generate_pdf_hb, generate_pdf_reportlab

CONJUNCTS = "ક્ષ જ્ઞ ત્ર શ્ર પ્ર ક્ર ગ્ર સ્વ દ્ર હ્ર"
GUJ_BLOCK = [
    {"text": CONJUNCTS, "align": "left", "bold": False},
    {"text": "ગુજરાત હાઇકોર્ટ, અમદાવાદ — ગુજરાત", "align": "center", "bold": True},
]


def _subset_font_names(raw: bytes) -> list:
    """All /BaseFont names that look like subset fonts (TAG+Lohit-...)."""
    names = re.findall(rb"/BaseFont\s*/([A-Z]{6}\+[^\s/>]+)", raw)
    return [n.decode("latin1") for n in names]


def _extract_gujarati(raw: bytes) -> str:
    """MuPDF splits per-glyph (ActualText per mark), so collapse whitespace."""
    doc = pymupdf.open(stream=raw, filetype="pdf")
    try:
        txt = "".join(p.get_text() for p in doc)
    finally:
        doc.close()
    return "".join(txt.split())


class PdfFontIdentityTest(unittest.TestCase):
    def test_every_generation_gets_distinct_identity(self):
        seen = set()
        for i in range(6):
            raw = base64.b64decode(generate_pdf_hb(GUJ_BLOCK))
            ids = _subset_font_names(raw)
            self.assertEqual(len(ids), 1, f"PDF {i+1}: expected one subset font, got {ids}")
            self.assertNotIn(ids[0], seen, f"PDF {i+1} reused identity {ids[0]}")
            seen.add(ids[0])
        self.assertEqual(len(seen), 6)

    def test_identity_is_never_fixed_aaaaaa(self):
        for i in range(3):
            raw = base64.b64decode(generate_pdf_hb(GUJ_BLOCK))
            ids = _subset_font_names(raw)
            self.assertTrue(ids, f"PDF {i+1}: no embedded subset font")
            self.assertNotEqual(ids[0], "AAAAAA+Lohit-Gujarati")

    def test_sequential_generation_a_b_a_c_b(self):
        """Same doc generated twice must still get distinct identities (cache key)."""
        raws = []
        for text in (GUJ_BLOCK, GUJ_BLOCK, GUJ_BLOCK, GUJ_BLOCK, GUJ_BLOCK):
            raws.append(base64.b64decode(generate_pdf_hb(text)))
        ids = [_subset_font_names(r)[0] for r in raws]
        self.assertEqual(len(set(ids)), 5, f"expected 5 distinct identities, got {ids}")

    def test_each_pdf_structurally_consistent(self):
        from fontTools.ttLib import TTFont as FTFont
        from pypdf import PdfReader

        for i in range(5):
            raw = base64.b64decode(generate_pdf_hb(GUJ_BLOCK))
            r = PdfReader(io.BytesIO(raw))
            page = r.pages[0]
            res = page["/Resources"]["/Font"]
            found = False
            for name, ref in res.items():
                f = ref.get_object()
                bf = str(f.get("/BaseFont"))
                if not bf.startswith("/") or "+" not in bf:
                    continue
                found = True
                desc_obj = f.get("/FontDescriptor")
                d = desc_obj.get_object() if hasattr(desc_obj, "get_object") else desc_obj
                fn = str(d.get("/FontName"))
                self.assertEqual(bf, fn, f"PDF {i+1}: BaseFont != FontName")
                self.assertIn("/ToUnicode", f, f"PDF {i+1}: missing ToUnicode")
                self.assertIsNotNone(f.get("/Widths"), f"PDF {i+1}: missing Widths")
                ff2 = d.get("/FontFile2")
                self.assertIsNotNone(ff2, f"PDF {i+1}: font not embedded")
                s = ff2.get_object() if hasattr(ff2, "get_object") else ff2
                # Decompress if ReportLab stored the stream compressed.
                raw_font = getattr(s, "get_data", lambda: s._data)()
                # A real embedded TrueType subset — must parse AND carry glyphs.
                ft = FTFont(io.BytesIO(raw_font))
                num_glyphs = ft["maxp"].numGlyphs
                self.assertGreater(num_glyphs, 10, f"PDF {i+1}: embedded font has no glyphs")
                self.assertGreater(len(raw_font), 2000, f"PDF {i+1}: suspiciously small font")
            self.assertTrue(found, f"PDF {i+1}: no subset font found")

    def test_gujarati_renders_correctly_in_every_pdf(self):
        for i in range(5):
            raw = base64.b64decode(generate_pdf_hb(GUJ_BLOCK))
            txt = _extract_gujarati(raw)
            for conj in ("ક્ષ", "જ્ઞ", "ત્ર", "શ્ર", "પ્ર", "ક્ર", "ગ્ર", "સ્વ", "દ્ર", "હ્ર"):
                self.assertIn(conj, txt, f"PDF {i+1}: conjunct {conj} missing")

    def test_gujarati_legal_paragraph_multiple_generations(self):
        para = (
            "અરજદાર તરફથી નીચે મુજબની અરજી દાખલ કરવામાં આવે છે. "
            "કે જેમાં ક્ષેત્ર, જ્ઞાન, ત્રાસ, શ્રમ, પ્રયત્ન, ક્રિયા, ગ્રંથ, "
            "સ્વરૂપ, દ્રવ્ય અને હ્રદયની બાબતોનો સમાવેશ થાય છે. "
            "તેમજ આ અરજીમાં કોર્ટના આદેશ મુજબ વિગતવાર હકીકતો જણાવવામાં આવે છે."
        )
        raws = [base64.b64decode(generate_pdf_hb([{"text": para, "align": "justify", "bold": False}])) for _ in range(3)]
        ids = [_subset_font_names(r)[0] for r in raws]
        self.assertEqual(len(set(ids)), 3)
        for i, raw in enumerate(raws):
            txt = _extract_gujarati(raw)
            self.assertIn("ક્ષેત્ર", txt, f"PDF {i+1}")
            self.assertIn("જ્ઞાન", txt, f"PDF {i+1}")
            self.assertIn("પ્રયત્ન", txt, f"PDF {i+1}")

    def test_english_reportlab_path_unique_when_ttf_embedded(self):
        """When a TTF is embedded for English (e.g. a custom body font), the
        identity must also be unique per document. Default English uses
        base-14 fonts (no embedding) so force a registered TTF if available."""
        from reportlab.pdfbase import pdfmetrics

        import doc_generator

        doc_generator.register_fonts()
        base14 = ("Helvetica", "Times-Roman", "Courier", "Symbol", "ZapfDingbats")
        ttf_candidates = [n for n in pdfmetrics.getRegisteredFontNames()
                          if n not in base14]
        if not ttf_candidates:
            self.skipTest("no registered TTF available for English path")
        eng_blocks = [{"text": "This is a legal application document.", "align": "left", "bold": False}]
        settings = {"english_font": ttf_candidates[0]}
        seen = set()
        for i in range(4):
            raw = base64.b64decode(generate_pdf_reportlab(eng_blocks, language="en", settings=settings))
            ids = re.findall(rb"/BaseFont\s*/([A-Z]{6}\+[^\s/>]+)", raw)
            for ident in ids:
                self.assertNotIn(ident.decode(), seen)
                seen.add(ident.decode())
        self.assertGreaterEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
