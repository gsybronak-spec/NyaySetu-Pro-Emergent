import pytest
from server import app

# Basic unit regression verifying drafts are deleted when a case is deleted.
@pytest.mark.asyncio
async def test_case_soft_delete_purges_drafts(monkeypatch):
    class MockDb:
        class cases:
            async def update_one(self, *a, **k):
                class R: matched_count = 1
                return R()
        class drafts:
            async def delete_many(self, query):
                assert query["case_id"] == "test_case"
                assert query["user_id"] == "test_user"

    monkeypatch.setattr("server.db", MockDb())

    from server import delete_case
    res = await delete_case("test_case", {"id": "test_user"})
    assert res["success"] is True
