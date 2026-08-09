"""Tests for NyaySetu Pro Admin Template Management — Phase 2A.

Covers:
- Seed migration creates 23 templates
- Seed migration is idempotent
- Existing template is not overwritten
- Lawyer template API reads published DB templates
- Seed fallback works when DB is empty
- Draft templates are hidden from lawyers
- Archived templates are hidden from lawyers
- Admin can list templates
- Admin can create template
- Admin can edit draft
- Published template cannot be mutated
- Clone creates new version
- Publish works
- Archive works
- Version history works
- Unknown placeholder blocks publish
- Valid auto-fill placeholders work
- Valid template fields work
- Lawyer JWT cannot access admin template APIs
- Admin JWT can access admin template APIs
- Full backward compatibility

Uses mongomock_motor (same pattern as existing test suite).
"""

import os
import sys
import uuid
import time
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_templates")

import pytest
import pytest_asyncio
import bcrypt
from datetime import datetime, timezone

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_templates"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, JWT_SECRET, TEMPLATES
from httpx import AsyncClient, ASGITransport


# ============================================================
# Fixtures
# ============================================================

@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def clean_db():
    """Drop all test collections before/after the test."""
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions"]:
        await db[coll_name].drop()


# ============================================================
# Helpers
# ============================================================

async def create_super_admin():
    """Create a super_admin and return (admin_doc, token)."""
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": "superadmin@test.com",
        "password_hash": hashed,
        "name": "Test Super Admin",
        "role": "super_admin",
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    token = make_admin_token(admin_id, admin["email"], admin["role"])
    return admin, token


async def create_regular_admin():
    """Create an admin (non-super) and return (admin_doc, token)."""
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": "admin@test.com",
        "password_hash": hashed,
        "name": "Test Admin",
        "role": "admin",
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    token = make_admin_token(admin_id, admin["email"], admin["role"])
    return admin, token


async def create_lawyer():
    """Create a lawyer user and return (user_doc, token)."""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": "9876500001",
        "name": "Test Lawyer",
        "provider": "mobile",
        "referral_code": "NS" + uuid.uuid4().hex[:6].upper(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    await db.wallets.insert_one({
        "user_id": user_id, "balance": 5,
        "free_credits_granted": 5, "total_used": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_token(user_id)
    return user, token


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


EXPECTED_IDS = [
    "adjournment", "certified_copy", "exemption_appearance", "cross_close",
    "evidence_produce", "document_produce", "time_extension", "case_transfer",
    "recall", "warrant_cancel", "bail_regular", "affidavit", "restoration",
    "condonation_delay", "interim_injunction", "vakalatnama", "return_documents",
    "inspection", "compromise", "withdrawal", "amendment", "surety", "early_hearing",
]


# ============================================================
# 1. SEED MIGRATION TESTS
# ============================================================

class TestSeedMigration:
    @pytest.mark.asyncio
    async def test_migrate_creates_23_templates(self, client, clean_db):
        """Seed migration must create exactly 23 templates."""
        _, token = await create_super_admin()
        r = await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["total_seed_templates"] == 23
        assert data["created"] == 23
        assert data["skipped"] == 0
        assert data["errors"] == 0
        # Verify all IDs
        for tid in EXPECTED_IDS:
            assert tid in data["created_ids"]

    @pytest.mark.asyncio
    async def test_migrate_is_idempotent(self, client, clean_db):
        """Running migration twice should skip already-migrated templates."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["created"] == 0
        assert data["skipped"] == 23

    @pytest.mark.asyncio
    async def test_migrate_does_not_overwrite_admin_edit(self, client, clean_db):
        """Edited template is NOT overwritten by re-migration."""
        _, token = await create_super_admin()
        # First migrate
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        # Manually modify a template in DB (simulate admin edit after clone)
        await db.templates.update_one(
            {"id": "adjournment"},
            {"$set": {"name_en": "Custom Adjournment", "status": "draft", "locked": False}},
        )
        # Run migration again
        r = await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        assert r.status_code == 200
        # adjournment should be skipped (already exists)
        assert "adjournment" in r.json()["skipped_ids"]
        # Verify edit is preserved
        t = await db.templates.find_one({"id": "adjournment"}, {"_id": 0})
        assert t["name_en"] == "Custom Adjournment"

    @pytest.mark.asyncio
    async def test_migrate_requires_super_admin(self, client, clean_db):
        """Regular admin cannot run seed migration."""
        _, token = await create_regular_admin()
        r = await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_migrate_creates_version_snapshots(self, client, clean_db):
        """Migration should also create version 1 snapshots."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        versions = await db.template_versions.find({"template_id": "adjournment"}).to_list(10)
        assert len(versions) == 1
        assert versions[0]["version"] == 1


# ============================================================
# 2. LAWYER TEMPLATE API TESTS (Backward Compatibility)
# ============================================================

class TestLawyerTemplateAPI:
    @pytest.mark.asyncio
    async def test_list_templates_seed_fallback(self, client, clean_db):
        """With no templates in DB, lawyer API should fall back to seed_data."""
        r = await client.get("/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 23
        ids = [t["id"] for t in data]
        for tid in EXPECTED_IDS:
            assert tid in ids

    @pytest.mark.asyncio
    async def test_list_templates_from_db(self, client, clean_db):
        """With migrated templates in DB, lawyer API should read from DB."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.get("/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 23

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, client, clean_db):
        """GET /templates/:id should return template with content."""
        r = await client.get("/api/templates/adjournment")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "adjournment"
        assert "content_en" in data
        assert "content_gu" in data
        assert "fields" in data

    @pytest.mark.asyncio
    async def test_template_response_shape_unchanged(self, client, clean_db):
        """public_template must return the exact same shape as before."""
        r = await client.get("/api/templates")
        assert r.status_code == 200
        t = r.json()[0]
        assert set(t.keys()) == {"id", "name_en", "name_gu", "category", "fields"}
        # Field shape check
        if t["fields"]:
            f = t["fields"][0]
            assert "key" in f
            assert "label_en" in f
            assert "label_gu" in f
            assert "type" in f
            assert "required" in f

    @pytest.mark.asyncio
    async def test_draft_templates_hidden_from_lawyers(self, client, clean_db):
        """Draft templates must NOT appear in lawyer template list."""
        _, admin_token = await create_super_admin()
        # Migrate, then create a draft
        await client.post("/api/admin/templates/migrate-seed", headers=auth(admin_token))
        await client.post("/api/admin/templates", headers=auth(admin_token), json={
            "name_en": "Test Draft", "name_gu": "ટેસ્ટ ડ્રાફ્ટ", "category": "General",
        })
        r = await client.get("/api/templates")
        ids = [t["id"] for t in r.json()]
        assert "test_draft" in [t["id"] for t in (await db.templates.find({"status": "draft"}).to_list(10))]
        assert "test_draft" not in ids

    @pytest.mark.asyncio
    async def test_archived_templates_hidden_from_lawyers(self, client, clean_db):
        """Archived templates must NOT appear in lawyer template list."""
        _, admin_token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(admin_token))
        await client.post("/api/admin/templates/adjournment/archive", headers=auth(admin_token))
        r = await client.get("/api/templates")
        ids = [t["id"] for t in r.json()]
        assert "adjournment" not in ids

    @pytest.mark.asyncio
    async def test_category_filter_still_works(self, client, clean_db):
        """Category filter on lawyer template API must still work."""
        r = await client.get("/api/templates?category=Criminal")
        assert r.status_code == 200
        for t in r.json():
            assert t["category"] == "Criminal"

    @pytest.mark.asyncio
    async def test_search_still_works(self, client, clean_db):
        """Search on lawyer template API must still work."""
        r = await client.get("/api/templates?q=mudat")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert any(t["id"] == "adjournment" for t in data)


# ============================================================
# 3. ADMIN TEMPLATE CRUD TESTS
# ============================================================

class TestAdminTemplateCRUD:
    @pytest.mark.asyncio
    async def test_admin_list_templates(self, client, clean_db):
        """Admin can list templates (all statuses)."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.get("/api/admin/templates", headers=auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 23

    @pytest.mark.asyncio
    async def test_admin_list_with_status_filter(self, client, clean_db):
        """Admin can filter by status."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.get("/api/admin/templates?status=published", headers=auth(token))
        assert r.status_code == 200
        for t in r.json():
            assert t["status"] == "published"

    @pytest.mark.asyncio
    async def test_admin_create_template(self, client, clean_db):
        """Admin can create a new template as draft."""
        _, token = await create_super_admin()
        r = await client.post("/api/admin/templates", headers=auth(token), json={
            "name_en": "Test Template",
            "name_gu": "ટેસ્ટ ટેમ્પ્લેટ",
            "category": "General",
            "fields": [{"key": "test_field", "label_en": "Test", "label_gu": "ટેસ્ટ", "type": "text", "required": True, "order": 0}],
            "content_en": "Test {{test_field}}",
            "content_gu": "ટેસ્ટ {{test_field}}",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "draft"
        assert data["version"] == 1
        assert data["source"] == "admin_created"
        assert data["locked"] is False

    @pytest.mark.asyncio
    async def test_admin_create_duplicate_id_fails(self, client, clean_db):
        """Cannot create template with duplicate ID."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "my_template", "name_en": "First", "name_gu": "પ્રથમ",
        })
        r = await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "my_template", "name_en": "Second", "name_gu": "બીજું",
        })
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_admin_edit_draft(self, client, clean_db):
        """Admin can edit a draft template."""
        _, token = await create_super_admin()
        r = await client.post("/api/admin/templates", headers=auth(token), json={
            "name_en": "Original", "name_gu": "મૂળ",
        })
        tid = r.json()["id"]
        r2 = await client.put(f"/api/admin/templates/{tid}", headers=auth(token), json={
            "name_en": "Updated Name",
        })
        assert r2.status_code == 200
        assert r2.json()["name_en"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_published_template_cannot_be_mutated(self, client, clean_db):
        """Published+locked templates cannot be directly edited."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.put("/api/admin/templates/adjournment", headers=auth(token), json={
            "name_en": "Hacked Name",
        })
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_get_template(self, client, clean_db):
        """Admin can get full template details."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.get("/api/admin/templates/adjournment", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "adjournment"
        assert "content_en" in data
        assert "content_gu" in data
        assert data["status"] == "published"


# ============================================================
# 4. TEMPLATE VERSIONING TESTS
# ============================================================

class TestTemplateVersioning:
    @pytest.mark.asyncio
    async def test_clone_creates_new_draft(self, client, clean_db):
        """Cloning a published template creates a new draft version."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.post("/api/admin/templates/adjournment/clone", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["new_version"] == 2
        t = data["template"]
        assert t["status"] == "draft"
        assert t["locked"] is False
        assert t["version"] == 2

    @pytest.mark.asyncio
    async def test_publish_locks_template(self, client, clean_db):
        """Publishing a draft locks it and makes it visible to lawyers."""
        _, token = await create_super_admin()
        # Create a template with valid placeholders
        await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "test_pub",
            "name_en": "Test Publish",
            "name_gu": "ટેસ્ટ પ્રકાશિત",
            "fields": [{"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True, "order": 0}],
            "content_en": "IN THE COURT OF {{court}}\nTest {{reason}}\n{{advocate_name}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\nટેસ્ટ {{reason}}\n{{advocate_name}}",
        })
        r = await client.post("/api/admin/templates/test_pub/publish", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        t = data["template"]
        assert t["status"] == "published"
        assert t["locked"] is True

    @pytest.mark.asyncio
    async def test_version_history_tracks_snapshots(self, client, clean_db):
        """Version history endpoint returns saved version snapshots."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.get("/api/admin/templates/adjournment/versions", headers=auth(token))
        assert r.status_code == 200
        versions = r.json()
        assert len(versions) >= 1
        assert versions[0]["version"] == 1

    @pytest.mark.asyncio
    async def test_archive_hides_template(self, client, clean_db):
        """Archiving a template hides it from lawyers."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.post("/api/admin/templates/adjournment/archive", headers=auth(token))
        assert r.status_code == 200
        t = await db.templates.find_one({"id": "adjournment"}, {"_id": 0})
        assert t["status"] == "archived"


# ============================================================
# 5. PLACEHOLDER VALIDATION TESTS
# ============================================================

class TestPlaceholderValidation:
    @pytest.mark.asyncio
    async def test_unknown_placeholder_blocks_publish(self, client, clean_db):
        """Templates with unknown placeholders cannot be published."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "bad_ph",
            "name_en": "Bad Placeholders",
            "name_gu": "ખરાબ",
            "fields": [],
            "content_en": "Test {{unknown_field}} and {{another_bad}}",
            "content_gu": "",
        })
        r = await client.post("/api/admin/templates/bad_ph/publish", headers=auth(token))
        assert r.status_code == 400
        assert "unknown placeholders" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_auto_fill_placeholders_are_valid(self, client, clean_db):
        """Auto-fill placeholders (court, district, etc.) should be accepted."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "auto_fill_test",
            "name_en": "Auto Fill Test",
            "name_gu": "ઓટો ફિલ",
            "fields": [],
            "content_en": "IN THE COURT OF {{court}}, {{district}}\n{{advocate_name}}\n{{today}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\n{{advocate_name}}",
        })
        r = await client.post("/api/admin/templates/auto_fill_test/publish", headers=auth(token))
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_template_fields_are_valid(self, client, clean_db):
        """Declared template fields should be valid placeholders."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates", headers=auth(token), json={
            "id": "field_test",
            "name_en": "Field Test",
            "name_gu": "ફિલ્ડ ટેસ્ટ",
            "fields": [{"key": "my_field", "label_en": "My Field", "label_gu": "મારું ફિલ્ડ", "type": "text", "required": True, "order": 0}],
            "content_en": "Value: {{my_field}}\n{{advocate_name}}",
            "content_gu": "મૂલ્ય: {{my_field}}\n{{advocate_name}}",
        })
        r = await client.post("/api/admin/templates/field_test/publish", headers=auth(token))
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_preview_returns_validation(self, client, clean_db):
        """Admin preview endpoint should return placeholder validation."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        r = await client.post("/api/admin/templates/adjournment/preview", headers=auth(token))
        assert r.status_code == 200
        data = r.json()
        assert "preview" in data
        assert "validation" in data
        assert "en" in data["preview"]
        assert "gu" in data["preview"]


# ============================================================
# 6. SECURITY ISOLATION TESTS
# ============================================================

class TestTemplateSecurityIsolation:
    @pytest.mark.asyncio
    async def test_lawyer_cannot_access_admin_templates(self, client, clean_db):
        """Lawyer JWT must NOT work on admin template endpoints."""
        _, lawyer_token = await create_lawyer()
        r = await client.get("/api/admin/templates", headers=auth(lawyer_token))
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_lawyer_cannot_create_template(self, client, clean_db):
        """Lawyer JWT must NOT create templates."""
        _, lawyer_token = await create_lawyer()
        r = await client.post("/api/admin/templates", headers=auth(lawyer_token), json={
            "name_en": "Hacked", "name_gu": "હેક",
        })
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_access_admin_templates(self, client, clean_db):
        """Admin JWT can access admin template endpoints."""
        _, token = await create_regular_admin()
        r = await client.get("/api/admin/templates", headers=auth(token))
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth_cannot_access_admin_templates(self, client, clean_db):
        """Unauthenticated requests must be rejected."""
        r = await client.get("/api/admin/templates")
        assert r.status_code == 401


# ============================================================
# 7. BACKWARD COMPATIBILITY (existing features still work)
# ============================================================

class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_preview_still_works_with_db_templates(self, client, clean_db):
        """Preview endpoint works after migration."""
        _, admin_token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(admin_token))
        _, lawyer_token = await create_lawyer()
        r = await client.post("/api/applications/preview", headers=auth(lawyer_token), json={
            "template_id": "adjournment",
            "language": "en",
            "values": {"reason": "Test reason", "next_date": "15-01-2027"},
        })
        assert r.status_code == 200
        data = r.json()
        assert "blocks" in data
        assert "content" in data
        assert "Test reason" in data["content"]

    @pytest.mark.asyncio
    async def test_preview_still_works_with_seed_fallback(self, client, clean_db):
        """Preview endpoint works with seed fallback (no DB templates)."""
        _, lawyer_token = await create_lawyer()
        r = await client.post("/api/applications/preview", headers=auth(lawyer_token), json={
            "template_id": "vakalatnama",
            "language": "gu",
            "values": {"client_name": "Test Client"},
        })
        assert r.status_code == 200
        assert "blocks" in r.json()

    @pytest.mark.asyncio
    async def test_template_ids_all_preserved(self, client, clean_db):
        """All 23 template IDs must be accessible after migration."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        for tid in EXPECTED_IDS:
            r = await client.get(f"/api/templates/{tid}")
            assert r.status_code == 200, f"Template {tid} not found"
            assert r.json()["id"] == tid
