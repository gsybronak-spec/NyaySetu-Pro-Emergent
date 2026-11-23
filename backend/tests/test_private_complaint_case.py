import unittest
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

class TestPrivateComplaintCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        server._CATALOG_MAPS_SYNCED = True

    def test_enrich_case_private_complaint_clears_police_station(self):
        raw_case = {
            "id": "case-123",
            "complaint_type": "private",
            "police_station": "City PS",
            "police_station_id": "ps_1",
            "police_station_custom": "City PS Custom",
        }
        enriched = server.enrich_case(dict(raw_case))
        self.assertIsNone(enriched["police_station_label"])
        self.assertIsNone(enriched["police_station"])
        self.assertIsNone(enriched["police_station_id"])
        self.assertIsNone(enriched["police_station_custom"])

    def test_validate_case_refs_passes_without_police_station_for_private_complaint(self):
        case_data = {
            "case_type_id": "criminal_case",
            "complaint_type": "private",
            "district_id": "dahod",
            # No police_station_id or fir_number
        }
        server._VALID_CASE_TYPE_IDS.add("criminal_case")
        server._VALID_DISTRICT_IDS.add("dahod")
        try:
            server.validate_case_refs(case_data)
        except Exception as e:
            self.fail(f"validate_case_refs failed for private complaint: {e}")

if __name__ == "__main__":
    unittest.main()
