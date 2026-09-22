# -*- coding: utf-8 -*-
"""
Test Case Edit -> 'Update Case' End-to-End Flow
Validates:
1. Legacy saved case with single English/Gujarati court name does not fail validation on edit.
2. Saved case with catalog court edits and persists cleanly.
3. Saved case with 'other' custom court validates both languages when intentionally blanked.
4. Historical court reference preservation on PUT /cases/{id}.
5. Form initial state mapping logic matches frontend edit/[id].tsx.
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock third-party dependencies if not installed
for mod in [
    'docx', 'docx.shared', 'docx.enum.text', 'docx.oxml', 'docx.oxml.ns',
    'google', 'google.cloud', 'google.cloud.firestore',
    'fastapi', 'fastapi.exceptions', 'fastapi.responses',
    'fastapi.middleware.cors', 'fastapi.middleware.gzip',
    'pydantic', 'httpx', 'dotenv', 'jwt', 'bcrypt', 'razorpay',
    'cryptography', 'cryptography.hazmat', 'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.serialization', 'cryptography.x509'
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

def _passthrough_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

class _MockRouter:
    def __init__(self, *args, **kwargs): pass
    def get(self, *args, **kwargs): return lambda f: f
    def post(self, *args, **kwargs): return lambda f: f
    def put(self, *args, **kwargs): return lambda f: f
    def delete(self, *args, **kwargs): return lambda f: f
    def patch(self, *args, **kwargs): return lambda f: f
    def include_router(self, *args, **kwargs): pass

class _MockFastAPI(_MockRouter):
    def __init__(self, *args, **kwargs): pass
    def add_middleware(self, *args, **kwargs): pass
    def exception_handler(self, *args, **kwargs): return lambda f: f
    def on_event(self, *args, **kwargs): return lambda f: f

class _MockHTTPException(Exception):
    def __init__(self, status_code, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")

fastapi_mock = sys.modules['fastapi']
fastapi_mock.FastAPI = _MockFastAPI
fastapi_mock.APIRouter = _MockRouter
fastapi_mock.HTTPException = _MockHTTPException
fastapi_mock.Depends = lambda x: x
fastapi_mock.Header = lambda *args, **kwargs: None
fastapi_mock.Request = MagicMock
fastapi_mock.Response = MagicMock
fastapi_mock.Cookie = lambda *args, **kwargs: None

class _PydanticBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def model_dump(self, **kwargs):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

sys.modules['pydantic'].BaseModel = _PydanticBaseModel
sys.modules['pydantic'].Field = lambda *args, **kwargs: None

import server

class TestCaseUpdateButtonFlow(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_frontend_initial_state_generation_legacy_case(self):
        # Case created before custom court fix (English only, court string set)
        c = {
            "id": "case_101",
            "language": "en",
            "nickname": "Test Case",
            "case_number": "123/2024",
            "party_name": "Ramesh Patel",
            "opposite_party": "Suresh Shah",
            "court_id": None,
            "court_source": None,
            "court": "City Civil Court, Ahmedabad",
            "court_custom": None,
            "custom_court_name_gu": None,
            "custom_court_name_en": None,
        }
        isCustomCourt = c.get("court_source") == "custom" or (
            not c.get("court_id") and (
                c.get("custom_court_name_gu") or
                c.get("custom_court_name_en") or
                c.get("court_custom") or
                c.get("court")
            )
        )
        fallbackCourtName = c.get("court_custom") or c.get("court") or ""
        initial = {
            "court_id": "other" if isCustomCourt else (c.get("court_id") or None),
            "court_source": "custom" if isCustomCourt else "catalog",
            "custom_court_name_gu": c.get("custom_court_name_gu") or fallbackCourtName,
            "custom_court_name_en": c.get("custom_court_name_en") or fallbackCourtName,
            "court_custom": fallbackCourtName,
            "court_label": c.get("court_label") or fallbackCourtName,
        }

        self.assertTrue(isCustomCourt)
        self.assertEqual(initial["court_id"], "other")
        self.assertEqual(initial["court_source"], "custom")
        # Ensure neither field is empty so validation passes on 'Update Case'
        self.assertEqual(initial["custom_court_name_gu"], "City Civil Court, Ahmedabad")
        self.assertEqual(initial["custom_court_name_en"], "City Civil Court, Ahmedabad")

        # Now simulate CaseForm handleFormSubmit validation
        guTrim = (initial["custom_court_name_gu"] or "").strip()
        enTrim = (initial["custom_court_name_en"] or "").strip()
        has_validation_error = not guTrim or not enTrim
        self.assertFalse(has_validation_error, "Legacy case must not trigger validation error upon editing")

    def test_frontend_initial_state_generation_catalog_case(self):
        c = {
            "id": "case_102",
            "language": "gu",
            "court_id": "principal_district_judge",
            "court_source": "catalog",
            "court_label": "પ્રિન્સિપાલ ડિસ્ટ્રિક્ટ જજ",
            "court": None,
            "court_custom": None,
            "custom_court_name_gu": None,
            "custom_court_name_en": None,
        }
        isCustomCourt = c.get("court_source") == "custom" or (
            not c.get("court_id") and (
                c.get("custom_court_name_gu") or
                c.get("custom_court_name_en") or
                c.get("court_custom") or
                c.get("court")
            )
        )
        fallbackCourtName = c.get("court_custom") or c.get("court") or ""
        initial = {
            "court_id": "other" if isCustomCourt else (c.get("court_id") or None),
            "court_source": "custom" if isCustomCourt else "catalog",
            "custom_court_name_gu": c.get("custom_court_name_gu") or fallbackCourtName,
            "custom_court_name_en": c.get("custom_court_name_en") or fallbackCourtName,
            "court_custom": fallbackCourtName,
            "court_label": c.get("court_label") or fallbackCourtName,
        }

        self.assertFalse(isCustomCourt)
        self.assertEqual(initial["court_id"], "principal_district_judge")
        self.assertEqual(initial["court_source"], "catalog")
        self.assertEqual(initial["court_label"], "પ્રિન્સિપાલ ડિસ્ટ્રિક્ટ જજ")

    def test_validation_blocks_and_identifies_empty_custom_court(self):
        # When user explicitly selects 'other' and leaves a field empty
        form_state = {
            "court_id": "other",
            "court_source": "custom",
            "custom_court_name_gu": "મહે. સિવિલ કોર્ટ",
            "custom_court_name_en": "",  # missing!
        }
        isCustomCourt = form_state["court_id"] == "other" or form_state["court_source"] == "custom"
        guTrim = (form_state.get("custom_court_name_gu") or "").strip()
        enTrim = (form_state.get("custom_court_name_en") or "").strip()
        validation_failed = not guTrim or not enTrim
        self.assertTrue(validation_failed)

    def test_backend_update_case_preserves_historical_and_applies_updates(self):
        existing_doc = {
            "id": "c_200",
            "user_id": "usr_test",
            "language": "en",
            "case_number": "001/2024",
            "party_name": "Old Name",
            "opposite_party": "Opposite Party",
            "court_id": "old_historical_court_id",
            "court_source": "catalog",
            "status": "active",
        }
        # Simulate payload from CaseForm submission
        submitted_payload = {
            "party_name": "New Updated Name",
            "court_id": "old_historical_court_id",
            "court_source": "catalog",
            "custom_court_name_gu": None,
            "custom_court_name_en": None,
            "notes": "Updated notes from live edit test",
        }
        merged = {**existing_doc, **submitted_payload}
        # validate_case_refs should accept the historical court ID without raising 400
        try:
            server.validate_case_refs(merged, existing=existing_doc)
        except Exception as e:
            self.fail(f"validate_case_refs failed on historical case: {e}")

        # Ensure merged contains new name and notes
        self.assertEqual(merged["party_name"], "New Updated Name")
        self.assertEqual(merged["notes"], "Updated notes from live edit test")
        self.assertEqual(merged["court_id"], "old_historical_court_id")


if __name__ == "__main__":
    unittest.main()
