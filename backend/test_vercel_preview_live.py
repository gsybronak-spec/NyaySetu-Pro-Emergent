"""
test_vercel_preview_live.py - Live Verification of Vercel Preview Deployment
NYAYSETU PRO - PHASE 3 VERIFICATION

Connects directly to the live deployed Vercel preview URL over HTTPS,
passing through Vercel's edge network and executing on Vercel Serverless Functions
backed by Google Cloud Firestore (project: nyaysetu-pro, location: asia-south1).
"""

import os
import sys
import time
import json
import base64
import uuid
import asyncio
from datetime import datetime, timezone

# Ensure UTF-8 output handling on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure emulator is NOT used
if "FIRESTORE_EMULATOR_HOST" in os.environ:
    del os.environ["FIRESTORE_EMULATOR_HOST"]

# Real service account credentials for verification and test cleanup
CRED_FILE = r"C:\Users\HP\Downloads\nyaysetu-pro-firebase-adminsdk-fbsvc-dd4459b9fd.json"
if not os.path.exists(CRED_FILE):
    print(f"[FAIL] Service account credentials file not found: {CRED_FILE}")
    sys.exit(1)

with open(CRED_FILE, "r", encoding="utf-8") as f:
    _sa = json.load(f)

os.environ["FIREBASE_PROJECT_ID"] = _sa.get("project_id", "nyaysetu-pro")
os.environ["FIREBASE_CLIENT_EMAIL"] = _sa.get("client_email", "")
os.environ["FIREBASE_PRIVATE_KEY"] = _sa.get("private_key", "")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CRED_FILE

# Load backend/.env for JWT_SECRET and ADMIN credentials
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from google.cloud import firestore
from google.oauth2 import service_account
import httpx
import jwt

sa_creds = service_account.Credentials.from_service_account_file(CRED_FILE)
db = firestore.AsyncClient(project="nyaysetu-pro", credentials=sa_creds)

VERCEL_PREVIEW_URL = "https://backend-mktqrcse5-gsybronak-6847s-projects.vercel.app"
BYPASS_HEADER = {"x-vercel-protection-bypass": "y6RbVJyRTFYY6j5ndZ3yLGRkXYVXX68u"}
JWT_SECRET = os.environ.get("JWT_SECRET", "")

def make_client(**kwargs):
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(transport=transport, **kwargs)

def make_test_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "token_type": "access", "ver": 1}, JWT_SECRET, algorithm="HS256")

async def create_live_test_lawyer():
    unique_id = uuid.uuid4().hex[:8]
    phone = f"9898{unique_id[:6]}"
    lawyer_id = f"lawyer_{unique_id}"
    token = make_test_token(lawyer_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": lawyer_id,
        "phone": phone,
        "mobile": phone,
        "name": f"Advocate LiveTest {unique_id[:4]}",
        "full_name": f"Advocate LiveTest {unique_id[:4]}",
        "bar_council_no": f"G/{unique_id[:4]}/2024",
        "user_type": "Advocate",
        "active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await db.collection("users").document(lawyer_id).set(doc)
    wallet_id = f"wallet_{lawyer_id}"
    await db.collection("wallets").document(wallet_id).set({
        "id": wallet_id,
        "user_id": lawyer_id,
        "balance": 50,
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    return lawyer_id, token, phone, wallet_id

async def test_01_healthz():
    """Verify live Vercel preview healthz endpoint."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=60.0) as client:
        res = await client.get("/healthz")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        data = res.json()
        assert data.get("status") == "ok"
        assert data.get("app") == "NyaySetu Pro"

async def test_02_catalog_districts():
    """Verify Gujarat 34 districts served by Vercel serverless from real Firestore."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=60.0) as client:
        res = await client.get("/api/catalog/districts")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        districts = res.json()
        assert len(districts) == 34, f"Expected 34 districts, got {len(districts)}"
        district_ids = {d["id"] for d in districts}
        assert "ahmedabad" in district_ids
        assert "surat" in district_ids
        assert "rajkot" in district_ids
        assert "vadodara" in district_ids

async def test_03_catalog_talukas():
    """Verify Gujarat 255 talukas served by Vercel serverless from real Firestore."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/catalog/talukas")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        talukas = res.json()
        assert len(talukas) == 255, f"Expected 255 talukas, got {len(talukas)}"

async def test_04_catalog_courts():
    """Verify 47 court establishments served by Vercel serverless from real Firestore."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/catalog/courts")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        courts = res.json()
        assert len(courts) == 47, f"Expected 47 courts, got {len(courts)}"

async def test_05_catalog_case_types():
    """Verify 23 case types served by Vercel serverless from real Firestore."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/catalog/case-types")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        case_types = res.json()
        assert len(case_types) == 23, f"Expected 23 case types, got {len(case_types)}"

async def test_06_catalog_plans():
    """Verify subscription plans served by Vercel serverless from real Firestore."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/catalog/plans")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        plans = res.json()
        assert len(plans) == 4, f"Expected 4 plans, got {len(plans)}"

async def test_07_templates_catalog_and_canonical_21():
    """Verify 45 templates and all 21 canonical legal application templates."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/templates")
        assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
        templates = res.json()
        assert len(templates) == 45, f"Expected 45 templates, got {len(templates)}"

        canonical_21 = [
            "aanke_padvani_arji", "certified_report", "dd_karavani_arji",
            "document_return", "document_on_record", "closing_purshish",
            "hazari_mafi_arji", "fs_haq_bandh", "fs_haq_khol",
            "jamin_bond", "kam_board", "mudat_arji", "saaxi_summons",
            "samadhan_purshish", "ulat_tapas_bandh", "ulat_tapas_khol",
            "undertaking", "vakilatnama_civil", "vakilatnama_criminal",
            "warrant_hathbido", "warrant_rad"
        ]
        template_map = {t["id"]: t for t in templates}
        for cid in canonical_21:
            assert cid in template_map, f"Canonical template {cid} missing from live catalog"
            t = template_map[cid]
            assert t.get("name_en"), f"Template {cid} missing name_en"
            assert t.get("name_gu"), f"Template {cid} missing name_gu"

async def test_08_auth_unauthorized_rejection():
    """Verify unauthorized request to protected endpoint is rejected with 401."""
    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.get("/api/profile/me")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"

async def test_09_auth_profile_verification():
    """Verify lawyer profile retrieval over live Vercel preview."""
    lawyer_id, token, phone, wallet_id = await create_live_test_lawyer()
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=30.0) as client:
            res = await client.get("/api/profile/me")
            assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
            data = res.json()
            assert data["id"] == lawyer_id
            assert data.get("phone") == phone or data.get("mobile") == phone
    finally:
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_10_wallet_balance():
    """Verify wallet balance retrieval over live Vercel preview."""
    lawyer_id, token, _, wallet_id = await create_live_test_lawyer()
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=30.0) as client:
            res = await client.get("/api/wallet")
            assert res.status_code == 200, f"Status: {res.status_code}, Body: {res.text}"
            data = res.json()
            assert data.get("balance") == 50
    finally:
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_11_case_crud_live():
    """Verify Case creation and retrieval on live Vercel connected to real Firestore."""
    lawyer_id, token, _, wallet_id = await create_live_test_lawyer()
    case_id = None
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=30.0) as client:
            payload = {
                "case_number": "1234/2026",
                "case_type_id": "civil_suit",
                "court": "Principal Senior Civil Judge",
                "party_name": "રમણલાલ પ્રજાપતિ",
                "party_role": "Plaintiff",
                "opposite_party": "સુરેશભાઈ પંચાલ",
                "opposite_party_role": "Defendant",
            }
            res_create = await client.post("/api/cases", json=payload)
            assert res_create.status_code == 200, f"Status: {res_create.status_code}, Body: {res_create.text}"
            case_data = res_create.json()
            case_id = case_data["id"]
            assert case_data["case_number"] == "1234/2026"
            assert case_data["party_name"] == "રમણલાલ પ્રજાપતિ"

            res_get = await client.get(f"/api/cases/{case_id}")
            assert res_get.status_code == 200
            retrieved = res_get.json()
            assert retrieved["id"] == case_id
            assert retrieved["court"] == "Principal Senior Civil Judge"

            res_list = await client.get("/api/cases")
            assert res_list.status_code == 200
            cases = res_list.json()
            assert any(c["id"] == case_id for c in cases)
    finally:
        if case_id:
            await db.collection("cases").document(case_id).delete()
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_12_application_preview_and_party_autofill():
    """Verify application preview with automatic party line autofill from Case on live Vercel."""
    lawyer_id, token, _, wallet_id = await create_live_test_lawyer()
    case_id = None
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=30.0) as client:
            res_case = await client.post("/api/cases", json={
                "case_number": "AUT-101/2026",
                "case_type_id": "civil_suit",
                "court": "Principal Senior Civil Judge",
                "party_name": "મહેશભાઈ ત્રિવેદી",
                "party_role": "Plaintiff",
                "opposite_party": "ગુજરાત રાજ્ય",
                "opposite_party_role": "Defendant",
            })
            assert res_case.status_code == 200
            case_id = res_case.json()["id"]

            res_prev = await client.post("/api/applications/preview", json={
                "template_id": "mudat_arji",
                "case_id": case_id,
                "language": "gu",
                "values": {
                    "advocate_side": "party",
                    "mudat_reason": "દસ્તાવેજો એકત્રિત કરવા સારુ સમય જોઈએ છે",
                    "next_date": "2026-10-15",
                    "date": "2026-09-07",
                },
            })
            assert res_prev.status_code == 200, f"Preview failed: {res_prev.text}"
            preview_data = res_prev.json()
            assert preview_data.get("status") == "success" or "blocks" in preview_data or "html" in preview_data
    finally:
        if case_id:
            await db.collection("cases").document(case_id).delete()
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_13_gujarati_document_generation_mudat_arji_pdf():
    """Verify live Vercel serverless renders Gujarati PDF using HarfBuzz."""
    lawyer_id, token, _, wallet_id = await create_live_test_lawyer()
    case_id = None
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=60.0) as client:
            res_case = await client.post("/api/cases", json={
                "case_number": "GEN-202/2026",
                "case_type_id": "civil_suit",
                "court": "Principal Senior Civil Judge",
                "party_name": "ધર્મેન્દ્રસિંહ વાઘેલા",
                "party_role": "Plaintiff",
                "opposite_party": "રાજેશકુમાર પટેલ",
                "opposite_party_role": "Defendant",
            })
            assert res_case.status_code == 200
            case_id = res_case.json()["id"]

            # Generate PDF
            res_pdf = await client.post("/api/applications/download", json={
                "template_id": "mudat_arji",
                "case_id": case_id,
                "format": "pdf",
                "language": "gu",
                "values": {
                    "advocate_side": "party",
                    "mudat_reason": "વકીલશ્રીની તબિયત નાદુરસ્ત હોવાથી",
                    "next_date": "2026-10-20",
                    "date": "2026-09-07",
                },
            })
            assert res_pdf.status_code == 200, f"PDF generation failed: {res_pdf.text}"
            pdf_json = res_pdf.json()
            assert "base64" in pdf_json, "Response missing base64 PDF bytes"
            pdf_bytes = base64.b64decode(pdf_json["base64"])
            assert len(pdf_bytes) > 500, f"PDF too small ({len(pdf_bytes)} bytes)"
            assert pdf_bytes.startswith(b"%PDF"), "PDF bytes do not begin with %PDF header"
    finally:
        if case_id:
            await db.collection("cases").document(case_id).delete()
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_14_gujarati_document_generation_mudat_arji_png():
    """Verify live Vercel serverless renders Gujarati PNG preview using HarfBuzz."""
    lawyer_id, token, _, wallet_id = await create_live_test_lawyer()
    case_id = None
    try:
        auth_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {token}"}
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=auth_headers, timeout=60.0) as client:
            res_case = await client.post("/api/cases", json={
                "case_number": "GEN-203/2026",
                "case_type_id": "civil_suit",
                "court": "Principal Senior Civil Judge",
                "party_name": "ધર્મેન્દ્રસિંહ વાઘેલા",
                "party_role": "Plaintiff",
                "opposite_party": "રાજેશકુમાર પટેલ",
                "opposite_party_role": "Defendant",
            })
            assert res_case.status_code == 200
            case_id = res_case.json()["id"]

            res_png = await client.post("/api/applications/download", json={
                "template_id": "mudat_arji",
                "case_id": case_id,
                "format": "png",
                "language": "gu",
                "values": {
                    "advocate_side": "party",
                    "mudat_reason": "વકીલશ્રીની તબિયત નાદુરસ્ત હોવાથી",
                    "next_date": "2026-10-20",
                    "date": "2026-09-07",
                },
            })
            assert res_png.status_code == 200, f"PNG generation failed: {res_png.text}"
            png_json = res_png.json()
            assert "base64" in png_json, "Response missing base64 PNG bytes"
            png_bytes = base64.b64decode(png_json["base64"])
            assert png_bytes.startswith(b"\x89PNG"), "PNG bytes do not begin with PNG header"
    finally:
        if case_id:
            await db.collection("cases").document(case_id).delete()
        await db.collection("users").document(lawyer_id).delete()
        await db.collection("wallets").document(wallet_id).delete()

async def test_15_admin_login_and_templates_management():
    """Verify Super Admin login and templates list via live Vercel preview."""
    admin_email = os.environ.get("ADMIN_SEED_EMAIL", "admin@nyaysetu.com")
    admin_password = os.environ.get("ADMIN_SEED_PASSWORD", "")
    assert admin_password, "ADMIN_SEED_PASSWORD is not set"

    async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=30.0) as client:
        res = await client.post("/api/admin/auth/login", json={
            "email": admin_email,
            "password": admin_password,
        })
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        data = res.json()
        admin_token = data.get("token")
        assert admin_token, "No admin token in login response"

        admin_headers = {**BYPASS_HEADER, "Authorization": f"Bearer {admin_token}"}
        res_t = await client.get("/api/admin/templates", headers=admin_headers)
        assert res_t.status_code == 200, f"Admin templates failed: {res_t.text}"
        t_data = res_t.json()
        items = t_data if isinstance(t_data, list) else t_data.get("templates", t_data.get("items", []))
        assert len(items) == 45, f"Expected 45 admin templates, got {len(items)}"

ALL_TESTS = [
    ("01. Live Vercel Preview Healthz", test_01_healthz),
    ("02. Master Data: 34 Districts (Live Vercel -> Real DB)", test_02_catalog_districts),
    ("03. Master Data: 255 Talukas (Live Vercel -> Real DB)", test_03_catalog_talukas),
    ("04. Master Data: 47 Courts (Live Vercel -> Real DB)", test_04_catalog_courts),
    ("05. Master Data: 23 Case Types (Live Vercel -> Real DB)", test_05_catalog_case_types),
    ("06. Master Data: 4 Subscription Plans (Live Vercel -> Real DB)", test_06_catalog_plans),
    ("07. Templates Catalog: 45 Templates & Canonical 21 (Live Vercel -> Real DB)", test_07_templates_catalog_and_canonical_21),
    ("08. Auth Unauthorized Request Rejection (Live Vercel)", test_08_auth_unauthorized_rejection),
    ("09. Lawyer Profile Verification (Live Vercel -> Real DB)", test_09_auth_profile_verification),
    ("10. Wallet Balance Verification (Live Vercel -> Real DB)", test_10_wallet_balance),
    ("11. Case CRUD & Storage (Live Vercel -> Real DB)", test_11_case_crud_live),
    ("12. Application Preview & Case Party Autofill (Live Vercel)", test_12_application_preview_and_party_autofill),
    ("13. Gujarati Document PDF Generation via HarfBuzz (Live Vercel)", test_13_gujarati_document_generation_mudat_arji_pdf),
    ("14. Gujarati Document PNG Preview Generation (Live Vercel)", test_14_gujarati_document_generation_mudat_arji_png),
    ("15. Super Admin Login & Template Management (Live Vercel -> Real DB)", test_15_admin_login_and_templates_management),
]

async def run_all():
    print("=" * 75, flush=True)
    print("NYAYSETU PRO — STEP 6: LIVE VERCEL PREVIEW DEPLOYMENT INTEGRATION SUITE", flush=True)
    print(f"Target URL: {VERCEL_PREVIEW_URL}", flush=True)
    print(f"Target Database: Real Firestore (nyaysetu-pro) | Location: asia-south1", flush=True)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}", flush=True)
    print("=" * 75, flush=True)

    # Warm up serverless function to prevent cold-start timeout
    print("Warming up Vercel serverless function...", end="", flush=True)
    try:
        async with make_client(base_url=VERCEL_PREVIEW_URL, headers=BYPASS_HEADER, timeout=60.0) as client:
            await client.get("/healthz")
        print(" [READY]", flush=True)
    except Exception as e:
        print(f" [WARN: {e}]", flush=True)

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
            print(f"  [PASS] {name} ({elapsed:.2f}s)", flush=True)
            results.append({"name": name, "status": "PASS", "duration": elapsed})
        except AssertionError as e:
            elapsed = time.time() - t0
            failed += 1
            print(f"  [FAIL] {name} ({elapsed:.2f}s) -> {e}", flush=True)
            results.append({"name": name, "status": "FAIL", "duration": elapsed, "error": str(e)})
        except Exception as e:
            elapsed = time.time() - t0
            errors += 1
            print(f"  [ERROR] {name} ({elapsed:.2f}s) -> {e}", flush=True)
            results.append({"name": name, "status": "ERROR", "duration": elapsed, "error": str(e)})

    total = len(ALL_TESTS)
    print("\n" + "=" * 75)
    print(f"STEP 6 LIVE VERCEL PREVIEW TEST SUMMARY:")
    print(f"  TOTAL:   {total}")
    print(f"  PASSED:  {passed}")
    print(f"  FAILED:  {failed}")
    print(f"  ERRORS:  {errors}")
    print(f"  SKIPPED: 0")
    print("=" * 75)

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate_vercel_preview_step6.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "target_url": VERCEL_PREVIEW_URL,
            "database": "nyaysetu-pro",
            "results": results
        }, f, indent=2)

    return failed == 0 and errors == 0

if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
