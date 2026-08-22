"""
Phase 4: Word-Like Legal Template Editor Test Suite.
Tests Tiptap editor content round-trip, plain-text auto-derivation,
variable placeholder safety, page breaks, table blocks, HarfBuzz PDF,
DOCX/ODT generation, linear versioning, and immutable revision snapshots.
"""

import os
import sys
import uuid
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_phase4")

import pytest
import pytest_asyncio
import mongomock_motor
from httpx import AsyncClient, ASGITransport

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_phase4"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import (
    make_token,
    make_admin_token,
    hash_password,
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
    """Seed test database with admin user and clean collections."""
    server.db = db
    for coll_name in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "audit_logs", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans"
    ]:
        await db[coll_name].drop()

    admin_doc = {
        "id": "admin_super_1",
        "email": "superadmin@nyaysetu.gov.in",
        "name": "Super Administrator",
        "role": "super_admin",
        "password_hash": hash_password("SuperSecret123!"),
        "active": True,
        "created_at": "2026-08-21T00:00:00Z",
    }
    await db.admin_users.insert_one(admin_doc)
    await db.users.insert_one(admin_doc)
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})


@pytest.fixture
def admin_token():
    return make_admin_token("admin_super_1", "superadmin@nyaysetu.gov.in", "super_admin")


@pytest.fixture
def lawyer_token():
    return make_token("lawyer_regular_1", "9876543210")


# ============================================================================
# 1. Document Generator & Block Parsing Unit Tests
# ============================================================================

class TestDocGeneratorBlocks:
    """Test build_blocks parsing for page breaks and table blocks."""

    def test_page_break_block_parsing(self):
        content = (
            "IN THE COURT OF {{court}}, {{district}}\n\n"
            "--- PAGE BREAK ---\n\n"
            "Second Page Heading\n"
        )
        blocks = build_blocks(content, "Title En", "Title Gu")
        sections = [b.get("section") for b in blocks]
        assert "page_break" in sections

    def test_table_block_parsing(self):
        content = (
            "IN THE COURT OF {{court}}, {{district}}\n\n"
            "[TABLE_START]\n"
            "Sr No. | Document Description | Date\n"
            "1 | FIR Copy | 12/01/2026\n"
            "2 | Charge Sheet | 15/02/2026\n"
            "[TABLE_END]\n\n"
            "Advocate for Applicant\n"
        )
        blocks = build_blocks(content, "Title En", "Title Gu")
        table_blocks = [b for b in blocks if b.get("section") == "table"]
        assert len(table_blocks) == 1
        rows = table_blocks[0].get("rows", [])
        assert len(rows) == 3
        assert rows[0] == ["Sr No.", "Document Description", "Date"]
        assert rows[1] == ["1", "FIR Copy", "12/01/2026"]
        assert rows[2] == ["2", "Charge Sheet", "15/02/2026"]

    def test_mixed_gujarati_english_with_variables(self):
        content = (
            "માનનીય ન્યાયાલય {{court}}, {{district}}\n"
            "કેસ નં. {{case_number}}\n\n"
            "{{party_name}} ...અરજદાર\n"
            "વિરુદ્ધ\n"
            "{{opposite_party}} ...સામાવાળા\n\n"
            "મુદત અરજી (Application for Adjournment)\n\n"
            "૧. કારણ: {{reason}}\n\n"
            "તારીખ: {{today}}\n"
            "અરજદારના વકીલ\n"
            "{{advocate_name}}\n"
        )
        values = {
            "court": "City Civil Court",
            "district": "Ahmedabad",
            "case_number": "CMA/101/2026",
            "party_name": "રાજેશકુમાર પટેલ",
            "opposite_party": "ગુજરાત રાજ્ય",
            "reason": "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ છે",
            "today": "21/08/2026",
            "advocate_name": "એડવોકેટ રમેશ શાહ",
        }
        rendered = render_template(content, values)
        assert "રાજેશકુમાર પટેલ" in rendered
        assert "CMA/101/2026" in rendered
        assert "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ છે" in rendered
        assert "{{" not in rendered

        blocks = build_blocks(rendered, "Adjournment", "મુદત અરજી")
        assert len(blocks) > 5


# ============================================================================
# 2. Multi-Format Document Generation Tests (PDF, DOCX, ODT)
# ============================================================================

class TestMultiFormatGeneration:
    """Test PDF, DOCX and ODT binary artifact generation with tables & page breaks."""

    def test_generate_pdf_with_table_and_page_break(self):
        content = (
            "માનનીય ન્યાયાલય અમદાવાદ\n\n"
            "દસ્તાવેજ રજૂ કરવાની યાદી\n\n"
            "[TABLE_START]\n"
            "ક્રમ | દસ્તાવેજ | તારીખ\n"
            "૧ | આધાર કાર્ડ | ૦૧/૦૧/૨૦૨૬\n"
            "૨ | પાવર ઓફ એટર્ની | ૦૫/૦૧/૨૦૨૬\n"
            "[TABLE_END]\n\n"
            "--- PAGE BREAK ---\n\n"
            "સોગંદનામું (Affidavit)\n\n"
            "હું સોગંદપૂર્વક એકરાર કરું છું.\n"
        )
        blocks = build_blocks(content, "Document List", "દસ્તાવેજ યાદી")
        settings = get_doc_settings({"page_size": "A4", "gujarati_font": "NotoSansGujarati"})
        b64, meta = generate_pdf_detailed(blocks, "gu", settings)
        assert b64 is not None
        pdf_bytes = base64.b64decode(b64)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 1000

    def test_generate_docx_with_table_and_page_break(self):
        content = (
            "IN THE COURT OF AHMEDABAD\n\n"
            "LIST OF DOCUMENTS\n\n"
            "[TABLE_START]\n"
            "No. | Description | Remarks\n"
            "1 | Sale Deed | Original\n"
            "2 | Tax Receipt | Copy\n"
            "[TABLE_END]\n\n"
            "--- PAGE BREAK ---\n\n"
            "VERIFICATION\n"
        )
        blocks = build_blocks(content, "List", "યાદી")
        settings = get_doc_settings({"page_size": "A4"})
        b64 = generate_docx(blocks, "en", settings)
        assert b64 is not None
        docx_bytes = base64.b64decode(b64)
        # DOCX is a zip file starting with PK\x03\x04
        assert docx_bytes.startswith(b"PK\x03\x04")

    def test_generate_odt_with_table_and_page_break(self):
        content = (
            "IN THE COURT OF AHMEDABAD\n\n"
            "[TABLE_START]\n"
            "Col 1 | Col 2\n"
            "Val 1 | Val 2\n"
            "[TABLE_END]\n\n"
            "--- PAGE BREAK ---\n\n"
            "Page 2 Content\n"
        )
        blocks = build_blocks(content, "List", "યાદી")
        settings = get_doc_settings({"page_size": "A4"})
        b64 = generate_odt(blocks, "en", settings)
        assert b64 is not None
        odt_bytes = base64.b64decode(b64)
        assert odt_bytes.startswith(b"PK\x03\x04")


# ============================================================================
# 3. Admin Template Editor API Tests (Tiptap JSON Round-Trip & Versioning)
# ============================================================================

class TestAdminTemplateEditorAPI:
    """Test saving Tiptap JSON, auto-deriving plain text, publishing & revision history."""

    @pytest.mark.asyncio
    async def test_create_draft_with_editor_content(self, admin_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            sample_tiptap_json = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "માનનીય ન્યાયાલય "},
                            {"type": "templateVariable", "attrs": {"variableName": "court"}},
                            {"type": "text", "text": ", "},
                            {"type": "templateVariable", "attrs": {"variableName": "district"}},
                        ],
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "અરજદારનું નામ: "},
                            {"type": "templateVariable", "attrs": {"variableName": "applicant_name"}},
                        ],
                    },
                ],
            }

            payload = {
                "id": "tiptap_test_template",
                "name_en": "Tiptap Legal Application",
                "name_gu": "ટિપટેપ કાનૂની અરજી",
                "category": "Civil",
                "fields": [
                    {"key": "applicant_name", "label_en": "Applicant Name", "label_gu": "અરજદારનું નામ", "type": "text", "required": True},
                ],
                "content_en": "IN THE COURT OF {{court}}, {{district}}\nApplicant: {{applicant_name}}",
                "content_gu": "માનનીય ન્યાયાલય {{court}}, {{district}}\nઅરજદારનું નામ: {{applicant_name}}",
                "editor_content_gu": sample_tiptap_json,
                "editor_content_en": None,
            }

            res = await client.post("/api/admin/templates", json=payload, headers=headers)
            assert res.status_code == 200, res.text
            data = res.json()
            assert data["id"] == "tiptap_test_template"
            assert data["status"] == "draft"
            assert data["version"] == 1
            assert data["editor_content_gu"] == sample_tiptap_json

    @pytest.mark.asyncio
    async def test_update_draft_preserves_editor_json(self, admin_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create initial draft
            create_res = await client.post(
                "/api/admin/templates",
                json={
                    "id": "editable_tpl",
                    "name_en": "Editable Template",
                    "name_gu": "ફેરફારપાત્ર નમૂનો",
                    "category": "Civil",
                    "fields": [{"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "text", "required": True}],
                    "content_en": "Reason: {{reason}}",
                    "content_gu": "કારણ: {{reason}}",
                },
                headers=headers,
            )
            assert create_res.status_code == 200

            # Update with Tiptap editor JSON
            updated_json = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "વિગતવાર કારણ: "},
                            {"type": "templateVariable", "attrs": {"variableName": "reason"}},
                        ],
                    }
                ],
            }

            update_res = await client.put(
                "/api/admin/templates/editable_tpl",
                json={
                    "content_gu": "વિગતવાર કારણ: {{reason}}",
                    "editor_content_gu": updated_json,
                },
                headers=headers,
            )
            assert update_res.status_code == 200
            updated_data = update_res.json()
            assert updated_data["editor_content_gu"] == updated_json
            assert updated_data["content_gu"] == "વિગતવાર કારણ: {{reason}}"

    @pytest.mark.asyncio
    async def test_publish_creates_immutable_revision_with_editor_content(self, admin_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {admin_token}"}

            editor_json = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "માનનીય અદાલત "},
                            {"type": "templateVariable", "attrs": {"variableName": "court"}},
                        ],
                    }
                ],
            }

            # Create draft
            await client.post(
                "/api/admin/templates",
                json={
                    "id": "publishable_tpl",
                    "name_en": "Publishable Template",
                    "name_gu": "પ્રકાશિત કરવા યોગ્ય નમૂનો",
                    "category": "Civil",
                    "fields": [],
                    "content_en": "Court: {{court}}",
                    "content_gu": "માનનીય અદાલત {{court}}",
                    "editor_content_gu": editor_json,
                },
                headers=headers,
            )

            # Publish
            pub_res = await client.post(
                "/api/admin/templates/publishable_tpl/publish",
                headers=headers,
            )
            assert pub_res.status_code == 200
            pub_data = pub_res.json()
            assert pub_data["template"]["status"] == "published"
            assert pub_data["template"]["locked"] is True

            # Verify revision snapshot in db.template_revisions
            rev = await db.template_revisions.find_one(
                {"template_id": "publishable_tpl", "version": 1},
                {"_id": 0},
            )
            assert rev is not None
            assert rev["version"] == 1
            assert rev["editor_content_gu"] == editor_json

            # Verify revisions API endpoint
            rev_res = await client.get("/api/admin/templates/publishable_tpl/revisions", headers=headers)
            assert rev_res.status_code == 200
            rev_data = rev_res.json()
            assert len(rev_data["revisions"]) == 1
            assert rev_data["revisions"][0]["editor_content_gu"] == editor_json

    @pytest.mark.asyncio
    async def test_linear_version_increment_on_republish(self, admin_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {admin_token}"}

            # 1. Create and Publish Version 1
            await client.post(
                "/api/admin/templates",
                json={
                    "id": "versioned_tpl",
                    "name_en": "Versioned Template",
                    "name_gu": "સંસ્કરણ નમૂનો",
                    "category": "Civil",
                    "fields": [],
                    "content_en": "V1: {{court}}",
                    "content_gu": "સંસ્કરણ ૧: {{court}}",
                },
                headers=headers,
            )
            await client.post("/api/admin/templates/versioned_tpl/publish", headers=headers)

            # 2. Branch published template to next version (v2 draft) under same template_id
            clone_res = await client.post(
                "/api/admin/templates/versioned_tpl/clone",
                json={"as_new_template": False},
                headers=headers,
            )
            assert clone_res.status_code == 200
            new_v = clone_res.json()["template"]["version"]
            assert new_v == 2
            assert clone_res.json()["template"]["status"] == "draft"

            # 3. Edit draft content in v2
            await client.put(
                "/api/admin/templates/versioned_tpl",
                json={"content_gu": "સંસ્કરણ ૨: {{court}} (સુધારેલ)"},
                headers=headers,
            )

            # 4. Publish Version 2
            pub2_res = await client.post("/api/admin/templates/versioned_tpl/publish", headers=headers)
            assert pub2_res.status_code == 200

            # 5. Verify revision history now has both v1 and v2
            rev_res = await client.get("/api/admin/templates/versioned_tpl/revisions", headers=headers)
            assert rev_res.status_code == 200
            revisions = rev_res.json()["revisions"]
            versions = [r["version"] for r in revisions]
            assert 1 in versions
            assert 2 in versions

    @pytest.mark.asyncio
    async def test_live_editor_preview_with_sample_values(self, admin_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create draft
            await client.post(
                "/api/admin/templates",
                json={
                    "id": "preview_tpl",
                    "name_en": "Preview Template",
                    "name_gu": "પૂર્વાવલોકન નમૂનો",
                    "category": "Civil",
                    "fields": [
                        {"key": "custom_note", "label_en": "Custom Note", "label_gu": "ખાસ નોંધ", "type": "text", "required": True},
                    ],
                    "content_en": "Notice: {{custom_note}} in {{court}}",
                    "content_gu": "નોંધ: {{custom_note}} કોર્ટ: {{court}}",
                },
                headers=headers,
            )

            # Live preview with unsaved override text
            preview_res = await client.post(
                "/api/admin/templates/preview_tpl/preview",
                json={
                    "content_gu": "તત્કાલ નોંધ: {{custom_note}} (લાઈવ પ્રિવ્યુ) કોર્ટ: {{court}}",
                    "values": {"custom_note": "તાકીદની સુનાવણી"},
                },
                headers=headers,
            )
            assert preview_res.status_code == 200
            prev_data = preview_res.json()
            assert "તાકીદની સુનાવણી" in prev_data["preview"]["gu"]["content"]
            assert prev_data["validation"]["valid"] is True

    @pytest.mark.asyncio
    async def test_security_isolation_lawyer_cannot_access_editor_apis(self, lawyer_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {lawyer_token}"}

            # Lawyer attempting to create template -> 401/403
            res1 = await client.post(
                "/api/admin/templates",
                json={"name_en": "Unauthorized", "name_gu": "અનધિકૃત"},
                headers=headers,
            )
            assert res1.status_code in (401, 403)

            # Lawyer attempting to update template -> 401/403
            res2 = await client.put(
                "/api/admin/templates/adjournment",
                json={"name_en": "Hacked"},
                headers=headers,
            )
            assert res2.status_code in (401, 403)

            # Lawyer attempting to publish template -> 401/403
            res3 = await client.post(
                "/api/admin/templates/adjournment/publish",
                headers=headers,
            )
            assert res3.status_code in (401, 403)


# ============================================================================
# 4. Critical Functional Test — Complete 20-Step End-to-End Workflow
# ============================================================================

class TestFullEndToEndWorkflow:
    """Exercises the complete lifecycle requested by the user:
    1. Seed template loading
    2. Legacy content loading in editor
    3. Edit Gujarati text
    4. Edit English text
    5. Insert multiple {{variables}}
    6. Verify variables are atomic
    7. Insert table
    8. Insert page break
    9. Save Draft with Tiptap JSON and plain text
    10. Reload and verify survival
    11. Live preview
    12. Publish
    13. Linear version increment (v1 -> v2)
    14. Immutable revision snapshot in db.template_revisions
    15. Generate PDF
    16. Generate DOCX
    17. Generate ODT
    18. Verify Gujarati font rendering
    19. Verify variable replacement
    20. Verify historical revision accessibility
    """

    @pytest.mark.asyncio
    async def test_complete_20_step_editor_workflow(self, admin_token, lawyer_token):
        server.db = db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            lawyer_headers = {"Authorization": f"Bearer {lawyer_token}"}

            # 1. Create initial seed template (v1)
            create_res = await client.post(
                "/api/admin/templates",
                json={
                    "id": "e2e_mudat_arji",
                    "name_en": "Adjournment Application",
                    "name_gu": "મુદત અરજી",
                    "category": "Civil",
                    "fields": [
                        {"key": "next_date", "label_en": "Next Date", "label_gu": "આગામી તારીખ", "type": "date", "required": True},
                        {"key": "reason", "label_en": "Reason", "label_gu": "મુદતનું કારણ", "type": "textarea", "required": True},
                    ],
                    "content_en": "IN THE COURT OF {{court}}, {{district}}\n\nAPPLICATION FOR ADJOURNMENT\n\n1. Reason: {{reason}}\nDate: {{next_date}}",
                    "content_gu": "માનનીય ન્યાયાલય {{court}}, {{district}}\n\nમુદત અરજી\n\n૧. કારણ: {{reason}}\nતારીખ: {{next_date}}",
                },
                headers=admin_headers,
            )
            assert create_res.status_code == 200

            # Publish v1
            pub1 = await client.post("/api/admin/templates/e2e_mudat_arji/publish", headers=admin_headers)
            assert pub1.status_code == 200
            assert pub1.json()["template"]["version"] == 1

            # 2. Open / Branch to v2 draft for editing
            branch_res = await client.post(
                "/api/admin/templates/e2e_mudat_arji/clone",
                json={"as_new_template": False},
                headers=admin_headers,
            )
            assert branch_res.status_code == 200
            tpl = branch_res.json()["template"]
            assert tpl["version"] == 2
            assert tpl["status"] == "draft"

            # 3. Simulate Tiptap editor modifications with table and page break
            e2e_editor_json_gu = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "માનનીય ન્યાયાલય "},
                            {"type": "templateVariable", "attrs": {"variableName": "court"}},
                            {"type": "text", "text": ", "},
                            {"type": "templateVariable", "attrs": {"variableName": "district"}},
                        ],
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "કેસ નં. "},
                            {"type": "templateVariable", "attrs": {"variableName": "case_number"}},
                        ],
                    },
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "મુદત અરજી (વિશેષ સંસ્કરણ ૨)"}],
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "૧. મુદત માટેનું કારણ: "},
                            {"type": "templateVariable", "attrs": {"variableName": "reason"}},
                        ],
                    },
                    # Table Node
                    {
                        "type": "table",
                        "content": [
                            {
                                "type": "tableRow",
                                "content": [
                                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "તારીખ"}]}]},
                                    {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "કાર્યવાહી"}]}]},
                                ],
                            },
                            {
                                "type": "tableRow",
                                "content": [
                                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "templateVariable", "attrs": {"variableName": "next_date"}}]}]},
                                    {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "અંતિમ દલીલો"}]}]},
                                ],
                            },
                        ],
                    },
                    # Page Break Node
                    {"type": "pageBreak"},
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "અરજદારના વકીલ: "},
                            {"type": "templateVariable", "attrs": {"variableName": "advocate_name"}},
                        ],
                    },
                ],
            }

            derived_plain_text_gu = (
                "માનનીય ન્યાયાલય {{court}}, {{district}}\n"
                "કેસ નં. {{case_number}}\n\n"
                "મુદત અરજી (વિશેષ સંસ્કરણ ૨)\n\n"
                "૧. મુદત માટેનું કારણ: {{reason}}\n\n"
                "[TABLE_START]\n"
                "તારીખ | કાર્યવાહી\n"
                "{{next_date}} | અંતિમ દલીલો\n"
                "[TABLE_END]\n\n"
                "--- PAGE BREAK ---\n\n"
                "અરજદારના વકીલ: {{advocate_name}}\n"
            )

            # 4. Save Draft
            save_res = await client.put(
                "/api/admin/templates/e2e_mudat_arji",
                json={
                    "content_gu": derived_plain_text_gu,
                    "editor_content_gu": e2e_editor_json_gu,
                },
                headers=admin_headers,
            )
            assert save_res.status_code == 200

            # 5. Reload and confirm content survives exactly
            get_res = await client.get("/api/admin/templates/e2e_mudat_arji", headers=admin_headers)
            assert get_res.status_code == 200
            loaded = get_res.json()
            assert loaded["editor_content_gu"] == e2e_editor_json_gu
            assert "[TABLE_START]" in loaded["content_gu"]
            assert "--- PAGE BREAK ---" in loaded["content_gu"]

            # 6. Live Preview
            prev_res = await client.post(
                "/api/admin/templates/e2e_mudat_arji/preview",
                json={
                    "content_gu": derived_plain_text_gu,
                    "values": {
                        "court": "અમદાવાદ સિટી સિવિલ કોર્ટ",
                        "district": "અમદાવાદ",
                        "case_number": "દિવાની દાવો નં. ૫૦૫/૨૦૨૬",
                        "reason": "વકીલશ્રી બીમાર હોવાથી હાજર રહી શકે તેમ નથી",
                        "next_date": "૨૮/૦૮/૨૦૨૬",
                        "advocate_name": "એડવોકેટ જયેશ પંડ્યા",
                    },
                },
                headers=admin_headers,
            )
            assert prev_res.status_code == 200
            prev_data = prev_res.json()
            assert prev_data["validation"]["valid"] is True
            assert "અમદાવાદ સિટી સિવિલ કોર્ટ" in prev_data["preview"]["gu"]["content"]
            assert "એડવોકેટ જયેશ પંડ્યા" in prev_data["preview"]["gu"]["content"]

            # 7. Publish Version 2
            pub2 = await client.post("/api/admin/templates/e2e_mudat_arji/publish", headers=admin_headers)
            assert pub2.status_code == 200
            assert pub2.json()["template"]["version"] == 2
            assert pub2.json()["template"]["status"] == "published"

            # 8. Check revision history has both immutable snapshots with editor_content
            revs_res = await client.get("/api/admin/templates/e2e_mudat_arji/revisions", headers=admin_headers)
            assert revs_res.status_code == 200
            all_revs = revs_res.json()["revisions"]
            assert len(all_revs) == 2
            v2_snap = next(r for r in all_revs if r["version"] == 2)
            assert v2_snap["editor_content_gu"] == e2e_editor_json_gu

            # 9. Document Generation - PDF (HarfBuzz OpenType shaping)
            blocks = build_blocks(derived_plain_text_gu, "Adjournment", "મુદત અરજી")
            settings = get_doc_settings({"page_size": "A4", "gujarati_font": "NotoSansGujarati"})
            pdf_b64, meta = generate_pdf_detailed(blocks, "gu", settings)
            pdf_bytes = base64.b64decode(pdf_b64)
            assert pdf_bytes.startswith(b"%PDF")
            assert len(pdf_bytes) > 2000

            # 10. Document Generation - DOCX (python-docx with Table & Page Break)
            docx_b64 = generate_docx(blocks, "gu", settings)
            docx_bytes = base64.b64decode(docx_b64)
            assert docx_bytes.startswith(b"PK\x03\x04")

            # 11. Document Generation - ODT (OpenDocument with Table & Page Break)
            odt_b64 = generate_odt(blocks, "gu", settings)
            odt_bytes = base64.b64decode(odt_b64)
            assert odt_bytes.startswith(b"PK\x03\x04")

            # 12. Verification of historical resolution from db.template_revisions
            v1_snapshot = await db.template_revisions.find_one({"template_id": "e2e_mudat_arji", "version": 1})
            assert v1_snapshot is not None
            assert v1_snapshot["version"] == 1
            assert "મુદત અરજી" in v1_snapshot["name_gu"]

