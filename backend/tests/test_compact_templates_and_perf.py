import asyncio
import json
import os
import sys
import unittest
from unittest.mock import patch

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import server


class CompactTemplatesAndPerfTests(unittest.TestCase):
    def test_public_template_compact_strips_bloated_catalog_options_only(self):
        sample = {
            "id": "mudat_arji",
            "name_en": "Adjournment Application",
            "name_gu": "મુદત અરજી",
            "category": "General",
            "fields": [
                {"key": "district", "label_en": "District", "label_gu": "જિલ્લો", "type": "select", "required": True, "options": [{"id": "d1"}]},
                {"key": "taluka", "label_en": "Taluka", "label_gu": "તાલુકો", "type": "select", "required": False, "options": [{"id": f"t{i}"} for i in range(255)]},
                {"key": "adjournment_reason", "label_en": "Reason", "label_gu": "કારણ", "type": "select", "required": True, "options": [{"value": "sick", "label_en": "Sick"}]},
            ],
        }
        full_shape = server.public_template(sample, compact=False)
        compact_shape = server.public_template(sample, compact=True)

        self.assertEqual(set(compact_shape.keys()), {"id", "name_en", "name_gu", "category", "fields"})
        full_taluka = next(f for f in full_shape["fields"] if f["key"] == "taluka")
        compact_taluka = next(f for f in compact_shape["fields"] if f["key"] == "taluka")
        self.assertEqual(len(full_taluka["options"]), 255)
        self.assertNotIn("options", compact_taluka)

        compact_reason = next(f for f in compact_shape["fields"] if f["key"] == "adjournment_reason")
        self.assertIn("options", compact_reason)
        self.assertEqual(len(compact_reason["options"]), 1)
        self.assertLess(len(json.dumps(compact_shape)), len(json.dumps(full_shape)) // 2)

    def test_list_and_get_template_support_compact(self):
        sample = {
            "id": "mudat_arji",
            "name_en": "Adjournment Application",
            "name_gu": "મુદત અરજી",
            "category": "General",
            "fields": [
                {"key": "taluka", "label_en": "Taluka", "label_gu": "તાલુકો", "type": "select", "required": False, "options": [{"id": f"t{i}"} for i in range(50)]},
                {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
            ],
            "content_en": "Body {{date}}",
            "content_gu": "લખાણ {{date}}",
        }

        async def _run():
            with patch.object(server, "_get_published_templates", return_value=[sample]), patch.object(
                server, "_get_template_by_id", return_value=sample
            ):
                compact_list = await server.list_templates(compact=True, authorization=None)
                self.assertEqual(len(compact_list), 1)
                self.assertNotIn("options", compact_list[0]["fields"][0])

                full_list = await server.list_templates(compact=False, authorization=None)
                self.assertEqual(len(full_list[0]["fields"][0]["options"]), 50)

                compact_single = await server.get_template("mudat_arji", compact=True)
                self.assertNotIn("options", compact_single["fields"][0])
                self.assertEqual(compact_single["content_gu"], "લખાણ {{date}}")

        asyncio.run(_run())

    def test_resolve_court_label_skips_firestore_for_non_id_strings(self):
        called_docs = []

        class FakeCourtsCollection:
            def document(self, doc_id):
                called_docs.append(doc_id)
                raise AssertionError(f"Should not query Firestore for non-ID court name: {doc_id}")

        class FakeDb:
            def collection(self, name):
                return FakeCourtsCollection()

        async def _run():
            with patch.object(server, "db", FakeDb()), patch.object(server, "_load_catalog", return_value=[]):
                res = await server.resolve_court_label("મહે. પ્રિન્સિપાલ સિવિલ જજ સાહેબશ્રીની કોર્ટ", "gu", case=None)
                self.assertIn("પ્રિન્સિપાલ સિવિલ જજ", res)
                self.assertEqual(called_docs, [])

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
