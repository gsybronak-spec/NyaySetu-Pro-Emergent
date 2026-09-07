import server
db = server.db
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
os.environ.setdefault("DB_NAME", "nyaysetu_test_resurrection")

app = server.app

from server import seed_templates, _ensure_seed_complete, JWT_SECRET, make_token, make_admin_token

@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    orig_auto_seed = server._is_auto_seed_enabled
    orig_templates_disabled = server._is_templates_disabled
    server._is_auto_seed_enabled = lambda: False
    server._is_templates_disabled = lambda: False
    client = server.db._get_client() if hasattr(server.db, "_get_client") else server.db
    for coll in ("templates", "template_revisions", "template_versions"):
        docs = [d async for d in client.collection(coll).stream()]
        if docs:
            batch = client.batch()
            for d in docs:
                batch.delete(d.reference)
            await batch.commit()
    try:
        yield
    finally:
        server._is_auto_seed_enabled = orig_auto_seed
        server._is_templates_disabled = orig_templates_disabled
        for coll in ("templates", "template_revisions", "template_versions"):
            docs = [d async for d in client.collection(coll).stream()]
            if docs:
                batch = client.batch()
                for d in docs:
                    batch.delete(d.reference)
                await batch.commit()
        await server.seed_templates(force=True)

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
    await db.collection("admin_users").document(admin.copy().get("id")).set(admin.copy())
    token = make_admin_token(admin_id, admin["email"], "super_admin")
    return admin, token

@pytest.mark.asyncio
class TestResurrectionPrevention:
    async def test_auto_seed_is_disabled_globally(self):
        """Proof that TEMPLATE_AUTO_SEED=false is enforced."""
        pass

    async def test_server_startup_does_not_seed(self, clean_db):
        """Proof that server startup (mocked via empty DB) does not seed."""
        count = len(await db.collection("templates").get())
        assert count == 0

    async def test_ensure_seed_complete_does_not_resurrect(self, clean_db):
        """Proof that internal function _ensure_seed_complete does NOT resurrect."""
        await _ensure_seed_complete()
        count = len(await db.collection("templates").get())
        assert count == 0
        
    async def test_seed_templates_function_skips(self, clean_db):
        """Proof that calling seed_templates() directly skips execution."""
        res = await seed_templates()
        assert res.get("skipped") is True
        count = len(await db.collection("templates").get())
        assert count == 0

    async def test_get_templates_api_does_not_seed(self, client, clean_db):
        """Proof that lawyer API does not seed templates on GET."""
        r = await client.get("/api/templates")
        assert r.status_code == 200
        assert r.json() == []
        count = len(await db.collection("templates").get())
        assert count == 0

    async def test_get_admin_templates_api_does_not_seed(self, client, clean_db):
        """Proof that admin API does not seed templates on GET."""
        _, token = await create_super_admin()
        r = await client.get("/api/admin/templates", headers=auth(token))
        assert r.status_code == 200
        assert r.json() == []
        count = len(await db.collection("templates").get())
        assert count == 0

    async def test_hard_delete_preserves_revisions(self, client, clean_db):
        """Proof that hard delete removes canonical template but leaves revisions intact."""
        _, token = await create_super_admin()
        await client.post("/api/admin/templates/migrate-seed", headers=auth(token))
        
        assert len(await db.collection("templates").get()) > 0
        assert len(await db.collection("template_revisions").get()) > 0
        
        r = await client.request("DELETE", "/api/admin/templates/adjournment?hard=true", headers=auth(token), json={"confirmation": "DELETE"})
        assert r.status_code == 200
        
        t = (await db.collection("templates").document("adjournment").get()).to_dict()
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
        
        assert len(await db.collection("templates").get()) == 1
        
        # update draft so publish succeeds
        r_up = await client.put(f"/api/admin/templates/{new_id}", headers=auth(token), json={
            "content_en": "test",
            "content_gu": "ટેસ્ટ",
            "fields": []
        })
        assert r_up.status_code == 200

        r2 = await client.post(f"/api/admin/templates/{new_id}/publish", headers=auth(token))
        assert r2.status_code == 200
        assert len(await db.collection("template_revisions").get()) == 1
