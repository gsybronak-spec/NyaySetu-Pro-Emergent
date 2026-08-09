"""Tests for referral rewards + Google session auth (iteration 2)."""
import os
import time
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_ref")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_ref"]

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
def s():
    return requests


def _mobile(seed: int = 0):
    return f"9{(int(time.time()*1000) + seed) % 1000000000:09d}"


def _new_user(sess, referral_code=None, seed=0):
    m = _mobile(seed)
    sess.post(f"{API}/auth/send-otp", json={"mobile": m})
    body = {"mobile": m, "otp": "123456"}
    if referral_code is not None:
        body["referral_code"] = referral_code
    r = sess.post(f"{API}/auth/verify-otp", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    return {"mobile": m, "token": d["token"], "user": d["user"], "is_new": d["is_new"]}


def _H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _wallet(sess, tok):
    return sess.get(f"{API}/wallet", headers=_H(tok)).json()["balance"]


# ---------- Referral core ----------
class TestReferral:
    def test_new_otp_user_has_referral_code(self, s):
        a = _new_user(s, seed=1)
        # Existing bug tolerance: referral_code should be in returned user
        assert "referral_code" in a["user"] and a["user"]["referral_code"], \
            "New user returned from verify-otp should include a referral_code"
        assert a["user"]["referral_code"].startswith("NS")

    def test_referral_grants_reward_and_no_double(self, s):
        # User A first
        a = _new_user(s, seed=2)
        time.sleep(0.02)
        code = a["user"]["referral_code"]
        assert code
        wa_before = _wallet(s, a["token"])
        assert wa_before == 5

        # New user B signs up with A's referral_code
        b = _new_user(s, referral_code=code, seed=3)
        assert b["is_new"] is True

        # A should now have +10 => 15
        wa_after = _wallet(s, a["token"])
        assert wa_after == wa_before + 10, f"expected {wa_before+10}, got {wa_after}"

        # B stays with 5
        assert _wallet(s, b["token"]) == 5

        # Re-verify B (existing user) with same referral: no double reward
        r = s.post(f"{API}/auth/verify-otp",
                   json={"mobile": b["mobile"], "otp": "123456", "referral_code": code})
        assert r.status_code == 200
        assert r.json()["is_new"] is False
        assert _wallet(s, a["token"]) == wa_after, "Referrer must not be re-rewarded"

    def test_self_referral_no_op(self, s):
        a = _new_user(s, seed=4)
        # Re-login with own referral code
        r = s.post(f"{API}/auth/verify-otp",
                   json={"mobile": a["mobile"], "otp": "123456",
                         "referral_code": a["user"]["referral_code"]})
        assert r.status_code == 200
        # Balance unchanged
        assert _wallet(s, a["token"]) == 5

    def test_invalid_referral_code_ignored(self, s):
        b = _new_user(s, referral_code="NSZZZZZZZZ", seed=5)
        assert b["is_new"] is True
        assert _wallet(s, b["token"]) == 5  # still gets 5 free credits

    def test_referral_me_endpoint(self, s):
        # A refers B and C
        a = _new_user(s, seed=6)
        code = a["user"]["referral_code"]
        time.sleep(0.02)
        _new_user(s, referral_code=code, seed=7)
        time.sleep(0.02)
        _new_user(s, referral_code=code, seed=8)

        r = s.get(f"{API}/referral/me", headers=_H(a["token"]))
        assert r.status_code == 200
        d = r.json()
        assert d["referral_code"] == code
        assert d["reward_per_referral"] == 10
        assert d["total_referred"] == 2
        assert d["total_reward_credits"] == 20
        assert isinstance(d["referrals"], list) and len(d["referrals"]) == 2


# ---------- Google OAuth ----------
class TestGoogleAuth:
    def test_invalid_session_id_returns_401(self, s):
        r = s.post(f"{API}/auth/google-session", json={"session_id": "clearly-not-valid-xyz-123"})
        assert r.status_code == 401

    def test_missing_session_id_returns_422(self, s):
        r = s.post(f"{API}/auth/google-session", json={})
        # Pydantic missing field
        assert r.status_code in (400, 422)


# ---------- Regression on existing flows ----------
class TestRegression:
    def test_wallet_and_profile_still_work(self, s):
        a = _new_user(s, seed=9)
        r = s.get(f"{API}/profile/me", headers=_H(a["token"]))
        assert r.status_code == 200
        assert r.json()["mobile"] == a["mobile"]
        assert r.json().get("referral_code")
        r = s.get(f"{API}/wallet", headers=_H(a["token"]))
        assert r.status_code == 200
        assert r.json()["balance"] == 5

    def test_template_and_download_still_work(self, s):
        a = _new_user(s, seed=10)
        r = s.get(f"{API}/templates")
        assert r.status_code == 200 and len(r.json()) >= 5
        r = s.post(f"{API}/applications/download", headers=_H(a["token"]),
                   json={"template_id": "adjournment", "language": "en", "format": "pdf",
                         "values": {"next_date": "10-01-2026", "reason": "TEST"}})
        assert r.status_code == 200
        assert r.json()["mime_type"] == "application/pdf"
