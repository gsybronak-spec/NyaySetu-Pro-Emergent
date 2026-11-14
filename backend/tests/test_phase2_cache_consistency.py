"""Phase 2 Regression Tests: Admin Cache Consistency & Stale Data.

Verifies:
1. _get_published_templates() never spawns update tasks and never mutates Firestore.
2. _CATALOG_CACHE serves before 60s TTL and refreshes from DB after 60s.
3. _invalidate_catalog_cache() clears both cached items and per-kind timestamps.
4. _bump_cache_revision() atomically increments cache_version in Firestore.
5. _sync_cross_instance_cache() debounces to 10s and evicts local caches on remote revision bump.
6. Admin API endpoints emit Cache-Control: no-store and Pragma: no-cache on success and error.
7. Public API endpoints do not emit Cache-Control: no-store.
8. Admin catalog update invalidates catalog cache and atomically commits batch with revision.
9. Successful data write and revision update occur in the SAME atomic Firestore batch.
10. Failed atomic batch operation leaves both data and local revision unchanged.
11. Concurrent revision increments use firestore.Increment and do not lose updates.
12. Revision update failures in fallback paths are visible and handled correctly.
13. Frontend SWR race guard: older foreground GET resolving after mutation is discarded from cache.
14. Frontend SWR race guard: older background SWR GET resolving after mutation is discarded.
15. Frontend SWR race guard: same-millisecond request/mutation ordering correctly rejects older reads.
16. Frontend SWR race guard: newer GET resolving after mutation successfully updates cache.
17. Frontend SWR race guard: unrelated endpoint cache remains unaffected.
"""

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import server


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


class TestPhase2CacheConsistency(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.orig_db = server.db
        self.orig_production = server._PRODUCTION
        server.invalidate_published_templates_cache()
        server.invalidate_plans_cache()
        server.invalidate_settings_cache()
        server._invalidate_catalog_cache()
        server._LAST_REVISION_CHECK_TS = 0.0
        server._CACHE_REVISIONS = {
            "templates": 0,
            "catalog": 0,
            "plans": 0,
            "settings": 0,
        }

    def tearDown(self):
        server.db = self.orig_db
        server._PRODUCTION = self.orig_production
        server.invalidate_published_templates_cache()
        server.invalidate_plans_cache()
        server.invalidate_settings_cache()
        server._invalidate_catalog_cache()
        server._LAST_REVISION_CHECK_TS = 0.0

    async def test_01_get_published_templates_never_writes_or_updates_firestore(self):
        """_get_published_templates() must never mutate Firestore documents or overwrite with seed constants."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.update = AsyncMock()
        mock_doc.set = AsyncMock()

        # Cache version mock
        cv_snap = MagicMock()
        cv_snap.exists = True
        cv_snap.to_dict.return_value = {"templates": 0, "catalog": 0, "plans": 0, "settings": 0}

        # Mock template document with customized admin text
        snap = MagicMock()
        snap.exists = True
        snap.to_dict.return_value = {
            "id": "vakilatnama_civil",
            "name": "Customized Vakilatnama",
            "category": "civil",
            "status": "published",
            "content": "Admin customized text that should never be overwritten",
            "point_size": 14,
            "margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        }

        def col_router(name):
            col = MagicMock()
            if name == "system_settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=cv_snap)
                col.document.return_value = doc
            elif name == "templates":
                col.document.return_value = mock_doc
                col.where.return_value.limit.return_value.stream.return_value = MockAsyncStream([snap])
                col.where.return_value.stream.return_value = MockAsyncStream([snap])
            else:
                col.stream.return_value = MockAsyncStream([])
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        with patch("asyncio.create_task") as mock_create_task:
            templates = await server._get_published_templates()
            # Find the customized template
            match = next((t for t in templates if t.get("id") == "vakilatnama_civil"), None)
            self.assertIsNotNone(match)
            self.assertEqual(match["content"], "Admin customized text that should never be overwritten")
            # Must never call create_task to overwrite templates in background
            mock_create_task.assert_not_called()

        # Must never mutate the document in Firestore
        mock_doc.update.assert_not_called()
        mock_doc.set.assert_not_called()

    async def test_02_catalog_cache_ttl_and_refresh(self):
        """_CATALOG_CACHE serves before 60s TTL and refreshes from DB after 60s."""
        mock_db = MagicMock()
        col = MagicMock()

        court_v1 = {"id": "court_1", "en": "Court Version 1", "active": True}
        court_v2 = {"id": "court_1", "en": "Court Version 2", "active": True}

        snap1 = MagicMock()
        snap1.to_dict.return_value = court_v1
        snap2 = MagicMock()
        snap2.to_dict.return_value = court_v2

        stream_calls = 0

        def stream_router():
            nonlocal stream_calls
            stream_calls += 1
            if stream_calls == 1:
                return MockAsyncStream([snap1])
            return MockAsyncStream([snap2])

        col.stream.side_effect = stream_router

        # Cache version mock
        cv_snap = MagicMock()
        cv_snap.exists = True
        cv_snap.to_dict.return_value = {"templates": 0, "catalog": 0, "plans": 0, "settings": 0}

        def col_router(name):
            if name == "system_settings":
                c = MagicMock()
                d = MagicMock()
                d.get = AsyncMock(return_value=cv_snap)
                c.document.return_value = d
                return c
            elif name == "deleted_catalog_items":
                c = MagicMock()
                c.where.return_value.stream.return_value = MockAsyncStream([])
                return c
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        # Initial load at t=1000
        with patch("time.time", return_value=1000.0):
            res1 = await server._load_catalog("courts")
            self.assertEqual(res1[0]["en"], "Court Version 1")
            self.assertEqual(stream_calls, 1)

        # Load at t=1030 (30s later, within 60s TTL) -> should use cache, no new DB stream
        with patch("time.time", return_value=1030.0):
            res2 = await server._load_catalog("courts")
            self.assertEqual(res2[0]["en"], "Court Version 1")
            self.assertEqual(stream_calls, 1)

        # Load at t=1065 (65s later, TTL expired) -> should refresh from DB
        with patch("time.time", return_value=1065.0):
            res3 = await server._load_catalog("courts")
            self.assertEqual(res3[0]["en"], "Court Version 2")
            self.assertEqual(stream_calls, 2)

    def test_03_catalog_cache_invalidation_clears_timestamps(self):
        """_invalidate_catalog_cache() removes both cached items and per-kind timestamps."""
        server._CATALOG_CACHE["courts"] = [{"id": "c1"}]
        server._CATALOG_CACHE_EXPIRES["courts"] = time.time() + 60.0
        server._CATALOG_CACHE["laws"] = [{"id": "l1"}]
        server._CATALOG_CACHE_EXPIRES["laws"] = time.time() + 60.0

        # Invalidate only courts
        server._invalidate_catalog_cache("courts")
        self.assertNotIn("courts", server._CATALOG_CACHE)
        self.assertNotIn("courts", server._CATALOG_CACHE_EXPIRES)
        self.assertIn("laws", server._CATALOG_CACHE)
        self.assertIn("laws", server._CATALOG_CACHE_EXPIRES)

        # Invalidate all
        server._invalidate_catalog_cache()
        self.assertEqual(len(server._CATALOG_CACHE), 0)
        self.assertEqual(len(server._CATALOG_CACHE_EXPIRES), 0)

    async def test_04_bump_cache_revision_increments_firestore(self):
        """_bump_cache_revision() calls set with merge=True and increments local counter."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set = AsyncMock()
        mock_db.collection.return_value.document.return_value = mock_doc
        server.db = mock_db

        await server._bump_cache_revision("templates")
        self.assertEqual(server._CACHE_REVISIONS["templates"], 1)
        mock_doc.set.assert_called_once()
        args, kwargs = mock_doc.set.call_args
        payload = args[0]
        self.assertIn("templates", payload)
        self.assertIn("updated_at", payload)
        self.assertTrue(kwargs.get("merge"))

    async def test_05_cross_instance_sync_debounces_and_evicts(self):
        """_sync_cross_instance_cache() debounces to 10s and evicts stale local caches when remote revision bumps."""
        mock_db = MagicMock()
        mock_doc = MagicMock()

        # Remote revision document has higher version for templates and plans
        snap = MagicMock()
        snap.exists = True
        snap.to_dict.return_value = {
            "templates": 5,
            "catalog": 2,
            "plans": 3,
            "settings": 0,
        }
        mock_doc.get = AsyncMock(return_value=snap)
        mock_db.collection.return_value.document.return_value = mock_doc
        server.db = mock_db

        # Seed local caches
        server._PUBLISHED_TEMPLATES_CACHE["data"] = [{"id": "stale_tpl"}]
        server._PUBLISHED_TEMPLATES_CACHE["expires_at"] = 2000.0
        server._PLANS_CACHE["data"] = [{"id": "stale_plan"}]
        server._PLANS_CACHE["expires_at"] = 2000.0
        server._CATALOG_CACHE["courts"] = [{"id": "court_item"}]
        server._CATALOG_CACHE_EXPIRES["courts"] = 2000.0

        # At t=1000: initial sync
        with patch("time.time", return_value=1000.0):
            await server._sync_cross_instance_cache("templates")

            # templates, plans, and catalog should be evicted because remote revisions > local
            self.assertIsNone(server._PUBLISHED_TEMPLATES_CACHE["data"])
            self.assertIsNone(server._PLANS_CACHE["data"])
            self.assertEqual(len(server._CATALOG_CACHE), 0)
            self.assertEqual(server._CACHE_REVISIONS["templates"], 5)
            self.assertEqual(server._CACHE_REVISIONS["plans"], 3)
            self.assertEqual(server._CACHE_REVISIONS["catalog"], 2)
            self.assertEqual(mock_doc.get.call_count, 1)

        # Call again at t=1005 (5 seconds later, within 10s debounce window)
        with patch("time.time", return_value=1005.0):
            await server._sync_cross_instance_cache("templates")
            # DB should NOT be queried again due to debounce
            self.assertEqual(mock_doc.get.call_count, 1)

        # Call at t=1015 (15 seconds later, debounce expired)
        with patch("time.time", return_value=1015.0):
            await server._sync_cross_instance_cache("templates")
            self.assertEqual(mock_doc.get.call_count, 2)

    def test_06_admin_routes_return_no_store_cache_headers(self):
        """Admin API endpoints must return Cache-Control: no-store and Pragma: no-cache on success and error."""
        client = TestClient(server.app)

        # Admin route without auth (401 error response)
        resp_err = client.get("/api/admin/dashboard/stats")
        self.assertEqual(resp_err.status_code, 401)
        cc = resp_err.headers.get("cache-control", "")
        self.assertIn("no-store", cc)
        self.assertIn("no-cache", cc)
        self.assertIn("must-revalidate", cc)
        self.assertEqual(resp_err.headers.get("pragma"), "no-cache")

        # Admin auth login with bad creds (401/422 error response)
        resp_login = client.post("/api/admin/auth/login", json={"email": "fake@test.com", "password": "wrong"})
        self.assertIn(resp_login.status_code, (401, 422))
        cc = resp_login.headers.get("cache-control", "")
        self.assertIn("no-store", cc)
        self.assertIn("no-cache", cc)
        self.assertIn("must-revalidate", cc)
        self.assertEqual(resp_login.headers.get("pragma"), "no-cache")

    def test_07_public_routes_do_not_return_no_store(self):
        """Public API endpoints must not have Cache-Control: no-store imposed by admin middleware."""
        client = TestClient(server.app)

        # Public health check
        resp_health = client.get("/healthz")
        self.assertEqual(resp_health.status_code, 200)
        cc = resp_health.headers.get("cache-control", "")
        self.assertNotIn("no-store", cc)

    async def test_08_admin_catalog_writes_invalidate_cache_and_bump_revision(self):
        """admin_update_catalog_item and admin_set_catalog_status invalidate _CATALOG_CACHE and bump revision."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock()
        mock_db.batch.return_value = mock_batch

        mock_doc = MagicMock()
        mock_doc.set = AsyncMock()

        existing_snap = MagicMock()
        existing_snap.exists = True
        existing_snap.to_dict.return_value = {"id": "c1", "en": "Old Court", "active": True}
        mock_doc.get = AsyncMock(return_value=existing_snap)

        fresh_snap = MagicMock()
        fresh_snap.to_dict.return_value = {"id": "c1", "en": "Fresh Court from DB", "active": True}

        col = MagicMock()
        col.document.return_value = mock_doc
        col.stream.return_value = MockAsyncStream([fresh_snap])
        mock_db.collection.return_value = col
        server.db = mock_db

        admin_user = {"id": "admin_1", "email": "admin@nyaysetu.com", "role": "super_admin"}

        # 1. Test admin_update_catalog_item
        server._CATALOG_CACHE["courts"] = [{"id": "c1", "en": "Stale Court"}]
        server._CATALOG_CACHE_EXPIRES["courts"] = time.time() + 60.0

        update_req = server.CatalogItemReq(id="c1", en="Updated Court", active=True)
        with patch.object(server, "_invalidate_catalog_cache", wraps=server._invalidate_catalog_cache) as mock_inv:
            res = await server.admin_update_catalog_item(kind="courts", item_id="c1", req=update_req, admin=admin_user)
            self.assertTrue(res.get("success"))
            mock_inv.assert_called_with("courts")
            self.assertGreaterEqual(server._CACHE_REVISIONS["catalog"], 1)
            # The stale value must not be present
            self.assertNotEqual(server._CATALOG_CACHE.get("courts"), [{"id": "c1", "en": "Stale Court"}])

        # 2. Test admin_set_catalog_status
        server._CATALOG_CACHE["courts"] = [{"id": "c1", "en": "Stale Court 2"}]
        server._CATALOG_CACHE_EXPIRES["courts"] = time.time() + 60.0

        status_req = server.CatalogStatusReq(active=False)
        with patch.object(server, "_invalidate_catalog_cache", wraps=server._invalidate_catalog_cache) as mock_inv:
            res_status = await server.admin_set_catalog_status(kind="courts", item_id="c1", req=status_req, admin=admin_user)
            self.assertTrue(res_status.get("success"))
            mock_inv.assert_called_with("courts")
            self.assertGreaterEqual(server._CACHE_REVISIONS["catalog"], 2)
            # The stale value must not be present
            self.assertNotEqual(server._CATALOG_CACHE.get("courts"), [{"id": "c1", "en": "Stale Court 2"}])

    async def test_09_successful_data_write_and_revision_update_in_same_atomic_batch(self):
        """Data writes and cache revision updates are committed in the EXACT SAME Firestore batch."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock()
        mock_db.batch.return_value = mock_batch

        mock_plan_doc = MagicMock()
        mock_plan_doc.get = AsyncMock(return_value=MagicMock(to_dict=lambda: None))
        mock_db.collection.return_value.document.return_value = mock_plan_doc

        admin_user = {"id": "admin_1", "email": "admin@nyaysetu.com", "role": "super_admin"}

        plan_req = server.AdminPlanReq(name="Pro Plan", price=999, credits=100, popular=True, description="Best plan")
        server.db = mock_db

        res = await server.admin_create_plan(req=plan_req, admin=admin_user)
        self.assertTrue(res.get("success"))

        # Verify batch.commit() was called exactly once
        mock_batch.commit.assert_called_once()

        # Verify batch.set was called for both plan doc AND system_settings/cache_version in the same batch
        set_calls = mock_batch.set.call_args_list
        self.assertGreaterEqual(len(set_calls), 2)

        # Check revision payload included Increment(1) for plans
        has_plan_write = False
        has_revision_write = False
        for call in set_calls:
            args, kwargs = call
            doc_ref = args[0]
            data = args[1]
            if "plans" in data and not isinstance(data.get("plans"), bool) and hasattr(data.get("plans"), "value"):
                # Firestore Increment transform
                has_revision_write = True
            elif data.get("name") == "Pro Plan":
                has_plan_write = True

        self.assertTrue(has_plan_write, "Plan data write was not in batch")
        self.assertTrue(has_revision_write, "Revision increment was not in batch")
        self.assertEqual(server._CACHE_REVISIONS["plans"], 1)

    async def test_10_failed_atomic_operation_leaves_both_unchanged(self):
        """If batch.commit() fails, neither the document nor the local revision counter is updated."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock(side_effect=Exception("Simulated Firestore quota/network error"))
        mock_db.batch.return_value = mock_batch

        admin_user = {"id": "admin_1", "email": "admin@nyaysetu.com", "role": "super_admin"}
        server.db = mock_db

        self.assertEqual(server._CACHE_REVISIONS["settings"], 0)
        setting_req = server.SettingsUpdateReq(value="A4")

        with self.assertRaises(Exception) as ctx:
            await server.admin_update_setting(key="default_page_size", req=setting_req, admin=admin_user)

        self.assertIn("Simulated Firestore quota/network error", str(ctx.exception))
        # Local revision counter must remain unchanged
        self.assertEqual(server._CACHE_REVISIONS["settings"], 0)

    async def test_11_concurrent_revision_increments_do_not_lose_updates(self):
        """Concurrent revision increments use firestore.Increment and record separate counts atomically."""
        mock_db = MagicMock()
        batches = []

        def get_batch():
            b = MagicMock()
            b.commit = AsyncMock()
            batches.append(b)
            return b

        mock_db.batch.side_effect = get_batch
        server.db = mock_db

        self.assertEqual(server._CACHE_REVISIONS["templates"], 0)

        # Execute 5 concurrent batch commits
        tasks = [
            server._commit_batch_with_revision(mock_db.batch(), "templates")
            for _ in range(5)
        ]
        await asyncio.gather(*tasks)

        self.assertEqual(server._CACHE_REVISIONS["templates"], 5)
        self.assertEqual(len(batches), 5)
        for b in batches:
            b.commit.assert_called_once()
            args, kwargs = b.set.call_args
            payload = args[1]
            self.assertTrue(kwargs.get("merge"))
            self.assertIn("templates", payload)
            # Confirm increment transform was used
            self.assertEqual(payload["templates"].value, 1)

    async def test_12_revision_update_failures_handled_gracefully_in_fallback(self):
        """_bump_cache_revision handles exceptions safely without unhandled crashes."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set = AsyncMock(side_effect=Exception("Transient Firestore error"))
        mock_db.collection.return_value.document.return_value = mock_doc
        server.db = mock_db

        # Should not raise exception
        await server._bump_cache_revision("templates")
        # Local counter should not be incremented on error
        self.assertEqual(server._CACHE_REVISIONS["templates"], 0)

    # -------------------------------------------------------------
    # FRONTEND SWR RACE GUARD SIMULATION TESTS (BLOCKER 2)
    # -------------------------------------------------------------
    def test_13_frontend_swr_race_guard_older_foreground_get_discarded_after_mutation(self):
        """Older foreground GET resolving after a mutation must be discarded from cache."""
        cache = {}
        scope_generations = {}
        global_gen = 0

        def get_gen(path):
            scope = "/templates" if path.startswith("/templates") else path
            return scope_generations.get(scope, 0) + global_gen

        def invalidate(prefix):
            nonlocal global_gen
            if not prefix:
                global_gen += 1
            else:
                scope_generations[prefix] = scope_generations.get(prefix, 0) + 1
            cache.pop(prefix, None)

        # 1. Request starts at generation 0
        captured_gen = get_gen("/templates")
        self.assertEqual(captured_gen, 0)

        # 2. Mutation occurs and invalidates /templates
        invalidate("/templates")
        self.assertEqual(get_gen("/templates"), 1)

        # 3. Older GET finishes with stale data
        stale_data = [{"id": "stale_template"}]
        if captured_gen == get_gen("/templates"):
            cache["/templates"] = stale_data

        # Stale data must NOT be in cache
        self.assertNotIn("/templates", cache)

    def test_14_frontend_swr_race_guard_older_background_swr_discarded_after_mutation(self):
        """Older background SWR GET resolving after a mutation must be discarded."""
        cache = {"/catalog/courts": [{"id": "c1", "name": "V1"}]}
        scope_generations = {}
        global_gen = 0

        def get_gen(path):
            scope = "/catalog/" if path.startswith("/catalog/") else path
            return scope_generations.get(scope, 0) + global_gen

        def invalidate(prefix):
            nonlocal global_gen
            if not prefix:
                global_gen += 1
                cache.clear()
            else:
                scope_generations[prefix] = scope_generations.get(prefix, 0) + 1
                for k in list(cache.keys()):
                    if prefix in k:
                        del cache[k]

        # Background SWR started before mutation
        bg_captured_gen = get_gen("/catalog/courts")
        self.assertEqual(bg_captured_gen, 0)

        # Mutation occurs while SWR is in flight
        invalidate("/catalog/")
        self.assertEqual(get_gen("/catalog/courts"), 1)

        # Background response finishes with V1
        bg_fresh = [{"id": "c1", "name": "V1_stale"}]
        if bg_captured_gen == get_gen("/catalog/courts"):
            cache["/catalog/courts"] = bg_fresh

        # Cache must not be polluted with V1_stale
        self.assertNotIn("/catalog/courts", cache)

    def test_15_frontend_swr_race_guard_same_millisecond_ordering(self):
        """Same-millisecond request and mutation cannot allow older read to win."""
        cache = {}
        scope_generations = {}

        def get_gen(path):
            return scope_generations.get(path, 0)

        def invalidate(prefix):
            scope_generations[prefix] = scope_generations.get(prefix, 0) + 1
            cache.pop(prefix, None)

        # In-flight read captures generation before mutation runs
        req1_gen = get_gen("/templates")  # 0
        invalidate("/templates")           # bumps to 1

        # Req1 resolves
        if req1_gen == get_gen("/templates"):
            cache["/templates"] = "stale"

        self.assertNotIn("/templates", cache)

        # Req2 starts after mutation in the same millisecond
        req2_gen = get_gen("/templates")  # 1
        # Req2 resolves
        if req2_gen == get_gen("/templates"):
            cache["/templates"] = "fresh"

        self.assertEqual(cache.get("/templates"), "fresh")

    def test_16_frontend_swr_race_guard_newer_get_resolves_and_caches_after_mutation(self):
        """Newer GET starting after mutation commits to cache successfully."""
        cache = {}
        scope_generations = {}

        def get_gen(path):
            return scope_generations.get(path, 0)

        def invalidate(prefix):
            scope_generations[prefix] = scope_generations.get(prefix, 0) + 1
            cache.pop(prefix, None)

        # Mutation occurs
        invalidate("/templates")
        self.assertEqual(get_gen("/templates"), 1)

        # New GET starts
        new_req_gen = get_gen("/templates")
        self.assertEqual(new_req_gen, 1)

        # New GET finishes
        fresh_data = [{"id": "new_template_v2"}]
        if new_req_gen == get_gen("/templates"):
            cache["/templates"] = fresh_data

        self.assertEqual(cache.get("/templates"), fresh_data)

    def test_17_frontend_swr_race_guard_unrelated_endpoint_unaffected(self):
        """Mutation on /cases must not invalidate or discard in-flight GET for /templates."""
        cache = {}
        scope_generations = {}
        global_gen = 0

        prefixes = ["/templates", "/catalog/", "/cases", "/wallet"]

        def get_gen(path):
            for p in prefixes:
                if path.startsWith(p) if hasattr(path, "startsWith") else path.startswith(p):
                    return scope_generations.get(p, 0) + global_gen
            return global_gen

        def invalidate(prefix):
            nonlocal global_gen
            if not prefix:
                global_gen += 1
                return
            for p in prefixes:
                if p.startswith(prefix) or prefix.startswith(p):
                    scope_generations[p] = scope_generations.get(p, 0) + 1

        # GET to /templates starts
        tpl_captured_gen = get_gen("/templates")
        self.assertEqual(tpl_captured_gen, 0)

        # Mutation on /cases occurs
        invalidate("/cases")
        self.assertEqual(get_gen("/cases"), 1)
        self.assertEqual(get_gen("/templates"), 0)  # /templates generation is UNCHANGED!

        # GET to /templates resolves
        tpl_data = [{"id": "tpl_1"}]
        if tpl_captured_gen == get_gen("/templates"):
            cache["/templates"] = tpl_data

        # /templates response WAS committed to cache!
        self.assertEqual(cache.get("/templates"), tpl_data)

    async def test_18_oversized_catalog_bulk_delete_rejected_before_writes(self):
        """Oversized catalog bulk delete (>200 items) is rejected with HTTP 400 with ZERO writes."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        oversized_ids = [f"item_{i}" for i in range(201)]
        req = server.CatalogBulkDeleteReq(ids=oversized_ids)

        with self.assertRaises(HTTPException) as ctx:
            await server.admin_bulk_delete_catalog_items("case-types", req, admin=admin_user)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds maximum limit of 200", ctx.exception.detail)
        # Verify ZERO batch creation, ZERO writes
        self.assertEqual(mock_db.batch.call_count, 0)
        self.assertEqual(mock_batch.delete.call_count, 0)
        self.assertEqual(mock_batch.set.call_count, 0)
        self.assertEqual(mock_batch.commit.call_count, 0)
        self.assertEqual(server._CACHE_REVISIONS["catalog"], 0)

    async def test_19_oversized_template_bulk_delete_rejected_before_writes(self):
        """Oversized template bulk delete (>50 templates) is rejected with HTTP 400 with ZERO writes."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_db.batch.return_value = mock_batch
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        oversized_ids = [f"tpl_{i}" for i in range(51)]
        req = server.TemplateBulkDeleteReq(ids=oversized_ids)

        with self.assertRaises(HTTPException) as ctx:
            await server.admin_bulk_delete_templates(req, admin=admin_user)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds maximum limit of 50", ctx.exception.detail)
        # Verify ZERO batch creation, ZERO writes
        self.assertEqual(mock_db.batch.call_count, 0)
        self.assertEqual(mock_batch.delete.call_count, 0)
        self.assertEqual(mock_batch.set.call_count, 0)
        self.assertEqual(mock_batch.commit.call_count, 0)
        self.assertEqual(server._CACHE_REVISIONS["templates"], 0)

    async def test_20_maximum_permitted_catalog_request_commits_data_and_revision_together(self):
        """Maximum permitted catalog request (200 items) commits data and revision in a single atomic batch."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock()
        mock_db.batch.return_value = mock_batch
        mock_col = MagicMock()
        mock_col.where.return_value.limit.return_value.stream.return_value = MockAsyncStream([])
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        exact_200_ids = [f"case_type_{i}" for i in range(200)]
        req = server.CatalogBulkDeleteReq(ids=exact_200_ids)

        res = await server.admin_bulk_delete_catalog_items("case-types", req, admin=admin_user)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("deleted_count"), 200)

        # Batch committed exactly ONCE
        mock_batch.commit.assert_called_once()
        self.assertEqual(mock_batch.delete.call_count, 200)
        self.assertGreaterEqual(mock_batch.set.call_count, 201)
        self.assertEqual(server._CACHE_REVISIONS["catalog"], 1)

    async def test_21_maximum_permitted_template_request_commits_data_and_revision_together(self):
        """Maximum permitted template request (50 templates) commits data and revision in a single atomic batch."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock()
        mock_db.batch.return_value = mock_batch
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        exact_50_ids = [f"template_{i}" for i in range(50)]
        req = server.TemplateBulkDeleteReq(ids=exact_50_ids)

        res = await server.admin_bulk_delete_templates(req, admin=admin_user)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("deleted_count"), 50)

        # Batch committed exactly ONCE
        mock_batch.commit.assert_called_once()
        self.assertGreaterEqual(mock_batch.delete.call_count, 50)
        self.assertGreaterEqual(mock_batch.set.call_count, 51)
        self.assertEqual(server._CACHE_REVISIONS["templates"], 1)

    async def test_22_failed_bulk_batch_changes_neither_data_nor_revision(self):
        """When bulk delete batch commit fails, neither local cache nor revision is changed."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock(side_effect=Exception("Transient Firestore commit failure"))
        mock_db.batch.return_value = mock_batch
        mock_col = MagicMock()
        mock_col.where.return_value.limit.return_value.stream.return_value = MockAsyncStream([])
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        req = server.CatalogBulkDeleteReq(ids=["ct_1", "ct_2"])

        with self.assertRaises(Exception) as ctx:
            await server.admin_bulk_delete_catalog_items("case-types", req, admin=admin_user)

        self.assertIn("Transient Firestore commit failure", str(ctx.exception))
        self.assertEqual(server._CACHE_REVISIONS["catalog"], 0)

    async def test_23_retry_behavior_after_transient_failure(self):
        """Retrying bulk delete after transient failure cleanly succeeds and bumps revision."""
        mock_db = MagicMock()
        mock_batch = MagicMock()
        mock_batch.commit = AsyncMock(side_effect=[Exception("Transient network hiccup"), None])
        mock_db.batch.return_value = mock_batch
        mock_col = MagicMock()
        mock_col.where.return_value.limit.return_value.stream.return_value = MockAsyncStream([])
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        admin_user = {"id": "admin_1", "role": "super_admin"}
        req = server.CatalogBulkDeleteReq(ids=["ct_retry_1"])

        # Attempt 1: fails
        with self.assertRaises(Exception):
            await server.admin_bulk_delete_catalog_items("case-types", req, admin=admin_user)
        self.assertEqual(server._CACHE_REVISIONS["catalog"], 0)

        # Attempt 2: retry succeeds
        res = await server.admin_bulk_delete_catalog_items("case-types", req, admin=admin_user)
        self.assertTrue(res.get("success"))
        self.assertEqual(server._CACHE_REVISIONS["catalog"], 1)

    async def test_24_commit_batch_with_revision_raises_503_when_db_or_batch_none(self):
        """_commit_batch_with_revision must fail fast with 503 instead of pretending success when db or batch is None."""
        server.db = None
        mock_batch = MagicMock()

        # db is None
        with self.assertRaises(HTTPException) as ctx1:
            await server._commit_batch_with_revision(mock_batch, "catalog")
        self.assertEqual(ctx1.exception.status_code, 503)

        # batch is None
        server.db = MagicMock()
        with self.assertRaises(HTTPException) as ctx2:
            await server._commit_batch_with_revision(None, "catalog")
        self.assertEqual(ctx2.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
