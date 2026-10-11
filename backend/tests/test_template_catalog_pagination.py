# -*- coding: utf-8 -*-
"""Unit tests for Backend Template Catalog & Full List Availability.

Verifies:
1. Backend _get_published_templates() returns all published templates without server-side limit of 10.
2. Published templates cover all 25 canonical base legal applications (9 protected + 14 ODT + 2 general).
3. Public template listing endpoint returns complete list for client-side batching.
"""
import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import server


class TestTemplateCatalogBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def test_published_templates_count_and_completeness(self):
        """Backend must provide all published templates, never truncated to 10."""
        published = self.loop.run_until_complete(server._get_published_templates())
        self.assertGreaterEqual(len(published), 25, f"Expected at least 25 templates, got {len(published)}")
        self.assertEqual(len(published), 40, f"Expected 40 published documents, got {len(published)}")

    def test_base_keys_cover_all_25_applications(self):
        """Extracting base keys from published templates must yield 25 unique legal applications."""
        published = self.loop.run_until_complete(server._get_published_templates())

        base_keys = set()
        for t in published:
            tid = t.get("id") or t.get("template_id") or ""
            base = t.get("base_key") or (tid[:-3] if tid.endswith(("_gu", "_en")) else tid)
            base_keys.add(base)

        expected_9_protected = {
            "aanke_padvani_arji",
            "certified_report",
            "closing_purshish",
            "closing_argument_right_application",
            "reopen_right_to_argue_application",
            "dd_karavani_arji",
            "exemption_arji",
            "vakilatnama_civil",
            "vakilatnama_criminal",
        }
        for k in expected_9_protected:
            self.assertIn(k, base_keys, f"Protected template {k} missing from published catalog")

        expected_14_target = {
            "document_parat_levani_arji",
            "document_swikaravani_arji",
            "fs_no_haq_bandh_karvani_arji",
            "fs_no_haq_kholvani_arji",
            "jamin_bond_swikarvani_arji",
            "kam_board_par_levani_arji",
            "mudat_arji",
            "saaxi_ne_summons",
            "samadhan_purshish",
            "ulat_tapas_no_haq_bandh_karavani_arji",
            "ulat_tapas_no_haq_kholvani_arji",
            "undertaking",
            "warrant_no_hath_bido_apvani_arji",
            "warrant_rad_karvani_arji",
        }
        for k in expected_14_target:
            self.assertIn(k, base_keys, f"Target template {k} missing from published catalog")

        self.assertGreaterEqual(len(base_keys), 25, f"Expected 25 unique base keys, got {len(base_keys)}")

    def test_list_templates_api_returns_all_without_limit(self):
        """list_templates endpoint must return all published templates when no query is passed."""
        items = self.loop.run_until_complete(server.list_templates(q=None, category=None, authorization=None))
        self.assertEqual(len(items), 40, f"Expected list_templates to return all 40 published templates, got {len(items)}")

        # Verify items have required frontend fields
        for item in items:
            self.assertIn("id", item)
            self.assertIn("name_gu", item)
            self.assertIn("name_en", item)
            self.assertIn("category", item)
            self.assertIn("fields", item)


if __name__ == "__main__":
    unittest.main()
