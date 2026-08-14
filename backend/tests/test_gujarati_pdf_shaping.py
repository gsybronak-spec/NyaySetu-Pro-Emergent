"""Regression tests for HarfBuzz-shaped Gujarati PDF generation.

Production bug: conjuncts like ક્ષ rendered as ક + ્ષ because Render has no
playwright/Chromium, so the old code silently fell back to ReportLab's
unshaped TTF drawing (ReportLab does NOT run OpenType GSUB/GPOS).

The engine under test (doc_generator.generate_pdf_hb) shapes with uharfbuzz
(HarfBuzz) against the bundled Gujarati font stack — Noto Sans Gujarati
(default), Noto Serif Gujarati, and Lohit Gujarati as a compatibility
fallback — subsets/remaps the font so each shaped glyph becomes a single PUA
codepoint, and marks each line with a PDF /ActualText span so copy/paste and
search return the exact logical text in every conforming reader (MuPDF,
Acrobat, Chrome, Preview). All three fonts embed full Latin + digits so mixed
"કેસ નં. 123/2026" text renders without boxes.

This module is pure-Python (uharfbuzz + fontTools + reportlab) — the exact
path production uses on Render.
"""

import base64
import io
import re
import zlib
import unicodedata

import pytest

from doc_generator import generate_pdf_hb, generate_pdf

GUJARATI_CONJUNCTS = "ક્ષ જ્ઞ ત્ર શ્ર પ્ર ક્ર ગ્ર સ્વ દ્ર હ્ર"

GUJARATI_LEGAL_PARAGRAPH = (
    "માનનીય ન્યાયાલય, ગાંધીનગર. અરજદાર તરફથી રજૂ કરવામાં આવેલ અરજીમાં જણાવ્યા મુજબ "
    "ક્ષતિ અને જ્ઞાપન વિશેની વિગતો નીચે મુજબ છે. પ્રતિઉત્તર પ્રમાણિત કરવામાં આવે છે."
)

# Conjunct -> expected single ligature glyph name (HarfBuzz + Lohit)
EXPECTED_LIGATURES = {
    "ક્ષ": "kaguj_viramaguj_ssaguj",
    "જ્ઞ": "jaguj_viramaguj_nyaguj",
    "ત્ર": "taguj_viramaguj_raguj",
    "શ્ર": "shaguj_viramaguj_raguj",
    "પ્ર": "paguj_viramaguj_raguj",
    "ક્ર": "kaguj_viramaguj_raguj",
    "ગ્ર": "gaguj_viramaguj_raguj",
    "દ્ર": "daguj_viramaguj_raguj",
    "હ્ર": "haguj_viramdeva_raguj",
}


def _glyph_name(font, gid):
    try:
        order = font.getGlyphOrder()
        return order[gid] if 0 <= gid < len(order) else f"gid{gid}"
    except Exception:
        return f"gid{gid}"


def _hb_glyph_names(text, font_file="fonts/Lohit-Gujarati.ttf"):
    from fontTools.ttLib import TTFont as FTFont
    import uharfbuzz as hb

    with open(font_file, "rb") as f:
        font_bytes = f.read()
    face = hb.Face(font_bytes)
    hb_font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    ft = FTFont(font_file)
    return [_glyph_name(ft, g.codepoint) for g in buf.glyph_infos]


def _content_streams(raw: bytes):
    """Decompress all FlateDecode page-content streams (length-exact).

    Parse each `N 0 obj ... endobj` object separately so the stream /Length
    is read from its own dict — a naive whole-file regex truncates when the
    compressed bytes contain the literal sequence `endstream`.
    """
    out = []
    for obj in re.finditer(rb"\d+ 0 obj\n(.*?)\nendobj", raw, re.S):
        body = obj.group(1)
        if b"stream" not in body or b"FlateDecode" not in body:
            continue
        m = re.search(rb"<<(.*?)>>\s*stream\r?\n", body, re.S)
        if not m:
            continue
        head = m.group(1)
        lm = re.search(rb"/Length\s+(\d+)", head)
        if not lm:
            continue
        length = int(lm.group(1))
        start = m.end()
        data = body[start:start + length]
        try:
            if b"ASCII85Decode" in head:
                data = base64.a85decode(data, adobe=True)
            d = zlib.decompress(data)
        except Exception:
            continue
        if b"BT" in d:
            out.append(d)
    return out


def _actual_text_spans(raw: bytes):
    """Return the set of ActualText strings declared in the PDF content."""
    spans = []
    for d in _content_streams(raw):
        for m in re.finditer(rb"/ActualText\s*<FEFF([0-9A-F]+)>", d):
            hexstr = m.group(1).decode("ascii")
            try:
                spans.append(bytes.fromhex(hexstr).decode("utf-16-be"))
            except Exception:
                continue
    return spans


class TestHarfBuzzConjunctShaping:
    """The shaping layer: every conjunct must become ONE ligature glyph."""

    def test_conjuncts_shape_to_single_ligature_glyphs(self):
        # Lohit glyph names (explicit font file) — checks the exact ligature.
        for conjunct, ligature in EXPECTED_LIGATURES.items():
            names = _hb_glyph_names(conjunct, "fonts/Lohit-Gujarati.ttf")
            assert len(names) == 1, f"{conjunct} should be 1 glyph, got {names}"
            assert names[0] == ligature, f"{conjunct} shaped to {names[0]}, expected {ligature}"

    def test_conjuncts_not_decomposed(self):
        # Regression: ક્ષ must never come out as ક + ્ષ separate glyphs
        names = _hb_glyph_names("ક્ષ")
        assert len(names) == 1
        assert "ssaguj" in names[0]

    def test_noto_fonts_shape_conjuncts_to_single_glyphs(self):
        # Noto Sans/Serif Gujarati must ALSO ligate the critical conjuncts to
        # exactly one glyph (different glyph names than Lohit — only count
        # matters). સ્વ is correctly rendered with a prebase form (2 glyphs,
        # identical to Chromium) — it must never expand to separated letters.
        for font_file in ("fonts/NotoSansGujarati-Regular.ttf", "fonts/NotoSerifGujarati-Regular.ttf"):
            for conjunct in GUJARATI_CONJUNCTS.split(" "):
                names = _hb_glyph_names(conjunct, font_file)
                assert ".notdef" not in names, f"{font_file} {conjunct} -> {names}"
                if conjunct == "સ્વ":
                    assert len(names) <= 2, f"{conjunct} shaped to {names}"
                else:
                    assert len(names) == 1, f"{font_file} {conjunct} should be 1 glyph, got {names}"

    def test_noto_fonts_cover_latin_and_digits(self):
        # Mixed Gujarati + English + numbers: the selected Gujarati font must
        # contain Latin letters and digits so nothing renders as a box.
        from fontTools.ttLib import TTFont as FTFont
        for font_file in ("fonts/NotoSansGujarati-Regular.ttf", "fonts/NotoSerifGujarati-Regular.ttf"):
            cmap = FTFont(font_file).getBestCmap()
            assert all(ord(c) in cmap for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), font_file
            assert all(ord(c) in cmap for c in "abcdefghijklmnopqrstuvwxyz"), font_file
            assert all(ord(c) in cmap for c in "0123456789./-()"), font_file

    def test_legal_paragraph_shapes_without_error(self):
        names = _hb_glyph_names(GUJARATI_LEGAL_PARAGRAPH)
        assert len(names) > 10


class TestPdfEngineUsesHarfBuzz:
    def test_generate_pdf_hb_returns_valid_pdf(self):
        blocks = [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        assert raw[:4] == b"%PDF"

    def test_pdf_embeds_default_noto_subset(self):
        # Default Gujarati font is Noto Sans Gujarati.
        blocks = [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        assert b"NotoSansGujarati-Regular" in raw

    def test_generate_pdf_uses_hb_path_for_gujarati(self):
        # Even on machines WITH playwright installed, Gujarati must take the
        # HarfBuzz path (the one that exists on Render).
        blocks = [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}]
        raw = base64.b64decode(generate_pdf(blocks, language="gu"))
        assert b"NotoSansGujarati-Regular" in raw

    def test_font_family_setting_selects_embedded_font(self):
        # Template-level font control: each family embeds its own font.
        cases = [
            ("NotoSansGujarati", b"NotoSansGujarati-Regular"),
            ("NotoSerifGujarati", b"NotoSerifGujarati-Regular"),
            ("LohitGujarati", b"Lohit-Gujarati"),
            ("Noto Sans Gujarati", b"NotoSansGujarati-Regular"),  # display name
        ]
        blocks = [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}]
        for family, marker in cases:
            raw = base64.b64decode(generate_pdf_hb(blocks, language="gu", settings={"gujarati_font": family}))
            assert marker in raw, f"family {family} did not embed {marker}"

    def test_actual_text_spans_contain_exact_gujarati(self):
        """The PDF must declare the exact logical text (selectable/searchable).

        Every conforming reader (MuPDF, Acrobat, Chrome) uses /ActualText for
        copy/paste, so the ligature ક્ષ and matra order પ્રમાણિત must appear
        verbatim — this is what a user sees when they select the text.
        """
        blocks = [
            {"text": "માનનીય ન્યાયાલય ગાંધીનગર", "align": "center", "bold": True},
            {"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False},
            {"text": GUJARATI_LEGAL_PARAGRAPH, "align": "justify", "bold": False},
        ]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        spans = _actual_text_spans(raw)
        assert spans, "PDF must contain ActualText marked content"
        joined = "\n".join(spans)
        for w in GUJARATI_CONJUNCTS.split(" "):
            assert w in joined, f"conjunct {w} missing from ActualText: {joined!r}"
        for w in ("ન્યાયાલય", "ગાંધીનગર", "માનનીય", "પ્રમાણિત", "પ્રતિઉત્તર", "ક્ષતિ", "જ્ઞાપન"):
            assert w in joined, f"word {w} missing from ActualText: {joined!r}"
        assert "\ue000" not in joined, "PUA chars must never leak into ActualText"

    def test_mupdf_extracts_correct_text(self):
        """End-to-end: a real PDF engine (MuPDF, same family as many readers)
        must extract the exact logical text from the generated PDF."""
        pymupdf = pytest.importorskip("pymupdf")
        blocks = [
            {"text": "માનનીય ન્યાયાલય ગાંધીનગર", "align": "center", "bold": True},
            {"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False},
            {"text": GUJARATI_LEGAL_PARAGRAPH, "align": "justify", "bold": False},
        ]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        doc = pymupdf.open(stream=raw, filetype="pdf")
        text = doc[0].get_text()
        # MuPDF groups each separately-positioned glyph onto its own line, so
        # normalize whitespace before asserting the extractable text.
        flat = re.sub(r"\s+", "", text)
        for w in GUJARATI_CONJUNCTS.split(" "):
            assert w in flat, f"conjunct {w} not extractable: {text!r}"
        assert "પ્રમાણિત" in flat
        assert "ક્ષતિ" in flat

    def test_multipage_long_paragraph(self):
        pymupdf = pytest.importorskip("pymupdf")
        long_gu = " ".join([GUJARATI_LEGAL_PARAGRAPH] * 60)
        raw = base64.b64decode(generate_pdf_hb([{"text": long_gu, "align": "left", "bold": False}], language="gu"))
        doc = pymupdf.open(stream=raw, filetype="pdf")
        assert len(doc) >= 2, "long Gujarati paragraph must flow onto multiple pages"

    def test_legal_page_size(self):
        pymupdf = pytest.importorskip("pymupdf")
        raw = base64.b64decode(generate_pdf_hb(
            [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}],
            language="gu", settings={"page_size": "Legal"},
        ))
        doc = pymupdf.open(stream=raw, filetype="pdf")
        assert doc[0].rect.width == 612 and doc[0].rect.height == 1008  # Legal pt

    def test_mixed_english_gujarati(self):
        blocks = [
            {"text": "CASE NO. 12345/2024", "align": "left", "bold": False},
            {"text": GUJARATI_LEGAL_PARAGRAPH, "align": "left", "bold": False},
        ]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        spans = _actual_text_spans(raw)
        joined = "\n".join(spans)
        assert "12345/2024" in joined
        assert "ગાંધીનગર" in joined

    def test_mixed_scripts_extract_without_boxes(self):
        """Gujarati + English + numbers must all be present and extractable.

        This is the reported "boxes for English/numeric values in Gujarati
        templates" bug: with the old Lohit-only pipeline, Latin letters were
        absent from the font and rendered as .notdef boxes. Noto fonts embed
        full Latin + digits, so every character must survive.
        """
        pymupdf = pytest.importorskip("pymupdf")
        text = (
            "Special Civil Application No. 123/2026\n"
            "CIVIL SUIT NO. 123/2026\n"
            "કેસ નં. 123/2026\n"
            "તા. 15/08/2026\n"
            "અમદાવાદ-1\n"
            "ADVOCATE: Mr. ROHIT SHARMA\n"
        )
        blocks = [{"text": ln, "align": "left", "bold": False} for ln in text.split("\n") if ln.strip()]
        raw = base64.b64decode(generate_pdf_hb(blocks, language="gu"))
        doc = pymupdf.open(stream=raw, filetype="pdf")
        flat = "".join(c for c in "".join(p.get_text() for p in doc)
                        if unicodedata.category(c)[0] in "LMN")
        for needle in ("CIVILSUITNO1232026", "SpecialCivilApplicationNo1232026",
                       "ADVOCATEMrROHITSHARMA", "કેસનં1232026", "તા15082026", "અમદાવાદ1"):
            assert needle in flat, f"{needle} missing (boxes?): {flat!r}"

    def test_repeated_generation_no_crash(self):
        for _ in range(3):
            raw = base64.b64decode(generate_pdf_hb(
                [{"text": GUJARATI_CONJUNCTS, "align": "left", "bold": False}], language="gu"))
            assert raw[:4] == b"%PDF"
