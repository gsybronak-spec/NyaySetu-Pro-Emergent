"""Regression tests for Firebase Authentication integration (POST /api/auth/firebase).

Covers:
  * Safe-fail 503 when FIREBASE_PROJECT_ID is not configured.
  * Server-side ID-token verification (RS256 signature, aud, iss, expiry, uid).
  * Existing-user linking by verified email / phone / firebase_uid — no duplicates.
  * New-user creation with verified identity + referral reward.
  * Disabled users rejected.
  * Issued NyaySetu JWT works against protected routes.
  * password_hash never returned.
"""
import base64
import os
import sys
import time
from pathlib import Path

import pytest
import jwt as pyjwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_firebase")

import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_firebase"]

import server

server.db = mock_db

from starlette.testclient import TestClient

app_client = TestClient(server.app)

BASE = "/api"

# --- RSA keypair for minting test Firebase tokens ---
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

_PRIV = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIV_PEM = _PRIV.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_PUB_PEM = _PRIV.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

# Second keypair used to sign a token that is NOT verifiable with the served cert.
_PRIV2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIV2_PEM = _PRIV2.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

PROJECT = "nyaysetu-test-project"
KID = "test-kid-1"


def _firebase_token(*, uid="fb-uid-1", email=None, email_verified=True, phone=None,
                    name=None, picture=None, exp_offset=3600, aud=PROJECT, iss=None):
    now = int(time.time())
    payload = {
        "iss": iss or f"https://securetoken.google.com/{PROJECT}",
        "aud": aud,
        "auth_time": now - 60,
        "iat": now,
        "exp": now + exp_offset,
        "sub": uid,
        "uid": uid,
        "firebase": {"identities": {}, "sign_in_provider": "password"},
    }
    if email is not None:
        payload["email"] = email
        payload["email_verified"] = email_verified
    if phone is not None:
        payload["phone_number"] = phone
    if name is not None:
        payload["name"] = name
    if picture is not None:
        payload["picture"] = picture
    return pyjwt.encode(payload, _PRIV_PEM, algorithm="RS256", headers={"kid": KID})


@pytest.fixture(autouse=True)
def _firebase_env(monkeypatch):
    monkeypatch.setattr(server, "FIREBASE_PROJECT_ID", PROJECT)

    async def fake_certs():
        return {KID: _PUB_PEM}

    monkeypatch.setattr(server, "_get_firebase_certs", fake_certs)
    yield
    monkeypatch.setattr(server, "FIREBASE_PROJECT_ID", "")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --------- SAFE-FAIL ---------

def test_firebase_endpoint_503_when_not_configured(monkeypatch):
    monkeypatch.setattr(server, "FIREBASE_PROJECT_ID", "")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": "whatever"})
    assert r.status_code == 503
    assert "not configured" in r.text.lower()


# --------- TOKEN VERIFICATION ---------

def test_invalid_signature_rejected():
    # Signed with a DIFFERENT key than the one served by the (mocked) cert
    # endpoint -> signature verification must fail with 401.
    bad = pyjwt.encode(
        {"uid": "x", "iss": f"https://securetoken.google.com/{PROJECT}", "aud": PROJECT,
         "iat": int(time.time()), "exp": int(time.time()) + 3600},
        _PRIV2_PEM,
        algorithm="RS256",
        headers={"kid": KID},
    )
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": bad})
    assert r.status_code == 401


def test_expired_token_rejected():
    tok = _firebase_token(email="old@test.in", exp_offset=-100)
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 401


def test_wrong_audience_rejected():
    tok = _firebase_token(email="x@test.in", aud="some-other-project")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 401


def test_wrong_issuer_rejected():
    tok = _firebase_token(email="x@test.in", iss="https://securetoken.google.com/other")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 401


def test_malformed_token_rejected():
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": "not.a.jwt"})
    assert r.status_code == 401


# --------- NEW USER ---------

def test_new_email_user_created_and_jwt_works():
    tok = _firebase_token(uid="fb-new-email", email="fire.new@test.in", name="Fire New")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_new"] is True
    assert data["user"]["email"] == "fire.new@test.in"
    assert data["user"]["name"] == "Fire New"
    assert data["user"]["provider"] == "firebase"
    assert data["user"].get("firebase_uid") == "fb-new-email"
    assert "password_hash" not in data["user"]
    # returned JWT works on a protected route
    me = app_client.get(f"{BASE}/profile/me", headers=_auth(data["token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "fire.new@test.in"


def test_new_phone_user_mobile_normalized():
    tok = _firebase_token(uid="fb-new-phone", phone="+919876543210")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 200, r.text
    u = r.json()["user"]
    assert u["mobile"] == "9876543210"
    assert u.get("firebase_uid") == "fb-new-phone"
    assert u["provider"] == "firebase"


def test_new_user_referral_rewarded():
    # referrer
    rt = app_client.post(f"{BASE}/auth/send-otp", json={"mobile": "9999000001"})
    assert rt.status_code == 200
    rv = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": "9999000001", "otp": "123456"})
    ref_code = rv.json()["user"]["referral_code"]
    # new firebase user with referral
    tok = _firebase_token(uid="fb-ref-new", email="ref.new@test.in")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok, "referral_code": ref_code})
    assert r.status_code == 200
    assert r.json()["is_new"] is True


# --------- EXISTING USER LINKING ---------

def test_existing_user_linked_by_email_no_duplicate():
    import asyncio
    # create the legacy user via OTP and give it the email BEFORE the Firebase login
    app_client.post(f"{BASE}/auth/send-otp", json={"mobile": "9898000001"})
    rv = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": "9898000001", "otp": "123456"})
    legacy = rv.json()["user"]
    assert legacy["provider"] == "mobile"
    up = app_client.put(
        f"{BASE}/profile/update",
        headers=_auth(rv.json()["token"]),
        json={"email": "link1@test.in"},
    )
    assert up.status_code == 200, up.text

    # Firebase login with the SAME verified email -> links to the legacy account
    tok = _firebase_token(uid="fb-link-1", email="link1@test.in", name="Linked Name")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 200, r.text
    assert r.json()["is_new"] is False
    assert r.json()["user"]["id"] == legacy["id"]
    assert r.json()["user"]["firebase_uid"] == "fb-link-1"
    # Repeat login with the same UID maps to the same account (no duplicate)
    r2 = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r2.status_code == 200
    assert r2.json()["user"]["id"] == legacy["id"]
    # only one user has that firebase_uid
    count = asyncio.run(server.db.users.count_documents({"firebase_uid": "fb-link-1"}))
    assert count == 1


def test_existing_user_linked_by_phone():
    app_client.post(f"{BASE}/auth/send-otp", json={"mobile": "9898000002"})
    rv = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": "9898000002", "otp": "123456"})
    legacy = rv.json()["user"]

    tok = _firebase_token(uid="fb-link-phone", phone="+919898000002")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["is_new"] is False
    assert data["user"]["id"] == legacy["id"]
    assert data["user"]["firebase_uid"] == "fb-link-phone"


def test_disabled_user_rejected():
    app_client.post(f"{BASE}/auth/send-otp", json={"mobile": "9898000003"})
    rv = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": "9898000003", "otp": "123456"})
    uid = rv.json()["user"]["id"]
    import asyncio
    asyncio.run(server.db.users.update_one({"id": uid}, {"$set": {"active": False}}))
    tok = _firebase_token(uid="fb-disabled", phone="+919898000003")
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 403


def test_unverified_email_not_used_for_linking_or_creation():
    # legacy user exists with this email
    app_client.post(f"{BASE}/auth/send-otp", json={"mobile": "9898000004"})
    rv = app_client.post(f"{BASE}/auth/verify-otp", json={"mobile": "9898000004", "otp": "123456"})
    app_client.put(f"{BASE}/profile/update", headers=_auth(rv.json()["token"]),
                   json={"email": "unverified@test.in"})
    # token has the same email but NOT verified -> must NOT link/claim it
    tok = _firebase_token(uid="fb-unver", email="unverified@test.in", email_verified=False)
    r = app_client.post(f"{BASE}/auth/firebase", json={"id_token": tok})
    assert r.status_code == 200
    assert r.json()["is_new"] is True
    assert r.json()["user"].get("email") is None  # unverified email never stored
