"""Regression tests for the ODT (OpenDocument Text) document engine.

Self-contained (sync TestClient + mongomock_motor), so the module never
depends on fixtures defined in other test files. Covers:

  * generate_odt produces a valid ODT ZIP with the correct mimetype, page
    geometry (A4 / Legal), margins, alignment and bold classification.
  * Gujarati text survives round-trip (Unicode passthrough).
  * analyze_odt parses a generated ODT back into the template shape
    (page size, draft lines, placeholders) and rejects garbage / non-ODT files.
  * The download endpoint accepts format=odt, returns the ODT mime type and
    valid ZIP bytes, and consumes exactly one credit (refund on failure).
  * The admin import analyze endpoint accepts .odt files.
  * Invalid download format still rejected with 422 mentioning 'odt'.
"""
import base64
import io
import os
import sys
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_odt")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_odt"]

import server
server.db = mock_db

from starlette.testclient import TestClient
app_client = TestClient(server.app)

ODT_MIME = "application/vnd.oasis.opendocument.text"


def _login(mobile: str) -> str:
    r = app_client.post("/api/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    r = app_client.post("/api/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _adjournment_payload(**overrides):
    payload = {
        "template_id": "adjournment",
        "language": "en",
        "values": {
            "next_date": "15-08-2026",
            "reason": "Personal reasons",
            "court": "District Court, Ahmedabad",
            "district": "Ahmedabad",
            "case_type": "Civil Suit",
            "case_number": "123/2026",
            "party_name": "Ramesh Patel",
            "today": "01-08-2026",
            "advocate_name": "Adv. A. Sharma",
        },
        "format": "odt",
        "filename": "adjournment_test.odt",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# generate_odt unit tests
# ---------------------------------------------------------------------------

class TestOdtGeneration:
    def test_generates_valid_odt_zip(self):
        from doc_generator import generate_odt
        b64 = generate_odt([{"text": "IN THE COURT OF District Court, Ahmedabad", "align": "center", "bold": True},
                            {"text": "Body line", "align": "left", "bold": False}], "en", {})
        raw = base64.b64decode(b64)
        assert raw[:2] == b"PK", "ODT must be a ZIP"
        z = zipfile.ZipFile(io.BytesIO(raw))
        names = z.namelist()
        assert "mimetype" in names and "content.xml" in names and "styles.xml" in names
        assert z.read("mimetype").decode() == ODT_MIME
        content = z.read("content.xml").decode("utf-8")
        assert "IN THE COURT OF" in content
        assert "text-align=\"center\"" in content
        assert "font-weight=\"bold\"" in content

    def test_legal_page_size_and_margins(self):
        from doc_generator import generate_odt
        b64 = generate_odt([{"text": "x", "align": "left", "bold": False}], "en",
                           {"page_size": "Legal", "margin_left_cm": 3.0})
        raw = base64.b64decode(b64)
        z = zipfile.ZipFile(io.BytesIO(raw))
        styles = z.read("styles.xml").decode("utf-8")
        assert "fo:page-width=\"21.59cm\"" in styles
        assert "fo:page-height=\"35.56cm\"" in styles
        assert "fo:margin-left=\"3cm\"" in styles

    def test_a4_page_size_default(self):
        from doc_generator import generate_odt
        b64 = generate_odt([{"text": "x", "align": "left", "bold": False}], "en", {})
        raw = base64.b64decode(b64)
        styles = zipfile.ZipFile(io.BytesIO(raw)).read("styles.xml").decode("utf-8")
        assert "fo:page-width=\"21cm\"" in styles
        assert "fo:page-height=\"29.7cm\"" in styles

    def test_gujarati_text_roundtrips(self):
        from doc_generator import generate_odt
        gu_text = "ક્ષ જ્ઞ શ્ર ક્ર ત્ર પ્ર દ્ર ર્ધ — પ્રમાણિત નકલ"
        b64 = generate_odt([{"text": gu_text, "align": "left", "bold": False}], "gu", {})
        raw = base64.b64decode(b64)
        content = zipfile.ZipFile(io.BytesIO(raw)).read("content.xml").decode("utf-8")
        assert gu_text in content, "Gujarati Unicode must survive ODT generation"


# ---------------------------------------------------------------------------
# analyze_odt unit tests
# ---------------------------------------------------------------------------

class TestOdtImport:
    def test_analyzes_generated_odt(self):
        from doc_generator import generate_odt
        from odt_import import analyze_odt
        blocks = [{"text": "IN THE COURT OF {{court}}, {{district}}", "align": "center", "bold": True},
                  {"text": ""},
                  {"text": "{{case_type}} No. {{case_number}}", "align": "left", "bold": False}]
        raw = base64.b64decode(generate_odt(blocks, "en", {"page_size": "Legal"}))
        an = analyze_odt(raw, "sample.odt")
        assert an["page_size"] == "Legal"
        assert an["draft_line_count"] == 3
        assert set(an["placeholders"]) >= {"court", "district", "case_type", "case_number"}
        keys = {f["key"] for f in an["fields"]}
        assert keys >= {"court", "district", "case_type", "case_number"}

    def test_rejects_non_odt(self):
        import pytest
        from odt_import import analyze_odt, OdtImportError
        with pytest.raises(OdtImportError):
            analyze_odt(b"not a zip file at all", "x.odt")
        # correct zip but wrong mimetype
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("mimetype", "application/zip")
            z.writestr("content.xml", "<root/>")
        with pytest.raises(OdtImportError):
            analyze_odt(buf.getvalue(), "x.odt")

    def test_rejects_wrong_extension(self):
        import pytest
        from odt_import import analyze_odt, OdtImportError
        with pytest.raises(OdtImportError):
            analyze_odt(b"x", "file.docx")
        with pytest.raises(OdtImportError):
            analyze_odt(b"x", "file.txt")


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

class TestOdtDownloadEndpoint:
    def test_download_odt_success_and_credit(self):
        token = _login("9900000001")
        headers = {"Authorization": f"Bearer {token}"}
        r = app_client.post("/api/applications/download", headers=headers,
                            json=_adjournment_payload())
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mime_type"] == ODT_MIME
        assert data["filename"].endswith(".odt")
        raw = base64.b64decode(data["base64"])
        assert raw[:2] == b"PK"
        z = zipfile.ZipFile(io.BytesIO(raw))
        assert z.read("mimetype").decode() == ODT_MIME
        content = z.read("content.xml").decode("utf-8")
        assert "Ramesh Patel" in content, "filled value missing from ODT"
        assert "Personal reasons" in content
        # Credit consumed exactly once (5 signup - 1 = 4)
        w = app_client.get("/api/wallet", headers=headers).json()
        assert w["balance"] == 4, f"expected 4 after one ODT download, got {w['balance']}"

    def test_download_odt_refund_on_failure(self):
        # Unknown template -> generation fails before credit is consumed
        token = _login("9900000002")
        headers = {"Authorization": f"Bearer {token}"}
        r = app_client.post("/api/applications/download", headers=headers,
                            json=_adjournment_payload(template_id="does_not_exist"))
        assert r.status_code == 404
        w = app_client.get("/api/wallet", headers=headers).json()
        assert w["balance"] == 5, "no credit should be consumed when the template is missing"

    def test_download_odt_invalid_format_rejected(self):
        token = _login("9900000003")
        headers = {"Authorization": f"Bearer {token}"}
        r = app_client.post("/api/applications/download", headers=headers,
                            json=_adjournment_payload(format="txt"))
        assert r.status_code == 422
        assert "odt" in r.json()["detail"]


class TestOdtAdminImport:
    def test_admin_import_analyze_accepts_odt(self):
        from doc_generator import generate_odt
        admin_email = f"odt_admin_{uuid.uuid4().hex[:8]}@nyaysetu.test"
        admin_password = "Str0ngAdminPass!"
        ts = server.now().isoformat()
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password_hash": server.hash_password(admin_password),
            "role": "super_admin",
            "active": True,
            "created_at": ts,
        }
        import asyncio
        asyncio.run(server.db.admin_users.insert_one(admin_doc))
        r = app_client.post("/api/admin/auth/login", json={"email": admin_email, "password": admin_password})
        assert r.status_code == 200, r.text
        token = r.json()["token"]

        raw = base64.b64decode(generate_odt(
            [{"text": "સાક્ષી નિવેદન {{witness_name}}", "align": "left", "bold": False}], "gu", {}))
        r2 = app_client.post("/api/admin/templates/import-word/analyze",
                             headers={"Authorization": f"Bearer {token}"},
                             json={"file_name": "statement.odt",
                                   "content_base64": base64.b64encode(raw).decode()})
        assert r2.status_code == 200, r2.text
        an = r2.json()
        assert an["page_size"] == "A4"
        assert "witness_name" in an["placeholders"]
