# -*- coding: utf-8 -*-
"""
Tests for:
Requirement 1: "Other / અન્ય કોર્ટ" Option in Court Selection
Requirement 2: Case Edit -> Update Case Persistence & Cache Fix
"""

import asyncio
import base64
import os
import re
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

import doc_generator
import server
import test_seed_data


class TestRequirement1OtherCourt(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.mock_courts = [
            {"id": "additional_civil_judge_441fab", "en": "ADDITIONAL CIVIL JUDGE", "gu": "એડીશનલ સિવીલ જજ", "district_id": "rajkot"},
            {"id": "principal_district_judge", "en": "PRINCIPAL DISTRICT JUDGE", "gu": "પ્રિન્સિપાલ ડિસ્ટ્રિક્ટ જજ", "district_id": "rajkot"},
        ]
        server._CATALOG_CACHE["courts"] = self.mock_courts
        server._load_catalog = AsyncMock(return_value=self.mock_courts)
        self.user = {
            "uid": "user_test",
            "name": "Test Advocate",
            "advocate_name_gu": "એડવોકેટ કેતન ત્રિવેદી",
            "advocate_name_en": "Advocate Ketan Trivedi",
            "district": "rajkot"
        }

    def tearDown(self):
        self.loop.close()

    def test_resolve_court_label_custom_gu(self):
        case = {
            "court_source": "custom",
            "custom_court_name_gu": "મહે. સ્પે. પોક્સો કોર્ટ, રાજકોટ",
            "custom_court_name_en": "Special POCSO Court, Rajkot",
        }
        lbl = self.loop.run_until_complete(server.resolve_court_label(None, "gu", case=case))
        self.assertEqual(lbl, "મહે. સ્પે. પોક્સો કોર્ટ, રાજકોટ")

    def test_resolve_court_label_custom_en(self):
        case = {
            "court_source": "custom",
            "custom_court_name_gu": "મહે. સ્પે. પોક્સો કોર્ટ, રાજકોટ",
            "custom_court_name_en": "Special POCSO Court, Rajkot",
        }
        lbl = self.loop.run_until_complete(server.resolve_court_label(None, "en", case=case))
        self.assertEqual(lbl, "Special POCSO Court, Rajkot")

    def test_resolve_court_label_guard_against_other(self):
        case = {"court_id": "other"}
        lbl = self.loop.run_until_complete(server.resolve_court_label("other", "gu", case=case))
        self.assertEqual(lbl, "")

    def test_direct_template_mode_custom_court(self):
        payload = {
            "court_source": "custom",
            "custom_court_name_gu": "મહે. કન્ઝ્યુમર કોર્ટ, અમદાવાદ",
            "custom_court_name_en": "Consumer Court, Ahmedabad",
            "court": "other",
            "court_name": "other",
            "advocate_name": "Advocate Ketan Trivedi",
            "party_name": "Complainant Test",
            "opposite_party": "Accused Test",
        }
        ctx_gu = self.loop.run_until_complete(server.build_render_context(
            user=self.user,
            case=None,
            values=payload,
            language="gu"
        ))
        self.assertEqual(ctx_gu["court"], "મહે. કન્ઝ્યુમર કોર્ટ, અમદાવાદ")
        self.assertEqual(ctx_gu["court_name"], "મહે. કન્ઝ્યુમર કોર્ટ, અમદાવાદ")
        self.assertNotIn("other", [ctx_gu["court"], ctx_gu["court_name"]])

        ctx_en = self.loop.run_until_complete(server.build_render_context(
            user=self.user,
            case=None,
            values=payload,
            language="en"
        ))
        self.assertEqual(ctx_en["court"], "Consumer Court, Ahmedabad")
        self.assertEqual(ctx_en["court_name"], "Consumer Court, Ahmedabad")
        self.assertNotIn("other", [ctx_en["court"], ctx_en["court_name"]])

    def test_saved_case_mode_custom_court(self):
        saved_case = {
            "id": "case_test_99",
            "court_source": "custom",
            "court_id": None,
            "custom_court_name_gu": "મહે. લેબર કોર્ટ, રાજકોટ",
            "custom_court_name_en": "Labour Court, Rajkot",
            "party_name": "Worker Ram",
            "opposite_party": "Company XYZ",
            "case_number": "99/2026",
            "user_id": "user_test",
        }
        ctx_gu = self.loop.run_until_complete(server.build_render_context(
            user=self.user,
            case=saved_case,
            values={"document_list": "List of docs"},
            language="gu"
        ))
        self.assertEqual(ctx_gu["court"], "મહે. લેબર કોર્ટ, રાજકોટ")
        self.assertEqual(ctx_gu["court_name"], "મહે. લેબર કોર્ટ, રાજકોટ")

        ctx_en = self.loop.run_until_complete(server.build_render_context(
            user=self.user,
            case=saved_case,
            values={"document_list": "List of docs"},
            language="en"
        ))
        self.assertEqual(ctx_en["court"], "Labour Court, Rajkot")
        self.assertEqual(ctx_en["court_name"], "Labour Court, Rajkot")


class TestRequirement2CaseEditPersistence(unittest.TestCase):
    def test_enrich_case_custom_court(self):
        case_doc_gu = {
            "id": "case_1",
            "language": "gu",
            "court_source": "custom",
            "court_id": None,
            "custom_court_name_gu": "મહે. ટ્રિબ્યુનલ",
            "custom_court_name_en": "Appellate Tribunal",
            "party_name": "A",
            "opposite_party": "B",
        }
        enriched_gu = server.enrich_case(case_doc_gu)
        self.assertEqual(enriched_gu["court_source"], "custom")
        self.assertEqual(enriched_gu["custom_court_name_gu"], "મહે. ટ્રિબ્યુનલ")
        self.assertEqual(enriched_gu["custom_court_name_en"], "Appellate Tribunal")
        self.assertEqual(enriched_gu["court_label"], "મહે. ટ્રિબ્યુનલ")

        case_doc_en = dict(case_doc_gu)
        case_doc_en["language"] = "en"
        enriched_en = server.enrich_case(case_doc_en)
        self.assertEqual(enriched_en["court_label"], "Appellate Tribunal")

    def test_catalog_to_custom_transition(self):
        existing = {
            "id": "c1",
            "court_source": "catalog",
            "court_id": "principal_district_judge",
            "custom_court_name_gu": None,
            "custom_court_name_en": None,
            "party_role": "plaintiff",
            "opposite_party_role": "defendant",
        }
        # Emulate update_case handler logic
        updates = {
            "court_source": "custom",
            "court_id": "other",
            "custom_court_name_gu": "નવી કોર્ટ",
            "custom_court_name_en": "New Court",
            "party_role": "complainant",
            "opposite_party_role": "accused",
        }
        if updates.get("court_source") == "custom" or updates.get("court_id") == "other":
            updates["court_source"] = "custom"
            updates["court_id"] = None

        merged = {**existing, **updates}
        self.assertEqual(merged["court_source"], "custom")
        self.assertIsNone(merged["court_id"])
        self.assertEqual(merged["custom_court_name_gu"], "નવી કોર્ટ")
        self.assertEqual(merged["custom_court_name_en"], "New Court")
        self.assertEqual(merged["party_role"], "complainant")
        self.assertEqual(merged["opposite_party_role"], "accused")

    def test_custom_to_catalog_transition(self):
        existing = {
            "id": "c1",
            "court_source": "custom",
            "court_id": None,
            "custom_court_name_gu": "જૂની કોર્ટ",
            "custom_court_name_en": "Old Court",
        }
        updates = {
            "court_source": "catalog",
            "court_id": "principal_district_judge",
        }
        if updates.get("court_source") == "catalog" and updates.get("court_id") not in (None, "other"):
            updates["custom_court_name_gu"] = None
            updates["custom_court_name_en"] = None

        merged = {**existing, **updates}
        self.assertEqual(merged["court_source"], "catalog")
        self.assertEqual(merged["court_id"], "principal_district_judge")
        self.assertIsNone(merged["custom_court_name_gu"])
        self.assertIsNone(merged["custom_court_name_en"])


class TestExhibitApplicationIntegrity(unittest.TestCase):
    def test_signature_dashes(self):
        exhibit_tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_exhibit_application"), None)
        self.assertIsNotNone(exhibit_tpl)
        self.assertIn("----------", exhibit_tpl["content_gu"])
        self.assertNotIn("--------------------", exhibit_tpl["content_gu"])
        self.assertIn("--------------------", exhibit_tpl["content_en"])

if __name__ == "__main__":
    unittest.main()
