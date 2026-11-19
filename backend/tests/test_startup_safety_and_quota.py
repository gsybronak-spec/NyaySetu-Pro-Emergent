"""Unit tests for Firestore 429 quota safety and startup resiliency in backend/server.py.

Covers:
1. Startup behavior when seed_complete read raises ResourceExhausted (429).
2. Startup behavior when Firestore encounters transient network failures.
3. Failed status read does NOT trigger unintended heavy first-time seeding in production.
4. Genuinely fresh database has a deliberate initialization path when TEMPLATE_AUTO_SEED=true.
5. Genuinely fresh database logs warning and skips seeding when TEMPLATE_AUTO_SEED=false in production.
6. seed_plans uses a bounded existence check (limit(1)) rather than a full collection scan.
7. Existing plans are never overwritten by seed_plans.
8. Database-dependent endpoints return proper errors rather than false success when Firestore is unavailable.
9. Bounded retry policy on seed_complete (max 1 retry with backoff on transient errors).
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import server


class FakeResourceExhausted(Exception):
    """Simulates google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded."""
    pass

class MockAsyncStream:
    def __init__(self, items):
        self.items = items
    def __aiter__(self):
        self.iter = iter(self.items)
        return self
    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


class TestStartupSafetyAndQuota(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.orig_db = server.db
        self.orig_production = server._PRODUCTION
        self.orig_synced = server._CATALOG_MAPS_SYNCED
        server.invalidate_published_templates_cache()

    def tearDown(self):
        server.db = self.orig_db
        server._PRODUCTION = self.orig_production
        server._CATALOG_MAPS_SYNCED = self.orig_synced
        server.invalidate_published_templates_cache()

    async def test_01_startup_resilient_to_firestore_429_resource_exhausted(self):
        """When seed_complete read throws ResourceExhausted (429), create_indexes does NOT crash

        and does NOT invoke heavy first-time seeding.
        """
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        # Mock get() to raise 429 ResourceExhausted
        mock_doc_ref.get = AsyncMock(side_effect=FakeResourceExhausted("429 Quota exceeded"))
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        with patch("server.seed_plans", new_callable=AsyncMock) as mock_seed_plans, \
             patch("server.seed_catalogs", new_callable=AsyncMock) as mock_seed_catalogs, \
             patch("server.seed_templates", new_callable=AsyncMock) as mock_seed_templates:

            # Execute startup
            await server.create_indexes()

            # Heavy seeding must NOT have been called
            mock_seed_plans.assert_not_called()
            mock_seed_catalogs.assert_not_called()
            mock_seed_templates.assert_not_called()

    async def test_02_startup_resilient_to_transient_network_failure(self):
        """When Firestore encounters a network glitch / timeout, startup completes safely

        without crashing the container and without triggering seeding.
        """
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.get = AsyncMock(side_effect=ConnectionError("Temporary network unreachable"))
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        with patch("server.seed_plans", new_callable=AsyncMock) as mock_seed_plans:
            await server.create_indexes()
            mock_seed_plans.assert_not_called()

    async def test_03_failed_status_read_does_not_trigger_seeding_in_production(self):
        """In production, a failed status check (None) must never be treated as is_seeded=False."""
        server._PRODUCTION = True
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.get = AsyncMock(side_effect=FakeResourceExhausted("429 Quota exceeded"))
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        with patch("server.seed_plans", new_callable=AsyncMock) as mock_seed_plans, \
             patch("server.seed_templates", new_callable=AsyncMock) as mock_seed_templates:
            await server.create_indexes()
            mock_seed_plans.assert_not_called()
            mock_seed_templates.assert_not_called()

    async def test_04_fresh_database_triggers_seeding_when_auto_seed_enabled(self):
        """A genuinely fresh database (seed_complete does not exist) triggers deliberate seeding

        when _is_auto_seed_enabled() returns True.
        """
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        # Document does not exist
        mock_snap = MagicMock()
        mock_snap.exists = False
        mock_doc_ref.get = AsyncMock(return_value=mock_snap)
        mock_doc_ref.set = AsyncMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        with patch("server._is_auto_seed_enabled", return_value=True), \
             patch("server.seed_plans", new_callable=AsyncMock) as mock_seed_plans, \
             patch("server.seed_catalogs", new_callable=AsyncMock) as mock_seed_catalogs, \
             patch("server.seed_super_admin", new_callable=AsyncMock) as mock_seed_admin, \
             patch("server.seed_templates", new_callable=AsyncMock) as mock_seed_templates, \
             patch("server.migrate_templates_to_revisions", new_callable=AsyncMock) as mock_migrate:

            await server.create_indexes()

            mock_seed_plans.assert_called_once()
            mock_seed_catalogs.assert_called_once()
            mock_seed_admin.assert_called_once()
            mock_seed_templates.assert_called_once_with(force=True, mark_system_seed_complete=False)
            mock_migrate.assert_called_once_with(mock_db)

    async def test_05_fresh_database_skips_seeding_in_production_without_auto_seed(self):
        """In production without TEMPLATE_AUTO_SEED=true, a fresh database logs warning

        and does NOT silently trigger heavy automated seeding.
        """
        server._PRODUCTION = True
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snap = MagicMock()
        mock_snap.exists = False
        mock_doc_ref.get = AsyncMock(return_value=mock_snap)
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        with patch("server._is_auto_seed_enabled", return_value=False), \
             patch("server.seed_plans", new_callable=AsyncMock) as mock_seed_plans:
            await server.create_indexes()
            mock_seed_plans.assert_not_called()

    async def test_06_seed_plans_uses_bounded_limit_1_existence_check(self):
        """seed_plans must use limit(1) stream/get check rather than scanning the whole collection."""
        mock_db = MagicMock()
        mock_plans_coll = MagicMock()
        mock_query = MagicMock()

        # Simulate 1 plan existing
        async def mock_stream():
            yield MagicMock(to_dict=lambda: {"id": "starter"})

        mock_query.stream.return_value = mock_stream()
        mock_plans_coll.limit.return_value = mock_query
        mock_db.collection.return_value = mock_plans_coll
        server.db = mock_db

        await server.seed_plans()

        # Verify limit(1) was called
        mock_plans_coll.limit.assert_called_once_with(1)
        # Verify no document was written (set not called)
        mock_plans_coll.document.assert_not_called()

    async def test_07_seed_plans_does_not_overwrite_existing_plans(self):
        """When plans exist, seed_plans immediately returns without modifying any documents."""
        mock_db = MagicMock()
        mock_plans_coll = MagicMock()
        mock_query = MagicMock()

        async def mock_stream():
            yield MagicMock(to_dict=lambda: {"id": "custom_plan", "name": "Custom"})

        mock_query.stream.return_value = mock_stream()
        mock_plans_coll.limit.return_value = mock_query
        mock_db.collection.return_value = mock_plans_coll
        server.db = mock_db

        await server.seed_plans()
        mock_plans_coll.document.assert_not_called()

    async def test_08_seed_plans_resilient_to_firestore_429(self):
        """When checking plans raises 429, seed_plans logs and returns safely without raising."""
        mock_db = MagicMock()
        mock_plans_coll = MagicMock()
        mock_plans_coll.limit.side_effect = FakeResourceExhausted("429 Quota exceeded")
        mock_db.collection.return_value = mock_plans_coll
        server.db = mock_db

        # Should not raise
        await server.seed_plans()

    async def test_09_database_dependent_endpoints_return_honest_errors_when_db_unavailable(self):
        """Database-dependent endpoints (e.g. get_user) must raise 503 rather than fake success."""
        server.db = None
        server.invalidate_user_session_cache("uncached_user")

        with self.assertRaises(HTTPException) as ctx:
            await server.get_user(f"Bearer {server.make_token('uncached_user')}")
        self.assertEqual(ctx.exception.status_code, 503)

    async def test_10_check_seed_complete_bounded_retry(self):
        """_check_seed_complete retries at most once when encountering a 429 error."""
        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        call_count = 0

        async def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FakeResourceExhausted("429 Quota exceeded")
            snap = MagicMock()
            snap.exists = True
            snap.to_dict.return_value = {"value": True}
            return snap

        mock_doc_ref.get = mock_get
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        server.db = mock_db

        # With retry, attempt 2 should succeed and return True
        res = await server._check_seed_complete()
        self.assertTrue(res)
        self.assertEqual(call_count, 2)


    async def test_11_cold_cache_catalog_read_with_firestore_429_returns_503(self):
        """When catalog cache is cold and Firestore returns 429, catalog APIs return 503 instead of static seed list."""
        server._invalidate_catalog_cache("courts")
        mock_db = MagicMock()
        mock_db.collection.side_effect = FakeResourceExhausted("429 Quota exceeded")
        server.db = mock_db

        with self.assertRaises(HTTPException) as ctx:
            await server._load_catalog("courts")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Database service unavailable", ctx.exception.detail)

    async def test_12_warm_cache_catalog_read_returns_cached_data_during_outage(self):
        """When valid warm catalog cache exists, it is served even if database is unavailable."""
        cached_courts = [{"id": "court_warm_1", "en": "Warm Court", "gu": "વોર્મ કોર્ટ", "active": True}]
        server._CATALOG_CACHE["courts"] = list(cached_courts)
        server.db = None  # DB is down

        res = await server._load_catalog("courts")
        self.assertEqual(res, cached_courts)
        server._invalidate_catalog_cache("courts")

    async def test_13_tombstone_read_failure_propagates_503_and_does_not_resurrect_deleted_records(self):
        """When reading deleted_catalog_items fails with 429, 503 is raised rather than returning empty tombstones."""
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.stream.side_effect = FakeResourceExhausted("429 Quota exceeded")
        mock_col = MagicMock()
        mock_col.where.return_value = mock_query
        mock_col.stream.side_effect = FakeResourceExhausted("429 Quota exceeded")
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        with self.assertRaises(HTTPException) as ctx:
            await server._get_deleted_catalog_ids("courts")
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("catalog tombstones", ctx.exception.detail)

    async def test_14_admin_created_catalog_records_not_replaced_by_static_seeds(self):
        """Admin-created catalog items are preserved from live Firestore and not replaced with static seeds."""
        server._invalidate_catalog_cache("courts")
        custom_court = {"id": "custom_court_999", "en": "Custom Special Court", "gu": "કસ્ટમ સ્પેશિયલ કોર્ટ", "active": True}

        class MockAsyncStream:
            def __init__(self, items):
                self.items = items
            def __aiter__(self):
                self.iter = iter(self.items)
                return self
            async def __anext__(self):
                try:
                    return next(self.iter)
                except StopIteration:
                    raise StopAsyncIteration

        mock_db = MagicMock()
        def mock_collection(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                col.where.return_value.stream.return_value = MockAsyncStream([])
                col.stream.return_value = MockAsyncStream([])
            elif name == "courts":
                doc = MagicMock()
                doc.to_dict.return_value = custom_court
                col.stream.return_value = MockAsyncStream([doc])
            return col

        mock_db.collection.side_effect = mock_collection
        server.db = mock_db

        items = await server._load_catalog("courts")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "custom_court_999")
        self.assertEqual(items[0]["en"], "Custom Special Court")
        server._invalidate_catalog_cache("courts")

    async def test_15_case_validation_remains_strict_against_unknown_ids(self):
        """Case validation strictly rejects unknown/invalid catalog IDs with 400 when maps are synced."""
        server._CATALOG_MAPS_SYNCED = True
        invalid_case_data = {
            "court_id": "completely_bogus_court_id_that_never_existed",
            "case_type_id": "bogus_case_type",
            "district_id": "bogus_district",
        }
        with self.assertRaises(HTTPException) as ctx:
            server.validate_case_refs(invalid_case_data)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid case_type_id", ctx.exception.detail)

    async def test_16_partial_template_migration_does_not_mark_global_seed_complete(self):
        """POST /api/admin/templates/migrate-seed must NOT mark system_settings/seed_complete=True."""
        class MockAsyncStream:
            def __init__(self, items):
                self.items = items
            def __aiter__(self):
                self.iter = iter(self.items)
                return self
            async def __anext__(self):
                try:
                    return next(self.iter)
                except StopIteration:
                    raise StopAsyncIteration

        mock_db = MagicMock()
        written_settings = {}

        def mock_collection(name):
            col = MagicMock()
            if name == "system_settings":
                doc_ref = MagicMock()
                async def mock_set(data, merge=False):
                    written_settings[doc_ref.doc_id] = data
                doc_ref.set = mock_set
                doc_ref.get = AsyncMock(return_value=MagicMock(exists=False))
                def doc_fn(doc_id):
                    doc_ref.doc_id = doc_id
                    return doc_ref
                col.document.side_effect = doc_fn
                col.where.return_value.limit.return_value.stream.return_value = MockAsyncStream([])
            elif name == "templates":
                doc_ref = MagicMock()
                doc_ref.get = AsyncMock(return_value=MagicMock(exists=False))
                doc_ref.set = AsyncMock()
                col.document.return_value = doc_ref
                col.stream.return_value = MockAsyncStream([])
            elif name in ("template_revisions", "template_versions"):
                col.document.return_value.set = AsyncMock()
            elif name == "deleted_catalog_items":
                col.stream.return_value = MockAsyncStream([])
            return col

        mock_db.collection.side_effect = mock_collection
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin", "active": True}
        res = await server.admin_migrate_seed(admin=admin_user)

        self.assertTrue(res["success"])
        self.assertFalse(res["seed_complete"])
        self.assertTrue(res["templates_seed_complete"])
        # Global seed_complete must NOT be written in partial migration
        self.assertNotIn("seed_complete", written_settings)
        # But templates_seed_complete must be written
        self.assertIn("templates_seed_complete", written_settings)

    async def test_17_readiness_probe_honest_health_reporting(self):
        """/healthz does not claim database is checked, while /readyz honestly returns 200 or 503."""
        # /healthz liveness
        health = await server.root()
        self.assertEqual(health["status"], "ok")
        self.assertEqual(health["database"], "not_checked")

        # /readyz when db is None
        server.db = None
        with self.assertRaises(HTTPException) as ctx:
            await server.readiness()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, {"ready": False, "database": "unconfigured"})

        # /readyz when db raises 429
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get = AsyncMock(side_effect=FakeResourceExhausted("429 Quota exceeded"))
        server.db = mock_db
        with self.assertRaises(HTTPException) as ctx_429:
            await server.readiness()
        self.assertEqual(ctx_429.exception.status_code, 503)
        self.assertEqual(ctx_429.exception.detail, {"ready": False, "database": "unavailable", "error": "database_unavailable"})

        # /readyz when db is healthy
        mock_db.collection.return_value.document.return_value.get = AsyncMock(return_value=MagicMock(exists=True))
        ready_res = await server.readiness()
        self.assertTrue(ready_res["ready"])
        self.assertEqual(ready_res["database"], "connected")

    async def test_18_legacy_seed_complete_marker_skips_template_seeding(self):
        """Legacy system_settings/seed_complete=True skips seed_templates without templates_seed_complete."""
        mock_db = MagicMock()
        set_called = False
        update_called = False

        def mock_collection(name):
            col = MagicMock()
            if name == "system_settings":
                def mock_where(filter=None):
                    where_mock = MagicMock()
                    key_val = getattr(filter, "value", None)
                    if key_val == "seed_complete":
                        doc = MagicMock()
                        doc.to_dict.return_value = {"key": "seed_complete", "value": True}
                        where_mock.limit.return_value.stream.return_value = MockAsyncStream([doc])
                    else:
                        where_mock.limit.return_value.stream.return_value = MockAsyncStream([])
                    return where_mock
                col.where.side_effect = mock_where
            elif name == "templates":
                col.stream.return_value = MockAsyncStream([MagicMock() for _ in range(25)])
                doc_mock = MagicMock()
                async def mock_set(*args, **kwargs):
                    nonlocal set_called
                    set_called = True
                async def mock_update(*args, **kwargs):
                    nonlocal update_called
                    update_called = True
                doc_mock.set = mock_set
                doc_mock.update = mock_update
                col.document.return_value = doc_mock
            return col

        mock_db.collection.side_effect = mock_collection
        server.db = mock_db

        with patch.object(server, "_is_auto_seed_enabled", return_value=True):
            res = await server.seed_templates(force=False)

        self.assertTrue(res["success"])
        self.assertTrue(res.get("seed_complete"))
        self.assertEqual(res["created"], 0)
        self.assertFalse(set_called, "seed_templates must NOT write new templates when legacy seed_complete=True")
        self.assertFalse(update_called, "seed_templates must NOT update templates when legacy seed_complete=True")

    def test_19_cold_start_sync_failure_rejects_case_validation_with_503(self):
        """When catalog maps have never synchronized (_CATALOG_MAPS_SYNCED=False), validate_case_refs returns 503."""
        server._CATALOG_MAPS_SYNCED = False
        valid_looking_case_data = {
            "case_type_id": "regular_bail",
            "district_id": "dahod",
        }
        with self.assertRaises(HTTPException) as ctx:
            server.validate_case_refs(valid_looking_case_data)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("database synchronization pending", ctx.exception.detail)

    def test_20_successful_sync_followed_by_outage_allows_validation(self):
        """Warm cached in-memory maps continue to validate cases when synced, even if Firestore is down."""
        server._CATALOG_MAPS_SYNCED = True
        server.db = None  # Simulating temporary outage or failure after sync

        # Ensure known valid test IDs are present in the synced maps
        server._VALID_CASE_TYPE_IDS.add("regular_bail")
        server._VALID_DISTRICT_IDS.add("dahod")

        valid_case_data = {
            "case_type_id": "regular_bail",
            "district_id": "dahod",
        }
        # Must NOT raise HTTPException
        try:
            server.validate_case_refs(valid_case_data)
        except HTTPException as e:
            self.fail(f"validate_case_refs unexpectedly raised HTTPException: {e.detail}")

    async def test_21_readiness_probe_does_not_expose_raw_exception_or_project_id(self):
        """Readiness endpoint returns generic sanitized error and never leaks project IDs or raw exceptions."""
        leaky_message = "projects/nyaysetu-pro-emerg/databases/(default)/documents/system_settings/seed_complete: ResourceExhausted: 429 Quota exceeded"
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get = AsyncMock(
            side_effect=Exception(leaky_message)
        )
        server.db = mock_db

        with self.assertRaises(HTTPException) as ctx:
            await server.readiness()

        self.assertEqual(ctx.exception.status_code, 503)
        detail = ctx.exception.detail
        self.assertEqual(detail, {"ready": False, "database": "unavailable", "error": "database_unavailable"})
        # Verify that internal GCP resource names, project IDs, or raw exceptions are NOT exposed
        detail_str = str(detail)
        self.assertNotIn("projects/nyaysetu-pro-emerg", detail_str)
        self.assertNotIn("ResourceExhausted", detail_str)
        self.assertNotIn("429 Quota exceeded", detail_str)


if __name__ == "__main__":
    unittest.main()
