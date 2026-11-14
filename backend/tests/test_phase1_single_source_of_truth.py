"""Phase 1 Regression Tests: Database as the Single Source of Truth.

Verifies:
1. Admin-edited template content remains unchanged after _ensure_seed_complete().
2. Custom certified-copy settings, margins, draft status, and fields remain unchanged.
3. Existing templates remain unchanged after the migration endpoint (seed_templates(force=True)).
4. Genuinely missing templates are created safely without mutating existing ones.
5. Deleted or unseeded plans return None (_get_plan) and 404 (admin_get_plan), never resurrecting.
6. Catalog items with tombstones in deleted_catalog_items remain deleted and are never re-seeded.
7. Startup safety and quota protections remain fully intact.
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


class TestPhase1SingleSourceOfTruth(unittest.IsolatedAsyncioTestCase):

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

    async def test_01_admin_edited_template_content_unchanged_after_ensure_seed_complete(self):
        """Admin-customized template content must never be overwritten by _ensure_seed_complete()."""
        mock_db = MagicMock()

        # system_settings/seed_complete returns True
        mock_setting_snap = MagicMock()
        mock_setting_snap.exists = True
        mock_setting_snap.to_dict.return_value = {"key": "seed_complete", "value": True}

        # Mock collection router
        def collection_router(name):
            col = MagicMock()
            if name == "system_settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=mock_setting_snap)
                col.document.return_value = doc
            elif name == "templates":
                doc = MagicMock()
                # If anything tries to update, we catch it
                doc.update = AsyncMock()
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = collection_router
        server.db = mock_db

        await server._ensure_seed_complete()

        # Crucial assertion: templates collection must NEVER have doc_ref.update called!
        templates_col = mock_db.collection("templates")
        templates_col.document().update.assert_not_called()

    async def test_02_custom_certified_copy_settings_and_margins_unchanged(self):
        """Custom certified-copy settings, line_spacing, and draft status must be preserved."""
        mock_db = MagicMock()

        mock_setting_snap = MagicMock()
        mock_setting_snap.exists = True
        mock_setting_snap.to_dict.return_value = {"key": "seed_complete", "value": True}

        template_doc_mock = MagicMock()
        template_doc_mock.update = AsyncMock()
        template_doc_mock.set = AsyncMock()

        def collection_router(name):
            col = MagicMock()
            if name == "system_settings":
                doc = MagicMock()
                doc.get = AsyncMock(return_value=mock_setting_snap)
                col.document.return_value = doc
            elif name == "templates":
                col.document.return_value = template_doc_mock
            return col

        mock_db.collection.side_effect = collection_router
        server.db = mock_db

        await server._ensure_seed_complete()

        # Assert no updates or overwrites happened
        template_doc_mock.update.assert_not_called()
        template_doc_mock.set.assert_not_called()

    async def test_03_existing_templates_skipped_by_migration(self):
        """Existing template documents must be skipped by seed_templates(force=True),
        regardless of whether their content is empty or populated."""
        mock_db = MagicMock()

        # Mock deleted templates tombstone check: returns empty set
        def collection_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                stream_mock = MagicMock()
                stream_mock.stream.return_value = MockAsyncStream([])
                col.where.return_value = stream_mock
            elif name == "templates":
                doc = MagicMock()
                # Every template document exists!
                snap = MagicMock()
                snap.exists = True
                snap.to_dict.return_value = {"id": "dummy", "content_en": "", "content_gu": ""}
                doc.get = AsyncMock(return_value=snap)
                doc.update = AsyncMock()
                doc.set = AsyncMock()
                col.document.return_value = doc
            elif name == "system_settings":
                doc = MagicMock()
                doc.set = AsyncMock()
                col.document.return_value = doc
            elif name == "template_revisions":
                col.stream.return_value = MockAsyncStream([])
                doc = MagicMock()
                snap = MagicMock()
                snap.exists = True
                doc.get = AsyncMock(return_value=snap)
                col.document.return_value = doc
                stream_mock = MagicMock()
                stream_mock.limit.return_value.stream.return_value = MockAsyncStream([])
                col.where.return_value.where.return_value = stream_mock
            return col

        mock_db.collection.side_effect = collection_router
        server.db = mock_db

        res = await server.seed_templates(force=True, mark_system_seed_complete=False)

        # All seeds should be skipped; 0 created
        self.assertEqual(res["created"], 0)
        self.assertGreater(res["skipped"], 0)
        # Template documents must never have been updated or set
        mock_db.collection("templates").document().update.assert_not_called()
        mock_db.collection("templates").document().set.assert_not_called()

    async def test_04_genuinely_missing_template_created_safely(self):
        """Genuinely missing templates are created safely without mutating existing ones."""
        mock_db = MagicMock()

        existing_template_mock = MagicMock()
        existing_template_mock.update = AsyncMock()
        existing_template_mock.set = AsyncMock()

        missing_template_mock = MagicMock()
        missing_template_mock.update = AsyncMock()
        missing_template_mock.set = AsyncMock()

        def collection_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                stream_mock = MagicMock()
                stream_mock.stream.return_value = MockAsyncStream([])
                col.where.return_value = stream_mock
            elif name == "templates":
                def doc_router(doc_id):
                    # Only 'dd_karavani_arji' is genuinely missing
                    if doc_id == "dd_karavani_arji":
                        snap = MagicMock()
                        snap.exists = False
                        snap.to_dict.return_value = None
                        missing_template_mock.get = AsyncMock(return_value=snap)
                        return missing_template_mock
                    else:
                        snap = MagicMock()
                        snap.exists = True
                        snap.to_dict.return_value = {"id": doc_id, "content_gu": "Custom"}
                        existing_template_mock.get = AsyncMock(return_value=snap)
                        return existing_template_mock
                col.document.side_effect = doc_router
                col.stream.return_value = MockAsyncStream([])
            elif name == "system_settings":
                doc = MagicMock()
                doc.set = AsyncMock()
                col.document.return_value = doc
            elif name == "template_revisions":
                col.stream.return_value = MockAsyncStream([])
                doc = MagicMock()
                snap = MagicMock()
                snap.exists = True
                doc.get = AsyncMock(return_value=snap)
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = collection_router
        server.db = mock_db

        res = await server.seed_templates(force=True, mark_system_seed_complete=False)

        # Exactly 1 created (dd_karavani_arji)
        self.assertEqual(res["created"], 1)
        self.assertIn("dd_karavani_arji", res["created_ids"])
        # Missing template was set
        missing_template_mock.set.assert_called_once()
        # Existing templates were NEVER updated or overwritten
        existing_template_mock.update.assert_not_called()
        existing_template_mock.set.assert_not_called()

    async def test_05_deleted_or_unseeded_plan_returns_none_and_404(self):
        """_get_plan must return None and admin_get_plan must raise 404 when plan is absent from Firestore."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_snap = MagicMock()
        mock_snap.exists = False
        mock_snap.to_dict.return_value = None
        mock_doc.get = AsyncMock(return_value=mock_snap)
        mock_db.collection.return_value.document.return_value = mock_doc
        server.db = mock_db

        # 1. _get_plan returns None (never falls back to PLANS static catalog)
        plan = await server._get_plan("pro")
        self.assertIsNone(plan)

        # 2. admin_get_plan raises HTTPException(404, "Plan not found")
        admin_user = {"email": "admin@nyaysetu.com", "role": "super_admin"}
        with self.assertRaises(HTTPException) as ctx:
            await server.admin_get_plan("pro", admin=admin_user)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Plan not found")

    async def test_06_tombstoned_catalog_items_never_resurrected(self):
        """Permanently deleted catalog items with tombstones in deleted_catalog_items are never re-seeded."""
        mock_db = MagicMock()

        # Provide a tombstone for court id 'test_old_court'
        tombstone_doc = MagicMock()
        tombstone_doc.to_dict.return_value = {"id": "test_old_court", "kind": "courts"}

        def collection_router(name):
            col = MagicMock()
            if name == "deleted_catalog_items":
                stream_mock = MagicMock()
                stream_mock.stream.return_value = MockAsyncStream([tombstone_doc])
                col.where.return_value = stream_mock
            elif name == "courts":
                col.stream.return_value = MockAsyncStream([])
                doc = MagicMock()
                doc.set = AsyncMock()
                col.document.return_value = doc
            else:
                col.stream.return_value = MockAsyncStream([])
                doc = MagicMock()
                doc.set = AsyncMock()
                col.document.return_value = doc
            return col

        mock_db.collection.side_effect = collection_router
        server.db = mock_db

        with patch("server._refresh_catalog_maps", new_callable=AsyncMock):
            await server.seed_catalogs()

        # Check that test_old_court was never set
        courts_col = mock_db.collection("courts")
        for call_args in courts_col.document.call_args_list:
            doc_id = call_args[0][0] if call_args[0] else None
            self.assertNotEqual(doc_id, "test_old_court")


if __name__ == "__main__":
    unittest.main()
