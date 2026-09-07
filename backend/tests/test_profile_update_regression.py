"""Regression test for Firestore profile update query.
Verifies that updating profile does not require a composite index
and duplicate mobile protection works correctly.
"""

import pytest
import uuid
import httpx
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server

@pytest.mark.asyncio
async def test_profile_update_no_composite_index_and_duplicate_check():
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]
    user1_id = f"test_user_{uid1}"
    user2_id = f"test_user_{uid2}"

    mobile1 = f"9876{uid1[:6]}"
    mobile2 = f"9876{uid2[:6]}"

    # Setup 2 temporary users in Firestore
    await server.db.collection("users").document(user1_id).set({
        "id": user1_id,
        "name": "User One",
        "email": f"user1_{uid1}@example.com",
        "mobile": None,
        "active": True,
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    })
    await server.db.collection("users").document(user2_id).set({
        "id": user2_id,
        "name": "User Two",
        "email": f"user2_{uid2}@example.com",
        "mobile": mobile2,
        "active": True,
        "created_at": server.now().isoformat(),
        "updated_at": server.now().isoformat(),
    })

    token1 = server.make_token(user1_id)
    token2 = server.make_token(user2_id)

    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. User 1 updates with unused mobile1 -> Should succeed (200) without composite index error
        res1 = await client.put(
            "/api/profile/update",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "first_name": "User",
                "last_name": "One",
                "mobile": mobile1,
                "user_type": "Advocate",
                "bar_council_no": f"G/{uid1[:4]}/2024",
                "state": "Gujarat",
                "district": "Ahmedabad",
            }
        )
        assert res1.status_code == 200, f"Expected 200, got {res1.status_code}: {res1.text}"
        data1 = res1.json()
        assert data1.get("mobile") == mobile1

        # 2. User 1 updates profile again keeping their own mobile1 -> Should succeed (200)
        res1_repeat = await client.put(
            "/api/profile/update",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "first_name": "User",
                "last_name": "One Updated",
                "mobile": mobile1,
                "user_type": "Advocate",
                "bar_council_no": f"G/{uid1[:4]}/2024",
                "state": "Gujarat",
                "district": "Ahmedabad",
            }
        )
        assert res1_repeat.status_code == 200, f"Expected 200, got {res1_repeat.status_code}: {res1_repeat.text}"

        # 3. User 1 tries to use User 2's mobile2 -> Should fail (400) duplicate check
        res_dup = await client.put(
            "/api/profile/update",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "mobile": mobile2,
            }
        )
        assert res_dup.status_code == 400, f"Expected 400 for duplicate mobile, got {res_dup.status_code}"
        assert "already registered" in res_dup.text

    # Cleanup temporary test users
    await server.db.collection("users").document(user1_id).delete()
    await server.db.collection("users").document(user2_id).delete()
