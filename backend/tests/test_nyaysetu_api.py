"""NyaySetu Pro API tests — covers auth, catalog, cases, templates, apps, wallet, drafts, search."""
import os
import time
import base64
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_api")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_api"]

import server
server.db = mock_db

from starlette.testclient import TestClient
app_client = TestClient(server.app)

API = "/api"


@pytest.fixture(scope="module")
def session():
    return app_client


@pytest.fixture(scope="module")
def user_ctx(session):
    """Create fresh user + token + initial test case."""
    mobile = f"9{int(time.time()) % 1000000000:09d}"
    r = session.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200
    r = session.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200
    data = r.json()
    assert data["is_new"] is True
    assert "token" in data and "user" in data
    token = data["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    case_res = session.post(f"{API}/cases", headers=headers, json={
        "language": "en",
        "nickname": "TEST_CaseA",
        "case_number": "12/2026",
        "case_type_id": "criminal_complaint",
        "complaint_type": "private",
        "law_id": "ni_act",
        "section_id": "138",
        "party_name": "TEST Party",
        "opposite_party": "TEST Opposite",
        "district_id": "ahmedabad",
        "court": "JMFC Ahmedabad",
    })
    case_id = case_res.json()["id"] if case_res.status_code == 200 else None
    return {"token": token, "mobile": mobile, "user_id": data["user"]["id"], "case_id": case_id}


def H(user_ctx):
    return {"Authorization": f"Bearer {user_ctx['token']}", "Content-Type": "application/json"}


# ---------- Health ----------
class TestHealth:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


# ---------- Auth ----------
class TestAuth:
    def test_send_otp_short_mobile(self, session):
        r = session.post(f"{API}/auth/send-otp", json={"mobile": "123"})
        assert r.status_code == 400

    def test_send_otp_ok(self, session):
        r = session.post(f"{API}/auth/send-otp", json={"mobile": "9876543210"})
        assert r.status_code == 200
        assert r.json().get("success") is True

    def test_verify_new_and_existing(self, session):
        mobile = f"9{int(time.time()*1000) % 1000000000:09d}"
        r1 = session.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
        assert r1.status_code == 200
        assert r1.json()["is_new"] is True
        r2 = session.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
        assert r2.status_code == 200
        assert r2.json()["is_new"] is False

    def test_verify_bad_otp(self, session):
        r = session.post(f"{API}/auth/verify-otp", json={"mobile": "9876543210", "otp": "abc"})
        assert r.status_code == 400

    def test_protected_requires_auth(self, session):
        r = session.get(f"{API}/profile/me")
        assert r.status_code == 401


# ---------- Profile ----------
class TestProfile:
    def test_me(self, session, user_ctx):
        r = session.get(f"{API}/profile/me", headers=H(user_ctx))
        assert r.status_code == 200
        assert r.json()["mobile"] == user_ctx["mobile"]

    def test_update(self, session, user_ctx):
        r = session.put(f"{API}/profile/update", headers=H(user_ctx),
                        json={"name": "TEST Advocate", "district": "ahmedabad", "court": "TEST Court"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST Advocate"


# ---------- Catalog ----------
class TestCatalog:
    def test_case_types(self, session):
        r = session.get(f"{API}/catalog/case-types")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 15
        assert any(c["id"] == "criminal_complaint" for c in data)

    def test_laws_and_sections(self, session):
        r = session.get(f"{API}/catalog/laws")
        assert r.status_code == 200
        laws = r.json()
        assert any(l["id"] == "ni_act" for l in laws)
        r2 = session.get(f"{API}/catalog/laws/ni_act/sections")
        assert r2.status_code == 200
        secs = r2.json()
        assert any(s["id"] == "138" for s in secs)

    def test_districts(self, session):
        r = session.get(f"{API}/catalog/districts")
        assert r.status_code == 200
        assert any(d["id"] == "ahmedabad" for d in r.json())

    def test_plans(self, session):
        r = session.get(f"{API}/catalog/plans")
        assert r.status_code == 200
        plans = r.json()
        ids = {p["id"] for p in plans}
        assert {"single", "plan_299", "plan_499", "plan_999"}.issubset(ids)

    def test_quote(self, session):
        r = session.get(f"{API}/catalog/quote")
        assert r.status_code == 200
        assert "quote" in r.json()


# ---------- Cases ----------
class TestCases:
    def test_case_crud_flow(self, session, user_ctx):
        payload = {
            "language": "en",
            "nickname": "TEST_CaseA",
            "case_number": "12/2026",
            "case_type_id": "criminal_complaint",
            "complaint_type": "private",
            "law_id": "ni_act",
            "section_id": "138",
            "party_name": "TEST Party",
            "opposite_party": "TEST Opposite",
            "district_id": "ahmedabad",
            "court": "JMFC Ahmedabad",
        }
        r = session.post(f"{API}/cases", headers=H(user_ctx), json=payload)
        assert r.status_code == 200
        case = r.json()
        cid = case["id"]
        assert case["nickname"] == "TEST_CaseA"

        # GET
        r = session.get(f"{API}/cases/{cid}", headers=H(user_ctx))
        assert r.status_code == 200
        assert r.json()["case_number"] == "12/2026"

        # LIST + search
        r = session.get(f"{API}/cases?q=TEST_CaseA", headers=H(user_ctx))
        assert r.status_code == 200
        assert any(c["id"] == cid for c in r.json())

        # UPDATE
        r = session.put(f"{API}/cases/{cid}", headers=H(user_ctx), json={"nickname": "TEST_CaseA_upd"})
        assert r.status_code == 200
        assert r.json()["nickname"] == "TEST_CaseA_upd"

        # Save id for later
        user_ctx["case_id"] = cid

    def test_delete_case(self, session, user_ctx):
        r = session.post(f"{API}/cases", headers=H(user_ctx), json={"nickname": "TEST_DEL"})
        cid = r.json()["id"]
        r = session.delete(f"{API}/cases/{cid}", headers=H(user_ctx))
        assert r.status_code == 200
        r = session.get(f"{API}/cases/{cid}", headers=H(user_ctx))
        assert r.status_code == 404


# ---------- Templates ----------
class TestTemplates:
    def test_list(self, session):
        r = session.get(f"{API}/templates")
        assert r.status_code == 200
        assert len(r.json()) >= 12

    def test_multilingual_alias_mudat(self, session):
        r = session.get(f"{API}/templates?q=mudat")
        assert r.status_code == 200
        items = r.json()
        assert any(t["id"] == "adjournment" for t in items), "Alias 'mudat' should match Adjournment"

    def test_category_filter(self, session):
        r = session.get(f"{API}/templates?category=Criminal")
        assert r.status_code == 200
        items = r.json()
        assert all(t["category"] == "Criminal" for t in items)
        assert len(items) >= 2

    def test_get_template(self, session):
        r = session.get(f"{API}/templates/adjournment")
        assert r.status_code == 200
        t = r.json()
        assert "content_en" in t and "content_gu" in t


# ---------- Applications ----------
class TestApplications:
    def test_preview_english(self, session, user_ctx):
        r = session.post(f"{API}/applications/preview", headers=H(user_ctx),
                         json={"template_id": "adjournment", "case_id": user_ctx["case_id"],
                               "language": "en", "values": {"next_date": "20-01-2026", "reason": "Illness"}})
        assert r.status_code == 200
        c = r.json()["content"]
        assert "ADJOURNMENT" in c.upper()
        assert "Illness" in c
        assert "20-01-2026" in c
        # case autofill
        assert "12/2026" in c

    def test_preview_gujarati(self, session, user_ctx):
        r = session.post(f"{API}/applications/preview", headers=H(user_ctx),
                         json={"template_id": "adjournment", "case_id": user_ctx["case_id"],
                               "language": "gu", "values": {"next_date": "૨૦-૦૧-૨૦૨૬", "reason": "બિમારી"}})
        assert r.status_code == 200
        c = r.json()["content"]
        assert "મુદત" in c
        assert "બિમારી" in c

    def test_download_pdf_and_credit_consumed(self, session, user_ctx):
        # wallet before
        wb = session.get(f"{API}/wallet", headers=H(user_ctx)).json()["balance"]
        r = session.post(f"{API}/applications/download", headers=H(user_ctx),
                         json={"template_id": "adjournment", "case_id": user_ctx["case_id"],
                               "language": "en", "format": "pdf",
                               "values": {"next_date": "20-01-2026", "reason": "Test"}})
        assert r.status_code == 200
        data = r.json()
        assert data["mime_type"] == "application/pdf"
        raw = base64.b64decode(data["base64"])
        assert raw.startswith(b"%PDF"), "Invalid PDF header"
        wa = session.get(f"{API}/wallet", headers=H(user_ctx)).json()["balance"]
        assert wa == wb - 1

    def test_download_docx(self, session, user_ctx):
        r = session.post(f"{API}/applications/download", headers=H(user_ctx),
                         json={"template_id": "adjournment", "case_id": user_ctx["case_id"],
                               "language": "gu", "format": "docx",
                               "values": {"next_date": "૨૦", "reason": "ટેસ્ટ"}})
        assert r.status_code == 200
        assert "wordprocessingml" in r.json()["mime_type"]
        raw = base64.b64decode(r.json()["base64"])
        assert raw[:2] == b"PK", "DOCX (zip) header expected"

    def test_402_when_wallet_empty(self, session):
        # Fresh user, consume all 5 credits then expect 402
        mobile = f"9{int(time.time()*1000) % 1000000000:09d}"
        session.post(f"{API}/auth/send-otp", json={"mobile": mobile})
        tok = session.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
        for _ in range(5):
            r = session.post(f"{API}/applications/download", headers=h,
                             json={"template_id": "adjournment", "language": "en", "format": "pdf",
                                   "values": {"next_date": "x", "reason": "x"}})
            assert r.status_code == 200
        r = session.post(f"{API}/applications/download", headers=h,
                         json={"template_id": "adjournment", "language": "en", "format": "pdf",
                               "values": {"next_date": "x", "reason": "x"}})
        assert r.status_code == 402


# ---------- Wallet / Purchase / Transactions ----------
class TestWalletPurchase:
    def test_mock_purchase_updates_balance(self, session, user_ctx):
        before = session.get(f"{API}/wallet", headers=H(user_ctx)).json()["balance"]
        r = session.post(f"{API}/purchase/mock", headers=H(user_ctx), json={"plan_id": "plan_299"})
        assert r.status_code == 200
        after = session.get(f"{API}/wallet", headers=H(user_ctx)).json()["balance"]
        assert after == before + 51

    def test_transactions_list(self, session, user_ctx):
        r = session.get(f"{API}/transactions", headers=H(user_ctx))
        assert r.status_code == 200
        txns = r.json()
        assert any(t["plan_id"] == "plan_299" for t in txns)

    def test_bad_plan(self, session, user_ctx):
        r = session.post(f"{API}/purchase/mock", headers=H(user_ctx), json={"plan_id": "unknown"})
        assert r.status_code == 404


# ---------- Drafts ----------
class TestDrafts:
    def test_draft_upsert_and_list(self, session, user_ctx):
        r = session.post(f"{API}/drafts", headers=H(user_ctx),
                         json={"template_id": "affidavit", "case_id": None,
                               "language": "en", "values": {"deponent_name": "TEST"}})
        assert r.status_code == 200
        r = session.get(f"{API}/drafts", headers=H(user_ctx))
        assert r.status_code == 200
        drafts = r.json()
        assert any(d["template_id"] == "affidavit" for d in drafts)

    def test_draft_deleted_after_download(self, session, user_ctx):
        # Save draft
        session.post(f"{API}/drafts", headers=H(user_ctx),
                     json={"template_id": "certified_copy", "case_id": user_ctx["case_id"],
                           "language": "en", "values": {"document_desc": "TEST"}})
        # Download
        r = session.post(f"{API}/applications/download", headers=H(user_ctx),
                        json={"template_id": "certified_copy", "case_id": user_ctx["case_id"],
                              "language": "en", "format": "pdf",
                              "values": {"document_desc": "TEST", "order_date": "01-01-2026"}})
        assert r.status_code == 200
        # Draft removed
        drafts = session.get(f"{API}/drafts", headers=H(user_ctx)).json()
        assert not any(d["template_id"] == "certified_copy" and d.get("case_id") == user_ctx["case_id"]
                       for d in drafts)


# ---------- Search ----------
class TestSearch:
    def test_global_search(self, session, user_ctx):
        r = session.get(f"{API}/search?q=TEST_CaseA", headers=H(user_ctx))
        assert r.status_code == 200
        data = r.json()
        assert "templates" in data and "cases" in data

    def test_search_multilingual(self, session, user_ctx):
        r = session.get(f"{API}/search?q=mudat", headers=H(user_ctx))
        assert r.status_code == 200
        assert any(t["id"] == "adjournment" for t in r.json()["templates"])
