import base64
import os
import sys
import time
import uuid
from pathlib import Path

import pytest
import jwt as pyjwt
import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from starlette.exceptions import HTTPException
from pydantic import ValidationError

backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("DB_NAME", "nyaysetu_test_fp")
os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-characters-long!"

# ---------------- Mock Firestore for Unit Testing ----------------
class MockDocSnap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data.copy() if data else None
        self.exists = data is not None

    def to_dict(self):
        return self._data.copy() if self._data else None

class MockDocRef:
    def __init__(self, coll_dict, doc_id):
        self._coll_dict = coll_dict
        self.id = doc_id

    async def get(self):
        return MockDocSnap(self.id, self._coll_dict.get(self.id))

    async def set(self, data, merge=False):
        if merge and self.id in self._coll_dict:
            self._coll_dict[self.id].update(data)
        else:
            self._coll_dict[self.id] = data.copy()
        self._coll_dict[self.id]["id"] = self.id

    async def delete(self):
        self._coll_dict.pop(self.id, None)

class MockQuery:
    def __init__(self, coll_dict, filters=None, limit_val=None):
        self._coll_dict = coll_dict
        self._filters = filters or []
        self._limit = limit_val

    def where(self, filter=None, **kwargs):
        new_filters = list(self._filters)
        if filter is not None:
            field = getattr(filter, "field_path", getattr(filter, "_field_path", None))
            op = getattr(filter, "op_string", getattr(filter, "_op_string", None))
            val = getattr(filter, "value", getattr(filter, "_value", None))
            new_filters.append((field, op, val))
        return MockQuery(self._coll_dict, new_filters, self._limit)

    def limit(self, n):
        return MockQuery(self._coll_dict, self._filters, n)

    async def stream(self):
        count = 0
        for doc_id, data in list(self._coll_dict.items()):
            match = True
            for field, op, val in self._filters:
                doc_val = data.get(field)
                if op == "==" and doc_val != val:
                    match = False
                    break
                elif op == "!=" and doc_val == val:
                    match = False
                    break
            if match:
                yield MockDocSnap(doc_id, data)
                count += 1
                if self._limit and count >= self._limit:
                    break

class MockFirestore:
    def __init__(self):
        self._data = {}

    def collection(self, name):
        if name not in self._data:
            self._data[name] = {}
        coll_dict = self._data[name]
        class MockCollection:
            def document(self, doc_id=""):
                if not doc_id:
                    doc_id = str(uuid.uuid4())
                return MockDocRef(coll_dict, doc_id)
            def where(self, filter=None, **kwargs):
                return MockQuery(coll_dict).where(filter=filter, **kwargs)
            def limit(self, n):
                return MockQuery(coll_dict).limit(n)
            async def stream(self):
                async for d in MockQuery(coll_dict).stream():
                    yield d
        return MockCollection()

mock_db = MockFirestore()

import server
server.db = mock_db

# RSA Keypair for signing test Firebase tokens
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

PROJECT = "nyaysetu-test-fp-project"
KID = "test-fp-kid"

def _make_firebase_token(*, uid="phone-uid-1", phone="+919898000001", email=None, provider="phone", exp_offset=3600):
    now = int(time.time())
    payload = {
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "aud": PROJECT,
        "auth_time": now - 60,
        "iat": now,
        "exp": now + exp_offset,
        "sub": uid,
        "uid": uid,
        "firebase": {"identities": {}, "sign_in_provider": provider},
    }
    if phone:
        payload["phone_number"] = phone
    if email:
        payload["email"] = email
        payload["email_verified"] = True
    return pyjwt.encode(payload, _PRIV_PEM, algorithm="RS256", headers={"kid": KID})


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setattr(server, "FIREBASE_PROJECT_ID", PROJECT)
    async def fake_certs():
        return {KID: _PUB_PEM}
    monkeypatch.setattr(server, "_get_firebase_certs", fake_certs)
    # Clear mock data
    mock_db._data.clear()
    yield


@pytest.mark.asyncio
async def test_case_1_phone_registered_account_recovery_succeeds():
    """Requirement 5.1: Existing Firebase user with matching linked phone -> OTP -> password reset succeeds."""
    mobile = "9898000001"
    fb_uid = "fb-phone-uid-case1"
    user_id = str(uuid.uuid4())
    
    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "mobile": mobile,
        "firebase_uid": fb_uid,
        "password_hash": server.hash_password("OldPassword123!"),
        "token_version": 1,
        "active": True
    })

    token = _make_firebase_token(uid=fb_uid, phone=f"+91{mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="NewPassword456!")
    res = await server.reset_password(req)
    
    assert res["success"] is True
    assert "Password reset successfully" in res["message"]

    snap = await server.db.collection("users").document(user_id).get()
    updated_user = snap.to_dict()
    assert updated_user["token_version"] == 2
    assert server.verify_password("NewPassword456!", updated_user["password_hash"])
    assert not server.verify_password("OldPassword123!", updated_user["password_hash"])


@pytest.mark.asyncio
async def test_case_2_unlinked_phone_must_not_reset_existing_account():
    """Requirement 5.2: Existing Firestore user with same mobile but different/unlinked Firebase UID -> MUST NOT reset."""
    mobile = "9898000002"
    original_fb_uid = "fb-original-account-uid"
    attacker_phone_uid = "fb-different-phone-uid-999"
    user_id = str(uuid.uuid4())

    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "mobile": mobile,
        "firebase_uid": original_fb_uid,
        "password_hash": server.hash_password("LegitPassword123!"),
        "token_version": 1,
        "active": True
    })

    token = _make_firebase_token(uid=attacker_phone_uid, phone=f"+91{mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="AttackerPassword789!")

    with pytest.raises(HTTPException) as exc_info:
        await server.reset_password(req)

    assert exc_info.value.status_code == 403
    assert "registered via Google or Email" in exc_info.value.detail

    snap = await server.db.collection("users").document(user_id).get()
    user = snap.to_dict()
    assert server.verify_password("LegitPassword123!", user["password_hash"])
    assert not server.verify_password("AttackerPassword789!", user["password_hash"])
    assert user["token_version"] == 1


@pytest.mark.asyncio
async def test_case_3_unknown_mobile_must_not_create_account():
    """Requirement 5.3: Unknown mobile -> MUST NOT create an account."""
    unknown_mobile = "9898000003"
    token = _make_firebase_token(uid="unknown-user-uid", phone=f"+91{unknown_mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="SomeNewPassword123!")

    with pytest.raises(HTTPException) as exc_info:
        await server.reset_password(req)

    assert exc_info.value.status_code == 404
    assert "No NyaySetu Pro account found" in exc_info.value.detail

    docs = [d async for d in server.db.collection("users").where(filter=server.firestore.FieldFilter("mobile", "==", unknown_mobile)).stream()]
    assert len(docs) == 0


@pytest.mark.asyncio
async def test_case_4_google_only_account_must_not_be_hijacked():
    """Requirement 5.4: Google-only account without linked phone -> MUST NOT be hijacked by a phone number matching a Firestore profile."""
    mobile = "9898000004"
    google_uid = "google-provider-uid-12345"
    user_id = str(uuid.uuid4())

    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "email": "advocate@gmail.com",
        "mobile": mobile,
        "firebase_uid": google_uid,
        "provider": "firebase",
        "password_hash": server.hash_password("OriginalPassword123!"),
        "token_version": 1,
        "active": True
    })

    token = _make_firebase_token(uid="fresh-phone-uid-888", phone=f"+91{mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="HijackPassword999!")

    with pytest.raises(HTTPException) as exc_info:
        await server.reset_password(req)

    assert exc_info.value.status_code == 403
    assert "registered via Google or Email" in exc_info.value.detail

    snap = await server.db.collection("users").document(user_id).get()
    assert server.verify_password("OriginalPassword123!", snap.to_dict()["password_hash"])


@pytest.mark.asyncio
async def test_case_5_legacy_account_linking_and_login():
    """Requirement 5.5: Legacy account (no firebase_uid) -> recovery links uid, updates password, new password works."""
    mobile = "9898000005"
    user_id = str(uuid.uuid4())

    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "mobile": mobile,
        "firebase_uid": None,
        "password_hash": server.hash_password("OldLegacyPass123!"),
        "token_version": 1,
        "active": True
    })

    new_fb_uid = "newly-verified-phone-uid"
    token = _make_firebase_token(uid=new_fb_uid, phone=f"+91{mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="NewLegacyPass456!")
    res = await server.reset_password(req)

    assert res["success"] is True

    snap = await server.db.collection("users").document(user_id).get()
    user = snap.to_dict()
    assert user["firebase_uid"] == new_fb_uid
    assert user["token_version"] == 2
    assert server.verify_password("NewLegacyPass456!", user["password_hash"])

    # Test login with new password works
    login_req = server.LoginReq(identifier=mobile, password="NewLegacyPass456!")
    login_res = await server.login_password(login_req)
    assert "token" in login_res

    # Test login with old password fails
    bad_login_req = server.LoginReq(identifier=mobile, password="OldLegacyPass123!")
    with pytest.raises(HTTPException) as exc_info:
        await server.login_password(bad_login_req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_case_6_password_length_validation():
    """Passwords shorter than 8 characters must be rejected."""
    token = _make_firebase_token()
    with pytest.raises((HTTPException, ValidationError)) as exc_info:
        req = server.ResetPasswordReq(id_token=token, new_password="short")
        await server.reset_password(req)
    if isinstance(exc_info.value, HTTPException):
        assert exc_info.value.status_code == 400
        assert "at least 8 characters" in exc_info.value.detail
    else:
        assert "at least 8 characters" in str(exc_info.value)


@pytest.mark.asyncio
async def test_case_7_session_and_token_invalidation():
    """Requirement 5.7: Successful password reset increments token_version."""
    mobile = "9898000007"
    fb_uid = "fb-uid-case7"
    user_id = str(uuid.uuid4())

    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "mobile": mobile,
        "firebase_uid": fb_uid,
        "password_hash": server.hash_password("InitialPass123!"),
        "token_version": 5,
        "active": True
    })

    old_jwt = server.make_token(user_id, token_version=5)

    token = _make_firebase_token(uid=fb_uid, phone=f"+91{mobile}")
    req = server.ResetPasswordReq(id_token=token, new_password="FreshPass12345!")
    res = await server.reset_password(req)
    assert res["success"] is True

    snap = await server.db.collection("users").document(user_id).get()
    assert snap.to_dict()["token_version"] == 6

    # Verify that an old JWT with token_version=5 is rejected by get_user dependency
    with pytest.raises(HTTPException) as exc_info:
        await server.get_user(authorization=f"Bearer {old_jwt}")
    assert exc_info.value.status_code in (401, 403)


@pytest.mark.asyncio
async def test_case_8_email_forgot_password_and_generic_response():
    """Requirement A: Registered and unknown emails receive generic success (no enumeration)."""
    email = "lawyer@nyaysetu.in"
    user_id = str(uuid.uuid4())
    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "email": email,
        "password_hash": server.hash_password("OldPass123!"),
        "token_version": 1,
        "active": True
    })

    res_reg = await server.forgot_password(server.ForgotPasswordReq(email=email))
    assert res_reg["success"] is True
    assert "password reset email has been sent" in res_reg["message"]

    res_unreg = await server.forgot_password(server.ForgotPasswordReq(email="unknown@nyaysetu.in"))
    assert res_unreg["success"] is True
    assert res_unreg["message"] == res_reg["message"]


@pytest.mark.asyncio
async def test_case_9_email_password_reset_sync_and_invalidation():
    """Requirement E: Email reset updates bcrypt hash, invalidates old password and sessions."""
    email = "advocate.synced@nyaysetu.in"
    user_id = str(uuid.uuid4())
    fb_uid = "fb-advocate-sync-uid"
    await server.db.collection("users").document(user_id).set({
        "id": user_id,
        "email": email,
        "firebase_uid": fb_uid,
        "password_hash": server.hash_password("OldLawyerPass123!"),
        "token_version": 2,
        "active": True
    })

    old_jwt = server.make_token(user_id, token_version=2)

    # Perform email reset with verified email token
    token = _make_firebase_token(uid=fb_uid, email=email, phone=None)
    req = server.ResetPasswordReq(id_token=token, new_password="NewLawyerPass456!")
    res = await server.reset_password(req)
    assert res["success"] is True

    # Check token_version was incremented
    snap = await server.db.collection("users").document(user_id).get()
    updated = snap.to_dict()
    assert updated["token_version"] == 3
    assert server.verify_password("NewLawyerPass456!", updated["password_hash"])

    # Login with new password succeeds
    login_res = await server.login(server.LoginReq(identifier=email, password="NewLawyerPass456!"))
    assert "token" in login_res

    # Login with old password fails
    with pytest.raises(HTTPException) as exc_info:
        await server.login(server.LoginReq(identifier=email, password="OldLawyerPass123!"))
    assert exc_info.value.status_code == 401

    # Old JWT session fails
    with pytest.raises(HTTPException) as exc_jwt:
        await server.get_user(authorization=f"Bearer {old_jwt}")
    assert exc_jwt.value.status_code in (401, 403)

