"""Tests for the safe removal of shadow draft/archived records of seed templates.

A seed template becomes "shadowed" when an admin branches it for editing: the
version-branch clone materialises a draft record under the SAME id, which hides
the seed from the lawyer-facing template list (23 instead of 24 templates,
single GET -> 404). This module covers the super_admin-only removal endpoint:

- Regular admin cannot remove a shadow draft (403)
- Super admin removes a valid draft shadowing a seed template
- Published templates are refused (409) — published versions never deleted
- Real (non-seed) templates are refused (409) — unrelated data never touched
- Missing record -> clean 404 (idempotent)
- Archived shadows require explicit confirm=true (400 otherwise)
- Removal is audit-logged (template_shadow_draft_delete)
- After removal the seed becomes visible again: lawyer count back to 24,
  GET /api/templates/document_return_application -> 200

Uses mongomock_motor (same pattern as the existing suite).
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_shadow_draft")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_shadow_draft"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_admin_token, now
from seed_data import TEMPLATES
from httpx import AsyncClient, ASGITransport

API = "/api"
ADMIN = "/api/admin"

SEED_IDS = {t["id"] for t in TEMPLATES}
assert "document_return_application" in SEED_IDS

COLLECTIONS = ["admin_users", "users", "wallets", "cases", "drafts",
               "applications", "transactions", "referrals",
               "templates", "template_versions", "otps", "audit_logs",
               "plans", "settings"]


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
    yield
    for coll in COLLECTIONS:
        await db[coll].drop()


async def create_admin(role="super_admin"):
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": f"{role}@test.com",
        "password_hash": hashed,
        "name": "Test Admin",
        "role": role,
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    token = make_admin_token(admin_id, admin["email"], admin["role"])
    return admin, token


async def shadow_doc(template_id, status="draft"):
    return {
        "id": template_id,
        "slug": template_id,
        "name_en": "Shadow (stale) copy",
        "name_gu": "શેડો નકલ",
        "category": "Civil",
        "status": status,
        "version": 2,
        "locked": True,
        "created_at": now().isoformat(),
        "updated_at": now().isoformat(),
    }


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def lawyer_template_count(client):
    r = await client.get(f"{API}/templates")
    assert r.status_code == 200, r.text
    ids = {t["id"] for t in r.json()}
    return len(ids), "document_return_application" in ids


class TestShadowDraftRemoval:
    @pytest.mark.asyncio
    async def test_regular_admin_cannot_remove_shadow(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        _, token = await create_admin(role="admin")  # regular admin
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft?confirm=true",
                                headers=H(token))
        assert r.status_code == 403, r.text
        # record untouched
        assert await db.templates.find_one({"id": "document_return_application"}) is not None

    @pytest.mark.asyncio
    async def test_super_admin_removes_valid_draft_shadow(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft",
                                headers=H(token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["removed_status"] == "draft"
        assert await db.templates.find_one({"id": "document_return_application"}) is None

    @pytest.mark.asyncio
    async def test_published_template_refused(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application", "published")).copy())
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft?confirm=true",
                                headers=H(token))
        assert r.status_code == 409, r.text
        assert "ublished" in r.json()["detail"]
        assert await db.templates.find_one({"id": "document_return_application"}) is not None

    @pytest.mark.asyncio
    async def test_non_seed_template_refused(self, client, clean_db):
        # A real admin-created template (no seed counterpart) must never be deleted
        await db.templates.insert_one((await shadow_doc("custom_user_template")).copy())
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/custom_user_template/draft?confirm=true",
                                headers=H(token))
        assert r.status_code == 409, r.text
        assert await db.templates.find_one({"id": "custom_user_template"}) is not None

    @pytest.mark.asyncio
    async def test_missing_record_clean_404(self, client, clean_db):
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/does_not_exist/draft?confirm=true",
                                headers=H(token))
        assert r.status_code == 404, r.text

    @pytest.mark.asyncio
    async def test_archived_shadow_requires_confirmation(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application", "archived")).copy())
        _, token = await create_admin(role="super_admin")
        # without confirm -> 400, record kept
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft",
                                headers=H(token))
        assert r.status_code == 400, r.text
        assert await db.templates.find_one({"id": "document_return_application"}) is not None
        # with confirm -> removed
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft?confirm=true",
                                headers=H(token))
        assert r.status_code == 200, r.text
        assert await db.templates.find_one({"id": "document_return_application"}) is None

    @pytest.mark.asyncio
    async def test_audit_log_created(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft",
                                headers=H(token))
        assert r.status_code == 200, r.text
        entry = await db.audit_logs.find_one({"action": "template_shadow_draft_delete"})
        assert entry is not None
        assert entry["target"] == "document_return_application"
        assert entry["metadata"]["removed_status"] == "draft"


class TestShadowDraftRestoresSeed:
    @pytest.mark.asyncio
    async def test_shadow_hides_seed_then_removal_restores_it(self, client, clean_db):
        # Baseline: all 24 seed templates visible
        n0, present0 = await lawyer_template_count(client)
        assert n0 == len(SEED_IDS) == 24 and present0 is True

        # Reproduce the production blocker: a draft record shadows the seed
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        n1, present1 = await lawyer_template_count(client)
        assert n1 == 23 and present1 is False, f"shadow not effective: {n1}/{present1}"
        r = await client.get(f"{API}/templates/document_return_application")
        assert r.status_code == 404, r.text

        # Super admin removes ONLY the shadow
        _, token = await create_admin(role="super_admin")
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft",
                                headers=H(token))
        assert r.status_code == 200, r.text

        # Seed visible again; count back to 24; single GET 200; nothing else touched
        n2, present2 = await lawyer_template_count(client)
        assert n2 == 24 and present2 is True
        r = await client.get(f"{API}/templates/document_return_application")
        assert r.status_code == 200, r.text
        assert r.json()["name_gu"] == "દસ્તાવેજ પરત મેળવવાની અરજી"
        assert await db.templates.count_documents({}) == 0  # no other records left

    @pytest.mark.asyncio
    async def test_admin_list_flags_shadow_rows(self, client, clean_db):
        """The admin list must expose is_seed_template so the UI can show the action."""
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        _, token = await create_admin(role="super_admin")
        r = await client.get(f"{ADMIN}/templates", headers=H(token))
        assert r.status_code == 200, r.text
        row = next(t for t in r.json() if t["id"] == "document_return_application")
        assert row["is_seed_template"] is True
        assert row["status"] == "draft"
        seed_row = next(t for t in r.json() if t["id"] == "adjournment")
        assert seed_row["is_seed_template"] is True
        assert seed_row["status"] == "seed"

    @pytest.mark.asyncio
    async def test_unauth_and_lawyer_token_rejected(self, client, clean_db):
        await db.templates.insert_one((await shadow_doc("document_return_application")).copy())
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft?confirm=true")
        assert r.status_code == 401, r.text
        from server import make_token
        lawyer_tok = make_token(str(uuid.uuid4()))
        r = await client.delete(f"{ADMIN}/templates/document_return_application/draft?confirm=true",
                                headers=H(lawyer_tok))
        assert r.status_code == 401, r.text
        assert await db.templates.find_one({"id": "document_return_application"}) is not None
