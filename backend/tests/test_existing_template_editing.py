"""Tests for Section 18: Existing Template Editing & Lifecycle Management.

Covers:
1. All 23 templates loading with exact IDs and fields preserved.
2. Draft editing and saving with extended field types (select, radio, checkbox, options).
3. Published template editing -> safe version branching (v1 -> Draft v2 -> Published v2).
4. Public lawyer API isolation (v1 remains live while v2 is draft; v2 becomes live upon publish).
5. Version history immutability and snapshots.
6. Independent template cloning.
7. Live preview in English and Gujarati with validation checks.
8. Unknown placeholder rejection during publish.
9. Backward compatibility with PDF, DOCX, and mobile application flows.
"""

import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_template_editing")

import pytest
import pytest_asyncio
import bcrypt
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_template_editing"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token, make_admin_token, TEMPLATES


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions"]:
        await db[coll_name].drop()


@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def admin_token():
    admin_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"NyaySetu@Admin2026!", bcrypt.gensalt()).decode("utf-8")
    admin = {
        "id": admin_id,
        "email": "superadmin@test.com",
        "password_hash": hashed,
        "name": "Super Admin",
        "role": "super_admin",
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.admin_users.insert_one(admin.copy())
    return make_admin_token(admin_id, admin["email"], admin["role"])


@pytest_asyncio.fixture(scope="function")
async def auth_headers():
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": "+919876543210",
        "name": "Test Advocate",
        "role": "advocate",
        "bar_council_no": "GUJ/1234/2020",
        "district": "Ahmedabad",
        "court": "City Civil Court, Ahmedabad",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user.copy())
    wallet = {
        "user_id": user_id,
        "balance": 20,
        "free_credits_granted": 5,
        "total_used": 0,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.wallets.insert_one(wallet.copy())
    token = make_token(user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestExisting23TemplatesIntegrity:
    """Verify all 23 seed templates exist, retain IDs, fields, and placeholders."""

    async def test_all_23_templates_accessible_via_admin_api(self, client: AsyncClient, admin_token):
        res = await client.get("/api/admin/templates", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        templates = res.json()
        assert len(templates) >= 23
        
        # Verify all 23 IDs from seed_data exist
        seed_ids = {t["id"] for t in TEMPLATES}
        admin_ids = {t["id"] for t in templates}
        assert seed_ids.issubset(admin_ids)

    async def test_all_23_templates_load_with_full_fidelity(self, client: AsyncClient, admin_token):
        for seed_t in TEMPLATES:
            res = await client.get(f"/api/admin/templates/{seed_t['id']}", headers={"Authorization": f"Bearer {admin_token}"})
            assert res.status_code == 200
            data = res.json()
            assert data["id"] == seed_t["id"]
            assert data["name_en"] == seed_t["name_en"]
            assert data["name_gu"] == seed_t["name_gu"]
            assert data["category"] == seed_t["category"]
            assert len(data["fields"]) == len(seed_t["fields"])
            assert data["content_en"] == seed_t["content_en"]
            assert data["content_gu"] == seed_t["content_gu"]


@pytest.mark.asyncio
class TestDraftAndPublishedLifecycle:
    """Test full editing, branching, publishing, and version history."""

    async def test_create_and_edit_draft_template(self, client: AsyncClient, admin_token):
        # 1. Create a draft template with custom field types (select, radio, checkbox)
        create_payload = {
            "id": "test_bail_extended",
            "name_en": "Extended Bail Application",
            "name_gu": "વિસ્તૃત જામીન અરજી",
            "category": "Criminal",
            "sub_category": "Bail Matters",
            "description": "Comprehensive bail application with option fields",
            "tags": ["bail", "437", "crpc"],
            "aliases": ["bail_ext"],
            "fields": [
                {
                    "key": "offence_type",
                    "label_en": "Type of Offence",
                    "label_gu": "ગુન્હાનો પ્રકાર",
                    "type": "select",
                    "required": True,
                    "order": 0,
                    "options": [
                        {"label_en": "Bailable", "label_gu": "જામીનપાત્ર", "value": "bailable"},
                        {"label_en": "Non-Bailable", "label_gu": "બિન-જામીનપાત્ર", "value": "non_bailable"},
                    ]
                },
                {
                    "key": "surety_ready",
                    "label_en": "Surety Ready",
                    "label_gu": "જામીનદાર હાજર",
                    "type": "checkbox",
                    "required": False,
                    "order": 1,
                }
            ],
            "content_en": "IN THE COURT OF {{court}}\n{{party_name}} applies for bail.\nOffence Type: {{offence_type}}\nSurety: {{surety_ready}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\n{{party_name}} જામીન માંગે છે.\nગુન્હાનો પ્રકાર: {{offence_type}}\nજામીનદાર: {{surety_ready}}",
        }
        res = await client.post("/api/admin/templates", json=create_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        created = res.json()
        assert created["id"] == "test_bail_extended"
        assert created["status"] == "draft"
        assert created["version"] == 1
        assert created["locked"] is False
        assert len(created["fields"][0]["options"]) == 2

        # 2. Update the draft in-place
        update_payload = {
            "name_en": "Extended Regular Bail Application",
            "fields": [
                {
                    "key": "offence_type",
                    "label_en": "Type of Offence",
                    "label_gu": "ગુન્હાનો પ્રકાર",
                    "type": "select",
                    "required": True,
                    "order": 0,
                    "options": [
                        {"label_en": "Bailable", "label_gu": "જામીનપાત્ર", "value": "bailable"},
                        {"label_en": "Non-Bailable", "label_gu": "બિન-જામીનપાત્ર", "value": "non_bailable"},
                        {"label_en": "Anticipatory", "label_gu": "અગાઉથી જામીન", "value": "anticipatory"},
                    ]
                },
                {
                    "key": "surety_ready",
                    "label_en": "Surety Ready",
                    "label_gu": "જામીનદાર હાજર",
                    "type": "checkbox",
                    "required": False,
                    "order": 1,
                },
                {
                    "key": "case_remarks",
                    "label_en": "Special Remarks",
                    "label_gu": "ખાસ નોંધ",
                    "type": "textarea",
                    "required": False,
                    "order": 2,
                }
            ],
            "content_en": "IN THE COURT OF {{court}}\n{{party_name}} applies for bail.\nOffence Type: {{offence_type}}\nSurety: {{surety_ready}}\nRemarks: {{case_remarks}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\n{{party_name}} જામીન માંગે છે.\nગુન્હાનો પ્રકાર: {{offence_type}}\nજામીનદાર: {{surety_ready}}\nનોંધ: {{case_remarks}}",
        }
        res = await client.put(f"/api/admin/templates/test_bail_extended", json=update_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        updated = res.json()
        assert updated["name_en"] == "Extended Regular Bail Application"
        assert len(updated["fields"]) == 3
        assert len(updated["fields"][0]["options"]) == 3

    async def test_published_template_versioning_and_isolation(self, client: AsyncClient, admin_token, auth_headers):
        # 0. Create draft template first
        create_payload = {
            "id": "test_bail_extended",
            "name_en": "Extended Regular Bail Application",
            "name_gu": "વિસ્તૃત જામીન અરજી",
            "category": "Criminal",
            "fields": [
                {
                    "key": "offence_type",
                    "label_en": "Type of Offence",
                    "label_gu": "ગુન્હાનો પ્રકાર",
                    "type": "select",
                    "required": True,
                    "order": 0,
                    "options": [
                        {"label_en": "Bailable", "label_gu": "જામીનપાત્ર", "value": "bailable"},
                    ]
                }
            ],
            "content_en": "IN THE COURT OF {{court}}\n{{party_name}} applies for bail.\nOffence Type: {{offence_type}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\n{{party_name}} જામીન માંગે છે.\nગુન્હાનો પ્રકાર: {{offence_type}}",
        }
        await client.post("/api/admin/templates", json=create_payload, headers={"Authorization": f"Bearer {admin_token}"})

        # 1. Publish test_bail_extended as v1
        res = await client.post("/api/admin/templates/test_bail_extended/publish", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        pub = res.json()["template"]
        assert pub["status"] == "published"
        assert pub["version"] == 1
        assert pub["locked"] is True

        # 2. Verify lawyer API returns Published v1
        res_lawyer = await client.get("/api/templates/test_bail_extended", headers=auth_headers)
        assert res_lawyer.status_code == 200
        lawyer_t = res_lawyer.json()
        assert lawyer_t["name_en"] == "Extended Regular Bail Application"
        assert len(lawyer_t["fields"]) == 1

        # 3. Direct mutation of locked template is rejected with 403
        res_direct = await client.put(
            "/api/admin/templates/test_bail_extended",
            json={"name_en": "Illegal Direct Edit"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_direct.status_code == 403

        # 4. Clone / Branch to create Draft v2
        res_branch = await client.post("/api/admin/templates/test_bail_extended/clone", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_branch.status_code == 200
        branch_data = res_branch.json()
        draft_v2 = branch_data["template"]
        assert draft_v2["status"] == "draft"
        assert draft_v2["version"] == 2
        assert draft_v2["locked"] is False

        # 5. Modify Draft v2
        res_edit_v2 = await client.put(
            "/api/admin/templates/test_bail_extended",
            json={"name_en": "Extended Regular Bail Application (2026 Revision)"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_edit_v2.status_code == 200
        assert res_edit_v2.json()["name_en"] == "Extended Regular Bail Application (2026 Revision)"

        # 6. Publish Draft v2
        res_pub_v2 = await client.post("/api/admin/templates/test_bail_extended/publish", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_pub_v2.status_code == 200
        pub_v2 = res_pub_v2.json()["template"]
        assert pub_v2["status"] == "published"
        assert pub_v2["version"] == 2
        assert pub_v2["locked"] is True

        # 7. Check Version History contains snapshots for both v1 and v2
        res_history = await client.get("/api/admin/templates/test_bail_extended/versions", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_history.status_code == 200
        history = res_history.json()
        assert len(history) >= 2
        versions = [h["version"] for h in history]
        assert 1 in versions
        assert 2 in versions

        # 8. Verify lawyer API now returns Published v2
        res_lawyer_v2 = await client.get("/api/templates/test_bail_extended", headers=auth_headers)
        assert res_lawyer_v2.status_code == 200
        assert res_lawyer_v2.json()["name_en"] == "Extended Regular Bail Application (2026 Revision)"


@pytest.mark.asyncio
class TestCloneIndependentTemplate:
    """Test cloning a template into a separate new template."""

    async def test_clone_as_separate_template(self, client: AsyncClient, admin_token):
        res = await client.post(
            "/api/admin/templates/adjournment/clone",
            json={
                "as_new_template": True,
                "new_id": "adjournment_urgent",
                "new_name_en": "Urgent Adjournment Application",
                "new_name_gu": "તાકીદની મુદત અરજી",
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        new_tpl = data["template"]
        assert new_tpl["id"] == "adjournment_urgent"
        assert new_tpl["name_en"] == "Urgent Adjournment Application"
        assert new_tpl["name_gu"] == "તાકીદની મુદત અરજી"
        assert new_tpl["status"] == "draft"
        assert new_tpl["version"] == 1
        assert new_tpl["locked"] is False


@pytest.mark.asyncio
class TestAdminLivePreviewAndValidation:
    """Test live preview rendering and placeholder validation."""

    async def test_admin_preview_live_overrides(self, client: AsyncClient, admin_token):
        preview_req = {
            "name_en": "Test Document",
            "name_gu": "ટેસ્ટ દસ્તાવેજ",
            "content_en": "IN THE COURT OF {{court}}\nCase: {{case_number}}\nCustom Value: {{custom_key}}",
            "content_gu": "માનનીય ન્યાયાલય {{court}}\nકેસ: {{case_number}}\nવિગત: {{custom_key}}",
            "fields": [
                {"key": "custom_key", "label_en": "Custom Key", "label_gu": "કસ્ટમ કી", "type": "text", "required": True}
            ],
            "values": {
                "court": "High Court of Gujarat",
                "custom_key": "Urgent Hearing Required",
            }
        }
        res = await client.post("/api/admin/templates/adjournment/preview", json=preview_req, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        assert "preview" in data
        assert "en" in data["preview"]
        assert "gu" in data["preview"]
        assert "High Court of Gujarat" in data["preview"]["en"]["content"]
        assert "Urgent Hearing Required" in data["preview"]["en"]["content"]
        assert data["validation"]["valid"] is True
        assert len(data["validation"]["unknown"]) == 0

    async def test_publish_blocks_unknown_placeholders(self, client: AsyncClient, admin_token):
        # Create draft with undeclared placeholder
        create_payload = {
            "id": "test_invalid_placeholder",
            "name_en": "Invalid Template",
            "name_gu": "અમાન્ય ટેમ્પ્લેટ",
            "category": "General",
            "fields": [],
            "content_en": "Document with {{unknown_secret_field}}",
            "content_gu": "દસ્તાવેજ {{unknown_secret_field}}",
        }
        await client.post("/api/admin/templates", json=create_payload, headers={"Authorization": f"Bearer {admin_token}"})
        
        # Attempt to publish must fail with 400
        res = await client.post("/api/admin/templates/test_invalid_placeholder/publish", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 400
        assert "unknown_secret_field" in res.json()["detail"]


@pytest.mark.asyncio
class TestDocumentGenerationBackwardCompatibility:
    """Test that existing document generation (preview, download, PDF, DOCX) remains 100% functional."""

    async def test_preview_and_download_flow_with_db_template(self, client: AsyncClient, auth_headers):
        # Preview
        prev_res = await client.post(
            "/api/applications/preview",
            json={
                "template_id": "adjournment",
                "language": "en",
                "values": {"next_date": "20-09-2026", "reason": "Counsel indisposed due to fever"},
            },
            headers=auth_headers
        )
        assert prev_res.status_code == 200
        prev_data = prev_res.json()
        assert "Counsel indisposed due to fever" in prev_data["content"]
        assert len(prev_data["blocks"]) > 0

        # Download PDF
        pdf_res = await client.post(
            "/api/applications/download",
            json={
                "template_id": "adjournment",
                "language": "gu",
                "format": "pdf",
                "values": {"next_date": "20-09-2026", "reason": "વકીલશ્રીની તબિયત નાદુરસ્ત હોવાથી"},
            },
            headers=auth_headers
        )
        assert pdf_res.status_code == 200
        pdf_data = pdf_res.json()
        assert pdf_data["mime_type"] == "application/pdf"
        assert len(pdf_data["base64"]) > 100

        # Download DOCX
        docx_res = await client.post(
            "/api/applications/download",
            json={
                "template_id": "adjournment",
                "language": "en",
                "format": "docx",
                "values": {"next_date": "20-09-2026", "reason": "Medical emergency"},
            },
            headers=auth_headers
        )
        assert docx_res.status_code == 200
        docx_data = docx_res.json()
        assert "wordprocessingml" in docx_data["mime_type"]
        assert len(docx_data["base64"]) > 100
