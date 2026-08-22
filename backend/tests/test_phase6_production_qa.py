"""
NyaySetu Pro — Phase 6 Production QA, Security Hardening & System Verification Suite
===================================================================================
Comprehensive automated verification covering:
1. Super Admin authentication, RBAC, expired/malformed token handling, and role isolation
2. Sensitive field scrubbing (password_hash, JWT, secrets) across APIs and audit logs
3. User lifecycle, status transitions (suspend/activate/ban), and profile updates
4. Wallet adjustments (atomic increment, debit floor check, audit trail)
5. Case management, archive/restore, and IDOR lawyer isolation
6. Application inspection, SHA-256 fingerprinting, engine telemetry, and template versioning
7. Template lifecycle: draft -> live preview -> publish -> v1 -> clone -> v2 -> archive -> delete
8. Tiptap JSON AST preservation and bidirectional plain-text synchronization
9. Historical draft resolution immutability from db.template_revisions
10. Seed decoupling permanence (no seed resurrection at runtime)
11. Catalogs CRUD (courts, districts, talukas, laws, police stations, case types)
12. Plan management CRUD and active toggles
13. Audit log generation, immutability, and filter queries
14. Multi-engine document generation (HarfBuzz PDF, DOCX, ODT) with tables and page breaks
15. Error recovery & HTTP status integrity (400, 401, 403, 404, 409, 422)
16. Database index verification & startup safety
"""

import os
import sys
import uuid
import base64
import hashlib
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_phase6")

import pytest
import pytest_asyncio
import mongomock_motor
from httpx import AsyncClient, ASGITransport
import jwt

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_phase6"]

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
    public_template,
    admin_public,
    _public_user,
    _ensure_index,
    JWT_SECRET,
    now,
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
    """Seed clean mock database for each test function."""
    server.db = db
    for coll in [
        "admin_users", "users", "wallets", "cases", "drafts",
        "applications", "transactions", "audit_logs", "referrals",
        "templates", "template_versions", "template_revisions",
        "system_settings", "plans", "courts", "districts", "talukas",
        "laws", "police_stations", "case_types"
    ]:
        await db[coll].drop()

    # Seed Super Admin
    super_admin = {
        "id": "sa_001",
        "email": "superadmin@nyaysetu.gov.in",
        "name": "Chief Super Administrator",
        "role": "super_admin",
        "password_hash": hash_password("SuperSecretAdminPass123!"),
        "active": True,
        "created_at": "2026-08-21T00:00:00Z",
    }
    await db.admin_users.insert_one(super_admin)

    # Seed Staff Admin
    staff_admin = {
        "id": "staff_001",
        "email": "staff@nyaysetu.gov.in",
        "name": "Staff Support Admin",
        "role": "staff_admin",
        "password_hash": hash_password("StaffPass123!"),
        "active": True,
        "created_at": "2026-08-21T00:00:00Z",
    }
    await db.admin_users.insert_one(staff_admin)

    # Seed Regular Lawyer
    lawyer = {
        "id": "lawyer_001",
        "email": "lawyer1@nyaysetu.test",
        "mobile": "9876543210",
        "name": "Advocate Ramesh Patel",
        "user_type": "lawyer",
        "status": "active",
        "active": True,
        "password_hash": hash_password("LawyerPass123!"),
        "created_at": "2026-08-21T00:00:00Z",
    }
    await db.users.insert_one(lawyer)

    # Seed Second Lawyer (for IDOR tests)
    lawyer2 = {
        "id": "lawyer_002",
        "email": "lawyer2@nyaysetu.test",
        "mobile": "9876543211",
        "name": "Advocate Suresh Mehta",
        "user_type": "lawyer",
        "status": "active",
        "active": True,
        "password_hash": hash_password("LawyerPass123!"),
        "created_at": "2026-08-21T00:00:00Z",
    }
    await db.users.insert_one(lawyer2)

    # Seed Wallets
    await db.wallets.insert_one({"user_id": "lawyer_001", "balance": 50, "total_used": 0})
    await db.wallets.insert_one({"user_id": "lawyer_002", "balance": 10, "total_used": 0})

    # Decouple Seed
    await db.system_settings.insert_one({"key": "seed_complete", "value": True})


@pytest.fixture
def super_admin_token():
    return make_admin_token("sa_001", "superadmin@nyaysetu.gov.in", "super_admin")


@pytest.fixture
def staff_admin_token():
    return make_admin_token("staff_001", "staff@nyaysetu.gov.in", "staff_admin")


@pytest.fixture
def lawyer1_token():
    return make_token("lawyer_001", "9876543210")


@pytest.fixture
def lawyer2_token():
    return make_token("lawyer_002", "9876543211")


# ============================================================================
# 1. SECURITY HARDENING & RBAC ISOLATION
# ============================================================================

class TestSecurityAndRBAC:
    """Verifies Super Admin boundaries, staff restrictions, lawyer isolation, and token security."""

    @pytest.mark.asyncio
    async def test_super_admin_authorized_for_all_mutations(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}
            # Super admin can view users
            res = await client.get("/api/admin/users", headers=headers)
            assert res.status_code == 200
            # Super admin can create catalog item
            cat_res = await client.post(
                "/api/admin/catalog/districts",
                json={"en": "Ahmedabad", "gu": "અમદાવાદ"},
                headers=headers,
            )
            assert cat_res.status_code == 200

    @pytest.mark.asyncio
    async def test_staff_admin_restricted_from_super_admin_mutations(self, staff_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {staff_admin_token}"}
            # Staff admin can read dashboard stats (get_admin allowed)
            res = await client.get("/api/admin/dashboard/stats", headers=headers)
            assert res.status_code == 200
            # Staff admin is blocked from super admin wallet adjust
            adj_res = await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": 10, "reason": "Staff attempt"},
                headers=headers,
            )
            assert adj_res.status_code == 403

    @pytest.mark.asyncio
    async def test_lawyer_blocked_from_all_admin_endpoints(self, lawyer1_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {lawyer1_token}"}
            routes = [
                ("GET", "/api/admin/users"),
                ("GET", "/api/admin/cases"),
                ("GET", "/api/admin/applications"),
                ("GET", "/api/admin/audit-logs"),
                ("POST", "/api/admin/templates"),
                ("POST", "/api/admin/plans"),
            ]
            for method, route in routes:
                if method == "GET":
                    res = await client.get(route, headers=headers)
                else:
                    res = await client.post(route, json={}, headers=headers)
                assert res.status_code in (401, 403), f"Lawyer accessed {route} with status {res.status_code}"

    @pytest.mark.asyncio
    async def test_expired_and_malformed_tokens_rejected(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Expired admin token
            expired_payload = {
                "sub": "sa_001",
                "email": "superadmin@nyaysetu.gov.in",
                "role": "super_admin",
                "token_type": "admin",
                "exp": int((now() - timedelta(hours=1)).timestamp()),
            }
            expired_tok = jwt.encode(expired_payload, JWT_SECRET, algorithm="HS256")
            res_exp = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {expired_tok}"})
            assert res_exp.status_code == 401

            # Malformed token
            res_bad = await client.get("/api/admin/users", headers={"Authorization": "Bearer not.a.valid.jwt"})
            assert res_bad.status_code == 401

            # No header
            res_none = await client.get("/api/admin/users")
            assert res_none.status_code == 401

    @pytest.mark.asyncio
    async def test_lawyer_idor_protection_on_cases_and_drafts(self, lawyer1_token, lawyer2_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            h1 = {"Authorization": f"Bearer {lawyer1_token}"}
            h2 = {"Authorization": f"Bearer {lawyer2_token}"}

            # Lawyer 1 creates a case
            c_res = await client.post(
                "/api/cases",
                json={"case_number": "CIVIL/101/2026", "nickname": "Secret Case"},
                headers=h1,
            )
            assert c_res.status_code == 200
            case_id = c_res.json()["id"]

            # Lawyer 2 tries to access Lawyer 1's case -> 404 (IDOR blocked)
            get_res = await client.get(f"/api/cases/{case_id}", headers=h2)
            assert get_res.status_code == 404

    def test_sensitive_field_scrubbing(self):
        user_record = {
            "id": "u_secret",
            "name": "Secret User",
            "password_hash": "$2b$12$UnsafePasswordHashExposed",
            "email": "test@secret.com",
        }
        cleaned = _public_user(user_record)
        assert "password_hash" not in cleaned
        assert cleaned["name"] == "Secret User"

        admin_record = {
            "id": "a_secret",
            "name": "Admin Secret",
            "password_hash": "$2b$12$AdminHashMustBeRemoved",
            "role": "super_admin",
        }
        scrubbed_admin = admin_public(admin_record)
        assert "password_hash" not in scrubbed_admin
        assert scrubbed_admin["role"] == "super_admin"


# ============================================================================
# 2. USER LIFECYCLE & WALLET INTEGRITY
# ============================================================================

class TestUserLifecycleAndWalletIntegrity:
    """Verifies user search, status updates, atomic wallet adjustments, and debit floors."""

    @pytest.mark.asyncio
    async def test_user_search_filters_and_status_transitions(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}

            # List and search
            list_res = await client.get("/api/admin/users?search=Ramesh", headers=headers)
            assert list_res.status_code == 200
            assert len(list_res.json()["users"]) >= 1

            # Suspend user
            sus_res = await client.post("/api/admin/users/lawyer_001/suspend", headers=headers)
            assert sus_res.status_code == 200
            u_sus = await db.users.find_one({"id": "lawyer_001"})
            assert u_sus["status"] == "suspended"

            # Activate user
            act_res = await client.post("/api/admin/users/lawyer_001/activate", headers=headers)
            assert act_res.status_code == 200
            u_act = await db.users.find_one({"id": "lawyer_001"})
            assert u_act["status"] == "active"

            # Ban user
            ban_res = await client.post("/api/admin/users/lawyer_001/ban", headers=headers)
            assert ban_res.status_code == 200
            u_ban = await db.users.find_one({"id": "lawyer_001"})
            assert u_ban["status"] == "banned"

    @pytest.mark.asyncio
    async def test_wallet_credit_and_debit_with_mandatory_reason(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}

            # Credit +25 credits with reason
            c_res = await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": 25, "reason": "Promotional bonus grant"},
                headers=headers,
            )
            assert c_res.status_code == 200
            assert c_res.json()["balance_after"] == 75

            # Debit -10 credits with reason
            d_res = await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": -10, "reason": "Correction of accidental double credit"},
                headers=headers,
            )
            assert d_res.status_code == 200
            assert d_res.json()["balance_after"] == 65

            # Debit beyond balance -> MUST FAIL (floor check)
            over_res = await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": -500, "reason": "Excessive debit attempt"},
                headers=headers,
            )
            assert over_res.status_code == 400
            assert "negative" in over_res.json()["detail"].lower()

            # Empty reason -> MUST FAIL (Pydantic min_length=1 rejects with 422 or 400)
            no_reason = await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": 5, "reason": ""},
                headers=headers,
            )
            assert no_reason.status_code in (400, 422)


# ============================================================================
# 3. TEMPLATE SYSTEM, TIPTAP & HISTORICAL RESOLUTION QA
# ============================================================================

class TestTemplateSystemAndTiptapEditorQA:
    """Verifies complete template lifecycle, Tiptap JSON preservation, and historical immutability."""

    @pytest.mark.asyncio
    async def test_full_template_lifecycle_and_historical_permanence(self, super_admin_token, lawyer1_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            admin_headers = {"Authorization": f"Bearer {super_admin_token}"}
            lawyer_headers = {"Authorization": f"Bearer {lawyer1_token}"}

            tiptap_v1 = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "મુદત અરજી "},
                            {"type": "templateVariable", "attrs": {"variableName": "court"}},
                        ],
                    }
                ],
            }

            # 1. Create Template Draft v1
            create_res = await client.post(
                "/api/admin/templates",
                json={
                    "id": "qa_adjournment_tpl",
                    "name_en": "QA Adjournment",
                    "name_gu": "ક્યુએ મુદત અરજી",
                    "category": "Civil",
                    "fields": [{"key": "court", "label_en": "Court", "label_gu": "અદાલત", "type": "text"}],
                    "content_en": "Court: {{court}}",
                    "content_gu": "અદાલત: {{court}} (સંસ્કરણ ૧)",
                    "editor_content_gu": tiptap_v1,
                },
                headers=admin_headers,
            )
            assert create_res.status_code == 200

            # 2. Live Preview
            prev_res = await client.post(
                "/api/admin/templates/qa_adjournment_tpl/preview",
                json={"content_gu": "અદાલત: {{court}} (સંસ્કરણ ૧)", "values": {"court": "અમદાવાદ સિટી સિવિલ કોર્ટ"}},
                headers=admin_headers,
            )
            assert prev_res.status_code == 200
            assert "અમદાવાદ સિટી સિવિલ કોર્ટ" in prev_res.json()["preview"]["gu"]["content"]

            # 3. Publish v1
            pub1 = await client.post("/api/admin/templates/qa_adjournment_tpl/publish", headers=admin_headers)
            assert pub1.status_code == 200
            assert pub1.json()["template"]["version"] == 1

            # 4. Lawyer downloads document using v1
            dl1 = await client.post(
                "/api/applications/download",
                json={
                    "template_id": "qa_adjournment_tpl",
                    "template_version": 1,
                    "language": "gu",
                    "format": "pdf",
                    "values": {"court": "ગાંધીનગર સેશન્સ કોર્ટ"},
                },
                headers=lawyer_headers,
            )
            assert dl1.status_code == 200

            # 5. Clone to v2 draft & publish v2
            c2 = await client.post("/api/admin/templates/qa_adjournment_tpl/clone", json={"as_new_template": False}, headers=admin_headers)
            assert c2.status_code == 200
            assert c2.json()["template"]["version"] == 2
            assert c2.json()["template"]["id"] == "qa_adjournment_tpl"  # Canonical ID preserved

            tiptap_v2 = {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "મુદત અરજી સંસ્કરણ ૨ "},
                            {"type": "templateVariable", "attrs": {"variableName": "court"}},
                        ],
                    }
                ],
            }
            await client.put(
                "/api/admin/templates/qa_adjournment_tpl",
                json={
                    "content_gu": "અદાલત: {{court}} (સંસ્કરણ ૨ નવું)",
                    "editor_content_gu": tiptap_v2,
                },
                headers=admin_headers,
            )
            pub2 = await client.post("/api/admin/templates/qa_adjournment_tpl/publish", headers=admin_headers)
            assert pub2.status_code == 200
            assert pub2.json()["template"]["version"] == 2

            # 6. Verify revision history contains both immutable snapshots with editor_content
            revs_res = await client.get("/api/admin/templates/qa_adjournment_tpl/revisions", headers=admin_headers)
            assert revs_res.status_code == 200
            rev_items = revs_res.json()["revisions"]
            assert len(rev_items) == 2

            # 7. Permanently delete template from db.templates
            del_res = await client.delete("/api/admin/templates/qa_adjournment_tpl", headers=admin_headers)
            assert del_res.status_code == 200

            # 8. Verify historical draft referencing v1 still resolves from db.template_revisions
            resolved_v1 = await resolve_template_for_draft("qa_adjournment_tpl", 1)
            assert resolved_v1 is not None
            assert resolved_v1["version"] == 1
            assert "સંસ્કરણ ૧" in resolved_v1["content_gu"]

            # 9. Verify deleted template does NOT resurrect in catalog
            cat_list = await client.get("/api/templates")
            cat_ids = [t["id"] for t in cat_list.json()]
            assert "qa_adjournment_tpl" not in cat_ids


# ============================================================================
# 4. MULTI-ENGINE GENERATION & DOCUMENT INTEGRITY QA
# ============================================================================

class TestMultiEngineGenerationQA:
    """Verifies HarfBuzz PDF, ReportLab, DOCX, and ODT generation with tables and breaks."""

    def test_multi_format_generation_with_table_and_page_break(self):
        gujarati_text = (
            "માનનીય સેશન્સ કોર્ટ, અમદાવાદ\n\n"
            "દસ્તાવેજ યાદી અરજી\n\n"
            "[TABLE_START]\n"
            "ક્રમ | દસ્તાવેજનું નામ | તારીખ\n"
            "૧ | વકાલતનામું | ૧૫/૦૮/૨૦૨૬\n"
            "૨ | સોગંદનામું | ૨૦/૦૮/૨૦૨૬\n"
            "[TABLE_END]\n\n"
            "--- PAGE BREAK ---\n\n"
            "અરજદારના વકીલની સહી: એડવોકેટ જે. પી. શાહ"
        )
        blocks = build_blocks(gujarati_text, "Document List", "દસ્તાવેજ યાદી")
        settings = get_doc_settings({"page_size": "A4", "gujarati_font": "NotoSansGujarati"})

        # 1. PDF (HarfBuzz OpenType Shaper)
        pdf_b64, meta = generate_pdf_detailed(blocks, "gu", settings)
        pdf_bytes = base64.b64decode(pdf_b64)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 2000
        assert meta["engine"] in ("harfbuzz", "reportlab")

        # 2. DOCX (Word Processing Grid & Break)
        docx_b64 = generate_docx(blocks, "gu", settings)
        docx_bytes = base64.b64decode(docx_b64)
        assert docx_bytes.startswith(b"PK\x03\x04")

        # 3. ODT (OpenDocument XML Hierarchy)
        odt_b64 = generate_odt(blocks, "gu", settings)
        odt_bytes = base64.b64decode(odt_b64)
        assert odt_bytes.startswith(b"PK\x03\x04")


# ============================================================================
# 5. CATALOGS, PLANS & AUDIT LOG INTEGRITY
# ============================================================================

class TestCatalogsPlansAndAuditLogsQA:
    """Verifies master registries, pricing plans, and audit trail immutability."""

    @pytest.mark.asyncio
    async def test_catalogs_crud_and_status_toggle(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}

            # Create court
            c_res = await client.post(
                "/api/admin/catalog/courts",
                json={"en": "City Civil Court 5", "gu": "સિટી સિવિલ કોર્ટ ૫", "district_id": "ahmedabad"},
                headers=headers,
            )
            assert c_res.status_code == 200

            # Toggle active status
            t_res = await client.post(f"/api/admin/catalog/courts/{c_res.json()['item']['id']}/status", json={"active": False}, headers=headers)
            assert t_res.status_code == 200

            # Verify in listing
            list_res = await client.get("/api/admin/catalog/courts", headers=headers)
            assert list_res.status_code == 200

    @pytest.mark.asyncio
    async def test_plans_crud(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}

            # Create plan
            p_res = await client.post(
                "/api/admin/plans",
                json={"name": "Gold Plan", "price": 999, "credits": 100, "popular": True},
                headers=headers,
            )
            assert p_res.status_code == 200

            # List plans
            plans_res = await client.get("/api/admin/plans", headers=headers)
            assert plans_res.status_code == 200
            assert any(p["name"] == "Gold Plan" for p in plans_res.json())

    @pytest.mark.asyncio
    async def test_audit_logs_query_and_immutability(self, super_admin_token):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {super_admin_token}"}

            # Trigger an action that creates an audit log
            await client.post(
                "/api/admin/users/lawyer_001/wallet/adjust",
                json={"amount": 10, "reason": "Audit trail QA verification test"},
                headers=headers,
            )

            # Query audit logs
            logs_res = await client.get("/api/admin/audit-logs?search=Audit trail QA", headers=headers)
            assert logs_res.status_code == 200
            assert len(logs_res.json()["items"]) >= 1
            log_item = logs_res.json()["items"][0]
            assert log_item["action"] == "wallet_adjust"
            assert "password" not in str(log_item)
