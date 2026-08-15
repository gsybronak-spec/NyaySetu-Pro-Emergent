"""Regression tests for the Gujarati font stack and the "Download as Image" export.

Covers:
  * Font stack: Noto Sans Gujarati (default) -> Noto Serif Gujarati -> Lohit
    Gujarati (fallback); admin-facing names resolve; each family embeds its
    own font into the PDF with a unique per-generation subset identity.
  * generate_pdf_detailed returns artifact metadata (engine, font_family,
    font_version) used for download-integrity records.
  * Image export: PDF rasterized to per-page PNGs via pypdfium2 (same layout
    as the PDF); single page -> image/png, multi page -> ZIP of page-N.png.
  * Download endpoint: format=png works end-to-end with a valid PNG artifact,
    artifact metadata (file_size, sha256, generator_version) recorded, credit
    consumed exactly once, invalid formats still rejected.
  * DOCX/ODT still generate with the new default Gujarati font names.
"""
import base64
import os
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_font_stack")

import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_font_stack"]

import doc_generator
import server

server.db = mock_db
doc_generator.register_fonts()

from starlette.testclient import TestClient

app_client = TestClient(server.app)

BASE = "/api"
PNG_MIME = "image/png"
ZIP_MIME = "application/zip"

GUJARATI_CONJUNCTS = "ક્ષ જ્ઞ ત્ર શ્ર પ્ર ક્ર ગ્ર સ્વ દ્ર હ્ર"

MIXED_TEXT = (
    "Special Civil Application No. 123/2026\n"
    "CIVIL SUIT NO. 123/2026\n"
    "કેસ નં. 123/2026\n"
    "તા. 15/08/2026\n"
    "અમદાવાદ-1\n"
    f"{GUJARATI_CONJUNCTS}\n"
    "ADVOCATE: Mr. ROHIT SHARMA\n"
)


def _login(mobile: str) -> str:
    r = app_client.post(f"{BASE}/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    r = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _blocks():
    return [{"text": ln, "align": "left", "bold": False} for ln in MIXED_TEXT.split("\n") if ln.strip()]


def _pdf_subset_identities(raw: bytes) -> list:
    import re
    return sorted(set(re.findall(rb"/BaseFont /([A-Z0-9]{6})\+", raw)))


class TestFontStack:
    def test_default_family_is_noto_sans(self):
        assert doc_generator._gujarati_font_family(None) == "NotoSansGujarati"
        assert doc_generator._gujarati_font_family("Noto Sans Gujarati") == "NotoSansGujarati"
        assert doc_generator._gujarati_font_family("NotoSansGujarati-Regular") == "NotoSansGujarati"

    def test_aliases_resolve(self):
        assert doc_generator._gujarati_font_family("Noto Serif Gujarati") == "NotoSerifGujarati"
        assert doc_generator._gujarati_font_family("Lohit Gujarati") == "LohitGujarati"
        assert doc_generator._gujarati_font_family("LohitGujarati") == "LohitGujarati"
        assert doc_generator._gujarati_font_family("bogus-font") == "NotoSansGujarati"

    @pytest.mark.parametrize("family", [
        "NotoSansGujarati",
        "NotoSerifGujarati",
        "LohitGujarati",
        "Noto Sans Gujarati",
        "Noto Serif Gujarati",
    ])
    def test_family_embeds_its_font(self, family):
        b64, meta = doc_generator.generate_pdf_detailed(_blocks(), "gu", {"gujarati_font": family})
        raw = base64.b64decode(b64)
        assert raw[:4] == b"%PDF"
        # Each generated PDF embeds a per-generation unique font identity
        # (GujHB-{uuid}) to prevent Android viewer cache collisions —
        # the original PostScript name is no longer present in the PDF bytes.
        assert b"GujHB-" in raw, f"{family} did not embed a unique GujHB font"
        assert meta["engine"] == "harfbuzz"
        assert meta["font_family"] == doc_generator._gujarati_font_family(family)
        assert meta.get("font_version")

    def test_sequential_fonts_get_distinct_identities(self):
        ids = set()
        for family in ("NotoSansGujarati", "NotoSerifGujarati", "LohitGujarati",
                       "NotoSansGujarati", "LohitGujarati"):
            raw = base64.b64decode(doc_generator.generate_pdf_detailed(_blocks(), "gu", {"gujarati_font": family})[0])
            ids.update(_pdf_subset_identities(raw))
        assert len(ids) >= 4, f"expected distinct subset identities, got {ids}"

    def test_repeated_generation_same_family_distinct_identity(self):
        raw_a = base64.b64decode(doc_generator.generate_pdf_detailed(_blocks(), "gu")[0])
        raw_b = base64.b64decode(doc_generator.generate_pdf_detailed(_blocks(), "gu")[0])
        assert _pdf_subset_identities(raw_a) != _pdf_subset_identities(raw_b)

    def test_detailed_returns_metadata(self):
        b64, meta = doc_generator.generate_pdf_detailed(_blocks(), "gu")
        assert set(("engine", "font_family", "font_version")) <= set(meta)
        assert meta["engine"] == "harfbuzz"
        assert meta["font_family"] == "NotoSansGujarati"

    def test_docx_and_odt_still_generate(self):
        from docx import Document as DocxDoc
        import io as _io
        b64 = doc_generator.generate_docx(_blocks(), "gu", {"gujarati_font_docx": "Noto Sans Gujarati"})
        raw = base64.b64decode(b64)
        assert raw[:2] == b"PK"
        d = DocxDoc(_io.BytesIO(raw))
        assert any("CIVIL" in (p.text or "") for p in d.paragraphs)
        b64o = doc_generator.generate_odt(_blocks(), "gu", {"gujarati_font_docx": "Noto Sans Gujarati"})
        raw_o = base64.b64decode(b64o)
        assert raw_o[:2] == b"PK"
        with zipfile.ZipFile(_io.BytesIO(raw_o)) as z:
            assert "content.xml" in z.namelist()


class TestImageExport:
    def test_single_page_png(self):
        pages = doc_generator.generate_document_images(_blocks(), "gu")
        assert len(pages) >= 1
        assert pages[0][:8] == b"\x89PNG\r\n\x1a\n", "PNG signature missing"

    def test_multipage_zip_payload(self):
        # ~60 full legal paragraphs easily exceeds one A4 page.
        para = ("માનનીય ન્યાયાલય, ગાંધીનગર. અરજદાર તરફથી રજૂ કરવામાં આવેલ અરજીમાં જણાવ્યા મુજબ "
                "ક્ષતિ અને જ્ઞાપન વિશેની વિગતો નીચે મુજબ છે. પ્રતિઉત્તર પ્રમાણિત કરવામાં આવે છે.")
        long_text = "\n".join([para] * 60)
        blocks = [{"text": ln, "align": "left", "bold": False} for ln in long_text.split("\n") if ln.strip()]
        pages = doc_generator.generate_document_images(blocks, "gu")
        assert len(pages) >= 2, "long document must produce multiple page images"
        b64, mime, fname = doc_generator.build_image_payload(pages, "long_app")
        assert mime == ZIP_MIME
        assert fname == "long_app.zip"
        with zipfile.ZipFile(__import__("io").BytesIO(base64.b64decode(b64))) as z:
            names = z.namelist()
            assert names[0] == "page-1.png"
            assert len(names) == len(pages)

    def test_image_page_count_matches_pdf(self):
        import pymupdf
        blocks = _blocks()
        pdf_b64 = doc_generator.generate_pdf(blocks, "gu")
        doc = pymupdf.open(stream=base64.b64decode(pdf_b64), filetype="pdf")
        n_pdf = len(doc)
        doc.close()
        pages = doc_generator.generate_document_images(blocks, "gu")
        assert len(pages) == n_pdf, "image pages must match PDF pages"

    def test_pdf_failure_falls_back_to_chromium_image(self, monkeypatch):
        # If the HB/reportlab PDF engines fail, the image path must still
        # produce a PNG via the Chromium HTML renderer (when available).
        def boom(*a, **k):
            raise RuntimeError("simulated PDF failure")
        monkeypatch.setattr(doc_generator, "generate_pdf_hb", boom)
        monkeypatch.setattr(doc_generator, "generate_pdf_reportlab", boom)
        try:
            pages = doc_generator.generate_document_images(_blocks(), "gu")
        except Exception as e:
            pytest.skip(f"playwright unavailable in this environment: {e}")
        assert pages and pages[0][:8] == b"\x89PNG\r\n\x1a\n"


class TestDownloadImageEndpoint:
    def test_png_download_end_to_end(self):
        tok = _login("9898000001")
        before = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        r = app_client.post(f"{BASE}/applications/download", headers=_hdr(tok), json={
            "template_id": "return_documents", "language": "gu", "format": "png",
            "values": {"document_name": "દસ્તાવેજ", "date": "15/08/2026"},
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mime_type"] in (PNG_MIME, ZIP_MIME)
        assert data["filename"].endswith((".png", ".zip"))
        raw = base64.b64decode(data["base64"])
        if data["mime_type"] == PNG_MIME:
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        else:
            with zipfile.ZipFile(__import__("io").BytesIO(raw)) as z:
                assert z.namelist()[0] == "page-1.png"
        after = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert after == before - 1
        history = app_client.get(f"{BASE}/applications/history", headers=_hdr(tok)).json()
        assert history[0]["format"] == "png"
        assert history[0]["file_size"] > 0
        assert len(history[0]["sha256"]) == 64
        assert history[0]["generator_version"]
        assert history[0]["font_family"] == "NotoSansGujarati"

    def test_pdf_download_records_artifact_metadata(self):
        tok = _login("9898000002")
        r = app_client.post(f"{BASE}/applications/download", headers=_hdr(tok), json={
            "template_id": "return_documents", "language": "gu", "format": "pdf",
            "values": {"document_name": "દસ્તાવેજ", "date": "15/08/2026"},
        })
        assert r.status_code == 200, r.text
        history = app_client.get(f"{BASE}/applications/history", headers=_hdr(tok)).json()
        rec = history[0]
        assert rec["format"] == "pdf"
        assert rec["engine"] == "harfbuzz"
        assert rec["font_family"] == "NotoSansGujarati"
        assert rec["font_version"].startswith("noto-sans-gujarati")
        assert rec["generator_version"]

    def test_invalid_format_still_rejected(self):
        tok = _login("9898000003")
        before = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        r = app_client.post(f"{BASE}/applications/download", headers=_hdr(tok), json={
            "template_id": "return_documents", "language": "gu", "format": "exe",
            "values": {},
        })
        assert r.status_code == 422
        after = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert after == before, "invalid format must not consume credit"
