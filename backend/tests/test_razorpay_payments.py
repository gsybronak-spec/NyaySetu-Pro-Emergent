"""Tests for NyaySetu Pro Razorpay payment architecture (Master Plan Phase A).

Covers:
- create-order fails safely (503) when Razorpay keys are not configured
- create-order requires auth, validates plan (unknown/inactive -> 404)
- create-order happy path stores the payment order for the webhook
- verify requires auth; rejects unknown orders, other-user orders, bad signatures
- verify grants credits exactly once; replay returns the existing transaction
- webhook verifies the raw-body signature; missing/bad signature rejected
- webhook payment.captured grants credits idempotently (replay safe)
- non-captured events and unknown orders are no-ops (200)

Uses mongomock_motor (same pattern as existing test suite). Razorpay network
calls are stubbed — no real provider is contacted.
"""

import os
import sys
import uuid
import json
import hmac
import hashlib
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_razorpay")

import pytest
import pytest_asyncio

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_razorpay"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, now
from httpx import AsyncClient, ASGITransport

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs",
               "plans", "payment_orders"]

KEY_ID = "rzp_test_key_id"
KEY_SECRET = "rzp_test_key_secret"
WEBHOOK_SECRET = "rzp_test_webhook_secret"


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll in COLLECTIONS:
        await db[coll].drop()
    await server.seed_plans()
    yield
    for coll in COLLECTIONS:
        await db[coll].drop()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def no_keys(monkeypatch):
    """Default: no Razorpay keys configured (safe-fail state)."""
    monkeypatch.setattr(server, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(server, "RAZORPAY_KEY_SECRET", "")
    monkeypatch.setattr(server, "RAZORPAY_WEBHOOK_SECRET", "")
    yield


@pytest_asyncio.fixture(scope="function")
async def razorpay_configured(monkeypatch):
    """Razorpay keys configured + stubbed create-order network call."""
    monkeypatch.setattr(server, "RAZORPAY_KEY_ID", KEY_ID)
    monkeypatch.setattr(server, "RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setattr(server, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)

    async def fake_create_order(amount_paise: int, receipt: str) -> dict:
        return {"id": "order_" + uuid.uuid4().hex[:20], "receipt": receipt,
                "amount": amount_paise, "currency": "INR"}

    monkeypatch.setattr(server, "_razorpay_create_order", fake_create_order)
    yield


async def create_lawyer(mobile):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "name": "Test Lawyer",
        "provider": "mobile",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({"user_id": user_id, "balance": 5, "total_used": 0,
                                 "free_credits_granted": 5, "updated_at": now().isoformat()})
    return user


def rz_signature(order_id: str, payment_id: str) -> str:
    return hmac.new(KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(),
                    hashlib.sha256).hexdigest()


def webhook_signature(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


# ============================================================
# create-order
# ============================================================

async def test_create_order_requires_auth(client, clean_db):
    r = await client.post("/api/payments/razorpay/create-order",
                          json={"plan_id": "single"})
    assert r.status_code == 401


async def test_create_order_fails_safely_without_keys(client, clean_db):
    lawyer = await create_lawyer("9876500001")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.post("/api/payments/razorpay/create-order",
                          json={"plan_id": "single"}, headers=headers)
    assert r.status_code == 503
    assert "RAZORPAY_KEY_ID" in r.json()["detail"]


async def test_create_order_rejects_unknown_or_inactive_plan(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500002")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}

    r = await client.post("/api/payments/razorpay/create-order",
                          json={"plan_id": "nope"}, headers=headers)
    assert r.status_code == 404

    await db.plans.update_one({"id": "single"}, {"$set": {"active": False}})
    r = await client.post("/api/payments/razorpay/create-order",
                          json={"plan_id": "single"}, headers=headers)
    assert r.status_code == 404


async def test_create_order_happy_path_stores_order(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500003")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}

    r = await client.post("/api/payments/razorpay/create-order",
                          json={"plan_id": "plan_499"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["order_id"].startswith("order_")
    assert body["key_id"] == KEY_ID
    assert body["amount_paise"] == 49900  # ₹499 in paise
    assert body["currency"] == "INR"
    assert body["plan"]["id"] == "plan_499"
    assert body["plan"]["credits"] > 0

    order = await db.payment_orders.find_one({"id": body["order_id"]}, {"_id": 0})
    assert order is not None
    assert order["user_id"] == lawyer["id"]
    assert order["plan_id"] == "plan_499"
    assert order["status"] == "created"


# ============================================================
# verify
# ============================================================

async def test_verify_requires_auth(client, clean_db):
    r = await client.post("/api/payments/razorpay/verify",
                          json={"plan_id": "single", "order_id": "order_x",
                                "payment_id": "pay_x", "signature": "sig"})
    assert r.status_code == 401


async def test_verify_fails_safely_without_keys(client, clean_db):
    lawyer = await create_lawyer("9876500004")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}
    r = await client.post("/api/payments/razorpay/verify",
                          json={"plan_id": "single", "order_id": "order_x",
                                "payment_id": "pay_x", "signature": "sig"},
                          headers=headers)
    assert r.status_code == 503


async def test_verify_rejects_unknown_order_and_foreign_order(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500005")
    other = await create_lawyer("9876500006")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}

    # Unknown order
    r = await client.post("/api/payments/razorpay/verify",
                          json={"plan_id": "single", "order_id": "order_missing",
                                "payment_id": "pay_1", "signature": "x"},
                          headers=headers)
    assert r.status_code == 404

    # Order belonging to another user
    await db.payment_orders.insert_one({
        "id": "order_foreign", "user_id": other["id"], "plan_id": "single",
        "status": "created", "created_at": now().isoformat()})
    sig = rz_signature("order_foreign", "pay_1")
    r = await client.post("/api/payments/razorpay/verify",
                          json={"plan_id": "single", "order_id": "order_foreign",
                                "payment_id": "pay_1", "signature": sig},
                          headers=headers)
    assert r.status_code == 403


async def test_verify_rejects_bad_signature(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500007")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}
    await db.payment_orders.insert_one({
        "id": "order_sig", "user_id": lawyer["id"], "plan_id": "single",
        "status": "created", "created_at": now().isoformat()})

    r = await client.post("/api/payments/razorpay/verify",
                          json={"plan_id": "single", "order_id": "order_sig",
                                "payment_id": "pay_1", "signature": "forged"},
                          headers=headers)
    assert r.status_code == 400
    assert "signature" in r.json()["detail"].lower()
    # No credits granted
    w = await db.wallets.find_one({"user_id": lawyer["id"]}, {"_id": 0})
    assert w["balance"] == 5


async def test_verify_grants_credits_once_and_is_idempotent(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500008")
    tok = make_token(lawyer["id"])
    headers = {"Authorization": f"Bearer {tok}"}
    plan = await db.plans.find_one({"id": "plan_499"}, {"_id": 0})
    await db.payment_orders.insert_one({
        "id": "order_ok", "user_id": lawyer["id"], "plan_id": "plan_499",
        "status": "created", "created_at": now().isoformat()})
    sig = rz_signature("order_ok", "pay_ok_1")

    payload = {"plan_id": "plan_499", "order_id": "order_ok",
               "payment_id": "pay_ok_1", "signature": sig}
    r = await client.post("/api/payments/razorpay/verify", json=payload, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["already_processed"] is False
    assert body["balance"] == 5 + plan["credits"]

    # Replay (client retry / duplicate submission) — no double grant
    r2 = await client.post("/api/payments/razorpay/verify", json=payload, headers=headers)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["already_processed"] is True
    assert body2["transaction_id"] == body["transaction_id"]
    assert body2["balance"] == 5 + plan["credits"]

    txns = await db.transactions.find({"razorpay_payment_id": "pay_ok_1"}).to_list(None)
    assert len(txns) == 1
    assert txns[0]["provider"] == "razorpay"
    assert txns[0]["status"] == "success"
    assert txns[0]["razorpay_order_id"] == "order_ok"
    order = await db.payment_orders.find_one({"id": "order_ok"}, {"_id": 0})
    assert order["status"] == "paid"


# ============================================================
# webhook
# ============================================================

async def test_webhook_requires_secret_and_signature(client, clean_db):
    # No secret configured
    r = await client.post("/api/payments/razorpay/webhook", json={"event": "payment.captured"})
    assert r.status_code == 503

    # Configured but missing signature header
    server.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
    r = await client.post("/api/payments/razorpay/webhook", json={"event": "payment.captured"})
    assert r.status_code == 400
    server.RAZORPAY_WEBHOOK_SECRET = ""


async def test_webhook_rejects_bad_signature(client, clean_db):
    server.RAZORPAY_WEBHOOK_SECRET = WEBHOOK_SECRET
    r = await client.post(
        "/api/payments/razorpay/webhook",
        json={"event": "payment.captured"},
        headers={"X-Razorpay-Signature": "forged"},
    )
    assert r.status_code == 400
    server.RAZORPAY_WEBHOOK_SECRET = ""


async def test_webhook_captured_grants_credits_idempotently(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500009")
    plan = await db.plans.find_one({"id": "plan_499"}, {"_id": 0})
    await db.payment_orders.insert_one({
        "id": "order_w", "user_id": lawyer["id"], "plan_id": "plan_499",
        "status": "created", "created_at": now().isoformat()})

    payload = {
        "event": "payment.captured",
        "payload": {"payment": {"id": "pay_w_1", "order_id": "order_w", "amount": 49900}},
    }
    raw = json.dumps(payload).encode()
    headers = {"X-Razorpay-Signature": webhook_signature(raw)}

    r = await client.post("/api/payments/razorpay/webhook", content=raw, headers=headers)
    assert r.status_code == 200
    assert r.json()["handled"] is True

    w = await db.wallets.find_one({"user_id": lawyer["id"]}, {"_id": 0})
    assert w["balance"] == 5 + plan["credits"]

    # Replay the same webhook — no double grant
    r2 = await client.post("/api/payments/razorpay/webhook", content=raw, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["already_processed"] is True
    w2 = await db.wallets.find_one({"user_id": lawyer["id"]}, {"_id": 0})
    assert w2["balance"] == 5 + plan["credits"]

    txns = await db.transactions.find({"razorpay_payment_id": "pay_w_1"}).to_list(None)
    assert len(txns) == 1


async def test_webhook_other_events_and_unknown_order_are_noops(client, clean_db, razorpay_configured):
    lawyer = await create_lawyer("9876500010")

    # Non-captured event
    raw = json.dumps({"event": "order.paid", "payload": {}}).encode()
    r = await client.post("/api/payments/razorpay/webhook", content=raw,
                          headers={"X-Razorpay-Signature": webhook_signature(raw)})
    assert r.status_code == 200
    assert r.json()["handled"] is False

    # Captured event for an unknown order
    raw = json.dumps({"event": "payment.captured",
                      "payload": {"payment": {"id": "pay_unknown", "order_id": "order_ghost"}}}).encode()
    r = await client.post("/api/payments/razorpay/webhook", content=raw,
                          headers={"X-Razorpay-Signature": webhook_signature(raw)})
    assert r.status_code == 200
    assert r.json()["handled"] is False

    w = await db.wallets.find_one({"user_id": lawyer["id"]}, {"_id": 0})
    assert w["balance"] == 5
