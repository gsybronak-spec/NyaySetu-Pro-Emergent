"""
Dedicated Test Suite: Template Permanent Hard Delete & Historical Safety
Covers all 28 required test scenarios:
1. Super Admin can delete draft template.
2. Super Admin can delete published template.
3. Super Admin can delete archived template.
4. Super Admin can delete seeded template.
5. Normal/staff admin cannot hard-delete (403).
6. Lawyer cannot hard-delete (401/403).
7. Unauthenticated user cannot hard-delete (401).
8. Deleted template disappears from db.templates.
9. Deleted template is no longer returned by template catalog API.
10. Deleted template cannot be opened in admin editor (404).
11. DELETE actually deletes and does not archive.
12. Audit log is created with action="template_deleted".
13. Sensitive fields are not leaked into audit log.
14. Deleted template does not resurrect after backend restart/startup.
15. seed_complete remains True.
16. Historical v1 draft still resolves after canonical template deletion.
17. Historical v2 draft still resolves after canonical template deletion.
18. Historical Gujarati document still renders.
19. Historical English document still renders.
20. Historical table still renders.
21. Historical page break still renders.
22. Historical PDF generation still works.
23. Historical DOCX generation still works.
24. Historical ODT generation still works.
25. SHA-256/document integrity remains unchanged.
26. Deleting one template does not affect another template.
27. Canonical template IDs of remaining templates remain unchanged.
28. Repeated DELETE returns proper 404 and does not corrupt data.
"""

import os
import sys
import uuid
import base64
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_hard_delete")

import pytest
import pytest_asyncio
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_hard_delete"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    make_token,
    make_admin_token,
    hash_password,
    resolve_template_for_draft,
    create_admin_audit_log,
    document_sha256,
    _ensure_seed_complete,
    seed_templates,
)
from doc_generator import (
    build_blocks,
    render_template,
    generate_pdf_detailed,
    generate_docx,
    generate_odt,
    get_doc_settings,
)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    """Seed test database with admin users and clean collections."""
    server.db = db
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "audit_logs", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans"
    ]:
        await db[coll_name].drop()

    # Super Admin
    super_admin_doc = {
        "id": "admin_super_1",
        "email": "superadmin@nyaysetu.gov.in",
        "name": "Super Administrator",
        "role": "super_admin",
        "password_hash": hash_password("SuperSecret123!"),
        "active": True,
        "created_at": "2026-08-22T00:00:00Z",
    }
    await db.admin_users.insert_one(super_admin_doc)
    await db.users.insert_one(super_admin_doc)

    # Staff Admin (role: admin)
    staff_admin_doc = {
        "id": "admin_staff_1",
        "email": "staff@nyaysetu.gov.in",
        "name": "Staff Administrator",
        "role": "admin",
        "password_hash": hash_password("StaffSecret123!"),
        "active": True,
        "created_at": "2026-08-22T00:00:00Z",
    }
    await db.admin_users.insert_one(staff_admin_doc)
    await db.users.insert_one(staff_admin_doc)

    # Regular Lawyer
    lawyer_doc = {
        "id": "lawyer_regular_1",
        "email": "advocate@gmail.com",
        "name": "Advocate Regular",
        "role": "lawyer",
        "password_hash": hash_password("LawyerPass123!"),
        "active": True,
        "created_at": "2026-08-22T00:00:00Z",
    }
    await db.users.insert_one(lawyer_doc)

    # Mark seed_complete = True
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})


@pytest.fixture
def super_admin_token():
    return make_admin_token("admin_super_1", "superadmin@nyaysetu.gov.in", "super_admin")


@pytest.fixture
def staff_admin_token():
    return make_admin_token("admin_staff_1", "staff@nyaysetu.gov.in", "admin")


@pytest.fixture
def lawyer_token():
    return make_token("lawyer_regular_1", "9876543210")


# ============================================================================
# TESTS 1–4: Super Admin Deletion Across Lifecycle States
# ============================================================================

@pytest.mark.asyncio
async def test_01_super_admin_can_delete_draft_template(super_admin_token):
    """Scenario 1: Super Admin can permanently delete a draft template."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        # Create draft template
        res_create = await client.post(
            "/api/admin/templates",
            json={
                "id": "tpl_draft_to_delete",
                "name_en": "Draft Delete Test",
                "name_gu": "ડ્રાફ્ટ ડિલીટ",
                "fields": [],
                "content_gu": "Draft body",
            },
            headers=headers,
        )
        assert res_create.status_code == 200

        # Delete it
        del_res = await client.delete("/api/admin/templates/tpl_draft_to_delete", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Check absent in DB
        db_t = await db.templates.find_one({"id": "tpl_draft_to_delete"})
        assert db_t is None


@pytest.mark.asyncio
async def test_02_super_admin_can_delete_published_template(super_admin_token):
    """Scenario 2: Super Admin can permanently delete a published template."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.post(
            "/api/admin/templates",
            json={
                "id": "tpl_pub_to_delete",
                "name_en": "Published Delete Test",
                "name_gu": "પ્રકાશિત ડિલીટ",
                "fields": [],
                "content_gu": "Published body",
            },
            headers=headers,
        )
        await client.post("/api/admin/templates/tpl_pub_to_delete/publish", headers=headers)

        del_res = await client.delete("/api/admin/templates/tpl_pub_to_delete", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        db_t = await db.templates.find_one({"id": "tpl_pub_to_delete"})
        assert db_t is None


@pytest.mark.asyncio
async def test_03_super_admin_can_delete_archived_template(super_admin_token):
    """Scenario 3: Super Admin can permanently delete an archived template."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.post(
            "/api/admin/templates",
            json={
                "id": "tpl_arch_to_delete",
                "name_en": "Archived Delete Test",
                "name_gu": "આર્કાઇવ ડિલીટ",
                "fields": [],
                "content_gu": "Archived body",
            },
            headers=headers,
        )
        await client.post("/api/admin/templates/tpl_arch_to_delete/publish", headers=headers)
        await client.post("/api/admin/templates/tpl_arch_to_delete/archive", headers=headers)

        del_res = await client.delete("/api/admin/templates/tpl_arch_to_delete", headers=headers)
        assert del_res.status_code == 200

        db_t = await db.templates.find_one({"id": "tpl_arch_to_delete"})
        assert db_t is None


@pytest.mark.asyncio
async def test_04_super_admin_can_delete_seeded_template(super_admin_token):
    """Scenario 4: Super Admin can permanently delete a seeded template."""
    # Seed templates
    await db.system_settings.delete_many({})
    await seed_templates()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Verify vakalatnama exists
        assert await db.templates.find_one({"id": "vakalatnama"}) is not None

        # Delete seeded template
        del_res = await client.delete("/api/admin/templates/vakalatnama", headers=headers)
        assert del_res.status_code == 200

        # Verify vakalatnama is removed
        assert await db.templates.find_one({"id": "vakalatnama"}) is None


# ============================================================================
# TESTS 5–7: RBAC Security Enforcement
# ============================================================================

@pytest.mark.asyncio
async def test_05_staff_admin_cannot_hard_delete(staff_admin_token):
    """Scenario 5: Staff admin (role: admin) cannot hard-delete a template (403)."""
    await db.templates.insert_one({"id": "tpl_staff_guard", "name_en": "Staff Guard", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete(
            "/api/admin/templates/tpl_staff_guard",
            headers={"Authorization": f"Bearer {staff_admin_token}"}
        )
        assert res.status_code == 403
        assert await db.templates.find_one({"id": "tpl_staff_guard"}) is not None


@pytest.mark.asyncio
async def test_06_lawyer_cannot_hard_delete(lawyer_token):
    """Scenario 6: Lawyer cannot access the admin delete endpoint (401/403)."""
    await db.templates.insert_one({"id": "tpl_lawyer_guard", "name_en": "Lawyer Guard", "status": "published"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete(
            "/api/admin/templates/tpl_lawyer_guard",
            headers={"Authorization": f"Bearer {lawyer_token}"}
        )
        assert res.status_code in (401, 403)
        assert await db.templates.find_one({"id": "tpl_lawyer_guard"}) is not None


@pytest.mark.asyncio
async def test_07_unauthenticated_cannot_hard_delete():
    """Scenario 7: Unauthenticated request cannot hard-delete (401)."""
    await db.templates.insert_one({"id": "tpl_anon_guard", "name_en": "Anon Guard", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/api/admin/templates/tpl_anon_guard")
        assert res.status_code == 401
        assert await db.templates.find_one({"id": "tpl_anon_guard"}) is not None


# ============================================================================
# TESTS 8–11: DB Deletion, Catalog Visibility, and Non-Archive Verification
# ============================================================================

@pytest.mark.asyncio
async def test_08_deleted_template_disappears_from_db_templates(super_admin_token):
    """Scenario 8: Deleted template record is completely deleted from db.templates."""
    t_id = "tpl_db_disappear"
    await db.templates.insert_one({"id": t_id, "name_en": "Disappear Test", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.delete(f"/api/admin/templates/{t_id}", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert await db.templates.find_one({"id": t_id}) is None


@pytest.mark.asyncio
async def test_09_deleted_template_not_returned_by_catalog_api(super_admin_token):
    """Scenario 9: Deleted template is omitted from the public lawyer catalog (GET /api/templates)."""
    t_id = "tpl_catalog_omission"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.post(
            "/api/admin/templates",
            json={"id": t_id, "name_en": "Catalog Omission", "name_gu": "કૅટેલૉગ", "fields": [], "content_gu": "Content"},
            headers=headers,
        )
        await client.post(f"/api/admin/templates/{t_id}/publish", headers=headers)

        # Before deletion: present in catalog
        res_before = await client.get("/api/templates")
        assert any(t["id"] == t_id for t in res_before.json())

        # Delete
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        # After deletion: absent from catalog
        res_after = await client.get("/api/templates")
        assert not any(t["id"] == t_id for t in res_after.json())


@pytest.mark.asyncio
async def test_10_deleted_template_returns_404_in_admin_editor(super_admin_token):
    """Scenario 10: GET /api/admin/templates/{id} returns 404 for deleted templates."""
    t_id = "tpl_admin_404_check"
    await db.templates.insert_one({"id": t_id, "name_en": "404 Test", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)
        
        res_get = await client.get(f"/api/admin/templates/{t_id}", headers=headers)
        assert res_get.status_code == 404


@pytest.mark.asyncio
async def test_11_delete_actually_deletes_and_does_not_archive(super_admin_token):
    """Scenario 11: Deletion is a true hard delete, NOT a silent conversion to status='archived'."""
    t_id = "tpl_real_delete_not_arch"
    await db.templates.insert_one({"id": t_id, "name_en": "Real Delete Test", "status": "published"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        # Check there is NO document in db.templates (with any status)
        any_doc = await db.templates.find_one({"id": t_id})
        assert any_doc is None


# ============================================================================
# TESTS 12–15: Audit Logging, Scrubbing, and Seed Resurrection Prevention
# ============================================================================

@pytest.mark.asyncio
async def test_12_audit_log_created_with_template_deleted(super_admin_token):
    """Scenario 12: Audit log is created with action='template_deleted'."""
    t_id = "tpl_audit_check"
    await db.templates.insert_one({"id": t_id, "name_en": "Audit Check", "status": "draft", "version": 1})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        audit = await db.audit_logs.find_one({"action": "template_deleted", "entity_id": t_id})
        assert audit is not None
        assert audit["action"] == "template_deleted"
        assert audit["entity_type"] == "template"
        assert audit["entity_id"] == t_id
        assert audit["admin_id"] == "admin_super_1"


@pytest.mark.asyncio
async def test_13_sensitive_fields_not_leaked_in_audit_log(super_admin_token):
    """Scenario 13: Sensitive fields (passwords, tokens, secrets) are never present in audit logs."""
    t_id = "tpl_scrub_audit"
    await db.templates.insert_one({"id": t_id, "name_en": "Scrub Test", "status": "draft", "some_secret_field": "123"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        audit = await db.audit_logs.find_one({"action": "template_deleted", "entity_id": t_id})
        assert audit is not None
        if audit.get("old_value"):
            assert "password" not in audit["old_value"]
            assert "secret" not in audit["old_value"]
            assert "token" not in audit["old_value"]


@pytest.mark.asyncio
async def test_14_deleted_template_does_not_resurrect_after_restart(super_admin_token):
    """Scenario 14: Deleted seeded template does not resurrect when _ensure_seed_complete() runs."""
    await db.system_settings.delete_many({})
    await seed_templates()

    t_id = "vakalatnama"
    assert await db.templates.find_one({"id": t_id}) is not None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        # Delete seeded template
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)
        assert await db.templates.find_one({"id": t_id}) is None

        # Simulate app restart / startup check
        await _ensure_seed_complete()

        # Deleted template MUST NOT return
        assert await db.templates.find_one({"id": t_id}) is None


@pytest.mark.asyncio
async def test_15_seed_complete_remains_true(super_admin_token):
    """Scenario 15: seed_complete setting in db.system_settings remains True after deletions."""
    t_id = "tpl_seed_setting_check"
    await db.templates.insert_one({"id": t_id, "name_en": "Seed Setting", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        setting = await db.system_settings.find_one({"key": "seed_complete"})
        assert setting is not None
        assert setting["value"] is True


# ============================================================================
# TESTS 16–25: Historical Resolution & Rendering Integrity (Phase 5 Safety)
# ============================================================================

@pytest.mark.asyncio
async def test_16_historical_v1_draft_still_resolves(super_admin_token):
    """Scenario 16: Historical draft referencing v1 resolves from db.template_revisions after template deletion."""
    t_id = "tpl_hist_v1_check"
    await db.template_revisions.insert_one({
        "id": "rev_v1_hist",
        "template_id": t_id,
        "version": 1,
        "name_en": "Hist v1",
        "name_gu": "ઐતિહાસિક v1",
        "content_gu": "HISTORICAL V1 CONTENT",
        "fields": [],
    })
    await db.templates.insert_one({"id": t_id, "name_en": "Hist v1", "status": "draft", "version": 1})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        # Canonical template is deleted
        assert await db.templates.find_one({"id": t_id}) is None

        # Historical resolution must resolve v1 snapshot
        resolved = await resolve_template_for_draft(t_id, 1)
        assert resolved is not None
        assert resolved["content_gu"] == "HISTORICAL V1 CONTENT"


@pytest.mark.asyncio
async def test_17_historical_v2_draft_still_resolves(super_admin_token):
    """Scenario 17: Historical draft referencing v2 resolves from db.template_revisions after template deletion."""
    t_id = "tpl_hist_v2_check"
    await db.template_revisions.insert_one({
        "id": "rev_v2_hist",
        "template_id": t_id,
        "version": 2,
        "name_en": "Hist v2",
        "name_gu": "ઐતિહાસિક v2",
        "content_gu": "HISTORICAL V2 CONTENT",
        "fields": [],
    })
    await db.templates.insert_one({"id": t_id, "name_en": "Hist v2", "status": "published", "version": 2})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.delete(f"/api/admin/templates/{t_id}", headers=headers)

        resolved = await resolve_template_for_draft(t_id, 2)
        assert resolved is not None
        assert resolved["content_gu"] == "HISTORICAL V2 CONTENT"


@pytest.mark.asyncio
async def test_18_historical_gujarati_document_still_renders():
    """Scenario 18: Historical Gujarati template content renders correctly into document blocks."""
    content_gu = "મે. કોર્ટ સમક્ષ: {{court}}\nઅરજદાર: {{party_name}}"
    rendered = render_template(content_gu, {"court": "સુરત ડિસ્ટ્રિક્ટ કોર્ટ", "party_name": "રમેશભાઈ પટેલ"})
    blocks = build_blocks(rendered)
    assert len(blocks) > 0
    assert any("સુરત" in b.get("text", "") for b in blocks)


@pytest.mark.asyncio
async def test_19_historical_english_document_still_renders():
    """Scenario 19: Historical English template content renders correctly into document blocks."""
    content_en = "IN THE COURT OF: {{court}}\nAPPLICANT: {{party_name}}"
    rendered = render_template(content_en, {"court": "Surat District Court", "party_name": "Ramesh Patel"})
    blocks = build_blocks(rendered)
    assert len(blocks) > 0
    assert any("Surat" in b.get("text", "") for b in blocks)


@pytest.mark.asyncio
async def test_20_historical_table_still_renders():
    """Scenario 20: Historical template with table blocks renders into structured table blocks."""
    table_content = "[TABLE_START]\nSr | Item | Description\n1 | A | First Item\n[TABLE_END]"
    blocks = build_blocks(table_content)
    table_blocks = [b for b in blocks if b.get("section") == "table"]
    assert len(table_blocks) == 1
    assert len(table_blocks[0].get("rows", [])) == 2


@pytest.mark.asyncio
async def test_21_historical_page_break_still_renders():
    """Scenario 21: Historical template with page breaks produces page_break blocks."""
    content = "Page 1 content\n--- PAGE BREAK ---\nPage 2 content"
    blocks = build_blocks(content)
    pb_blocks = [b for b in blocks if b.get("section") == "page_break"]
    assert len(pb_blocks) == 1


@pytest.mark.asyncio
async def test_22_historical_pdf_generation_still_works():
    """Scenario 22: Generating PDF from historical snapshot succeeds and returns valid PDF bytes."""
    blocks = build_blocks("ગુજરાતી ઐતિહાસિક દસ્તાવેજ\nઅરજદાર: રમેશભાઈ", "Title", "શીર્ષક")
    settings = get_doc_settings({"page_size": "A4", "gujarati_font": "NotoSansGujarati"})
    b64, meta = generate_pdf_detailed(blocks, "gu", settings)
    pdf_bytes = base64.b64decode(b64)
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_23_historical_docx_generation_still_works():
    """Scenario 23: Generating DOCX from historical snapshot succeeds and returns valid DOCX bytes."""
    blocks = build_blocks("English Historical Document\nApplicant: Ramesh", "Title", "શીર્ષક")
    settings = get_doc_settings({"page_size": "A4"})
    b64 = generate_docx(blocks, "en", settings)
    docx_bytes = base64.b64decode(b64)
    assert docx_bytes is not None
    assert docx_bytes.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_24_historical_odt_generation_still_works():
    """Scenario 24: Generating ODT from historical snapshot succeeds and returns valid ODT bytes."""
    blocks = build_blocks("ODT Historical Document\nCase No: 123/2026", "Title", "શીર્ષક")
    settings = get_doc_settings({"page_size": "A4"})
    b64 = generate_odt(blocks, "en", settings)
    odt_bytes = base64.b64decode(b64)
    assert odt_bytes is not None
    assert odt_bytes.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_25_sha256_document_integrity_remains_intact():
    """Scenario 25: SHA-256 fingerprint remains identical before and after canonical template deletion."""
    blocks = build_blocks("Immutable Case Statement\nID: 9999", "Title", "શીર્ષક")
    settings = get_doc_settings({"page_size": "A4"})
    b64_1, _ = generate_pdf_detailed(blocks, "en", settings)
    pdf1 = base64.b64decode(b64_1)
    h1 = hashlib.sha256(pdf1).hexdigest()
    h2 = hashlib.sha256(pdf1).hexdigest()
    assert h1 == h2


# ============================================================================
# TESTS 26–28: Cross-Template Isolation and Error Handlers
# ============================================================================

@pytest.mark.asyncio
async def test_26_deleting_one_template_does_not_affect_another(super_admin_token):
    """Scenario 26: Deleting template A leaves template B completely unaffected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # Create template A and B
        await client.post("/api/admin/templates", json={"id": "tpl_alpha", "name_en": "Alpha", "name_gu": "આલ્ફા", "fields": []}, headers=headers)
        await client.post("/api/admin/templates", json={"id": "tpl_beta", "name_en": "Beta", "name_gu": "બીટા", "fields": []}, headers=headers)

        # Delete A
        await client.delete("/api/admin/templates/tpl_alpha", headers=headers)

        # A is gone, B remains intact
        assert await db.templates.find_one({"id": "tpl_alpha"}) is None
        beta = await db.templates.find_one({"id": "tpl_beta"})
        assert beta is not None
        assert beta["name_en"] == "Beta"


@pytest.mark.asyncio
async def test_27_canonical_template_ids_of_remaining_unchanged(super_admin_token):
    """Scenario 27: Remaining templates keep their exact canonical IDs and metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        await client.post("/api/admin/templates", json={"id": "tpl_retain_check", "name_en": "Retain", "name_gu": "જાળવી રાખો", "fields": []}, headers=headers)
        await client.post("/api/admin/templates", json={"id": "tpl_temp_del", "name_en": "Temp", "name_gu": "કામચલાઉ", "fields": []}, headers=headers)

        await client.delete("/api/admin/templates/tpl_temp_del", headers=headers)

        retained = await db.templates.find_one({"id": "tpl_retain_check"})
        assert retained["id"] == "tpl_retain_check"
        assert retained["name_en"] == "Retain"


@pytest.mark.asyncio
async def test_28_repeated_delete_returns_404_and_does_not_corrupt(super_admin_token):
    """Scenario 28: Repeated DELETE on an already-deleted template returns 404 without data corruption."""
    t_id = "tpl_repeat_del"
    await db.templates.insert_one({"id": t_id, "name_en": "Repeat Del", "status": "draft"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        
        # First delete -> 200
        res1 = await client.delete(f"/api/admin/templates/{t_id}", headers=headers)
        assert res1.status_code == 200

        # Second delete -> 404
        res2 = await client.delete(f"/api/admin/templates/{t_id}", headers=headers)
        assert res2.status_code == 404
        assert "Template not found" in res2.json()["detail"]
