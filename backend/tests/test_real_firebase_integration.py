"""NyaySetu Pro — Step 5: Real Cloud Firebase Integration Test Suite.

Tests the full FastAPI backend stack against the live Cloud Firestore
instance (`nyaysetu-pro`) without mocking database operations.
"""

import asyncio
import io
import json
import os
import sys
import uuid
import pytest
import httpx
from datetime import datetime, timezone

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
from google.cloud import firestore

# Real Firestore test fixture
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def real_fs_client():
    """Verify that server.db is connected to the real Cloud Firestore, not the emulator."""
    assert server.db is not None, "server.db is None — credentials not initialized"
    assert "FIRESTORE_EMULATOR_HOST" not in os.environ or not os.environ["FIRESTORE_EMULATOR_HOST"], (
        "FIRESTORE_EMULATOR_HOST is set! Tests must run against Real Cloud Firestore."
    )
    return server.db

@pytest.fixture(scope="session")
async def async_client():
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

# Helper to create a test lawyer
async def create_test_lawyer(prefix="test_lawyer"):
    unique_id = uuid.uuid4().hex[:8]
    phone = f"9898{unique_id[:6]}"
    lawyer_id = f"lawyer_{unique_id}"
    token = server.create_access_token({"sub": lawyer_id, "phone": phone, "role": "advocate"})
    doc = {
        "id": lawyer_id,
        "phone": phone,
        "full_name": f"Advocate {prefix}",
        "bar_council_number": f"G/{unique_id[:4]}/2024",
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    }
    await server.db.collection("lawyers").document(lawyer_id).set(doc)
    # Also initialize wallet
    await server.db.collection("wallets").document(lawyer_id).set({
        "id": lawyer_id,
        "lawyer_id": lawyer_id,
        "balance": 50,
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    })
    return lawyer_id, token, phone

# ============================================================
# 1. AUTHENTICATION INTEGRATION TESTS
# ============================================================
@pytest.mark.asyncio
async def test_auth_token_issuance_and_profile(async_client, real_fs_client):
    lawyer_id, token, phone = await create_test_lawyer("auth_test")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = await async_client.get("/api/auth/me", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["id"] == lawyer_id
        assert data["phone"] == phone
    finally:
        await real_fs_client.collection("lawyers").document(lawyer_id).delete()
        await real_fs_client.collection("wallets").document(lawyer_id).delete()

@pytest.mark.asyncio
async def test_auth_unauthorized_access(async_client):
    res = await async_client.get("/api/auth/me")
    assert res.status_code == 401

# ============================================================
# 2. MASTER DATA CATALOG TESTS (FROM REAL FIRESTORE)
# ============================================================
@pytest.mark.asyncio
async def test_master_data_districts(real_fs_client):
    docs = [d async for d in real_fs_client.collection("districts").stream()]
    assert len(docs) == 34, f"Expected 34 districts in real Firestore, got {len(docs)}"

@pytest.mark.asyncio
async def test_master_data_talukas(real_fs_client):
    docs = [d async for d in real_fs_client.collection("talukas").stream()]
    assert len(docs) == 255, f"Expected 255 talukas in real Firestore, got {len(docs)}"

@pytest.mark.asyncio
async def test_master_data_courts(real_fs_client):
    docs = [d async for d in real_fs_client.collection("courts").stream()]
    assert len(docs) == 47, f"Expected 47 courts in real Firestore, got {len(docs)}"

@pytest.mark.asyncio
async def test_master_data_case_types(real_fs_client):
    docs = [d async for d in real_fs_client.collection("case_types").stream()]
    assert len(docs) == 23, f"Expected 23 case types in real Firestore, got {len(docs)}"

# ============================================================
# 3. TEMPLATES CATALOG & REVISION SNAPSHOTS
# ============================================================
@pytest.mark.asyncio
async def test_templates_catalog_count(real_fs_client):
    docs = [d async for d in real_fs_client.collection("templates").stream()]
    assert len(docs) == 45, f"Expected 45 templates in real Firestore, got {len(docs)}"

@pytest.mark.asyncio
async def test_all_21_canonical_templates_retrieval(real_fs_client):
    CANONICAL_21 = [
        "aanke_padvani_arji", "certified_report", "dd_karavani_arji",
        "document_return", "document_on_record", "closing_purshish",
        "hazari_mafi_arji", "fs_haq_bandh", "fs_haq_khol",
        "jamin_bond", "kam_board", "mudat_arji", "saaxi_summons",
        "samadhan_purshish", "ulat_tapas_bandh", "ulat_tapas_khol",
        "undertaking", "vakilatnama_civil", "vakilatnama_criminal",
        "warrant_hathbido", "warrant_rad"
    ]
    for tid in CANONICAL_21:
        snap = await real_fs_client.collection("templates").document(tid).get()
        assert snap.exists, f"Template '{tid}' missing in real Firestore"
        doc = snap.to_dict()
        assert doc.get("name_gu"), f"Template '{tid}' missing name_gu"
        assert doc.get("name_en"), f"Template '{tid}' missing name_en"
        assert len(doc.get("fields", [])) > 0, f"Template '{tid}' has no fields"

# ============================================================
# 4. CASE MANAGEMENT CRUD & OWNERSHIP ISOLATION
# ============================================================
@pytest.mark.asyncio
async def test_case_crud_and_isolation(async_client, real_fs_client):
    lawyer_a, token_a, _ = await create_test_lawyer("lawyer_a")
    lawyer_b, token_b, _ = await create_test_lawyer("lawyer_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    case_id = None
    try:
        # Create case for Lawyer A
        create_payload = {
            "case_number": "1234/2026",
            "case_type": "Special Civil Suit",
            "court": "Principal Senior Civil Judge",
            "taluka": "Ahmedabad",
            "district": "Ahmedabad",
            "party_name": "Rameshbhai Patel",
            "party_role": "Plaintiff",
            "opposite_party": "Sureshbhai Shah",
            "opposite_party_role": "Defendant",
        }
        res = await async_client.post("/api/cases", json=create_payload, headers=headers_a)
        assert res.status_code == 200, f"Create case failed: {res.text}"
        case_data = res.json()
        case_id = case_data["id"]
        assert case_data["case_number"] == "1234/2026"

        # Read case by Lawyer A
        res = await async_client.get(f"/api/cases/{case_id}", headers=headers_a)
        assert res.status_code == 200
        assert res.json()["id"] == case_id

        # Read case by Lawyer B -> MUST BE 404 (Tenancy isolation)
        res_b = await async_client.get(f"/api/cases/{case_id}", headers=headers_b)
        assert res_b.status_code == 404, f"IDOR Vulnerability: Lawyer B accessed Lawyer A case! Status={res_b.status_code}"

        # Update case by Lawyer A
        update_payload = {"party_name": "Rameshbhai J. Patel"}
        res_update = await async_client.put(f"/api/cases/{case_id}", json=update_payload, headers=headers_a)
        assert res_update.status_code == 200
        assert res_update.json()["party_name"] == "Rameshbhai J. Patel"

        # Delete case by Lawyer A
        res_del = await async_client.delete(f"/api/cases/{case_id}", headers=headers_a)
        assert res_del.status_code == 200
        case_id = None  # deleted
    finally:
        if case_id:
            await real_fs_client.collection("cases").document(case_id).delete()
        await real_fs_client.collection("lawyers").document(lawyer_a).delete()
        await real_fs_client.collection("wallets").document(lawyer_a).delete()
        await real_fs_client.collection("lawyers").document(lawyer_b).delete()
        await real_fs_client.collection("wallets").document(lawyer_b).delete()

# ============================================================
# 5. APPLICATION FLOW & AUTO-FILL
# ============================================================
@pytest.mark.asyncio
async def test_application_create_and_case_autofill(async_client, real_fs_client):
    lawyer_id, token, _ = await create_test_lawyer("app_test")
    headers = {"Authorization": f"Bearer {token}"}
    case_id = None
    app_id = None

    try:
        # Create parent case
        case_payload = {
            "case_number": "999/2026",
            "case_type": "Regular Civil Suit",
            "court": "Senior Civil Court",
            "taluka": "Surat",
            "district": "Surat",
            "party_name": "Hareshbhai",
            "party_role": "Plaintiff",
            "opposite_party": "Dineshbhai",
            "opposite_party_role": "Defendant",
        }
        res_case = await async_client.post("/api/cases", json=case_payload, headers=headers)
        assert res_case.status_code == 200
        case_id = res_case.json()["id"]

        # Create Mudat Arji application linked to case
        app_payload = {
            "template_id": "mudat_arji",
            "case_id": case_id,
            "field_values": {
                "advocate_side": "party",
                "mudat_reason": "Advocate is arguing in High Court",
                "next_date": "2026-09-25",
                "date": "2026-09-06",
            },
        }
        res_app = await async_client.post("/api/applications", json=app_payload, headers=headers)
        assert res_app.status_code == 200, f"App creation failed: {res_app.text}"
        app_data = res_app.json()
        app_id = app_data["id"]
        assert app_data["template_id"] == "mudat_arji"
        assert app_data["case_id"] == case_id

        # Verify application retrieval
        res_get = await async_client.get(f"/api/applications/{app_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["id"] == app_id
    finally:
        if app_id:
            await real_fs_client.collection("applications").document(app_id).delete()
        if case_id:
            await real_fs_client.collection("cases").document(case_id).delete()
        await real_fs_client.collection("lawyers").document(lawyer_id).delete()
        await real_fs_client.collection("wallets").document(lawyer_id).delete()

# ============================================================
# 6. DOCUMENT GENERATION & GUJARATI RENDERING ON REAL DATA
# ============================================================
@pytest.mark.asyncio
async def test_document_generation_mudat_arji_pdf_and_image(async_client, real_fs_client):
    lawyer_id, token, _ = await create_test_lawyer("doc_test")
    headers = {"Authorization": f"Bearer {token}"}
    case_id = None
    app_id = None

    try:
        case_payload = {
            "case_number": "456/2026",
            "case_type": "Special Civil Suit",
            "court": "Principal Civil Court",
            "taluka": "Rajkot",
            "district": "Rajkot",
            "party_name": "કાંતિલાલ મહેતા",
            "party_role": "Plaintiff",
            "opposite_party": "વિજયભાઈ સોની",
            "opposite_party_role": "Defendant",
        }
        res_case = await async_client.post("/api/cases", json=case_payload, headers=headers)
        case_id = res_case.json()["id"]

        app_payload = {
            "template_id": "mudat_arji",
            "case_id": case_id,
            "field_values": {
                "advocate_side": "party",
                "mudat_reason": "વકીલશ્રીની તબિયત નાદુરસ્ત હોવાથી",
                "next_date": "2026-09-30",
                "date": "2026-09-06",
            },
        }
        res_app = await async_client.post("/api/applications", json=app_payload, headers=headers)
        app_id = res_app.json()["id"]

        # Generate PDF
        res_pdf = await async_client.post(
            f"/api/applications/{app_id}/generate",
            json={"format": "pdf", "language": "gu"},
            headers=headers
        )
        assert res_pdf.status_code == 200, f"PDF generation failed: {res_pdf.text}"
        pdf_bytes = res_pdf.content
        assert len(pdf_bytes) > 500, "Generated PDF is abnormally small"
        assert pdf_bytes.startswith(b"%PDF"), "Output bytes do not start with %PDF header"

        # Generate Image (PNG preview)
        res_img = await async_client.post(
            f"/api/applications/{app_id}/generate",
            json={"format": "png", "language": "gu"},
            headers=headers
        )
        assert res_img.status_code == 200, f"Image generation failed: {res_img.text}"
        assert res_img.headers.get("content-type") == "image/png"
        assert res_img.content.startswith(b"\x89PNG"), "Image bytes do not start with PNG magic"

    finally:
        if app_id:
            await real_fs_client.collection("applications").document(app_id).delete()
        if case_id:
            await real_fs_client.collection("cases").document(case_id).delete()
        await real_fs_client.collection("lawyers").document(lawyer_id).delete()
        await real_fs_client.collection("wallets").document(lawyer_id).delete()

# ============================================================
# 7. SUPER ADMIN AUTHENTICATION & OPERATIONS
# ============================================================
@pytest.mark.asyncio
async def test_super_admin_login(async_client, real_fs_client):
    admin_email = os.environ.get("ADMIN_SEED_EMAIL", "admin@nyaysetu.com")
    admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "")
    assert admin_password, "ADMIN_SEED_PASSWORD not configured in environment"

    login_res = await async_client.post("/api/auth/admin-login", json={
        "email": admin_email,
        "password": admin_password,
    })
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    admin_token = login_res.json().get("access_token")
    assert admin_token, "No access_token returned in admin login response"

    # Verify admin templates retrieval
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = await async_client.get("/api/admin/templates", headers=admin_headers)
    assert res.status_code == 200
    templates_list = res.json()
    assert len(templates_list) >= 45
