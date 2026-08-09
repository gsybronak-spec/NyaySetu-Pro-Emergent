"""Backend tests for the NyaySetu Pro document engine fix.

Covers:
  * Blocks-classification correctness (numbered points NOT bold/centered).
  * Real PDF/DOCX generation with content inspection (pdfminer / python-docx).
  * Certified Copy order_date optional.
  * Credit safety (preview does not decrement; download decrements exactly 1).
  * Regression: OTP login, google 401, referral +10, template list count+search.
"""
import base64
import io
import os
import re
import time

import pytest
import requests
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pdfminer.high_level import extract_text

BASE = os.environ["EXPO_PUBLIC_BACKEND_URL"].rstrip("/") + "/api"


# --------- helpers ---------
def _login(mobile: str) -> str:
    r = requests.post(f"{BASE}/auth/send-otp", json={"mobile": mobile}, timeout=15)
    assert r.status_code == 200, r.text
    r = requests.post(f"{BASE}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _new_mobile():
    return "9" + str(int(time.time() * 1000))[-9:]


@pytest.fixture(scope="module")
def token():
    return _login(_new_mobile())


# --------- BLOCK CLASSIFICATION ---------
class TestBlocksClassification:
    def test_gu_adjournment_points_not_bold(self, token):
        # Create a case first so case_id can be attached
        c = requests.post(
            f"{BASE}/cases",
            headers=_hdr(token),
            json={
                "nickname": "TEST_Doc",
                "case_number": "42/2026",
                "case_type_id": "civil_suit",
                "district_id": "ahmedabad",
                "party_name": "TEST Party",
                "language": "gu",
            },
            timeout=15,
        )
        assert c.status_code == 200, c.text
        case_id = c.json()["id"]

        r = requests.post(
            f"{BASE}/applications/preview",
            headers=_hdr(token),
            json={
                "template_id": "adjournment",
                "language": "gu",
                "case_id": case_id,
                "values": {"next_date": "2026-02-15", "reason": "વ્યક્તિગત કારણોસર"},
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        blocks = r.json()["blocks"]
        assert isinstance(blocks, list) and len(blocks) > 5

        # Extract points ૧. ૨. ૩.
        point_blocks = [b for b in blocks if re.match(r"^[૧૨૩]\.", b["text"].strip())]
        assert len(point_blocks) >= 3, f"expected 3 numbered points, got {[b['text'] for b in point_blocks]}"
        for pb in point_blocks:
            assert pb["align"] == "left", f"Point wrongly centered: {pb}"
            assert pb["bold"] is False, f"Point wrongly bold: {pb}"

        # Court heading + title should be center+bold
        centered = [b for b in blocks if b["align"] == "center" and b["bold"]]
        assert any(b["text"].startswith("માનનીય ન્યાયાલય") for b in centered), "court heading not centered"
        assert any("મુદત" in b["text"] and b["bold"] for b in centered), "title not bold+center"

    def test_en_affidavit_headings(self, token):
        r = requests.post(
            f"{BASE}/applications/preview",
            headers=_hdr(token),
            json={
                "template_id": "affidavit",
                "language": "en",
                "values": {
                    "deponent_name": "Ravi",
                    "father_name": "Kishor",
                    "age": 30,
                    "address": "Ahmedabad",
                    "statement": "This is my statement.",
                },
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        blocks = r.json()["blocks"]
        # AFFIDAVIT + VERIFICATION centered+bold
        assert any(b["text"] == "AFFIDAVIT" and b["align"] == "center" and b["bold"] for b in blocks)
        assert any(b["text"] == "VERIFICATION" and b["align"] == "center" and b["bold"] for b in blocks)
        # Any numbered points 1./2./3. must be left+not-bold
        for b in blocks:
            if re.match(r"^\d+\.", b["text"].strip()):
                assert b["align"] == "left" and b["bold"] is False, f"numbered point wrong: {b}"


# --------- REAL FILE GENERATION ---------
class TestPdfGeneration:
    def test_gu_pdf_has_gujarati_text(self, token):
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "adjournment",
                "language": "gu",
                "format": "pdf",
                "consume_credit": True,
                "values": {"next_date": "2026-02-15", "reason": "વ્યક્તિગત કારણોસર"},
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        b64 = r.json()["base64"]
        raw = base64.b64decode(b64)
        assert raw[:4] == b"%PDF"
        text = extract_text(io.BytesIO(raw))
        # Prove Lohit glyphs embedded — extractable Gujarati unicode
        assert "મુદત" in text, f"'મુદત' not extractable from PDF (Lohit not embedded). Extracted head: {text[:400]!r}"
        assert "અરજદાર" in text, f"'અરજદાર' not extractable. Head: {text[:400]!r}"

    def test_en_pdf_ok(self, token):
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "affidavit",
                "language": "en",
                "format": "pdf",
                "consume_credit": True,
                "values": {
                    "deponent_name": "Ravi",
                    "father_name": "Kishor",
                    "age": 30,
                    "address": "Ahmedabad",
                    "statement": "This is my statement.",
                },
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        raw = base64.b64decode(r.json()["base64"])
        assert raw[:4] == b"%PDF"
        text = extract_text(io.BytesIO(raw))
        assert "AFFIDAVIT" in text
        assert "VERIFICATION" in text
        assert "Ravi" in text


class TestDocxGeneration:
    def test_gu_docx_paragraphs_and_font(self, token):
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "adjournment",
                "language": "gu",
                "format": "docx",
                "consume_credit": True,
                "values": {"next_date": "2026-02-15", "reason": "કારણ"},
            },
            timeout=30,
        )
        assert r.status_code == 200
        raw = base64.b64decode(r.json()["base64"])
        doc = Document(io.BytesIO(raw))
        paragraphs = [p for p in doc.paragraphs if p.text.strip()]
        assert len(paragraphs) > 5
        # Find numbered points & check they are LEFT / not bold
        for p in paragraphs:
            if re.match(r"^[૧૨૩]\.", p.text.strip()):
                assert p.alignment in (WD_ALIGN_PARAGRAPH.LEFT, None), f"Gujarati point centered: {p.text}"
                for run in p.runs:
                    assert not run.bold, f"Gujarati point bold: {p.text}"
        # Find title / court heading -> center+bold
        centered_bold = [
            p for p in paragraphs
            if p.alignment == WD_ALIGN_PARAGRAPH.CENTER and any(r.bold for r in p.runs)
        ]
        assert any("માનનીય ન્યાયાલય" in p.text or "મુદત" in p.text for p in centered_bold)
        # Font name = Lohit Gujarati on at least one run
        fonts = {run.font.name for p in paragraphs for run in p.runs if run.font.name}
        assert "Lohit Gujarati" in fonts, f"Fonts used: {fonts}"

    def test_en_docx_font_times(self, token):
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "affidavit",
                "language": "en",
                "format": "docx",
                "consume_credit": True,
                "values": {
                    "deponent_name": "Ravi",
                    "father_name": "Kishor",
                    "age": 30,
                    "address": "Ahmedabad",
                    "statement": "This is my statement.",
                },
            },
            timeout=30,
        )
        assert r.status_code == 200
        raw = base64.b64decode(r.json()["base64"])
        doc = Document(io.BytesIO(raw))
        paragraphs = [p for p in doc.paragraphs if p.text.strip()]
        fonts = {run.font.name for p in paragraphs for run in p.runs if run.font.name}
        assert "Times New Roman" in fonts, f"Fonts: {fonts}"
        # AFFIDAVIT / VERIFICATION center+bold
        cb_texts = [p.text for p in paragraphs
                    if p.alignment == WD_ALIGN_PARAGRAPH.CENTER and any(r.bold for r in p.runs)]
        assert "AFFIDAVIT" in cb_texts
        assert "VERIFICATION" in cb_texts
        # numbered points left/not-bold
        for p in paragraphs:
            if re.match(r"^\d+\.", p.text.strip()):
                assert p.alignment in (WD_ALIGN_PARAGRAPH.LEFT, None)
                for run in p.runs:
                    assert not run.bold


# --------- PDF vs DOCX consistency ---------
class TestPdfDocxConsistency:
    def test_same_text_content(self):
        token = _login(_new_mobile())  # fresh 5 credits
        payload = {
            "template_id": "affidavit",
            "language": "en",
            "consume_credit": True,
            "values": {
                "deponent_name": "Alice",
                "father_name": "Bob",
                "age": 40,
                "address": "Rajkot",
                "statement": "Truthful statement.",
            },
        }
        rp = requests.post(f"{BASE}/applications/download",
                           headers=_hdr(token), json={**payload, "format": "pdf"}, timeout=30)
        rd = requests.post(f"{BASE}/applications/download",
                           headers=_hdr(token), json={**payload, "format": "docx"}, timeout=30)
        assert rp.status_code == 200 and rd.status_code == 200
        pdf_text = extract_text(io.BytesIO(base64.b64decode(rp.json()["base64"])))
        docx_text = "\n".join(
            p.text for p in Document(io.BytesIO(base64.b64decode(rd.json()["base64"]))).paragraphs
        )
        for token_ in ["AFFIDAVIT", "VERIFICATION", "Alice", "Bob", "Rajkot", "Truthful statement"]:
            assert token_ in pdf_text, f"{token_} missing in PDF"
            assert token_ in docx_text, f"{token_} missing in DOCX"


# --------- CERTIFIED COPY ORDER DATE OPTIONAL ---------
class TestCertifiedCopyOptional:
    def test_without_order_date(self):
        token = _login(_new_mobile())
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "certified_copy",
                "language": "en",
                "format": "pdf",
                "consume_credit": True,
                "values": {"document_desc": "Order dated in the above matter"},
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text
        raw = base64.b64decode(r.json()["base64"])
        assert raw[:4] == b"%PDF"

    def test_with_order_date(self):
        token = _login(_new_mobile())
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(token),
            json={
                "template_id": "certified_copy",
                "language": "en",
                "format": "pdf",
                "consume_credit": True,
                "values": {"document_desc": "Order", "order_date": "2026-01-10"},
            },
            timeout=30,
        )
        assert r.status_code == 200
        assert base64.b64decode(r.json()["base64"])[:4] == b"%PDF"

    def test_field_marked_optional_in_catalog(self):
        # No auth needed for detail? Try both.
        tok = _login(_new_mobile())
        r = requests.get(f"{BASE}/templates/certified_copy", headers=_hdr(tok), timeout=15)
        assert r.status_code == 200, r.text
        fields = r.json()["fields"]
        od = next((f for f in fields if f["key"] == "order_date"), None)
        assert od is not None
        assert od["required"] is False


# --------- CREDIT SAFETY ---------
class TestCreditSafety:
    def test_preview_no_credit_deduct(self):
        tok = _login(_new_mobile())  # fresh user w/ 5 credits
        before = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        requests.post(
            f"{BASE}/applications/preview",
            headers=_hdr(tok),
            json={"template_id": "adjournment", "language": "en",
                  "values": {"next_date": "2026-02-01", "reason": "x"}},
            timeout=15,
        )
        after = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert after == before, f"preview deducted credit! {before}->{after}"

    def test_download_deducts_exactly_one(self):
        tok = _login(_new_mobile())
        before = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(tok),
            json={"template_id": "adjournment", "language": "en", "format": "pdf",
                  "consume_credit": True,
                  "values": {"next_date": "2026-02-01", "reason": "x"}},
            timeout=30,
        )
        assert r.status_code == 200
        after = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert after == before - 1, f"expected -1, got {before}->{after}"

    def test_insufficient_balance_402(self):
        tok = _login(_new_mobile())
        # Drain 5 credits
        for _ in range(5):
            requests.post(
                f"{BASE}/applications/download",
                headers=_hdr(tok),
                json={"template_id": "adjournment", "language": "en", "format": "pdf",
                      "consume_credit": True,
                      "values": {"next_date": "2026-02-01", "reason": "x"}},
                timeout=30,
            )
        bal = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert bal == 0
        r = requests.post(
            f"{BASE}/applications/download",
            headers=_hdr(tok),
            json={"template_id": "adjournment", "language": "en", "format": "pdf",
                  "consume_credit": True,
                  "values": {"next_date": "2026-02-01", "reason": "x"}},
            timeout=30,
        )
        assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"
        # Balance still 0 (no deduction)
        bal2 = requests.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
        assert bal2 == 0


# --------- REGRESSION ---------
class TestRegression:
    def test_google_invalid_401(self):
        r = requests.post(f"{BASE}/auth/google-session",
                          json={"session_id": "invalid_abc"}, timeout=15)
        assert r.status_code == 401, r.text

    def test_referral_plus_10(self):
        # Existing user shares referral, new user signs up with it
        ref_tok = _login(_new_mobile())
        me = requests.get(f"{BASE}/referral/me", headers=_hdr(ref_tok), timeout=15).json()
        code = me.get("referral_code") or me.get("code")
        assert code, f"referral code missing in response: {me}"
        bal_before = requests.get(f"{BASE}/wallet", headers=_hdr(ref_tok)).json()["balance"]

        new_mobile = _new_mobile()
        requests.post(f"{BASE}/auth/send-otp", json={"mobile": new_mobile}, timeout=15)
        r = requests.post(f"{BASE}/auth/verify-otp",
                          json={"mobile": new_mobile, "otp": "123456", "referral_code": code}, timeout=15)
        assert r.status_code == 200

        bal_after = requests.get(f"{BASE}/wallet", headers=_hdr(ref_tok)).json()["balance"]
        assert bal_after == bal_before + 10, f"referral +10 failed: {bal_before}->{bal_after}"

    def test_template_list_and_search(self, token):
        r = requests.get(f"{BASE}/templates", headers=_hdr(token), timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 23, f"expected >=23 templates, got {len(items)}"

        # multilingual search
        for q in ["mudat", "વિલંબ", "vakalat"]:
            rr = requests.get(f"{BASE}/templates", headers=_hdr(token),
                              params={"q": q}, timeout=15)
            assert rr.status_code == 200
            assert len(rr.json()) >= 1, f"no result for {q}"
