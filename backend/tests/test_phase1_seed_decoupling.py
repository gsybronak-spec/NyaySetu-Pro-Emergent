"""Tests for Phase 1: Backend Seed Decoupling & Template Revision / Historical Data Safety.

Covers all 17 requirements:
1. Seed runs when seed_complete does not exist.
2. Seed does not run again when seed_complete=True.
3. Runtime endpoints do not merge Python seed arrays.
4. Existing DB templates are not duplicated.
5. Deleted templates do not reappear from Python seed data.
6. Archived templates do not appear as published.
7. Initial template revision is created.
8. Publishing creates a new revision snapshot.
9. Version numbers remain linear (1 -> 2 -> 3...).
10. Drafts store template_version.
11. Historical drafts resolve from template_revisions.
12. Historical drafts still resolve after current template deletion.
13. Migration is idempotent.
14. Existing production template IDs remain unchanged.
15. Normal editing does not generate _copy_ timestamp IDs.
16. Explicit "Duplicate As New Template" still generates a new ID.
17. Existing drafts without template_version remain backward compatible.
"""

import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_seed_decoupling")

import pytest
import pytest_asyncio
import bcrypt
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_seed_decoupling"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    make_token, make_admin_token,
    seed_templates, migrate_templates_to_revisions, resolve_template_for_draft,
    TEMPLATES, TEMPLATES_V2,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans", "districts", "talukas", "courts",
        "case_types", "police_stations", "laws"
    ]:
        await db[coll_name].drop()
    yield
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans", "districts", "talukas", "courts",
        "case_types", "police_stations", "laws"
    ]:
        await db[coll_name].drop()


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_auth():
    admin_id = str(uuid.uuid4())
    email = "admin_phase1@nyaysetu.in"
    hashed = bcrypt.hashpw(b"Secret123!", bcrypt.gensalt()).decode("utf-8")
    await db.admin_users.insert_one({
        "id": admin_id,
        "email": email,
        "password_hash": hashed,
        "name": "Super Admin Phase 1",
        "role": "super_admin",
        "active": True,
        "last_login": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_admin_token(admin_id, email, "super_admin")
    return {"Authorization": f"Bearer {token}", "admin_id": admin_id}


@pytest_asyncio.fixture
async def lawyer_auth():
    user_id = str(uuid.uuid4())
    mobile = "9876543210"
    email = "lawyer@example.com"
    await db.users.insert_one({
        "id": user_id,
        "mobile": mobile,
        "email": email,
        "name": "Advocate Test",
        "user_type": "Advocate",
        "active": True,
        "profile_completed": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.wallets.insert_one({
        "user_id": user_id,
        "balance": 10,
        "free_credits_granted": 5,
        "total_used": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    token = make_token(user_id)
    return {"Authorization": f"Bearer {token}", "user_id": user_id}


# ============================================================
# 1 & 2. Seed Execution & seed_complete Flag
# ============================================================

@pytest.mark.asyncio
async def test_seed_runs_when_seed_complete_missing():
    """Seed must initialize templates into db.templates and set seed_complete=True."""
    setting = await db.system_settings.find_one({"key": "seed_complete"})
    assert setting is None

    await seed_templates()

    # Verify templates inserted
    tpl_count = await db.templates.count_documents({})
    assert tpl_count > 0

    # Verify seed_complete set
    setting = await db.system_settings.find_one({"key": "seed_complete"})
    assert setting is not None
    assert setting.get("value") is True
    assert "completed_at" in setting


@pytest.mark.asyncio
async def test_seed_does_not_run_when_seed_complete_true():
    """When seed_complete=True, seed_templates should be a complete no-op."""
    await seed_templates()
    initial_count = await db.templates.count_documents({})
    assert initial_count > 0

    # Manually delete one template to test that seed does NOT resurrect it
    sample_id = "civil_suit" if await db.templates.find_one({"id": "civil_suit"}) else (await db.templates.find_one({}))["id"]
    await db.templates.delete_one({"id": sample_id})
    assert await db.templates.find_one({"id": sample_id}) is None

    # Call seed_templates again without force
    await seed_templates()

    # The deleted template must NOT be resurrected
    assert await db.templates.find_one({"id": sample_id}) is None
    assert (await db.templates.count_documents({})) == initial_count - 1


# ============================================================
# 3, 5, 6. Runtime Decoupling & MongoDB as Source of Truth
# ============================================================

@pytest.mark.asyncio
async def test_runtime_endpoints_do_not_merge_seed_arrays(client, lawyer_auth, admin_auth):
    """Runtime endpoints must only return templates present in MongoDB."""
    await seed_templates()

    # Choose a template and delete it from DB
    target_id = "adjournment"
    assert await db.templates.find_one({"id": target_id}) is not None

    await db.templates.delete_one({"id": target_id})

    # Lawyer API GET /api/templates
    resp = await client.get("/api/templates", headers=lawyer_auth)
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert target_id not in ids, "Deleted template must NOT reappear in lawyer templates list"

    # Lawyer API GET /api/templates/{id}
    resp = await client.get(f"/api/templates/{target_id}", headers=lawyer_auth)
    assert resp.status_code == 404, "Deleted template must return 404 from lawyer API"

    # Admin API GET /api/admin/templates
    resp = await client.get("/api/admin/templates", headers=admin_auth)
    assert resp.status_code == 200
    admin_ids = [t["id"] for t in resp.json()]
    assert target_id not in admin_ids, "Deleted template must NOT reappear in admin templates list"

    # Admin API GET /api/admin/templates/{id}
    resp = await client.get(f"/api/admin/templates/{target_id}", headers=admin_auth)
    assert resp.status_code == 404, "Deleted template must return 404 from admin API"


@pytest.mark.asyncio
async def test_archived_templates_hidden_from_lawyer_api(client, lawyer_auth, admin_auth):
    """Archived templates must not appear in published results or lawyer API."""
    await seed_templates()
    target_id = "certified_copy"

    # Archive the template via Admin API
    resp = await client.post(f"/api/admin/templates/{target_id}/archive", headers=admin_auth)
    assert resp.status_code == 200

    # Lawyer API must NOT return it in published list
    resp = await client.get("/api/templates", headers=lawyer_auth)
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert target_id not in ids

    # Direct fetch by lawyer returns 404
    resp = await client.get(f"/api/templates/{target_id}", headers=lawyer_auth)
    assert resp.status_code == 404


# ============================================================
# 4, 13, 14. Idempotent Migration & Stable IDs
# ============================================================

@pytest.mark.asyncio
async def test_idempotent_template_revisions_migration():
    """Running migrate_templates_to_revisions multiple times produces identical state."""
    await seed_templates()

    # Initial migration ran in seed_templates
    rev_count_1 = await db.template_revisions.count_documents({})
    assert rev_count_1 > 0

    # Run migration again
    res2 = await migrate_templates_to_revisions(db)
    assert res2["migrated"] == 0
    assert res2["skipped"] == rev_count_1
    assert (await db.template_revisions.count_documents({})) == rev_count_1

    # Run migration 5 more times
    for _ in range(5):
        res = await migrate_templates_to_revisions(db)
        assert res["migrated"] == 0

    assert (await db.template_revisions.count_documents({})) == rev_count_1


@pytest.mark.asyncio
async def test_production_template_ids_unchanged():
    """All seed template IDs must be preserved identically in DB and revisions."""
    await seed_templates()
    all_seed_ids = {t["id"] for t in [*TEMPLATES, *TEMPLATES_V2]}

    db_ids = {t["id"] for t in await db.templates.find({}, {"_id": 0, "id": 1}).to_list(1000)}
    assert all_seed_ids.issubset(db_ids)

    rev_ids = {r["template_id"] for r in await db.template_revisions.find({}, {"_id": 0, "template_id": 1}).to_list(1000)}
    assert all_seed_ids.issubset(rev_ids)


# ============================================================
# 7, 8, 9, 15, 16. Publish Workflow, Linear Versioning & Clone
# ============================================================

@pytest.mark.asyncio
async def test_linear_versioning_and_publish_snapshot(client, admin_auth):
    """Publishing a branched template increments version linearly without changing ID."""
    await seed_templates()
    tid = "vakalatnama"

    tpl_v1 = await db.templates.find_one({"id": tid}, {"_id": 0})
    assert tpl_v1["version"] == 1
    assert tpl_v1["status"] == "published"

    # Branch into version 2 draft (normal edit: as_new_template=False)
    resp = await client.post(f"/api/admin/templates/{tid}/clone", json={"as_new_template": False}, headers=admin_auth)
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_version"] == 2
    assert data["template"]["id"] == tid, "Stable template ID must be preserved"
    assert data["template"]["status"] == "draft"

    # Update draft fields
    update_payload = {
        "name_en": "Updated Civil Vakalatnama",
        "name_gu": "સુધારેલ વકાલતનામા",
        "content_en": "Vakalatnama for {party_name} in {court}",
        "content_gu": "{court} માં {party_name} માટે વકાલતનામા",
        "fields": [
            {"key": "party_name", "label_en": "Party Name", "label_gu": "પક્ષકારનું નામ", "type": "text", "required": True},
            {"key": "court", "label_en": "Court", "label_gu": "કોર્ટ", "type": "text", "required": True},
        ]
    }
    resp = await client.put(f"/api/admin/templates/{tid}", json=update_payload, headers=admin_auth)
    assert resp.status_code == 200

    # Publish version 2
    resp = await client.post(f"/api/admin/templates/{tid}/publish", headers=admin_auth)
    assert resp.status_code == 200
    published = resp.json()["template"]
    assert published["id"] == tid
    assert published["version"] == 2
    assert published["status"] == "published"
    assert published["locked"] is True

    # Check template_revisions contains both v1 and v2
    v1_rev = await db.template_revisions.find_one({"template_id": tid, "version": 1}, {"_id": 0})
    v2_rev = await db.template_revisions.find_one({"template_id": tid, "version": 2}, {"_id": 0})
    assert v1_rev is not None
    assert v2_rev is not None
    assert v2_rev["name_en"] == "Updated Civil Vakalatnama"
    assert "vakilatnama_civil_copy_" not in published["id"]


@pytest.mark.asyncio
async def test_explicit_duplicate_as_new_template(client, admin_auth):
    """Explicit 'Duplicate As New' (as_new_template=True) creates a new template ID."""
    await seed_templates()
    tid = "vakalatnama"

    resp = await client.post(
        f"/api/admin/templates/{tid}/clone",
        json={"as_new_template": True, "new_name_en": "Vakalatnama Custom"},
        headers=admin_auth,
    )
    assert resp.status_code == 200
    data = resp.json()
    new_template = data["template"]
    assert new_template["id"] != tid
    assert tid in new_template["id"]
    assert new_template["version"] == 1
    assert new_template["status"] == "draft"


# ============================================================
# 10, 11, 12, 17. Draft Historical Versioning & Resolution
# ============================================================

@pytest.mark.asyncio
async def test_draft_stores_template_version(client, lawyer_auth):
    """Creating a draft saves the current template_version in db.drafts."""
    await seed_templates()
    tid = "affidavit"

    # Save draft
    save_req = {
        "template_id": tid,
        "language": "gu",
        "values": {"deponent_name": "Ramesh Patel", "facts": "Test affidavit facts"}
    }
    resp = await client.post("/api/drafts", json=save_req, headers=lawyer_auth)
    assert resp.status_code == 200

    draft = await db.drafts.find_one({"user_id": lawyer_auth["user_id"], "template_id": tid}, {"_id": 0})
    assert draft is not None
    assert draft.get("template_version") == 1


@pytest.mark.asyncio
async def test_historical_draft_resolves_from_revisions_after_template_edit_and_deletion(client, admin_auth, lawyer_auth):
    """A draft saved under version 1 continues to resolve v1 even after v2 is published and template is deleted."""
    await seed_templates()
    tid = "compromise"

    # 1. User saves draft on Version 1
    await client.post("/api/drafts", json={
        "template_id": tid,
        "language": "en",
        "values": {"terms": "Settlement terms v1"}
    }, headers=lawyer_auth)

    # Verify draft saved with version 1
    draft = await db.drafts.find_one({"template_id": tid}, {"_id": 0})
    assert draft["template_version"] == 1

    # 2. Admin branches and publishes Version 2 with different content
    await client.post(f"/api/admin/templates/{tid}/clone", json={"as_new_template": False}, headers=admin_auth)
    await client.put(f"/api/admin/templates/{tid}", json={
        "name_en": "Compromise Deed V2",
        "name_gu": "સમાધાન અરજી V2",
        "content_en": "Version 2 terms: {terms_v2}",
        "content_gu": "આવૃત્તિ ૨ શરતો: {terms_v2}",
        "fields": [{"key": "terms_v2", "label_en": "Terms V2", "label_gu": "શરતો V2", "type": "text", "required": True}]
    }, headers=admin_auth)
    await client.post(f"/api/admin/templates/{tid}/publish", headers=admin_auth)

    # 3. Resolve template for v1 draft
    v1_resolved = await resolve_template_for_draft(tid, draft["template_version"])
    assert v1_resolved is not None
    assert v1_resolved["version"] == 1
    assert "Version 2" not in v1_resolved.get("name_en", "")

    # 4. Resolve template for v2 draft
    v2_resolved = await resolve_template_for_draft(tid, 2)
    assert v2_resolved is not None
    assert v2_resolved["version"] == 2
    assert "Compromise Deed V2" in v2_resolved.get("name_en", "")

    # 5. Delete current template from db.templates (simulating admin purge)
    await db.templates.delete_one({"id": tid})
    assert await db.templates.find_one({"id": tid}) is None

    # 6. Historical draft MUST still resolve successfully from db.template_revisions
    v1_still_resolves = await resolve_template_for_draft(tid, draft["template_version"])
    assert v1_still_resolves is not None
    assert v1_still_resolves["version"] == 1
    assert v1_still_resolves["id"] == tid


@pytest.mark.asyncio
async def test_legacy_draft_without_template_version_backward_compatible():
    """A legacy draft with template_version=None resolves from db.templates gracefully."""
    await seed_templates()
    tid = "inspection"

    # Call resolve_template_for_draft with None
    resolved = await resolve_template_for_draft(tid, None)
    assert resolved is not None
    assert resolved["id"] == tid
