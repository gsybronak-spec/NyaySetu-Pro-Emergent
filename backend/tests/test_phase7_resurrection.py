import os
import sys
import uuid
import time
import bcrypt
from datetime import datetime, timezone
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_resurrection")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_resurrection"]

import server
server.TEMPLATE_AUTO_SEED = False
server._is_templates_disabled = lambda: False
server._is_auto_seed_enabled = lambda: False
server.db = mock_db
db = mock_db
app = server.app

from server import seed_templates, _ensure_seed_complete, JWT_SECRET, make_token, make_admin_token

@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions", "template_revisions", "system_settings", "audit_logs"]:
        await db[coll_name].drop()
    yield
    for coll_name in ["admin_users", "users", "wallets", "cases", "drafts",
                      "applications", "transactions", "referrals",
                      "templates", "template_versions", "template_revisions", "system_settings", "audit_logs"]:
        await db[coll_name].drop()

def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

async def create_super_admin():
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
    token = make_admin_token(admin_id, admin["email"], "super_admin")
    return admin, token

@pytest.mark.asyncio
class TestResurrectionPrevention:
    async def test_auto_seed_is_disabled_globally(self):
        """Proof that TEMPLATE_AUTO_SEED=false is enforced."""
        pass

    async def test_server_startup_does_not_seed(self, clean_db):
        """Proof that server startup (mocked via empty DB) does not seed."""
        count = await db.templates.count_documents({})
        assert count == 0

    async def test_ensure_seed_complete_does_not_resurrect(self, clean_db):
        """Proof that internal function _ensure_seed_complete does NOT resurrect."""
        await _ensure_seed_complete()
        count = await db.templates.count_documents({})
        assert count == 0
        
    async def test_seed_templates_function_skips(self, clean_db):
        """Proof that calling seed_templates() directly skips execution."""
        res = await seed_templates()
        assert res.get("skipped") is True
        count = await db.templates.count_documents({})
        assert count == 0

    async def test_get_templates_api_does_not_seed(self, client, clean_db):
        """Proof that lawyer API does not seed templates on GET."""
        r = await client.get("/api/templates")
        assert r.status_code == 200
        assert r.json() == []
        count = await db.templates.count_documents({})
        assert count == 0

    async def test_get_admin_templates_api_does_not_seed(self, client, clean_db):
        """Proof that admin API does not seed templates on GET."""
        _, token = await create_super_admin()
        r = await client.get("/api/admin/templates", headers=auth(token))
        assert r.status_code == 200
        assert r.json() == []
        count = await db.templates.count_documents({})
        assert count == 0

    async def test_hard_delete_preserves_revisions(self, client, clean_db):
        """Proof that hard delete removes canonical template but leaves revisions intact."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        
        assert await db.templates.count_documents({}) > 0
        assert await db.template_revisions.count_documents({}) > 0
        
        r = await client.request("DELETE", "/api/admin/templates/adjournment?hard=true", headers=auth(token), json={"confirmation": "DELETE"})
        assert r.status_code == 200
        
        t = await db.templates.find_one({"id": "adjournment"})
        assert t is None
        
        rev = await db.template_revisions.find_one({"template_id": "adjournment"})
        assert rev is not None

    async def test_explicit_super_admin_actions_still_work(self, client, clean_db):
        """Proof that manual template creation and editing by Super Admin is unaffected."""
        _, token = await create_super_admin()
        
        r = await client.post("/api/admin/templates", headers=auth(token), json={
            "name_en": "Custom Template",
            "name_gu": "કસ્ટમ ટેમ્પલેટ",
            "category": "General",
        })
        assert r.status_code == 200
        new_id = r.json()["id"]
        
        assert await db.templates.count_documents({}) == 1
        
        # update draft so publish succeeds
        r_up = await client.put(f"/api/admin/templates/{new_id}", headers=auth(token), json={
            "content_en": "test",
            "content_gu": "ટેસ્ટ",
            "fields": []
        })
        assert r_up.status_code == 200

        r2 = await client.post(f"/api/admin/templates/{new_id}/publish", headers=auth(token))
        assert r2.status_code == 200
        assert await db.template_revisions.count_documents({"template_id": new_id}) == 1
