import os
import sys
import asyncio
import uuid
import pytest
import pytest_asyncio
from google.cloud import firestore

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Force Firestore Emulator usage
os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
os.environ["FIREBASE_PROJECT_ID"] = "demo-test"
os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-characters-long!"
os.environ["ADMIN_SEED_EMAIL"] = "admin@test.com"
os.environ["ADMIN_SEED_PASSWORD"] = "TestAdmin123!"

import server



class FirestoreClientProxy:
    """Native Firestore AsyncClient proxy that provides a client bound to the current running event loop.
    Prevents gRPC 'Event loop is closed' or 'attached to different loop' errors across pytest tests and threads.
    """
    def __init__(self, project_id="demo-test", credentials=None):
        self._project_id = project_id
        self._credentials = credentials
        self._clients = {}

    def _get_client(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop not in self._clients:
            self._clients[loop] = firestore.AsyncClient(
                project=self._project_id,
                credentials=self._credentials
            )
        return self._clients[loop]

    def collection(self, name):
        col = self._get_client().collection(name)
        class _ColWrapper:
            def __init__(self, c):
                self._c = c
            def document(self, doc_id=""):
                if not doc_id:
                    doc_id = "empty_id_doc"
                return self._c.document(doc_id)
            def __getattr__(self, attr):
                return getattr(self._c, attr)
        return _ColWrapper(col)

    def batch(self):
        return self._get_client().batch()

    def __getattr__(self, name):
        try:
            return getattr(self._get_client(), name)
        except AttributeError:
            from tests.firestore_test_utils import _FirestoreCollectionProxy
            return _FirestoreCollectionProxy(self, name)

    def __getitem__(self, name):
        from tests.firestore_test_utils import _FirestoreCollectionProxy
        return _FirestoreCollectionProxy(self, name)

from google.auth.credentials import AnonymousCredentials
_global_firestore_proxy = FirestoreClientProxy("demo-test", AnonymousCredentials())
server.db = _global_firestore_proxy

async def _async_init_db():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            await http.delete("http://127.0.0.1:8080/emulator/v1/projects/demo-test/databases/(default)/documents")
    except Exception as e:
        print(f"Failed to clear emulator database: {e}")

    client = _global_firestore_proxy._get_client()
    try:
        import test_seed_data
        import test_seed_data_templates_v2
        
        async def _seed_collection(coll_name, items):
            batch = client.batch()
            count = 0
            for item in items:
                item_copy = dict(item)
                if coll_name == "templates":
                    item_copy.setdefault("status", "published")
                    item_copy.setdefault("version", 1)
                doc_id = item_copy.get("id", str(uuid.uuid4()))
                ref = client.collection(coll_name).document(doc_id)
                batch.set(ref, item_copy)
                count += 1
                if count == 500:
                    await batch.commit()
                    batch = client.batch()
                    count = 0
            if count > 0:
                await batch.commit()
                
        await _seed_collection("templates", test_seed_data.TEMPLATES)
        await _seed_collection("templates", test_seed_data_templates_v2.TEMPLATES_V2)
        await _seed_collection("case_types", test_seed_data.CASE_TYPES)
        await _seed_collection("laws", test_seed_data.LAWS)
        await _seed_collection("districts", test_seed_data.DISTRICTS)
        await _seed_collection("talukas", test_seed_data.TALUKAS)
        await _seed_collection("courts", test_seed_data.COURTS)
        await _seed_collection("police_stations", test_seed_data.POLICE_STATIONS)
        if hasattr(test_seed_data, "PLANS"):
            await _seed_collection("plans", test_seed_data.PLANS)
            
        test_admins = [
            {
                "id": "admin_super_1",
                "email": "superadmin@nyaysetu.gov.in",
                "name": "Super Admin",
                "role": "super_admin",
                "active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "staff_admin_1",
                "email": "staff@nyaysetu.gov.in",
                "name": "Staff Admin",
                "role": "admin",
                "active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "admin_staff_1",
                "email": "staff@nyaysetu.gov.in",
                "name": "Staff Admin",
                "role": "admin",
                "active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "sa_001",
                "email": "superadmin@nyaysetu.gov.in",
                "name": "Super Admin QA",
                "role": "super_admin",
                "active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "staff_001",
                "email": "staff@nyaysetu.gov.in",
                "name": "Staff Admin QA",
                "role": "admin",
                "active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ]
        await _seed_collection("admin_users", test_admins)
        test_users = [
            {
                "id": "lawyer_regular_1",
                "mobile": "9876543210",
                "email": "lawyer@test.com",
                "name": "Regular Lawyer",
                "role": "lawyer",
                "active": True,
                "credits": 100,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "lawyer_001",
                "mobile": "9876543210",
                "email": "lawyer1@test.com",
                "name": "Adv. Ramesh Patel",
                "role": "lawyer",
                "active": True,
                "credits": 50,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": "lawyer_002",
                "mobile": "9876543211",
                "email": "lawyer2@test.com",
                "name": "Lawyer 2 QA",
                "role": "lawyer",
                "active": True,
                "credits": 100,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ]
        await _seed_collection("users", test_users)
        await _seed_collection("wallets", [
            {"id": "wallet_lawyer_regular_1", "user_id": "lawyer_regular_1", "balance": 100},
            {"id": "wallet_lawyer_001", "user_id": "lawyer_001", "balance": 50},
            {"id": "wallet_lawyer_002", "user_id": "lawyer_002", "balance": 100},
        ])
    except Exception as e:
        print(f"Error seeding test data: {e}")

@pytest.fixture(scope="session", autouse=True)
def initialize_emulator_database():
    """Wipes emulator once at test session start and seeds baseline catalogs."""
    import asyncio
    asyncio.run(_async_init_db())

@pytest_asyncio.fixture(autouse=True)
async def ensure_baseline_templates(request):
    """Ensures templates and baseline auth exist for tests that need them."""
    import server
    server._rate_buckets.clear()
    node_id = getattr(request.node, "nodeid", "")
    client = _global_firestore_proxy._get_client()

    # Ensure baseline test admins exist
    snap_adm = await client.collection("admin_users").document("admin_super_1").get()
    if not snap_adm.exists:
        test_admins = [
            {"id": "admin_super_1", "email": "superadmin@nyaysetu.gov.in", "name": "Super Admin", "role": "super_admin", "active": True, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "staff_admin_1", "email": "staff@nyaysetu.gov.in", "name": "Staff Admin", "role": "admin", "active": True, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "admin_staff_1", "email": "staff@nyaysetu.gov.in", "name": "Staff Admin", "role": "admin", "active": True, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "sa_001", "email": "superadmin@nyaysetu.gov.in", "name": "Super Admin QA", "role": "super_admin", "active": True, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "staff_001", "email": "staff@nyaysetu.gov.in", "name": "Staff Admin QA", "role": "admin", "active": True, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        ]
        for a in test_admins:
            await client.collection("admin_users").document(a["id"]).set(a)

    # Ensure baseline test users exist
    snap_usr = await client.collection("users").document("lawyer_001").get()
    if not snap_usr.exists:
        test_users = [
            {"id": "lawyer_regular_1", "mobile": "9876543210", "email": "lawyer@test.com", "name": "Regular Lawyer", "role": "lawyer", "active": True, "credits": 100, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "lawyer_001", "mobile": "9876543210", "email": "lawyer1@test.com", "name": "Adv. Ramesh Patel", "role": "lawyer", "active": True, "credits": 50, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
            {"id": "lawyer_002", "mobile": "9876543211", "email": "lawyer2@test.com", "name": "Lawyer 2 QA", "role": "lawyer", "active": True, "credits": 100, "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z"},
        ]
        for u in test_users:
            await client.collection("users").document(u["id"]).set(u)
            bal = 50 if u["id"] == "lawyer_001" else 100
            await client.collection("wallets").document(f"wallet_{u['id']}").set({"id": f"wallet_{u['id']}", "user_id": u["id"], "balance": bal})
            await client.collection("wallets").document(u["id"]).set({"id": u["id"], "user_id": u["id"], "balance": bal})
    else:
        # Re-activate lawyer_001 and restore wallet if modified by previous tests
        await client.collection("users").document("lawyer_001").set({"active": True, "status": "active"}, merge=True)
        await client.collection("wallets").document("lawyer_001").set({"id": "lawyer_001", "user_id": "lawyer_001", "balance": 50}, merge=True)
        await client.collection("wallets").document("wallet_lawyer_001").set({"id": "wallet_lawyer_001", "user_id": "lawyer_001", "balance": 50}, merge=True)
        await client.collection("settings").document("signup_credits").set({"key": "signup_credits", "value": 5, "type": "int"}, merge=True)
        await client.collection("settings").document("otp_max_attempts").set({"key": "otp_max_attempts", "value": 5, "type": "int"}, merge=True)

    skip_seed = (
        "empty_templates" in node_id
        or "preview_fails_if_template_missing" in node_id
        or "resurrection" in node_id
        or "test_admin_templates" in node_id
        or "test_phase2_admin_api" in node_id
        or "test_template_page_size" in node_id
    )
    if not skip_seed:
        snap = await client.collection("templates").document("vakalatnama").get()
        if not snap.exists:
            import test_seed_data
            import test_seed_data_templates_v2
            batch = client.batch()
            count = 0
            for item in [*test_seed_data.TEMPLATES, *test_seed_data_templates_v2.TEMPLATES_V2]:
                item_copy = dict(item)
                item_copy.setdefault("status", "published")
                item_copy.setdefault("version", 1)
                doc_id = item_copy.get("id", str(uuid.uuid4()))
                ref = client.collection("templates").document(doc_id)
                batch.set(ref, item_copy)
                count += 1
                if count == 500:
                    await batch.commit()
                    batch = client.batch()
                    count = 0
            if count > 0:
                await batch.commit()
    yield

@pytest.fixture(autouse=True)
def mock_db():
    """Ensures server.db points to the FirestoreClientProxy for every test."""
    server.db = _global_firestore_proxy
    yield _global_firestore_proxy

@pytest.fixture
def mock_firebase_verify_token(monkeypatch):
    """Mocks Firebase token verification to allow local test tokens."""
    def _mock_verify(token):
        return {"uid": token, "email": f"{token}@test.com"}
    import firebase_init
    monkeypatch.setattr(firebase_init.auth, "verify_id_token", _mock_verify)

@pytest_asyncio.fixture
async def app_client(mock_db, mock_firebase_verify_token):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as ac:
        yield ac
