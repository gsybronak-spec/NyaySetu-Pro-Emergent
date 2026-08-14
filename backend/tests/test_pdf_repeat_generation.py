# -*- coding: utf-8 -*-
"""Repeated-generation isolation for the Gujarati HarfBuzz PDF engine.

Regression for the reported production bug where the FIRST Gujarati PDF was
perfect but a SECOND (and later) PDF came out corrupted. The engine must be
fully per-generation: no shared HarfBuzz font state, no shared subset font
state, no global counter collisions, no silent fallback to the unshaped
ReportLab path for Gujarati content.

The suite generates at least five PDFs sequentially in one process
(A, B, A, C, B), asserts byte determinism modulo the standard /ID and
timestamps, verifies semantic text via MuPDF (which honours ActualText), and
proves no unshaped fallback ever runs for Gujarati.
"""
import base64
import io
import re
import threading

import pytest

from doc_generator import generate_pdf

pymupdf = pytest.importorskip("pymupdf")

GU_CONJUNCTS = "ક્ષ જ્ઞ ત્ર શ્ર પ્ર ક્ર ગ્ર સ્વ દ્ર હ્ર"

BLOCK_A = [
    {"text": "માનનીય કોર્ટ સમક્ષ ક્ષતિ અને જ્ઞાપન અરજી", "align": "center", "bold": True},
    {"text": f"સદર કેસમાં અરજદાર {GU_CONJUNCTS} દ્વારા આ અરજી રજૂ કરવામાં આવે છે.", "align": "justify"},
    {"text": "તારીખ : 14-08-2026", "align": "left"},
]

BLOCK_B = [
    {"text": "બેલ અરજી — આરોપીની અટકાયત ગેરકાયદેસર છે", "align": "center", "bold": True},
    {"text": "આ આરોપી સામે પ્રમાણિત દસ્તાવેજો રજૂ કરવામાં આવ્યા છે તથા સાક્ષી ઊભી રહેશે.", "align": "justify"},
]

BLOCK_C = [
    {"text": "ત્રિપક્ષીય કરાર અમલમાં છે. ક્રમશઃ વિચારણા કરવામાં આવશે.", "align": "justify"},
]


def _gen_pdf(blocks):
    return base64.b64decode(generate_pdf(blocks, "gu"))


def _mupdf_text(raw):
    doc = pymupdf.open(stream=raw, filetype="pdf")
    try:
        return " ".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _normalize(raw):
    """Strip volatile per-document metadata (ID + timestamps) for comparison."""
    s = re.sub(rb"/ID\s*\[[^\]]*\]", b"", raw)
    s = re.sub(rb"/CreationDate\s*\([^)]*\)", b"", s)
    s = re.sub(rb"/ModDate\s*\([^)]*\)", b"", s)
    return s


def _assert_correct_gujarati(text):
    """Every generation must contain at least one real Gujarati word."""
    for marker in ("ક્ષ", "અરજ", "અટકાય", "કરાર", "પ્રમાણિત"):
        if marker in text:
            return True
    return False


def test_sequential_generations_stay_correct():
    """A, B, A, C, B sequentially in one process — all must be correct."""
    seq = [("A", BLOCK_A), ("B", BLOCK_B), ("A", BLOCK_A), ("C", BLOCK_C), ("B", BLOCK_B)]
    out = {}
    for i, (label, blocks) in enumerate(seq, 1):
        raw = _gen_pdf(blocks)
        out[label + str(i)] = raw
        text = _mupdf_text(raw)
        assert _assert_correct_gujarati(text), f"gen #{i} ({label}) corrupted: {text[:80]!r}"
        assert "\\ue0" not in repr(text), f"gen #{i} ({label}) leaked PUA glyph codes"
    # Same content -> byte-identical output (modulo /ID + timestamps)
    assert _normalize(out["A1"]) == _normalize(out["A3"])
    assert _normalize(out["B2"]) == _normalize(out["B5"])


def test_repeated_generation_is_deterministic():
    """Generating the same document 3x yields identical normalized bytes."""
    raws = [_gen_pdf(BLOCK_A) for _ in range(3)]
    n = [_normalize(r) for r in raws]
    assert n[0] == n[1] == n[2]
    for r in raws:
        assert _assert_correct_gujarati(_mupdf_text(r))


def test_multipage_gujarati_pdf():
    """A long Gujarati paragraph must paginate without corrupting glyphs."""
    para = ("સદર કેસમાં નીચેના અરજદારે આપ નામદાર કોર્ટ સમક્ષ નીચે મુજબની અરજી "
            "રજૂ કરવામાં આવે છે કે, અરજદારનો કેસ આ કોર્ટમાં ચાલી રહ્યો છે અને "
            "હાલમાં ડિસ્પોઝ થયેલ છે. ક્ષતિ, જ્ઞાપન, શ્રમ, ક્રિયા, ત્રાસ, પ્રમાણ, "
            "દ્રષ્ટિ, હ્રદય અને સ્વયં જેવા શબ્દો સાથેનો આ લાંબો ફકરો બહુવિધ "
            "પાનાંઓમાં વિભાજિત થાય છે તેમ છતાં દરેક શબ્દ યોગ્ય રીતે છપાવો જોઈએ. ") * 12
    blocks = [{"text": para, "align": "justify"}, {"text": "હરજી નં. 123/2026", "align": "right"}]
    raw = _gen_pdf(blocks)
    doc = pymupdf.open(stream=raw, filetype="pdf")
    try:
        assert doc.page_count >= 2, f"expected multiple pages, got {doc.page_count}"
        text = " ".join(page.get_text() for page in doc)
    finally:
        doc.close()
    assert "ક્ષ" in text and "જ્ઞ" in text and "પ્રમાણ" in text


def test_no_unshaped_fallback_for_gujarati(monkeypatch):
    """Gujarati must NEVER reach the unshaped ReportLab path."""
    import doc_generator as dg

    calls = {"reportlab": 0, "playwright": 0}

    def boom_reportlab(*a, **k):
        calls["reportlab"] += 1
        raise AssertionError("unshaped ReportLab fallback used for Gujarati!")

    def boom_playwright(*a, **k):
        calls["playwright"] += 1
        raise AssertionError("Playwright fallback should not run while HB works")

    monkeypatch.setattr(dg, "generate_pdf_reportlab", boom_reportlab)
    monkeypatch.setattr(dg, "generate_pdf_playwright", boom_playwright)

    raw = _gen_pdf(BLOCK_A)  # HB must succeed on its own
    assert _assert_correct_gujarati(_mupdf_text(raw))
    assert calls == {"reportlab": 0, "playwright": 0}


def test_concurrent_generations_all_correct():
    """Threads generating Gujarati PDFs concurrently must not corrupt each other."""
    results = [None] * 16

    def worker(idx):
        blocks = BLOCK_A if idx % 2 == 0 else BLOCK_B
        try:
            raw = _gen_pdf(blocks)
            results[idx] = _assert_correct_gujarati(_mupdf_text(raw))
        except Exception as e:  # noqa: BLE001
            results[idx] = f"EXC {type(e).__name__}: {e}"

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r is True for r in results), [r for r in results if r is not True]
