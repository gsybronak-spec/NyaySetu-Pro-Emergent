"""NyaySetu Pro — Step 5: Real Cloud Firebase Integration Test Suite.

Tests the full FastAPI backend stack against the live Cloud Firestore
instance (`nyaysetu-pro`) without mocking database operations.
"""

import asyncio
import io
import json
import os
import sys
import time
import uuid
import httpx
from datetime import datetime, timezone

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Verify emulator is NOT used
if "FIRESTORE_EMULATOR_HOST" in os.environ:
    del os.environ["FIRESTORE_EMULATOR_HOST"]

# Ensure templates are enabled
os.environ["TEMPORARILY_DISABLE_ALL_TEMPLATES"] = "false"

import server
from google.cloud import firestore

# Global HTTP test client
transport = httpx.ASGITransport(app=server.app)
http_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

async def create_test_lawyer(prefix="test_lawyer"):
    unique_id = uuid.uuid4().hex[:8]
    phone = f"9898{unique_id[:6]}"
    lawyer_id = f"lawyer_{unique_id}"
    token = server.make_token(lawyer_id)
    doc = {
        "id": lawyer_id,
        "phone": phone,
        "name": f"Advocate {prefix}",
        "full_name": f"Advocate {prefix}",
        "bar_council_number": f"G/{unique_id[:4]}/2024",
        "active": True,
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    }
    await server.db.collection("users").document(lawyer_id).set(doc)
    # Wallet document in wallets collection
    wallet_id = f"wallet_{lawyer_id}"
    await server.db.collection("wallets").document(wallet_id).set({
        "id": wallet_id,
        "user_id": lawyer_id,
        "balance": 50,
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    })
    return lawyer_id, token, phone, wallet_id

# ============================================================
# TEST CASES
# ============================================================

async def test_01_real_firestore_client_connection():
    """Verify backend client is bound to real Cloud Firestore (nyaysetu-pro)."""
    assert server.db is not None, "server.db is None"
    assert "FIRESTORE_EMULATOR_HOST" not in os.environ, "FIRESTORE_EMULATOR_HOST is present in env"
    project = os.environ.get("FIREBASE_PROJECT_ID", "")
    assert project == "nyaysetu-pro", f"Expected project nyaysetu-pro, got {project}"

async def test_02_auth_token_issuance_and_profile():
    """Verify lawyer profile and JWT validation against real Firestore."""
    lawyer_id, token, phone, wallet_id = await create_test_lawyer("auth_test")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = await http_client.get("/api/profile/me", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["id"] == lawyer_id
        assert data["phone"] == phone
    finally:
        await server.db.collection("users").document(lawyer_id).delete()
        await server.db.collection("wallets").document(wallet_id).delete()

async def test_03_auth_unauthorized_access():
    """Verify unauthenticated requests are rejected."""
    res = await http_client.get("/api/profile/me")
    assert res.status_code == 401

async def test_04_master_data_districts():
    """Verify Gujarat's 34 districts in real Firestore."""
    docs = [d async for d in server.db.collection("districts").stream()]
    assert len(docs) == 34, f"Expected 34 districts in real Firestore, got {len(docs)}"

async def test_05_master_data_talukas():
    """Verify Gujarat's 255 talukas in real Firestore."""
    docs = [d async for d in server.db.collection("talukas").stream()]
    assert len(docs) == 255, f"Expected 255 talukas in real Firestore, got {len(docs)}"

async def test_06_master_data_courts():
    """Verify 47 court establishments in real Firestore."""
    docs = [d async for d in server.db.collection("courts").stream()]
    assert len(docs) == 47, f"Expected 47 courts in real Firestore, got {len(docs)}"

async def test_07_master_data_case_types():
    """Verify 23 case types in real Firestore."""
    docs = [d async for d in server.db.collection("case_types").stream()]
    assert len(docs) == 23, f"Expected 23 case types in real Firestore, got {len(docs)}"

async def test_08_templates_catalog_count():
    """Verify total 45 templates exist in real Firestore."""
    docs = [d async for d in server.db.collection("templates").stream()]
    assert len(docs) == 45, f"Expected 45 templates in real Firestore, got {len(docs)}"

async def test_09_all_21_canonical_templates_retrieval():
    """Verify all 21 canonical NyaySetu Pro templates in real Firestore."""
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
        snap = await server.db.collection("templates").document(tid).get()
        assert snap.exists, f"Canonical template '{tid}' missing in real Firestore"
        doc = snap.to_dict()
        assert doc.get("name_gu"), f"Template '{tid}' missing name_gu"
        assert doc.get("name_en"), f"Template '{tid}' missing name_en"
        assert len(doc.get("fields", [])) > 0, f"Template '{tid}' has no fields"

async def test_10_case_crud_and_isolation():
    """Verify Case CRUD and strict tenant isolation on real Firestore."""
    lawyer_a, token_a, _, wallet_a = await create_test_lawyer("lawyer_a")
    lawyer_b, token_b, _, wallet_b = await create_test_lawyer("lawyer_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    case_id = None
    try:
        create_payload = {
            "case_number": "1234/2026",
            "case_type_id": "civil_suit",
            "court": "Principal Senior Civil Judge",
            "party_name": "Rameshbhai Patel",
            "party_role": "Plaintiff",
            "opposite_party": "Sureshbhai Shah",
            "opposite_party_role": "Defendant",
        }
        res = await http_client.post("/api/cases", json=create_payload, headers=headers_a)
        assert res.status_code == 200, f"Create case failed: {res.text}"
        case_data = res.json()
        case_id = case_data["id"]
        assert case_data["case_number"] == "1234/2026"

        res_a = await http_client.get(f"/api/cases/{case_id}", headers=headers_a)
        assert res_a.status_code == 200
        assert res_a.json()["id"] == case_id

        # Tenant isolation check
        res_b = await http_client.get(f"/api/cases/{case_id}", headers=headers_b)
        assert res_b.status_code == 404, f"IDOR Failure: Lawyer B accessed Lawyer A case: {res_b.status_code}"

        # Update case
        update_payload = {"party_name": "Rameshbhai J. Patel"}
        res_update = await http_client.put(f"/api/cases/{case_id}", json=update_payload, headers=headers_a)
        assert res_update.status_code == 200
        assert res_update.json()["party_name"] == "Rameshbhai J. Patel"

        # Delete case
        res_del = await http_client.delete(f"/api/cases/{case_id}", headers=headers_a)
        assert res_del.status_code == 200
        case_id = None
    finally:
        if case_id:
            await server.db.collection("cases").document(case_id).delete()
        await server.db.collection("users").document(lawyer_a).delete()
        await server.db.collection("wallets").document(wallet_a).delete()
        await server.db.collection("users").document(lawyer_b).delete()
        await server.db.collection("wallets").document(wallet_b).delete()

async def test_11_application_preview_and_case_autofill():
    """Verify application preview with case party and court auto-fill."""
    lawyer_id, token, _, wallet_id = await create_test_lawyer("app_test")
    headers = {"Authorization": f"Bearer {token}"}
    case_id = None

    try:
        case_payload = {
            "case_number": "999/2026",
            "case_type_id": "regular_civil_suit",
            "court": "Senior Civil Court Surat",
            "party_name": "હરેશભાઈ પટેલ",
            "party_role": "Plaintiff",
            "opposite_party": "દિનેશભાઈ શાહ",
            "opposite_party_role": "Defendant",
        }
        res_case = await http_client.post("/api/cases", json=case_payload, headers=headers)
        assert res_case.status_code == 200
        case_id = res_case.json()["id"]

        preview_payload = {
            "template_id": "mudat_arji",
            "case_id": case_id,
            "language": "gu",
            "values": {
                "advocate_side": "party",
                "mudat_reason": "વકીલશ્રી હાઇકોર્ટમાં રોકાયેલ હોવાથી",
                "next_date": "2026-09-25",
                "date": "2026-09-06",
            },
        }
        res_preview = await http_client.post("/api/applications/preview", json=preview_payload, headers=headers)
        assert res_preview.status_code == 200, f"Preview failed: {res_preview.text}"
        preview_data = res_preview.json()
        assert "content" in preview_data
        assert "Senior Civil Court Surat" in preview_data["content"] or "હરેશભાઈ પટેલ" in preview_data["content"]
        assert len(preview_data.get("blocks", [])) > 0
    finally:
        if case_id:
            await server.db.collection("cases").document(case_id).delete()
        await server.db.collection("users").document(lawyer_id).delete()
        await server.db.collection("wallets").document(wallet_id).delete()

async def test_12_draft_save_and_retrieve():
    """Verify draft saving and retrieval against real Firestore."""
    lawyer_id, token, _, wallet_id = await create_test_lawyer("draft_test")
    headers = {"Authorization": f"Bearer {token}"}
    draft_id = f"draft_{lawyer_id}_undertaking_none"

    try:
        draft_payload = {
            "template_id": "undertaking",
            "language": "gu",
            "values": {
                "undertaking_details": "બાંહેધરી મુસદ્દો",
                "date": "2026-09-06",
            },
        }
        res_save = await http_client.post("/api/drafts", json=draft_payload, headers=headers)
        assert res_save.status_code == 200, f"Draft save failed: {res_save.text}"

        res_list = await http_client.get("/api/drafts", headers=headers)
        assert res_list.status_code == 200
        drafts = res_list.json()
        assert len(drafts) >= 1
        assert any(d.get("template_id") == "undertaking" for d in drafts)
    finally:
        await server.db.collection("drafts").document(draft_id).delete()
        await server.db.collection("users").document(lawyer_id).delete()
        await server.db.collection("wallets").document(wallet_id).delete()

async def test_13_document_generation_mudat_arji_pdf_and_image():
    """Verify Gujarati PDF and PNG rendering from real Firestore data."""
    lawyer_id, token, _, wallet_id = await create_test_lawyer("doc_test")
    headers = {"Authorization": f"Bearer {token}"}
    case_id = None

    try:
        case_payload = {
            "case_number": "456/2026",
            "case_type_id": "special_civil_suit",
            "court": "Principal Civil Court Rajkot",
            "party_name": "કાંતિલાલ મહેતા",
            "party_role": "Plaintiff",
            "opposite_party": "વિજયભાઈ સોની",
            "opposite_party_role": "Defendant",
        }
        res_case = await http_client.post("/api/cases", json=case_payload, headers=headers)
        case_id = res_case.json()["id"]

        download_payload = {
            "template_id": "mudat_arji",
            "case_id": case_id,
            "format": "pdf",
            "language": "gu",
            "values": {
                "advocate_side": "party",
                "mudat_reason": "વકીલશ્રીની તબિયત નાદુરસ્ત હોવાથી",
                "next_date": "2026-09-30",
                "date": "2026-09-06",
            },
        }

        # PDF generation
        res_pdf = await http_client.post(
            "/api/applications/download",
            json=download_payload,
            headers=headers
        )
        assert res_pdf.status_code == 200, f"PDF generation failed: {res_pdf.text}"
        pdf_data = res_pdf.json()
        assert "base64" in pdf_data, "Response missing base64 key"
        import base64
        pdf_bytes = base64.b64decode(pdf_data["base64"])
        assert len(pdf_bytes) > 500, "Generated PDF is abnormally small"
        assert pdf_bytes.startswith(b"%PDF"), "Output bytes do not start with %PDF header"

        # Image generation (PNG preview)
        download_payload["format"] = "png"
        res_img = await http_client.post(
            "/api/applications/download",
            json=download_payload,
            headers=headers
        )
        assert res_img.status_code == 200, f"Image generation failed: {res_img.text}"
        img_data = res_img.json()
        assert "base64" in img_data, "Image response missing base64 key"
        img_bytes = base64.b64decode(img_data["base64"])
        assert img_bytes.startswith(b"\x89PNG"), "Image bytes do not start with PNG header"

        # Repeat generation (verify no font corruption or state leaks)
        download_payload["format"] = "pdf"
        res_pdf2 = await http_client.post(
            "/api/applications/download",
            json=download_payload,
            headers=headers
        )
        assert res_pdf2.status_code == 200
        pdf_bytes2 = base64.b64decode(res_pdf2.json()["base64"])
        assert pdf_bytes2.startswith(b"%PDF")

    finally:
        if case_id:
            await server.db.collection("cases").document(case_id).delete()
        await server.db.collection("users").document(lawyer_id).delete()
        await server.db.collection("wallets").document(wallet_id).delete()

async def test_14_super_admin_login():
    """Verify super admin login and template management access."""
    admin_email = os.environ.get("ADMIN_SEED_EMAIL", "admin@nyaysetu.com")
    admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "")
    assert admin_password, "ADMIN_SEED_PASSWORD not configured"

    login_res = await http_client.post("/api/admin/auth/login", json={
        "email": admin_email,
        "password": admin_password,
    })
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    data = login_res.json()
    admin_token = data.get("token")
    assert admin_token, "No token returned in admin login response"

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res = await http_client.get("/api/admin/templates", headers=admin_headers)
    assert res.status_code == 200
    res_data = res.json()
    items = res_data if isinstance(res_data, list) else res_data.get("templates", res_data.get("items", []))
    assert len(items) >= 45

async def test_15_wallet_balance_and_transaction():
    """Verify wallet creation and balance check against real Firestore."""
    lawyer_id, token, _, wallet_id = await create_test_lawyer("wallet_test")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = await http_client.get("/api/wallet", headers=headers)
        assert res.status_code == 200, f"Wallet retrieval failed: {res.text}"
        data = res.json()
        assert data["balance"] == 50
    finally:
        await server.db.collection("users").document(lawyer_id).delete()
        await server.db.collection("wallets").document(wallet_id).delete()

# ============================================================
# RUNNER
# ============================================================

ALL_TESTS = [
    ("01. Real Firestore Client Connection", test_01_real_firestore_client_connection),
    ("02. Auth Token Issuance & Profile (Real DB)", test_02_auth_token_issuance_and_profile),
    ("03. Auth Unauthorized Rejection", test_03_auth_unauthorized_access),
    ("04. Master Data: 34 Districts (Real DB)", test_04_master_data_districts),
    ("05. Master Data: 255 Talukas (Real DB)", test_05_master_data_talukas),
    ("06. Master Data: 47 Courts (Real DB)", test_06_master_data_courts),
    ("07. Master Data: 23 Case Types (Real DB)", test_07_master_data_case_types),
    ("08. Templates Catalog: 45 Templates (Real DB)", test_08_templates_catalog_count),
    ("09. All 21 Canonical Templates Retrieval (Real DB)", test_09_all_21_canonical_templates_retrieval),
    ("10. Case CRUD & Tenancy Isolation (Real DB)", test_10_case_crud_and_isolation),
    ("11. Application Preview & Case Autofill (Real DB)", test_11_application_preview_and_case_autofill),
    ("12. Draft Save & Retrieve (Real DB)", test_12_draft_save_and_retrieve),
    ("13. Document Generation PDF & PNG Rendering (Real DB)", test_13_document_generation_mudat_arji_pdf_and_image),
    ("14. Super Admin Login & Authorization (Real DB)", test_14_super_admin_login),
    ("15. Wallet Balance & Transactions (Real DB)", test_15_wallet_balance_and_transaction),
]

async def run_all():
    print("=" * 70)
    print("NYAYSETU PRO — STEP 5: REAL CLOUD FIREBASE INTEGRATION TEST SUITE")
    print(f"Target Database: Real Firestore (nyaysetu-pro) | Location: asia-south1")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    passed = 0
    failed = 0
    errors = 0
    results = []

    for name, test_fn in ALL_TESTS:
        t0 = time.time()
        try:
            await test_fn()
            elapsed = time.time() - t0
            passed += 1
            print(f"  [PASS] {name} ({elapsed:.2f}s)")
            results.append({"name": name, "status": "PASS", "duration": elapsed})
        except AssertionError as e:
            elapsed = time.time() - t0
            failed += 1
            print(f"  [FAIL] {name} ({elapsed:.2f}s) -> {e}")
            results.append({"name": name, "status": "FAIL", "duration": elapsed, "error": str(e)})
        except Exception as e:
            elapsed = time.time() - t0
            errors += 1
            print(f"  [ERROR] {name} ({elapsed:.2f}s) -> {e}")
            results.append({"name": name, "status": "ERROR", "duration": elapsed, "error": str(e)})

    total = len(ALL_TESTS)
    print("\n" + "=" * 70)
    print(f"STEP 5 REAL FIREBASE TEST SUMMARY:")
    print(f"  TOTAL:   {total}")
    print(f"  PASSED:  {passed}")
    print(f"  FAILED:  {failed}")
    print(f"  ERRORS:  {errors}")
    print(f"  SKIPPED: 0")
    print("=" * 70)

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_real_firebase_step5.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": 0,
            "target": "nyaysetu-pro",
            "results": results
        }, f, indent=2)

    return failed == 0 and errors == 0

if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
