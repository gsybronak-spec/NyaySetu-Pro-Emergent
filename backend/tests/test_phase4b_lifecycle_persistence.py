"""Phase 4B Regression Tests: Backend Core & Lifecycle Hardening.

Verifies:
1. _SETTINGS_CACHE starts unpopulated and reads authoritative values from Firestore on cold starts.
2. _get_setting() falls back to _SETTING_DEFAULTS only when the document genuinely does not exist.
3. Archived canonical templates are never resurrected into the lawyer catalog.
4. Draft templates serve their latest published revision snapshot from template_revisions without resurrecting Python seeds.
5. Brand-new draft templates without published revisions remain strictly hidden from lawyers.
6. In-memory catalog maps are hydrated from Firestore via _ensure_catalog_maps_synced() on cold starts.
7. _commit_batch_with_revision() immediately invalidates local component cache on the writer instance.
8. _bump_cache_revision() immediately invalidates local component cache.
9. _get_published_templates() sorts according to the authoritative template_display_order setting.
"""

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from google.cloud import firestore

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


class TestPhase4BLifecyclePersistence(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.orig_db = server.db
        server.invalidate_settings_cache()
        server.invalidate_published_templates_cache()
        server._invalidate_catalog_cache()
        server.invalidate_plans_cache()

    def tearDown(self):
        server.db = self.orig_db
        server.invalidate_settings_cache()
        server.invalidate_published_templates_cache()
        server._invalidate_catalog_cache()
        server.invalidate_plans_cache()

    async def test_01_settings_cache_starts_unpopulated_and_reads_firestore_on_cold_start(self):
        """On cold start, _SETTINGS_CACHE must be empty and _get_setting() must read the live DB value."""
        server.invalidate_settings_cache()
        self.assertEqual(len(server._SETTINGS_CACHE), 0)

        # Mock DB returning custom signup credits (15 instead of default 10)
        mock_db = MagicMock()
        snap = MagicMock()
        snap.exists = True
        snap.to_dict.return_value = {"value": 15, "key": "signup_credits"}

        col = MagicMock()
        doc = MagicMock()
        doc.get = AsyncMock(return_value=snap)
        col.document.return_value = doc

        cv_snap = MagicMock()
        cv_snap.exists = True
        cv_snap.to_dict.return_value = {"settings": 0}
        sys_col = MagicMock()
        sys_doc = MagicMock()
        sys_doc.get = AsyncMock(return_value=cv_snap)
        sys_col.document.return_value = sys_doc

        def router(name):
            if name == "settings":
                return col
            if name == "system_settings":
                return sys_col
            return MagicMock()

        mock_db.collection.side_effect = router
        server.db = mock_db

        val = await server._get_setting("signup_credits")
        self.assertEqual(val, 15)
        # Should now be cached
        self.assertIn("signup_credits", server._SETTINGS_CACHE)
        self.assertEqual(server._SETTINGS_CACHE["signup_credits"]["value"], 15)

    async def test_02_get_setting_fallback_to_defaults_only_when_document_missing(self):
        """When Firestore document does not exist, _get_setting() safely uses _SETTING_DEFAULTS."""
        server.invalidate_settings_cache()
        mock_db = MagicMock()
        snap = MagicMock()
        snap.exists = False
        snap.to_dict.return_value = None

        col = MagicMock()
        doc = MagicMock()
        doc.get = AsyncMock(return_value=snap)
        col.document.return_value = doc

        mock_db.collection.return_value = col
        server.db = mock_db

        val = await server._get_setting("otp_max_attempts")
        self.assertEqual(val, server._SETTING_DEFAULTS["otp_max_attempts"])

    async def test_03_archived_canonical_template_is_never_resurrected(self):
        """An archived canonical template in Firestore must stay hidden and NEVER resurrect from Python seeds."""
        mock_db = MagicMock()
        server.invalidate_published_templates_cache()

        # Mock Firestore where 'exemption_arji' is archived
        archived_snap = MagicMock()
        archived_snap.to_dict.return_value = {
            "id": "exemption_arji",
            "name_en": "Exemption Arji",
            "status": "archived",
            "version": 1,
        }

        # Mock Firestore where 'closing_purshish' is published
        published_snap = MagicMock()
        published_snap.to_dict.return_value = {
            "id": "closing_purshish",
            "name_en": "Closing Purshish",
            "status": "published",
            "version": 1,
        }

        def col_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                col.stream.return_value = MockAsyncStream([])
                col.where.return_value.stream.return_value = MockAsyncStream([])
            elif name == "templates":
                def where_router(filter=None):
                    wcol = MagicMock()
                    # If querying status in ['draft', 'archived']
                    if filter and hasattr(filter, "value") and ("archived" in str(filter.value) or "draft" in str(filter.value)):
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([archived_snap])
                        wcol.stream.return_value = MockAsyncStream([archived_snap])
                    elif filter and hasattr(filter, "value") and filter.value == "published":
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([published_snap])
                        wcol.stream.return_value = MockAsyncStream([published_snap])
                    else:
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([])
                        wcol.stream.return_value = MockAsyncStream([])
                    return wcol
                col.where.side_effect = where_router
            elif name == "settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            elif name == "system_settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        published = await server._get_published_templates()
        published_ids = {t["id"] for t in published}

        # 'closing_purshish' must be present
        self.assertIn("closing_purshish", published_ids)
        # 'exemption_arji' MUST NOT be present (never resurrected from canonical seed map)
        self.assertNotIn("exemption_arji", published_ids)

    async def test_04_draft_template_serves_published_revision_snapshot(self):
        """When a canonical template is branched to draft v2, lawyers receive the published v1 revision snapshot."""
        mock_db = MagicMock()
        server.invalidate_published_templates_cache()

        # Draft v2 in templates
        draft_snap = MagicMock()
        draft_snap.to_dict.return_value = {
            "id": "dd_karavani_arji",
            "name_en": "DD Karavani (In-Progress Draft v2)",
            "status": "draft",
            "version": 2,
        }

        # Published v1 in template_revisions
        rev1_snap = MagicMock()
        rev1_snap.exists = True
        rev1_snap.to_dict.return_value = {
            "id": "dd_karavani_arji_1",
            "template_id": "dd_karavani_arji",
            "name_en": "DD Karavani (Approved Published v1)",
            "status": "published",
            "version": 1,
            "fields": [],
        }

        def col_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                col.stream.return_value = MockAsyncStream([])
                col.where.return_value.stream.return_value = MockAsyncStream([])
            elif name == "templates":
                def where_router(filter=None):
                    wcol = MagicMock()
                    if filter and hasattr(filter, "value") and ("archived" in str(filter.value) or "draft" in str(filter.value)):
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([draft_snap])
                        wcol.stream.return_value = MockAsyncStream([draft_snap])
                    else:
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([])
                        wcol.stream.return_value = MockAsyncStream([])
                    return wcol
                col.where.side_effect = where_router
            elif name == "template_revisions":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=rev1_snap)
                col.document.return_value = doc
            elif name in ("settings", "system_settings"):
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        published = await server._get_published_templates()
        dd_tpl = next((t for t in published if t["id"] == "dd_karavani_arji"), None)

        self.assertIsNotNone(dd_tpl)
        # Must serve the published v1 revision text, NOT the in-progress v2 draft text
        self.assertEqual(dd_tpl.get("name_en"), "DD Karavani (Approved Published v1)")
        self.assertEqual(dd_tpl.get("status"), "published")

    async def test_05_new_draft_template_without_revision_remains_hidden(self):
        """A newly created draft template (version 1) without any prior published revision must remain hidden."""
        mock_db = MagicMock()
        server.invalidate_published_templates_cache()

        new_draft_snap = MagicMock()
        new_draft_snap.to_dict.return_value = {
            "id": "new_unreleased_petition",
            "name_en": "New Unreleased Petition",
            "status": "draft",
            "version": 1,
        }

        def col_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                col.stream.return_value = MockAsyncStream([])
                col.where.return_value.stream.return_value = MockAsyncStream([])
            elif name == "templates":
                def where_router(filter=None):
                    wcol = MagicMock()
                    if filter and hasattr(filter, "value") and ("archived" in str(filter.value) or "draft" in str(filter.value)):
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([new_draft_snap])
                        wcol.stream.return_value = MockAsyncStream([new_draft_snap])
                    else:
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([])
                        wcol.stream.return_value = MockAsyncStream([])
                    return wcol
                col.where.side_effect = where_router
            elif name in ("settings", "system_settings", "template_revisions"):
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        published = await server._get_published_templates()
        published_ids = {t["id"] for t in published}

        self.assertNotIn("new_unreleased_petition", published_ids)

    async def test_06_catalog_maps_hydrated_from_firestore_on_cold_start(self):
        """_ensure_catalog_maps_synced() populates in-memory maps from Firestore."""
        server._CATALOG_MAPS_SYNCED = False
        mock_db = MagicMock()

        custom_court = {"id": "court_custom_ahmedabad_commercial", "en": "Ahmedabad Commercial Court", "active": True}
        court_snap = MagicMock()
        court_snap.to_dict.return_value = custom_court

        custom_dist = {"id": "district_gandhinagar_east", "en": "Gandhinagar East", "active": True}
        dist_snap = MagicMock()
        dist_snap.to_dict.return_value = custom_dist

        def col_router(name):
            col = MagicMock()
            if name == "courts":
                col.stream.return_value = MockAsyncStream([court_snap])
            elif name == "districts":
                col.stream.return_value = MockAsyncStream([dist_snap])
            elif name == "deleted_catalog_items":
                col.where.return_value.stream.return_value = MockAsyncStream([])
                col.stream.return_value = MockAsyncStream([])
            else:
                col.stream.return_value = MockAsyncStream([])
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        await server._ensure_catalog_maps_synced()

        self.assertTrue(server._CATALOG_MAPS_SYNCED)
        self.assertIn("court_custom_ahmedabad_commercial", server._COURT_MAP)
        self.assertIn("district_gandhinagar_east", server._DISTRICT_MAP)

    async def test_07_commit_batch_with_revision_invalidates_local_component_cache(self):
        """_commit_batch_with_revision() immediately invalidates local in-memory caches on the writer instance."""
        # Preload settings cache
        server._SETTINGS_CACHE["signup_credits"] = {"value": 99, "expires_at": time.time() + 300}
        self.assertIn("signup_credits", server._SETTINGS_CACHE)

        mock_db = MagicMock()
        batch = MagicMock()
        batch.commit = AsyncMock()

        server.db = mock_db
        await server._commit_batch_with_revision(batch, "settings")

        # Local settings cache must have been invalidated immediately
        self.assertEqual(len(server._SETTINGS_CACHE), 0)

    async def test_08_bump_cache_revision_invalidates_local_component_cache(self):
        """_bump_cache_revision() immediately invalidates local in-memory cache on fallback mutations."""
        server._PLANS_CACHE["data"] = [{"id": "test_plan"}]
        self.assertIsNotNone(server._PLANS_CACHE["data"])

        mock_db = MagicMock()
        doc = MagicMock()
        doc.set = AsyncMock()
        mock_db.collection.return_value.document.return_value = doc

        server.db = mock_db
        await server._bump_cache_revision("plans")

        self.assertIsNone(server._PLANS_CACHE["data"])

    async def test_09_canonical_template_display_order_honors_authoritative_settings(self):
        """_get_published_templates() orders templates using the authoritative template_display_order setting."""
        server.invalidate_published_templates_cache()
        server.invalidate_settings_cache()

        # Custom display order placing mudat_arji first and closing_purshish second
        custom_order = [
            "mudat_arji",
            "closing_purshish",
            "vakilatnama_civil",
            "vakilatnama_criminal",
            "document_exhibit_application",
        ]

        mock_db = MagicMock()

        snap_mudat = MagicMock()
        snap_mudat.to_dict.return_value = {"id": "mudat_arji", "status": "published", "name_en": "Mudat Arji"}

        snap_closing = MagicMock()
        snap_closing.to_dict.return_value = {"id": "closing_purshish", "status": "published", "name_en": "Closing Purshish"}

        def col_router(name):
            col = MagicMock()
            if name == "templates":
                def where_router(filter=None):
                    wcol = MagicMock()
                    if filter and hasattr(filter, "value") and filter.value == "published":
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([snap_mudat, snap_closing])
                    else:
                        wcol.limit.return_value.stream.return_value = MockAsyncStream([])
                    return wcol
                col.where.side_effect = where_router
            elif name == "settings":
                doc = MagicMock()
                snap = MagicMock()
                snap.exists = True
                snap.to_dict.return_value = {"value": custom_order}
                doc.get = AsyncMock(return_value=snap)
                col.document.return_value = doc
            elif name == "deleted_catalog_items":
                col.where.return_value.stream.return_value = MockAsyncStream([])
                col.stream.return_value = MockAsyncStream([])
            elif name == "system_settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=MagicMock(exists=False))
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = col_router
        server.db = mock_db

        templates = await server._get_published_templates()
        first_id = templates[0]["id"]
        second_id = templates[1]["id"]

        self.assertEqual(first_id, "mudat_arji")
        self.assertEqual(second_id, "closing_purshish")


if __name__ == "__main__":
    unittest.main()
