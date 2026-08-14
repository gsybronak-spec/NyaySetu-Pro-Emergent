"""Iteration 4 tests — 24 templates (bilingual aliases), catalog/courts, catalog/police-stations, case with court_id/police_station_id + resolved labels, sort=name/type/updated."""
import os
import time
import base64
import os
import time
import base64
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_iter4")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_iter4"]

import server
server.db = mock_db

from starlette.testclient import TestClient
app_client = TestClient(server.app)

class TestClientWrapper:
    def get(self, url, **kwargs):
        kwargs.pop("timeout", None)
        return app_client.get(url, **kwargs)
    def post(self, url, **kwargs):
        kwargs.pop("timeout", None)
        return app_client.post(url, **kwargs)
    def put(self, url, **kwargs):
        kwargs.pop("timeout", None)
        return app_client.put(url, **kwargs)
    def delete(self, url, **kwargs):
        kwargs.pop("timeout", None)
        return app_client.delete(url, **kwargs)

requests = TestClientWrapper()
API = "/api"


@pytest.fixture(scope="module")
def session():
    return requests


@pytest.fixture(scope="module")
def auth(session):
    mobile = f"9{int(time.time()*1000) % 1000000000:09d}"
    session.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    r = session.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200
    return {"token": r.json()["token"], "mobile": mobile, "user_id": r.json()["user"]["id"]}


def H(auth):
    return {"Authorization": f"Bearer {auth['token']}", "Content-Type": "application/json"}


# ---------- Templates: 23 bilingual with aliases ----------
class TestTemplatesExpanded:
    def test_23_templates_available(self, session):
        r = session.get(f"{API}/templates")
        assert r.status_code == 200
        items = r.json()
        # Legacy 24-template catalog + v2 application catalog (21) = 45 seeds.
        assert len(items) == 45, f"Expected 45 templates, got {len(items)}"

    def test_alias_vakalat(self, session):
        r = session.get(f"{API}/templates?q=vakalat")
        assert r.status_code == 200
        items = r.json()
        assert any(t["id"] == "vakalatnama" for t in items)

    def test_alias_mudat_adjournment(self, session):
        r = session.get(f"{API}/templates?q=mudat")
        items = r.json()
        assert any(t["id"] == "adjournment" for t in items)

    def test_alias_condonation(self, session):
        r = session.get(f"{API}/templates?q=condonation")
        items = r.json()
        assert any(t["id"] == "condonation_delay" for t in items)

    def test_alias_injunction(self, session):
        r = session.get(f"{API}/templates?q=injunction")
        items = r.json()
        assert any(t["id"] == "interim_injunction" for t in items)

    def test_gujarati_vilamb_condonation(self, session):
        r = session.get(f"{API}/templates", params={"q": "વિલંબ"})
        assert r.status_code == 200
        items = r.json()
        assert any(t["id"] == "condonation_delay" for t in items), \
            f"Gujarati 'વિલંબ' should map to condonation_delay. Got: {[t['id'] for t in items]}"

    @pytest.mark.parametrize("tid", [
        "vakalatnama", "restoration", "condonation_delay", "interim_injunction",
        "compromise", "withdrawal", "amendment", "surety", "early_hearing",
        "return_documents", "inspection",
    ])
    def test_new_template_details(self, session, tid):
        r = session.get(f"{API}/templates/{tid}")
        assert r.status_code == 200, f"Template {tid} missing"
        t = r.json()
        assert t.get("content_en") and t.get("content_gu")
        assert "fields" in t


# ---------- Catalog: courts + police-stations ----------
class TestCatalogCourtsAndPolice:
    def test_courts_ahmedabad_specific_plus_generic(self, session):
        r = session.get(f"{API}/catalog/courts", params={"district_id": "ahmedabad"})
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 3, f"Expected specific+generic courts, got {len(items)}"
        d_ids = {c["district_id"] for c in items}
        assert "ahmedabad" in d_ids
        assert "generic" in d_ids
        # ahmedabad-specific should come first
        first_specific_idx = next((i for i, c in enumerate(items) if c["district_id"] == "ahmedabad"), -1)
        first_generic_idx = next((i for i, c in enumerate(items) if c["district_id"] == "generic"), -1)
        assert first_specific_idx < first_generic_idx, "Specific courts should precede generic courts"

    def test_courts_all_no_filter(self, session):
        r = session.get(f"{API}/catalog/courts")
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 5

    def test_police_stations_surat_only(self, session):
        r = session.get(f"{API}/catalog/police-stations", params={"district_id": "surat"})
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        assert all(p["district_id"] == "surat" for p in items), \
            f"Non-surat leaked: {[p['district_id'] for p in items]}"


# ---------- Case with court_id + police_station_id -> labels ----------
class TestCaseCourtPoliceLabels:
    def test_case_with_court_and_police_ids_returns_labels_en(self, session, auth):
        # Pick real ids from catalog
        courts = session.get(f"{API}/catalog/courts", params={"district_id": "ahmedabad"}).json()
        ah_court = next(c for c in courts if c["district_id"] == "ahmedabad")
        ps = session.get(f"{API}/catalog/police-stations", params={"district_id": "surat"}).json()
        ah_ps = ps[0]

        payload = {
            "language": "en",
            "nickname": "TEST_iter4_labels",
            "case_type_id": "criminal_complaint",
            "complaint_type": "police",
            "party_name": "TEST P",
            "district_id": "ahmedabad",
            "court_id": ah_court["id"],
            "police_station_id": ah_ps["id"],
        }
        r = session.post(f"{API}/cases", headers=H(auth), json=payload)
        assert r.status_code == 200
        cid = r.json()["id"]
        auth["case_labeled_id"] = cid

        g = session.get(f"{API}/cases/{cid}", headers=H(auth)).json()
        assert g["court_label"] == ah_court["en"], f"expected {ah_court['en']} got {g.get('court_label')}"
        assert g["police_station_label"] == ah_ps["en"]

    def test_case_gujarati_labels(self, session, auth):
        courts = session.get(f"{API}/catalog/courts", params={"district_id": "ahmedabad"}).json()
        ah_court = next(c for c in courts if c["district_id"] == "ahmedabad")
        payload = {
            "language": "gu",
            "nickname": "TEST_iter4_gu",
            "case_type_id": "criminal_complaint",
            "district_id": "ahmedabad",
            "court_id": ah_court["id"],
        }
        r = session.post(f"{API}/cases", headers=H(auth), json=payload)
        cid = r.json()["id"]
        g = session.get(f"{API}/cases/{cid}", headers=H(auth)).json()
        assert g["court_label"] == ah_court["gu"], f"Gujarati label expected. Got {g.get('court_label')}"

    def test_court_other_uses_custom(self, session, auth):
        payload = {
            "language": "en",
            "nickname": "TEST_iter4_custom_court",
            "case_type_id": "criminal_complaint",
            "complaint_type": "police",
            "court_id": "other",
            "court_custom": "TEST Custom Court X",
            "police_station_id": "other",
            "police_station_custom": "TEST Custom PS Y",
        }
        r = session.post(f"{API}/cases", headers=H(auth), json=payload)
        assert r.status_code == 200
        cid = r.json()["id"]
        g = session.get(f"{API}/cases/{cid}", headers=H(auth)).json()
        assert g["court_label"] == "TEST Custom Court X"
        assert g["police_station_label"] == "TEST Custom PS Y"

    def test_generated_document_contains_court_name(self, session, auth):
        cid = auth["case_labeled_id"]
        # get label
        g = session.get(f"{API}/cases/{cid}", headers=H(auth)).json()
        court_name = g["court_label"]
        # preview
        r = session.post(f"{API}/applications/preview", headers=H(auth),
                         json={"template_id": "adjournment", "case_id": cid,
                               "language": "en",
                               "values": {"next_date": "20-01-2026", "reason": "TEST"}})
        assert r.status_code == 200
        content = r.json()["content"]
        assert court_name in content, f"Court name '{court_name}' not in generated doc"
        # ensure the raw court_id isn't leaking in place of name
        assert g.get("court_id") not in content or court_name in content

        # download PDF too — must succeed and content should be similar
        r = session.post(f"{API}/applications/download", headers=H(auth),
                         json={"template_id": "adjournment", "case_id": cid,
                               "language": "en", "format": "pdf",
                               "values": {"next_date": "20-01-2026", "reason": "TEST"}})
        assert r.status_code == 200
        assert base64.b64decode(r.json()["base64"]).startswith(b"%PDF")


# ---------- Case sorting ----------
class TestCaseSorting:
    def test_sort_name_and_type(self, session, auth):
        # Create 3 cases with predictable names/types
        payloads = [
            {"nickname": "Zebra_case", "case_type_id": "civil_suit", "party_name": "PZ"},
            {"nickname": "Alpha_case", "case_type_id": "criminal_complaint", "party_name": "PA"},
            {"nickname": "Mango_case", "case_type_id": "other_civil", "party_name": "PM"},
        ]
        ids = []
        for p in payloads:
            r = session.post(f"{API}/cases", headers=H(auth), json=p)
            assert r.status_code == 200
            ids.append(r.json()["id"])
            time.sleep(0.05)

        # sort=name
        r = session.get(f"{API}/cases", headers=H(auth), params={"sort": "name"})
        assert r.status_code == 200
        names = [c.get("nickname") or "" for c in r.json() if c["id"] in ids]
        assert names == sorted(names, key=str.lower), f"Not A-Z sorted: {names}"

        # sort=type
        r = session.get(f"{API}/cases", headers=H(auth), params={"sort": "type"})
        assert r.status_code == 200
        types = [c.get("case_type_label") or "" for c in r.json() if c["id"] in ids]
        assert types == sorted(types, key=str.lower), f"Not type-sorted: {types}"

        # default updated: most recent first (last created 'Mango' should appear before earlier)
        r = session.get(f"{API}/cases", headers=H(auth), params={"sort": "updated"})
        listed = [c["id"] for c in r.json() if c["id"] in ids]
        assert listed[0] == ids[-1], "Newest should be first for sort=updated"

    def test_sort_with_category_filter(self, session, auth):
        r = session.get(f"{API}/cases", headers=H(auth),
                        params={"sort": "name", "category": "Civil"})
        assert r.status_code == 200
        items = r.json()
        # All returned should be Civil, and sorted A-Z by name
        assert all(c.get("category") == "Civil" for c in items)
        names = [c.get("nickname") or c.get("party_name") or "" for c in items]
        assert names == sorted(names, key=str.lower)


# ---------- Regression essentials ----------
class TestRegression:
    def test_google_invalid_session_401(self, session):
        r = session.post(f"{API}/auth/google-session", json={"session_id": "INVALID_XYZ"})
        assert r.status_code == 401

    def test_referral_plus_10_on_new_signup(self, session):
        # Create referrer
        m1 = f"9{int(time.time()*1000+1) % 1000000000:09d}"
        session.post(f"{API}/auth/send-otp", json={"mobile": m1})
        tok1 = session.post(f"{API}/auth/verify-otp", json={"mobile": m1, "otp": "123456"}).json()["token"]
        h1 = {"Authorization": f"Bearer {tok1}", "Content-Type": "application/json"}
        code = session.get(f"{API}/referral/me", headers=h1).json()["referral_code"]
        bal_before = session.get(f"{API}/wallet", headers=h1).json()["balance"]

        # New user with referral code
        m2 = f"9{int(time.time()*1000+2) % 1000000000:09d}"
        session.post(f"{API}/auth/send-otp", json={"mobile": m2})
        r = session.post(f"{API}/auth/verify-otp", json={"mobile": m2, "otp": "123456", "referral_code": code})
        assert r.status_code == 200

        bal_after = session.get(f"{API}/wallet", headers=h1).json()["balance"]
        assert bal_after == bal_before + 10

    def test_case_archive_restore_delete(self, session, auth):
        r = session.post(f"{API}/cases", headers=H(auth), json={"nickname": "TEST_iter4_arch"})
        cid = r.json()["id"]
        assert session.post(f"{API}/cases/{cid}/archive", headers=H(auth)).status_code == 200
        assert session.post(f"{API}/cases/{cid}/restore", headers=H(auth)).status_code == 200
        assert session.delete(f"{API}/cases/{cid}", headers=H(auth)).status_code == 200
        assert session.get(f"{API}/cases/{cid}", headers=H(auth)).status_code == 404
