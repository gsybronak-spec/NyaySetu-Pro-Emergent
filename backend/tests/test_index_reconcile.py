"""
Regression tests for the production startup fix:

MongoDB IndexOptionsConflict on otps.ttl_at_1 crashed the FastAPI app at
startup because the TTL index's expireAfterSeconds drifted from the
admin-configured otp_ttl_seconds setting. create_indexes() must now be fully
idempotent: detect an existing index with the same key/name, reconcile the TTL
configuration safely, and never crash on restart.
"""
import pytest_asyncio
import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_indexes"]

import server
server.db = mock_db
db = mock_db

from server import _ensure_index, _ensure_ttl_index, create_indexes


INDEXED_COLLECTIONS = [
    "users", "cases", "wallets", "applications", "drafts", "transactions",
    "payment_orders", "referrals", "otps", "admin_users", "templates",
    "template_versions", "case_forms", "settings", "plans",
    "case_types", "laws", "districts", "talukas", "courts", "police_stations",
    "audit_logs",
]


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    # Other test modules swap the shared server.db global; re-assert ours so
    # create_indexes() operates on this module's mock database.
    server.db = mock_db
    for coll in INDEXED_COLLECTIONS:
        await db[coll].drop()
    yield
    server.db = mock_db
    for coll in INDEXED_COLLECTIONS:
        await db[coll].drop()


async def _set_otp_ttl(seconds: int):
    await db.settings.update_one(
        {"key": "otp_ttl_seconds"},
        {"$set": {"key": "otp_ttl_seconds", "value": seconds}},
        upsert=True,
    )


async def _ttl_of(coll_name: str, field: str) -> int | None:
    indexes = await db[coll_name].list_indexes().to_list(100)
    for ix in indexes:
        if tuple(sorted(ix.get("key", {}).items())) == tuple(sorted([(field, 1)])):
            return ix.get("expireAfterSeconds")
    return None


class TestTtlReconcile:
    async def test_ttl_conflict_rebuilds_to_required(self):
        """Reproduce the production bug: index exists with 360, app requires 560."""
        await db.otps.create_index("ttl_at", expireAfterSeconds=360)
        await _set_otp_ttl(500)
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_ttl_existing_larger_than_required_is_kept(self):
        """Reported variant: existing index 560, app requests 360 — must NOT crash
        and must keep the more conservative index."""
        await db.otps.create_index("ttl_at", expireAfterSeconds=560)
        await _set_otp_ttl(300)
        await _ensure_ttl_index(db.otps, "ttl_at", 360)
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_ttl_correct_value_is_noop(self):
        await db.otps.create_index("ttl_at", expireAfterSeconds=560)
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_ttl_missing_is_created(self):
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_ttl_reconcile_is_repeatable(self):
        """Running the reconcile repeatedly must be a no-op after the first run."""
        await db.otps.create_index("ttl_at", expireAfterSeconds=360)
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        await _ensure_ttl_index(db.otps, "ttl_at", 560)
        assert await _ttl_of("otps", "ttl_at") == 560
        # only one ttl_at index remains (no duplicates)
        names = [ix["name"] for ix in await db.otps.list_indexes().to_list(100)
                 if "ttl_at" in ix["name"]]
        assert names == ["ttl_at_1"]


class TestEnsureIndex:
    async def test_existing_index_is_skipped_not_duplicated(self):
        await db.users.create_index("id", unique=True)
        await _ensure_index(db.users, "id", unique=True)
        await _ensure_index(db.users, "id", unique=True)
        names = [ix["name"] for ix in await db.users.list_indexes().to_list(100)]
        assert names.count("id_1") == 1

    async def test_missing_index_is_created(self):
        await _ensure_index(db.users, "id", unique=True)
        names = [ix["name"] for ix in await db.users.list_indexes().to_list(100)]
        assert "id_1" in names

    async def test_compound_and_sparse_specs_normalize(self):
        await _ensure_index(db.transactions, "razorpay_payment_id", unique=True, sparse=True)
        await _ensure_index(db.transactions, "razorpay_payment_id", unique=True, sparse=True)
        names = [ix["name"] for ix in await db.transactions.list_indexes().to_list(100)]
        assert names.count("razorpay_payment_id_1") == 1
        await _ensure_index(db.cases, [("user_id", 1), ("status", 1)])
        await _ensure_index(db.cases, [("user_id", 1), ("status", 1)])
        names = [ix["name"] for ix in await db.cases.list_indexes().to_list(100)]
        assert names.count("user_id_1_status_1") == 1


class TestStartup:
    async def test_startup_succeeds_with_old_ttl_index(self):
        """Full startup path: the exact reported conflict must not crash the app."""
        await _set_otp_ttl(500)
        await db.otps.create_index("ttl_at", expireAfterSeconds=360)  # stale TTL
        await create_indexes()  # must not raise IndexOptionsConflict
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_startup_succeeds_when_correct_ttl_exists(self):
        await _set_otp_ttl(500)
        await db.otps.create_index("ttl_at", expireAfterSeconds=560)
        await create_indexes()
        assert await _ttl_of("otps", "ttl_at") == 560

    async def test_startup_repeatable(self):
        """Repeated restarts (fresh process each time) must never fail."""
        await _set_otp_ttl(500)
        for _ in range(3):
            await db.otps.drop()  # simulate restart with a clean-ish otps collection
            await create_indexes()
        assert await _ttl_of("otps", "ttl_at") == 560
