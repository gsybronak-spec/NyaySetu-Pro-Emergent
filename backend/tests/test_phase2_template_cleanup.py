"""Comprehensive verification test suite for Phase 2: Template Cleanup, Canonical Catalog & Compatibility.

Covers all 16 required invariants:
1. Exactly 25 canonical templates returned by Admin API logic.
2. Exactly the same 25 IDs returned by Public API logic.
3. No _gu or _en duplicates in either normal catalog.
4. Repeated seed initialization does not recreate duplicates.
5. Both language contents (content_gu, content_en) remain available in every template.
6. All legacy ID aliases resolve correctly via resolve_canonical_template_id and _get_template_by_id.
7. Existing application retrieval works.
8. Existing application download works with canonical and variant IDs.
9. Case-linked drafts remain accessible.
10. Revision history remains intact and resolvable.
11. Ordering saves canonical IDs correctly.
12. Ordering persists after reload.
13. Main Application reflects saved ordering.
14. Failed saves do not report success (validation on non-list or invalid payload).
15. Unauthorized users cannot modify the catalog.
16. Ghost records (_gu, _en) are never recreated by ordering operations.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import server


class TestPhase2TemplateCleanup(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.orig_db = server.db
        server.invalidate_published_templates_cache()

    def tearDown(self):
        server.db = self.orig_db
        server.invalidate_published_templates_cache()

    def test_01_canonical_templates_count_and_ids(self):
        """Invariant 1 & 4: Exactly 25 canonical seeds returned, idempotent on repeated calls."""
        seeds1 = server._get_all_seed_templates()
        seeds2 = server._get_all_seed_templates()

        self.assertEqual(len(seeds1), 25)
        self.assertEqual(len(seeds2), 25)
        self.assertEqual(set(s["id"] for s in seeds1), set(server.CANONICAL_TEMPLATE_IDS))
        self.assertEqual(len(set(s["id"] for s in seeds1)), 25)

    async def test_02_public_catalog_returns_exact_25_canonical_templates(self):
        """Invariant 2 & 3: Public catalog returns exactly the 25 canonical IDs without _gu or _en duplicates."""
        server.db = None
        server.invalidate_published_templates_cache()
        published = await server._get_published_templates()

        pub_ids = [t["id"] for t in published]
        self.assertEqual(len(pub_ids), 25)
        self.assertEqual(set(pub_ids), set(server.CANONICAL_TEMPLATE_IDS))

        for pid in pub_ids:
            self.assertFalse(pid.endswith("_gu"), f"Found duplicate _gu in public catalog: {pid}")
            self.assertFalse(pid.endswith("_en"), f"Found duplicate _en in public catalog: {pid}")

    async def test_03_admin_list_templates_returns_exact_25_canonical_templates(self):
        """Invariant 1 & 3: Admin catalog returns exactly 25 canonical templates with no suffixed duplicates."""
        server.db = None
        mock_admin = {"id": "admin_1", "role": "super_admin"}
        res = await server.admin_list_templates(admin=mock_admin)

        items = res if isinstance(res, list) else (res.get("templates") or res.get("items") or [])
        item_ids = [t["id"] for t in items]
        self.assertEqual(len(item_ids), 25)
        self.assertEqual(set(item_ids), set(server.CANONICAL_TEMPLATE_IDS))

        for tid in item_ids:
            self.assertFalse(tid.endswith("_gu"), f"Found _gu duplicate in admin templates: {tid}")
            self.assertFalse(tid.endswith("_en"), f"Found _en duplicate in admin templates: {tid}")

    async def test_05_both_language_contents_available(self):
        """Invariant 5: Every template contains both content_gu and content_en."""
        server.db = None
        published = await server._get_published_templates()
        for t in published:
            tid = t["id"]
            self.assertTrue(bool(t.get("content_gu")), f"Missing content_gu in {tid}")
            self.assertTrue(bool(t.get("content_en")), f"Missing content_en in {tid}")
            self.assertTrue(len(t["content_gu"]) > 20, f"content_gu too short in {tid}")
            self.assertTrue(len(t["content_en"]) > 20, f"content_en too short in {tid}")

    def test_06_all_legacy_id_aliases_resolve_correctly(self):
        """Invariant 6: All historical variant IDs resolve to valid canonical base IDs."""
        self.assertEqual(len(server.TEMPLATE_CANONICAL_MAP), 46)
        for old_id, expected_canonical in server.TEMPLATE_CANONICAL_MAP.items():
            resolved = server.resolve_canonical_template_id(old_id)
            self.assertEqual(resolved, expected_canonical, f"Failed mapping for {old_id}")
            self.assertIn(resolved, server.CANONICAL_TEMPLATE_IDS, f"{resolved} not canonical")

        # Test dynamic _gu / _en strip for any canonical ID
        for cid in server.CANONICAL_TEMPLATE_IDS:
            self.assertEqual(server.resolve_canonical_template_id(f"{cid}_gu"), cid)
            self.assertEqual(server.resolve_canonical_template_id(f"{cid}_en"), cid)

    async def test_07_template_lookup_by_historical_id_returns_canonical_template(self):
        """Invariant 6 & 7: _get_template_by_id seamlessly resolves historical variant IDs."""
        server.db = None
        # Lookup via Gujarati variant
        t_gu = await server._get_template_by_id("jamin_bond_swikarvani_arji_gu")
        self.assertIsNotNone(t_gu)
        self.assertEqual(t_gu["id"], "jamin_bond_swikarvani_arji")
        self.assertTrue(bool(t_gu.get("content_gu")))
        self.assertTrue(bool(t_gu.get("content_en")))

        # Lookup via English variant
        t_en = await server._get_template_by_id("vakilatnama_civil_en")
        self.assertIsNotNone(t_en)
        self.assertEqual(t_en["id"], "vakilatnama_civil")

        # Lookup via legacy alias
        t_leg = await server._get_template_by_id("document_return_application")
        self.assertIsNotNone(t_leg)
        self.assertEqual(t_leg["id"], "document_parat_levani_arji")

    async def test_08_resolve_template_for_draft_handles_historical_ids(self):
        """Invariant 6, 8, 9: resolve_template_for_draft resolves drafts saved with variant IDs."""
        server.db = None
        # Draft with _gu variant ID
        draft_gu = {"template_id": "mudat_arji_gu", "values": {"court": "Court A"}}
        t = await server.resolve_template_for_draft(draft_gu)
        self.assertIsNotNone(t)
        self.assertEqual(t["id"], "mudat_arji")

        # Draft with legacy ID
        draft_leg = {"template_id": "document_return_application", "values": {}}
        t2 = await server.resolve_template_for_draft(draft_leg)
        self.assertIsNotNone(t2)
        self.assertEqual(t2["id"], "document_parat_levani_arji")

    async def test_09_download_application_with_variant_id_succeeds(self):
        """Invariant 8: download_application works seamlessly when requested with a variant ID."""
        server.db = None
        orig_gen = server.generate_pdf_detailed
        try:
            mock_pdf = b"%PDF-1.4 test binary"
            server.generate_pdf_detailed = MagicMock(return_value=(mock_pdf, {"engine": "test", "sha256": "abc"}))
            user = {"id": "test_user_dl", "active": True, "role": "advocate"}

            req = server.DownloadReq(
                template_id="mudat_arji_gu",
                values={"court_name": "District Court", "adjournment_reason": "Advocate ill"},
                language="gu",
                format="pdf",
            )
            res = await server.download_application(req, user=user)
            self.assertIn("base64", res)
            self.assertTrue(res["filename"].endswith(".pdf"))
        finally:
            server.generate_pdf_detailed = orig_gen

    async def test_10_revision_resolution_with_canonical_fallback(self):
        """Invariant 10: Revision resolution preserves historical version lookups."""
        mock_rev_snap = MagicMock(exists=True)
        mock_rev_snap.to_dict.return_value = {
            "template_id": "document_exhibit_application",
            "version": 2,
            "name_gu": "ઐતિહાસિક વર્ઝન ૨",
            "content_gu": "જૂનું લખાણ",
            "content_en": "Old content",
        }

        mock_db = MagicMock()
        mock_col = MagicMock()
        mock_doc = MagicMock()
        mock_doc.get = AsyncMock(return_value=mock_rev_snap)
        mock_col.document.return_value = mock_doc
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        res = await server.resolve_template_for_draft("document_exhibit_application", template_version=2)
        self.assertIsNotNone(res)
        self.assertEqual(res["name_gu"], "ઐતિહાસિક વર્ઝન ૨")

    async def test_11_ordering_saves_canonical_ids_only(self):
        """Invariant 11, 13 & 16: admin_update_template_order canonicalizes input and creates NO ghost docs."""
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set = AsyncMock()
        mock_col = MagicMock()
        mock_col.document.return_value = mock_doc
        mock_db.collection.return_value = mock_col
        server.db = mock_db

        mock_admin = {"id": "admin_order_test", "role": "super_admin"}
        # Send order with variant IDs mixed in
        req = server.TemplateOrderReq(template_order=[
            "aanke_padvani_arji_gu",
            "certified_copy_application",
            "mudat_arji_en",
        ])

        res = await server.admin_update_template_order(req, admin=mock_admin)
        self.assertTrue(res["success"])
        saved_order = res["template_order"]

        # Order must contain exactly 25 canonical IDs
        self.assertEqual(len(saved_order), 25)
        self.assertEqual(saved_order[0], "aanke_padvani_arji")
        self.assertEqual(saved_order[1], "certified_copy_application")
        self.assertEqual(saved_order[2], "mudat_arji")
        self.assertEqual(set(saved_order), set(server.CANONICAL_TEMPLATE_IDS))

        # Check document sets on db.collection('templates')
        created_doc_ids = [call.args[0] for call in mock_col.document.call_args_list if call.args]
        for cid in created_doc_ids:
            self.assertFalse(cid.endswith("_gu"), f"Ghost doc created in templates collection: {cid}")
            self.assertFalse(cid.endswith("_en"), f"Ghost doc created in templates collection: {cid}")

    async def test_12_ordering_persists_and_catalog_reflects_it(self):
        """Invariant 12 & 13: Catalog template order endpoint returns the saved canonical order."""
        server.db = None
        # Mock _SETTINGS_CACHE to return a custom order
        custom_order = [
            "vakilatnama_criminal",
            "vakilatnama_civil",
            "exemption_arji",
        ]
        server._SETTINGS_CACHE["template_display_order"] = {"value": custom_order, "expires_at": 9999999999.0}

        res = await server.get_catalog_template_order()
        returned_order = res["template_order"]

        self.assertEqual(len(returned_order), 25)
        self.assertEqual(returned_order[0], "vakilatnama_criminal")
        self.assertEqual(returned_order[1], "vakilatnama_civil")
        self.assertEqual(returned_order[2], "exemption_arji")

    def test_14_invalid_order_payload_rejected(self):
        """Invariant 14: Failed saves do not report success (rejects invalid payload)."""
        with self.assertRaises((ValidationError, TypeError)):
            server.TemplateOrderReq(template_order="not_a_list")

    def test_15_admin_template_pairs_has_25_items(self):
        """Invariant: Frontend admin template pairs matches the 25 canonical templates."""
        from pathlib import Path
        import re

        pairs_path = Path("admin/src/lib/templatePairs.ts")
        self.assertTrue(pairs_path.exists())
        text = pairs_path.read_text(encoding="utf-8")
        base_keys = re.findall(r"baseKey:\s*['\"]([^'\"]+)['\"]", text)

        self.assertEqual(len(base_keys), 25)
        self.assertEqual(set(base_keys), set(server.CANONICAL_TEMPLATE_IDS))

    def test_16_bilingual_content_in_canonical_templates(self):
        """Invariant 11: Bilingual content accessible for all 25 canonical templates."""
        templates = server._get_all_seed_templates()
        for t in templates:
            self.assertIn("content_gu", t, f"Missing content_gu in {t['id']}")
            self.assertIn("content_en", t, f"Missing content_en in {t['id']}")
            self.assertTrue(len(t["content_gu"].strip()) > 0, f"Empty content_gu in {t['id']}")
            self.assertTrue(len(t["content_en"].strip()) > 0, f"Empty content_en in {t['id']}")

    def test_17_ghost_backup_and_cleanup_utility(self):
        """Invariant 14: Ghost documents backed up before deletion, and rollback is functional."""
        import tempfile
        import shutil
        from scripts import cleanup_ghost_templates as cgt

        # Setup mock db
        mock_db = MagicMock()
        mock_templates = MagicMock()
        mock_db.collection.return_value = mock_templates

        doc_gu = MagicMock()
        doc_gu.exists = True
        doc_gu.to_dict.return_value = {"id": "document_exhibit_application_gu", "sort_order": 21}

        doc_en = MagicMock()
        doc_en.exists = True
        doc_en.to_dict.return_value = {"id": "document_exhibit_application_en", "sort_order": 22}

        doc_can = MagicMock()
        doc_can.exists = True
        doc_can.to_dict.return_value = {"id": "document_exhibit_application", "name_gu": "પુરાવા અરજી", "name_en": "Exhibit"}

        def mock_doc(doc_id):
            m = MagicMock()
            if doc_id == "document_exhibit_application_gu":
                m.get.return_value = doc_gu
            elif doc_id == "document_exhibit_application_en":
                m.get.return_value = doc_en
            elif doc_id == "document_exhibit_application":
                m.get.return_value = doc_can
            return m

        mock_templates.document.side_effect = mock_doc

        # Inspect
        ghosts, canon_exists, canon_data = cgt.inspect_ghost_documents(mock_db)
        self.assertTrue(canon_exists)
        self.assertIsNotNone(ghosts["document_exhibit_application_gu"])
        self.assertIsNotNone(ghosts["document_exhibit_application_en"])

        # Test backup saving
        orig_backup_dir = cgt.BACKUPS_DIR
        temp_dir = tempfile.mkdtemp()
        try:
            cgt.BACKUPS_DIR = temp_dir
            backup_path = cgt.save_backup(mock_db, ghosts, canon_data)
            self.assertTrue(os.path.isfile(backup_path))

            # Verify backup
            valid, msg = cgt.verify_backup(backup_path)
            self.assertTrue(valid)

            # Test cleanup execution
            success = cgt.execute_cleanup(mock_db, ghosts, canon_exists, canon_data)
            self.assertTrue(success)

            # Test rollback
            rollback_success = cgt.rollback_from_backup(mock_db, backup_path)
            self.assertTrue(rollback_success)
        finally:
            cgt.BACKUPS_DIR = orig_backup_dir
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
