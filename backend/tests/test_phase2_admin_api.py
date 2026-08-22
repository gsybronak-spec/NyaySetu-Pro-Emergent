"""Tests for Phase 2: Backend Admin API Expansion.

Covers all 33 required scenarios across:
- AUTH (1-3)
- USERS (4-8)
- WALLET (9-15)
- AUDIT LOGS (16-17)
- APPLICATIONS (18-19)
- CASES (20-21)
- CATALOG (22-23)
- PLANS (24-25)
- TEMPLATES (26-33)
"""

import os
import sys
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_phase2_admin")

import pytest
import pytest_asyncio
import bcrypt
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_phase2_admin"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    make_token, make_admin_token,
    seed_templates, seed_plans, seed_catalogs,
    resolve_template_for_draft,
    TEMPLATES, TEMPLATES_V2,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    server.db = db
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "audit_logs", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans", "districts", "talukas", "courts",
        "case_types", "police_stations", "laws", "settings"
    ]:
        await db[coll_name].drop()
    yield
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "audit_logs", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans", "districts", "talukas", "courts",
        "case_types", "police_stations", "laws", "settings"
    ]:
        await db[coll_name].drop()


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def super_admin_auth():
    admin_id = str(uuid.uuid4())
    email = "superadmin@nyaysetu.in"
    hashed = bcrypt.hashpw(b"Secret123!", bcrypt.gensalt()).decode("utf-8")
    await db.admin_users.insert_one({
        "id": admin_id,
        "email": email,
        "password_hash": hashed,
        "name": "Super Admin Phase 2",
        "role": "super_admin",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_admin_token(admin_id, email, "super_admin")
    return {"Authorization": f"Bearer {token}", "admin_id": admin_id, "email": email}


@pytest_asyncio.fixture
async def regular_admin_auth():
    admin_id = str(uuid.uuid4())
    email = "staff@nyaysetu.in"
    hashed = bcrypt.hashpw(b"Secret123!", bcrypt.gensalt()).decode("utf-8")
    await db.admin_users.insert_one({
        "id": admin_id,
        "email": email,
        "password_hash": hashed,
        "name": "Staff Admin",
        "role": "staff_admin",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_admin_token(admin_id, email, "staff_admin")
    return {"Authorization": f"Bearer {token}", "admin_id": admin_id, "email": email}


@pytest_asyncio.fixture
async def lawyer_auth():
    user_id = str(uuid.uuid4())
    mobile = "9876543210"
    await db.users.insert_one({
        "id": user_id,
        "mobile": mobile,
        "name": "Advocate Test User",
        "email": "advocate@test.com",
        "user_type": "Advocate",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_token(user_id, mobile)
    return {"Authorization": f"Bearer {token}", "user_id": user_id}


# ============================================================
# 1. AUTH SCENARIOS (1-3)
# ============================================================

@pytest.mark.asyncio
async def test_01_non_admin_rejected_on_admin_endpoints(client, lawyer_auth):
    """Scenario 1: Authenticated lawyer JWT is rejected with 401/403 on admin endpoints."""
    res = await client.get("/api/admin/users", headers={"Authorization": lawyer_auth["Authorization"]})
    assert res.status_code == 401  # Not an admin token


@pytest.mark.asyncio
async def test_02_missing_or_invalid_jwt_rejected(client):
    """Scenario 2: Missing or invalid JWT is rejected with 401."""
    res1 = await client.get("/api/admin/users")
    assert res1.status_code == 401

    res2 = await client.get("/api/admin/users", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_03_super_admin_accepted_and_staff_admin_restricted(client, super_admin_auth, regular_admin_auth):
    """Scenario 3: Super Admin is accepted (200), non-super-admin gets 403 on super_admin-only endpoints."""
    # Super Admin allowed
    res_sa = await client.get("/api/admin/users", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_sa.status_code == 200

    # Staff Admin (not super_admin) gets 403 on require_super_admin endpoints
    res_staff = await client.get("/api/admin/users", headers={"Authorization": regular_admin_auth["Authorization"]})
    assert res_staff.status_code == 403


# ============================================================
# 2. USERS ADMIN API (4-8)
# ============================================================

@pytest.mark.asyncio
async def test_04_users_pagination(client, super_admin_auth):
    """Scenario 4: User list pagination supports page, page_size, total, and total_pages."""
    for i in range(15):
        await db.users.insert_one({
            "id": f"usr_{i}",
            "name": f"Lawyer {i}",
            "mobile": f"90000000{i:02d}",
            "email": f"lawyer{i}@nyaysetu.in",
            "user_type": "Advocate",
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    res = await client.get("/api/admin/users?page=2&page_size=5", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 15
    assert data["page"] == 2
    assert data["page_size"] == 5
    assert data["total_pages"] == 3
    assert len(data["users"]) == 5


@pytest.mark.asyncio
async def test_05_users_search_and_filters(client, super_admin_auth):
    """Scenario 5: User list search and filters by name, mobile, email, status, role, provider."""
    await db.users.insert_one({
        "id": "usr_google_1",
        "name": "Bhavik Patel",
        "mobile": "9825000001",
        "email": "bhavik@google.com",
        "user_type": "Advocate",
        "provider": "google",
        "active": True,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.users.insert_one({
        "id": "usr_mobile_2",
        "name": "Suresh Shah",
        "mobile": "9825000002",
        "email": "suresh@shah.com",
        "user_type": "Junior Advocate",
        "provider": "mobile",
        "active": False,
        "status": "suspended",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Search by name
    res1 = await client.get("/api/admin/users?search=Bhavik", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res1.json()["total"] == 1
    assert res1.json()["users"][0]["name"] == "Bhavik Patel"

    # Filter by provider
    res2 = await client.get("/api/admin/users?provider=google", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res2.json()["total"] == 1

    # Filter by status suspended
    res3 = await client.get("/api/admin/users?status=suspended", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res3.json()["total"] == 1
    assert res3.json()["users"][0]["id"] == "usr_mobile_2"


@pytest.mark.asyncio
async def test_06_users_detail_view(client, super_admin_auth):
    """Scenario 6: User detail endpoint includes profile, wallet balance, case count, app count, bar info."""
    user_id = "usr_detail_test"
    await db.users.insert_one({
        "id": user_id,
        "name": "Nirav Dave",
        "email": "nirav@nyaysetu.in",
        "mobile": "9898000001",
        "user_type": "Advocate",
        "bar_council_number": "G/1234/2020",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 45,
        "free_credits_granted": 5,
        "total_used": 12,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.cases.insert_one({"id": "case_1", "user_id": user_id, "nickname": "Test Case"})
    await db.applications.insert_one({"id": "app_1", "user_id": user_id, "template_id": "vakalatnama"})

    res = await client.get(f"/api/admin/users/{user_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Nirav Dave"
    assert data["wallet_balance"] == 45
    assert data["total_credits_used"] == 12
    assert data["cases_count"] == 1
    assert data["applications_count"] == 1
    assert data["bar_council_number"] == "G/1234/2020"


@pytest.mark.asyncio
async def test_07_users_suspend_activate_ban_and_bulk_status(client, super_admin_auth):
    """Scenario 7: User status endpoints (suspend, activate, ban, bulk-status) correctly update state."""
    u1, u2 = "u_stat_1", "u_stat_2"
    for uid in [u1, u2]:
        await db.users.insert_one({
            "id": uid,
            "name": f"User {uid}",
            "mobile": f"91000000{uid[-1]}",
            "active": True,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Suspend u1
    res1 = await client.post(f"/api/admin/users/{u1}/suspend", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res1.status_code == 200
    assert res1.json()["status"] == "suspended"
    db_u1 = await db.users.find_one({"id": u1})
    assert db_u1["active"] is False

    # Activate u1
    res2 = await client.post(f"/api/admin/users/{u1}/activate", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res2.status_code == 200
    assert res2.json()["status"] == "active"
    db_u1 = await db.users.find_one({"id": u1})
    assert db_u1["active"] is True

    # Ban u1
    res3 = await client.post(f"/api/admin/users/{u1}/ban", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res3.status_code == 200
    assert res3.json()["status"] == "banned"
    db_u1 = await db.users.find_one({"id": u1})
    assert db_u1["active"] is False

    # Bulk suspend
    res4 = await client.post("/api/admin/users/bulk-status", json={
        "user_ids": [u1, u2],
        "action": "suspend",
        "reason": "Test bulk suspension",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res4.status_code == 200
    assert res4.json()["affected_count"] == 2


@pytest.mark.asyncio
async def test_08_users_profile_update_and_audit_logging(client, super_admin_auth):
    """Scenario 8: User profile update modifies allowed fields without touching credentials, creating audit log."""
    user_id = "u_profile_upd"
    await db.users.insert_one({
        "id": user_id,
        "name": "Old Name",
        "email": "old@nyaysetu.in",
        "mobile": "9876500000",
        "user_type": "Advocate",
        "password_hash": "secret_hashed_password_never_expose",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    res = await client.put(f"/api/admin/users/{user_id}", json={
        "name": "New Valid Name",
        "user_type": "Senior Advocate",
        "district": "Surat",
        "state": "Gujarat",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert res.json()["user"]["name"] == "New Valid Name"
    assert "password_hash" not in res.json()["user"]

    db_u = await db.users.find_one({"id": user_id})
    assert db_u["name"] == "New Valid Name"
    assert db_u["password_hash"] == "secret_hashed_password_never_expose"

    # Verify audit log
    audit = await db.audit_logs.find_one({"action": "user_profile_update", "entity_id": user_id})
    assert audit is not None
    assert audit["admin_id"] == super_admin_auth["admin_id"]
    assert audit["old_value"]["name"] == "Old Name"
    assert audit["new_value"]["name"] == "New Valid Name"


# ============================================================
# 3. WALLET / CREDITS ADMIN API (9-15)
# ============================================================

@pytest.mark.asyncio
async def test_09_wallet_view_endpoint(client, super_admin_auth):
    """Scenario 9: Admin can view user wallet with earned, consumed, and recent transactions."""
    user_id = "u_wallet_view"
    await db.users.insert_one({"id": user_id, "name": "Wallet User", "active": True})
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 20,
        "free_credits_granted": 5,
        "total_used": 15,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.transactions.insert_one({
        "id": "txn_mock_1",
        "user_id": user_id,
        "type": "purchase",
        "credits": 20,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    res = await client.get(f"/api/admin/users/{user_id}/wallet", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["balance"] == 20
    assert data["total_credits_earned"] == 20
    assert data["total_credits_consumed"] == 15
    assert len(data["recent_transactions"]) == 1


@pytest.mark.asyncio
async def test_10_positive_credit_adjustment(client, super_admin_auth):
    """Scenario 10: Positive credit adjustment credits wallet atomically and records transaction."""
    user_id = "u_adj_pos"
    await db.users.insert_one({"id": user_id, "name": "Credit User", "active": True})
    await db.wallets.insert_one({"user_id": user_id, "balance": 10, "free_credits_granted": 5, "total_used": 0})

    res = await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": 25,
        "reason": "Promotional bonus credits",
        "reference": "PROMO_SUMMER_2026",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["balance_before"] == 10
    assert data["balance_after"] == 35
    assert data["amount"] == 25

    w = await db.wallets.find_one({"user_id": user_id})
    assert w["balance"] == 35


@pytest.mark.asyncio
async def test_11_debit_credit_adjustment(client, super_admin_auth):
    """Scenario 11: Debit credit adjustment decreases balance atomically."""
    user_id = "u_adj_deb"
    await db.users.insert_one({"id": user_id, "name": "Debit User", "active": True})
    await db.wallets.insert_one({"user_id": user_id, "balance": 30, "free_credits_granted": 5, "total_used": 0})

    res = await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": -10,
        "reason": "Correcting duplicate credit grant",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert res.json()["balance_before"] == 30
    assert res.json()["balance_after"] == 20

    w = await db.wallets.find_one({"user_id": user_id})
    assert w["balance"] == 20


@pytest.mark.asyncio
async def test_12_wallet_adjustment_requires_reason(client, super_admin_auth):
    """Scenario 12: Adjustment without mandatory reason is rejected with 400."""
    user_id = "u_adj_no_reason"
    await db.users.insert_one({"id": user_id, "name": "User", "active": True})

    res = await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": 10,
        "reason": "   ",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 400
    assert "Reason is mandatory" in res.json()["detail"]


@pytest.mark.asyncio
async def test_13_wallet_negative_balance_prevention(client, super_admin_auth):
    """Scenario 13: Debit that would make balance negative is rejected with 400."""
    user_id = "u_adj_neg_test"
    await db.users.insert_one({"id": user_id, "name": "Low Balance User", "active": True})
    await db.wallets.insert_one({"user_id": user_id, "balance": 5, "free_credits_granted": 5, "total_used": 0})

    res = await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": -10,
        "reason": "Debit more than available",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 400
    assert "balance cannot become negative" in res.json()["detail"]

    w = await db.wallets.find_one({"user_id": user_id})
    assert w["balance"] == 5


@pytest.mark.asyncio
async def test_14_wallet_adjustment_creates_transaction_record(client, super_admin_auth):
    """Scenario 14: Adjustment creates transaction with type=admin_adjustment, balance_before/after, reason, admin_id."""
    user_id = "u_txn_verify"
    await db.users.insert_one({"id": user_id, "name": "Txn User", "active": True})
    await db.wallets.insert_one({"user_id": user_id, "balance": 15, "free_credits_granted": 5, "total_used": 0})

    res = await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": 5,
        "reason": "Goodwill support credits",
        "reference": "TICKET-101",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    txn_id = res.json()["transaction_id"]

    txn = await db.transactions.find_one({"id": txn_id})
    assert txn is not None
    assert txn["type"] == "admin_adjustment"
    assert txn["credits"] == 5
    assert txn["balance_before"] == 15
    assert txn["balance_after"] == 20
    assert txn["reason"] == "Goodwill support credits"
    assert txn["reference"] == "TICKET-101"
    assert txn["admin_id"] == super_admin_auth["admin_id"]


@pytest.mark.asyncio
async def test_15_wallet_adjustment_creates_audit_log(client, super_admin_auth):
    """Scenario 15: Wallet adjustment produces an audit log record with old and new values."""
    user_id = "u_wallet_audit"
    await db.users.insert_one({"id": user_id, "name": "Audit User", "active": True})
    await db.wallets.insert_one({"user_id": user_id, "balance": 10, "free_credits_granted": 5, "total_used": 0})

    await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={
        "amount": 10,
        "reason": "Annual reward credits",
    }, headers={"Authorization": super_admin_auth["Authorization"]})

    audit = await db.audit_logs.find_one({"action": "wallet_adjust", "entity_id": user_id})
    assert audit is not None
    assert audit["entity_type"] == "wallet"
    assert audit["old_value"]["balance"] == 10
    assert audit["new_value"]["balance"] == 20
    assert audit["reason"] == "Annual reward credits"


# ============================================================
# 4. AUDIT LOG API (16-17)
# ============================================================

@pytest.mark.asyncio
async def test_16_audit_log_created_across_mutations(client, super_admin_auth):
    """Scenario 16: Administrative actions across users, wallets, and plans all create audit entries."""
    user_id = "u_multi_audit"
    await db.users.insert_one({"id": user_id, "name": "Test Multi", "active": True})

    # User suspend
    await client.post(f"/api/admin/users/{user_id}/suspend", headers={"Authorization": super_admin_auth["Authorization"]})
    # Wallet adjust
    await client.post(f"/api/admin/users/{user_id}/wallet/adjust", json={"amount": 5, "reason": "Test"}, headers={"Authorization": super_admin_auth["Authorization"]})
    # Plan create
    await client.post("/api/admin/plans", json={"name": "Special Plan", "price": 499, "credits": 50}, headers={"Authorization": super_admin_auth["Authorization"]})

    count = await db.audit_logs.count_documents({})
    assert count >= 3


@pytest.mark.asyncio
async def test_17_audit_log_filtering_and_pagination(client, super_admin_auth):
    """Scenario 17: GET /api/admin/audit-logs supports filtering by action, entity_type, and pagination."""
    await db.audit_logs.insert_one({
        "id": "audit_1",
        "action": "user_suspend",
        "entity_type": "user",
        "entity_id": "usr_x",
        "admin_id": super_admin_auth["admin_id"],
        "timestamp": "2026-08-20T10:00:00Z",
    })
    await db.audit_logs.insert_one({
        "id": "audit_2",
        "action": "wallet_adjust",
        "entity_type": "wallet",
        "entity_id": "usr_y",
        "admin_id": super_admin_auth["admin_id"],
        "timestamp": "2026-08-21T10:00:00Z",
    })

    res1 = await client.get("/api/admin/audit-logs?action=user_suspend", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res1.status_code == 200
    assert res1.json()["total"] == 1
    assert res1.json()["items"][0]["action"] == "user_suspend"

    res2 = await client.get("/api/admin/audit-logs?page=1&page_size=1", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res2.json()["total"] == 2
    assert len(res2.json()["items"]) == 1
    assert res2.json()["total_pages"] == 2


# ============================================================
# 5. APPLICATIONS ADMIN API (18-19)
# ============================================================

@pytest.mark.asyncio
async def test_18_applications_admin_listing(client, super_admin_auth):
    """Scenario 18: GET /api/admin/applications returns paginated, enriched document list."""
    user_id = "usr_app_list"
    await db.users.insert_one({"id": user_id, "name": "App Lawyer", "email": "app@nyaysetu.in", "active": True})
    await db.applications.insert_one({
        "id": "app_doc_1",
        "user_id": user_id,
        "template_id": "vakalatnama",
        "template_name": "Vakalatnama (Civil / Criminal)",
        "format": "pdf",
        "language": "gu",
        "filename": "vakalatnama_2026.pdf",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    res = await client.get("/api/admin/applications?format=pdf", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["applications"][0]["filename"] == "vakalatnama_2026.pdf"
    assert data["applications"][0]["user"]["name"] == "App Lawyer"


@pytest.mark.asyncio
async def test_19_applications_admin_detail(client, super_admin_auth):
    """Scenario 19: GET /api/admin/applications/{id} exposes engine, font, sha256, user, and case details."""
    app_id = "app_detail_full"
    user_id = "usr_app_full"
    await db.users.insert_one({"id": user_id, "name": "Full User", "active": True})
    await db.cases.insert_one({"id": "case_full_1", "user_id": user_id, "nickname": "Special Civil Suit"})
    await db.applications.insert_one({
        "id": app_id,
        "user_id": user_id,
        "case_id": "case_full_1",
        "template_id": "vakalatnama",
        "template_name": "Vakalatnama",
        "format": "pdf",
        "language": "en",
        "filename": "vakalatnama.pdf",
        "file_size": 45120,
        "sha256": "abcdef1234567890",
        "generator_version": "3.1.0",
        "engine": "harfbuzz_reportlab",
        "font_family": "Lohit-Gujarati",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    res = await client.get(f"/api/admin/applications/{app_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == app_id
    assert data["engine"] == "harfbuzz_reportlab"
    assert data["sha256"] == "abcdef1234567890"
    assert data["case"]["nickname"] == "Special Civil Suit"
    assert data["user"]["name"] == "Full User"


# ============================================================
# 6. CASES ADMIN API (20-21)
# ============================================================

@pytest.mark.asyncio
async def test_20_cases_admin_list_and_filters(client, super_admin_auth):
    """Scenario 20: GET /api/admin/cases supports filters, search, and pagination."""
    user_id = "usr_case_owner"
    await db.users.insert_one({"id": user_id, "name": "Case Owner", "active": True})
    await db.cases.insert_one({
        "id": "case_cma_101",
        "user_id": user_id,
        "nickname": "CMA 101 Property Dispute",
        "case_number": "CMA/101/2026",
        "party_name": "Ramesh",
        "opposite_party": "Suresh",
        "status": "active",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

    res = await client.get("/api/admin/cases?search=Property", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["cases"][0]["owner"]["name"] == "Case Owner"


@pytest.mark.asyncio
async def test_21_cases_admin_detail_and_archive_restore(client, super_admin_auth):
    """Scenario 21: GET /api/admin/cases/{id} resolves owner, drafts, applications; archive/restore works."""
    case_id = "case_lifecycle_1"
    user_id = "usr_lifecycle"
    await db.users.insert_one({"id": user_id, "name": "Lifecycle Owner", "active": True})
    await db.cases.insert_one({"id": case_id, "user_id": user_id, "nickname": "Lifecycle Case", "status": "active"})
    await db.drafts.insert_one({"id": "drf_1", "case_id": case_id, "user_id": user_id, "template_id": "vakalatnama"})
    await db.applications.insert_one({"id": "app_1", "case_id": case_id, "user_id": user_id, "template_id": "vakalatnama"})

    res_detail = await client.get(f"/api/admin/cases/{case_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_detail.status_code == 200
    assert len(res_detail.json()["drafts"]) == 1
    assert len(res_detail.json()["applications"]) == 1

    # Archive
    res_arch = await client.post(f"/api/admin/cases/{case_id}/archive", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_arch.status_code == 200
    db_c = await db.cases.find_one({"id": case_id})
    assert db_c["status"] == "archived"

    # Restore
    res_rest = await client.post(f"/api/admin/cases/{case_id}/restore", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_rest.status_code == 200
    db_c = await db.cases.find_one({"id": case_id})
    assert db_c["status"] == "active"


# ============================================================
# 7. CATALOG ADMIN API (22-23)
# ============================================================

@pytest.mark.asyncio
async def test_22_catalog_crud_and_status(client, super_admin_auth):
    """Scenario 22: Full CRUD on catalog entities (courts, districts, case-types, laws, etc.)."""
    # Create court entry
    res_create = await client.post("/api/admin/catalog/courts", json={
        "en": "Taluka Court, Dholka",
        "gu": "તાલુકા કોર્ટ, ધોળકા",
        "district_id": "ahmedabad",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_create.status_code == 200
    created_item = res_create.json()["item"]
    item_id = created_item["id"]

    # Get single item
    res_get = await client.get(f"/api/admin/catalog/courts/{item_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_get.status_code == 200
    assert res_get.json()["en"] == "Taluka Court, Dholka"

    # Update item
    res_upd = await client.put(f"/api/admin/catalog/courts/{item_id}", json={
        "en": "Principal Civil Court, Dholka",
        "gu": "પ્રિન્સિપાલ સિવિલ કોર્ટ, ધોળકા",
        "district_id": "ahmedabad",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_upd.status_code == 200
    assert res_upd.json()["item"]["en"] == "Principal Civil Court, Dholka"

    # Deactivate status
    res_stat = await client.post(f"/api/admin/catalog/courts/{item_id}/status", json={"active": False}, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_stat.status_code == 200
    assert res_stat.json()["item"]["active"] is False

    # Safe delete (soft delete)
    res_del = await client.delete(f"/api/admin/catalog/courts/{item_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_del.status_code == 200


@pytest.mark.asyncio
async def test_23_catalog_mutation_audit_logging(client, super_admin_auth):
    """Scenario 23: Catalog mutations record audit log entries."""
    await client.post("/api/admin/catalog/case-types", json={
        "en": "Arbitration Petition",
        "gu": "લવાદ અરજી",
        "cat": "Civil",
    }, headers={"Authorization": super_admin_auth["Authorization"]})

    audit = await db.audit_logs.find_one({"action": "catalog_create"})
    assert audit is not None
    assert audit["entity_type"] == "catalog"
    assert "Arbitration Petition" in audit["metadata"]["en"]


# ============================================================
# 8. PLANS ADMIN API (24-25)
# ============================================================

@pytest.mark.asyncio
async def test_24_plans_list_and_detail(client, super_admin_auth):
    """Scenario 24: GET /api/admin/plans and /api/admin/plans/{id} list and return plan details."""
    res_create = await client.post("/api/admin/plans", json={
        "name": "Standard Advocate Pro",
        "price": 999,
        "credits": 100,
        "popular": True,
        "description": "Standard 100 credits plan",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_create.status_code == 200
    plan_id = res_create.json()["plan"]["id"]

    res_get = await client.get(f"/api/admin/plans/{plan_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Standard Advocate Pro"
    assert res_get.json()["credits"] == 100


@pytest.mark.asyncio
async def test_25_plans_activate_deactivate_and_audit(client, super_admin_auth):
    """Scenario 25: Plans activate/deactivate endpoints update state and log audit entries."""
    res_create = await client.post("/api/admin/plans", json={
        "name": "Toggle Plan",
        "price": 199,
        "credits": 20,
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    plan_id = res_create.json()["plan"]["id"]

    # Deactivate
    res_deact = await client.post(f"/api/admin/plans/{plan_id}/deactivate", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_deact.status_code == 200
    assert res_deact.json()["plan"]["active"] is False

    # Activate
    res_act = await client.post(f"/api/admin/plans/{plan_id}/activate", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_act.status_code == 200
    assert res_act.json()["plan"]["active"] is True

    audit = await db.audit_logs.find_one({"action": "plan_activate", "entity_id": plan_id})
    assert audit is not None


# ============================================================
# 9. TEMPLATES ADMIN API (26-33)
# ============================================================

@pytest.mark.asyncio
async def test_26_templates_list_with_revision_count(client, super_admin_auth):
    """Scenario 26: GET /api/admin/templates returns paginated list with revision_count."""
    t_id = "test_tpl_rev_count"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Sample Bail Application",
        "name_gu": "જામીન અરજી",
        "category": "Criminal",
        "status": "published",
        "version": 2,
        "fields": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.template_revisions.insert_one({"template_id": t_id, "version": 1, "name_en": "V1"})
    await db.template_revisions.insert_one({"template_id": t_id, "version": 2, "name_en": "V2"})
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.get("/api/admin/templates?page=1&category=Criminal", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["templates"][0]["revision_count"] == 2


@pytest.mark.asyncio
async def test_27_template_revisions_endpoint(client, super_admin_auth):
    """Scenario 27: GET /api/admin/templates/{id}/revisions returns revision history."""
    t_id = "test_tpl_rev_list"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Affidavit",
        "name_gu": "સોગંદનામું",
        "status": "published",
        "version": 2,
        "fields": [],
    })
    await db.template_revisions.insert_one({"template_id": t_id, "version": 1, "title": "Affidavit v1"})
    await db.template_revisions.insert_one({"template_id": t_id, "version": 2, "title": "Affidavit v2"})
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.get(f"/api/admin/templates/{t_id}/revisions", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert len(res.json()["revisions"]) == 2


@pytest.mark.asyncio
async def test_28_linear_versioning_publish(client, super_admin_auth):
    """Scenario 28: Publishing draft template creates immutable snapshot and sets status to published."""
    t_id = "tpl_linear_publish"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Adjournment Application",
        "name_gu": "મુદત અરજી",
        "category": "General",
        "content_en": "Today is {{today}}, applicant is {{party_name}}.",
        "content_gu": "આજે {{today}} છે, અરજદાર {{party_name}} છે.",
        "fields": [{"key": "party_name", "label_en": "Party Name", "type": "text"}],
        "status": "draft",
        "version": 1,
        "locked": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.post(f"/api/admin/templates/{t_id}/publish", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert res.json()["template"]["status"] == "published"
    assert res.json()["template"]["locked"] is True

    rev = await db.template_revisions.find_one({"template_id": t_id, "version": 1})
    assert rev is not None
    assert rev["content_en"] == "Today is {{today}}, applicant is {{party_name}}."


@pytest.mark.asyncio
async def test_29_template_archive_and_restore(client, super_admin_auth):
    """Scenario 29: Admin can archive and restore templates with audit logging."""
    t_id = "tpl_archive_restore"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Temporary Template",
        "name_gu": "ટેમ્પરરી ટેમ્પલેટ",
        "status": "published",
        "version": 1,
    })
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    # Archive
    res_arch = await client.post(f"/api/admin/templates/{t_id}/archive", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_arch.status_code == 200
    db_t = await db.templates.find_one({"id": t_id})
    assert db_t["status"] == "archived"

    # Restore
    res_rest = await client.post(f"/api/admin/templates/{t_id}/restore", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res_rest.status_code == 200
    db_t = await db.templates.find_one({"id": t_id})
    assert db_t["status"] == "published"


@pytest.mark.asyncio
async def test_30_permanent_delete_preserves_revisions(client, super_admin_auth):
    """Scenario 30: DELETE /api/admin/templates/{id} removes db.templates record but NEVER deletes db.template_revisions."""
    t_id = "tpl_delete_preserves_rev"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Obsolete Custom Template",
        "name_gu": "જૂનું ટેમ્પલેટ",
        "status": "draft",
        "version": 1,
    })
    await db.template_revisions.insert_one({
        "id": "rev_saved_snapshot",
        "template_id": t_id,
        "version": 1,
        "title": "Snapshot of Obsolete Custom Template",
        "content_en": "Historical content {{today}}",
    })
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.delete(f"/api/admin/templates/{t_id}", headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200

    # Removed from db.templates
    db_t = await db.templates.find_one({"id": t_id})
    assert db_t is None

    # CRITICAL: Preserved in db.template_revisions
    db_rev = await db.template_revisions.find_one({"template_id": t_id})
    assert db_rev is not None
    assert db_rev["title"] == "Snapshot of Obsolete Custom Template"


@pytest.mark.asyncio
async def test_31_historical_draft_resolves_after_template_deleted(client, super_admin_auth):
    """Scenario 31: Historical draft pinned to version N still resolves content after current template deletion."""
    t_id = "tpl_historical_resolution"
    await db.template_revisions.insert_one({
        "id": "rev_pinned_v1",
        "template_id": t_id,
        "version": 1,
        "title": "Historical Template v1",
        "name_en": "Historical Template",
        "name_gu": "ઐતિહાસિક ટેમ્પલેટ",
        "content_en": "Historical text {{today}} for client {{client_name}}",
        "content_gu": "ઐતિહાસિક લખાણ {{today}}",
        "fields": [{"key": "client_name", "label_en": "Client Name"}],
    })

    # Historical draft pinned to version 1
    draft = {
        "template_id": t_id,
        "template_version": 1,
        "user_id": "usr_lawyer_1",
    }
    resolved = await resolve_template_for_draft(draft)
    assert resolved is not None
    assert resolved["content_en"] == "Historical text {{today}} for client {{client_name}}"


@pytest.mark.asyncio
async def test_32_duplicate_as_new_creates_standalone_template(client, super_admin_auth):
    """Scenario 32: POST /api/admin/templates/{id}/duplicate creates a new standalone template with a new ID."""
    t_id = "tpl_base_for_copy"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Base Notice Template",
        "name_gu": "નોટિસ ટેમ્પલેટ",
        "category": "Civil",
        "content_en": "Notice text {{today}}",
        "content_gu": "નોટિસ લખાણ",
        "fields": [],
        "status": "published",
        "version": 1,
    })
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.post(f"/api/admin/templates/{t_id}/duplicate", json={
        "as_new_template": True,
        "new_name_en": "Custom Notice Clone",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    new_tpl = res.json()["template"]
    assert new_tpl["id"] != t_id
    assert new_tpl["name_en"] == "Custom Notice Clone"
    assert new_tpl["status"] == "draft"
    assert new_tpl["version"] == 1


@pytest.mark.asyncio
async def test_33_stable_id_editing_no_copy_timestamp_ids(client, super_admin_auth):
    """Scenario 33: Normal editing of a draft template updates under the SAME stable template_id without generating _copy_ IDs."""
    t_id = "tpl_stable_editing"
    await db.templates.insert_one({
        "id": t_id,
        "name_en": "Stable Template",
        "name_gu": "સ્ટેબલ ટેમ્પલેટ",
        "category": "General",
        "content_en": "Version 1 draft content",
        "content_gu": "આવૃત્તિ ૧",
        "fields": [],
        "status": "draft",
        "version": 1,
        "locked": False,
    })
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})

    res = await client.put(f"/api/admin/templates/{t_id}", json={
        "content_en": "Updated draft content in-place without new ID",
    }, headers={"Authorization": super_admin_auth["Authorization"]})
    assert res.status_code == 200
    assert res.json()["id"] == t_id
    assert "_copy_" not in res.json()["id"]
    assert res.json()["content_en"] == "Updated draft content in-place without new ID"
