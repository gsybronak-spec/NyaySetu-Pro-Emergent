import pytest
import pytest_asyncio
import uuid
import time
from httpx import AsyncClient, ASGITransport
import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_fav_order"]

import server
server.db = mock_db
db = mock_db
app = server.app

from server import make_token

API = "/api"

def H(token):
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture(scope="function")
async def client():
    server.db = mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(scope="function")
async def clean_db():
    for coll in ["users", "wallets", "cases", "applications", "drafts",
                 "transactions", "referrals", "admin_users", "templates",
                 "template_versions", "case_forms", "otps"]:
        await db[coll].drop()
    yield
    for coll in ["users", "wallets", "cases", "applications", "drafts",
                 "transactions", "referrals", "admin_users", "templates",
                 "template_versions", "case_forms", "otps"]:
        await db[coll].drop()

async def create_test_lawyer(mobile="9900000001", email="test@nyaysetu.in"):
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "mobile": mobile,
        "email": email,
        "name": "Adv. Test Lawyer",
        "provider": "mobile",
        "status": "active",
        "created_at": server.now().isoformat(),
    }
    await db.users.insert_one(user)
    token = make_token(user_id)
    return user, token

@pytest.mark.asyncio
async def test_template_favorites_and_order_flow(client, clean_db):
    user_a, token_a = await create_test_lawyer(mobile="9900000001", email="lawyer_a@nyaysetu.in")
    user_b, token_b = await create_test_lawyer(mobile="9900000002", email="lawyer_b@nyaysetu.in")

    # 1. User A favorites vakilatnama_civil
    r = await client.post(f"{API}/favourites/templates/vakilatnama_civil", headers=H(token_a))
    assert r.status_code == 200
    assert "vakilatnama_civil" in r.json()["favourite_templates"]

    # User B should NOT see User A's favorites (isolation)
    r_b = await client.get(f"{API}/favourites/templates", headers=H(token_b))
    assert r_b.status_code == 200
    assert "vakilatnama_civil" not in r_b.json()["favourite_templates"]

    # 2. User A gets /templates with auth header
    r_list = await client.get(f"{API}/templates", headers=H(token_a))
    assert r_list.status_code == 200
    items = r_list.json()
    fav_item = next(t for t in items if t["id"] == "vakilatnama_civil")
    assert fav_item["is_favorite"] is True
    non_fav = next(t for t in items if t["id"] != "vakilatnama_civil")
    assert non_fav["is_favorite"] is False

    # 3. User A sets custom template ordering
    custom_order = ["vakilatnama_criminal", "vakilatnama_civil", "mudat_arji"]
    r_order = await client.put(f"{API}/user/template-order", json={"template_order": custom_order}, headers=H(token_a))
    assert r_order.status_code == 200
    assert r_order.json()["template_order"] == custom_order

    # 4. User A gets /templates and items are sorted by custom order
    r_list_sorted = await client.get(f"{API}/templates", headers=H(token_a))
    items_sorted = r_list_sorted.json()
    assert items_sorted[0]["id"] == "vakilatnama_criminal"
    assert items_sorted[1]["id"] == "vakilatnama_civil"
    assert items_sorted[2]["id"] == "mudat_arji"

    # User B's template list is NOT affected by User A's order
    r_list_b = await client.get(f"{API}/templates", headers=H(token_b))
    items_b = r_list_b.json()
    assert items_b != items_sorted

    # 5. User A removes favorite
    r_del = await client.delete(f"{API}/favourites/templates/vakilatnama_civil", headers=H(token_a))
    assert r_del.status_code == 200
    assert "vakilatnama_civil" not in r_del.json()["favourite_templates"]
