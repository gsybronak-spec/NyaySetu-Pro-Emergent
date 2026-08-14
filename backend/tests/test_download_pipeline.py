"""Regression tests for the PDF/DOCX download pipeline.

Covers:
  * Download requires authentication (401 without token).
  * Successful PDF/DOCX responses carry the correct mime_type, filename, and
    valid binary body (magic bytes, filled values).
  * Invalid format is rejected with 422 BEFORE any credit is deducted.
  * Generation failure refunds the credit and records a refund transaction.
  * Successful generation deducts exactly one credit and records exactly one
    document transaction; the application history gets one entry.
  * Failed generation never leaves an application record.
"""
import base64
import io
import os
import sys
from pathlib import Path

import pytest
from docx import Document
from pdfminer.high_level import extract_text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_download")

import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_download"]

import server

server.db = mock_db

from starlette.testclient import TestClient

app_client = TestClient(server.app)

BASE = "/api"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _login(mobile: str) -> str:
    r = app_client.post(f"{BASE}/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    r = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _adjournment_payload():
    return {
        "template_id": "adjournment",
        "language": "en",
        "values": {"next_date": "2026-03-01", "reason": "Personal reasons"},
    }


def test_download_requires_auth():
    r = app_client.post(
        f"{BASE}/applications/download",
        json={**_adjournment_payload(), "format": "pdf"},
    )
    assert r.status_code == 401, r.text


def test_pdf_response_contract():
    tok = _login("9898000001")
    r = app_client.post(
        f"{BASE}/applications/download",
        headers=_hdr(tok),
        json={**_adjournment_payload(), "format": "pdf", "filename": "my_app.pdf"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mime_type"] == "application/pdf"
    assert data["filename"] == "my_app.pdf"
    assert data["filename"].endswith(".pdf")
    raw = base64.b64decode(data["base64"])
    assert len(raw) > 500, "PDF body suspiciously small"
    assert raw[:4] == b"%PDF", f"PDF magic missing: {raw[:8]!r}"
    text = extract_text(io.BytesIO(raw))
    assert "Personal reasons" in text, "filled value missing from PDF"


def test_docx_response_contract():
    tok = _login("9898000002")
    r = app_client.post(
        f"{BASE}/applications/download",
        headers=_hdr(tok),
        json={**_adjournment_payload(), "format": "docx", "filename": "my_app.docx"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mime_type"] == DOCX_MIME
    assert data["filename"] == "my_app.docx"
    assert data["filename"].endswith(".docx")
    raw = base64.b64decode(data["base64"])
    assert len(raw) > 500, "DOCX body suspiciously small"
    assert raw[:2] == b"PK", f"DOCX zip magic missing: {raw[:8]!r}"
    doc = Document(io.BytesIO(raw))
    joined = "\n".join(p.text for p in doc.paragraphs)
    assert "Personal reasons" in joined, "filled value missing from DOCX"


def test_invalid_format_rejected_before_credit_deduct():
    tok = _login("9898000003")
    before = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
    r = app_client.post(
        f"{BASE}/applications/download",
        headers=_hdr(tok),
        json={**_adjournment_payload(), "format": "exe"},
    )
    assert r.status_code == 422, r.text
    assert "pdf" in r.text.lower() and "docx" in r.text.lower()
    after = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
    assert after == before, f"invalid format deducted credit! {before}->{after}"


def test_generation_failure_refunds_credit(monkeypatch):
    tok = _login("9898000004")
    before = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]

    def boom(*args, **kwargs):
        raise RuntimeError("simulated generator failure")

    monkeypatch.setattr(server, "generate_pdf_detailed", boom)
    r = app_client.post(
        f"{BASE}/applications/download",
        headers=_hdr(tok),
        json={**_adjournment_payload(), "format": "pdf"},
    )
    assert r.status_code == 500, r.text
    after = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
    assert after == before, f"failure deducted credit! {before}->{after}"
    # Refund transaction recorded
    txns = app_client.get(f"{BASE}/transactions", headers=_hdr(tok)).json()
    refunds = [t for t in txns if t.get("type") == "refund" and t.get("status") == "refunded"]
    assert len(refunds) == 1, f"expected 1 refund txn, got {len(refunds)}"
    # No application record for the failed generation
    history = app_client.get(f"{BASE}/applications/history", headers=_hdr(tok)).json()
    assert len(history) == 0, f"failed generation left an application record: {history}"


def test_success_deducts_exactly_once_and_records_transaction():
    tok = _login("9898000005")
    before = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
    r = app_client.post(
        f"{BASE}/applications/download",
        headers=_hdr(tok),
        json={**_adjournment_payload(), "format": "pdf"},
    )
    assert r.status_code == 200, r.text
    after = app_client.get(f"{BASE}/wallet", headers=_hdr(tok)).json()["balance"]
    assert after == before - 1, f"expected exactly -1, got {before}->{after}"
    txns = app_client.get(f"{BASE}/transactions", headers=_hdr(tok)).json()
    docs = [t for t in txns if t.get("type") == "document" and t.get("status") == "success"]
    assert len(docs) == 1, f"expected exactly 1 document txn, got {len(docs)}"
    assert docs[0]["credits"] == -1
    history = app_client.get(f"{BASE}/applications/history", headers=_hdr(tok)).json()
    assert len(history) == 1
    assert history[0]["template_id"] == "adjournment"
    assert history[0]["format"] == "pdf"
