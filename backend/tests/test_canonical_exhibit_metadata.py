# -*- coding: utf-8 -*-
"""
Tests for Canonical Exhibit Application Field Metadata & Dynamic Role Options.
Verifies against Canonical PDF Page 1:
1. 12-field architecture & field keys preserved.
2. party_1_role options: ["ફરીયાદી", "અરજદાર", "વાદી"] (Complainant, Applicant, Plaintiff).
3. party_2_role options: ["આરોપી", "સામાવાળા", "પ્રતિવાદી"] (Accused, Opponent, Defendant).
4. representing_party label: "કોના તરફે એડવોકેટ", type: "select", options matching canonical roles.
5. Case number placeholder: "દા.ત. ૧૦૧/૨૦૨૪".
6. Direct Template Mode & Saved Case Mode dynamic role options resolution.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

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

sys.modules['pydantic'].BaseModel = _PydanticBaseModel
sys.modules['pydantic'].Field = lambda *args, **kwargs: None

import test_seed_data
import server


class TestCanonicalExhibitMetadata(unittest.TestCase):
    def setUp(self):
        self.tpl = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_exhibit_application"), None)
        self.assertIsNotNone(self.tpl, "document_exhibit_application missing from test_seed_data")

    def test_12_field_architecture(self):
        fields = self.tpl["fields"]
        self.assertEqual(len(fields), 12)
        expected_keys = [
            "district", "taluka", "court_name", "case_type", "case_number",
            "party_1_role", "party_1_name", "party_2_role", "party_2_name",
            "representing_party", "document_details", "date"
        ]
        self.assertEqual([f["key"] for f in fields], expected_keys)

    def test_party_1_role_canonical_order(self):
        f = next(f for f in self.tpl["fields"] if f["key"] == "party_1_role")
        self.assertEqual(f["label_gu"], "પક્ષકાર-૧ની ભૂમિકા")
        opts = [o["value"] for o in f["options"]]
        self.assertEqual(opts, ["ફરીયાદી", "અરજદાર", "વાદી"])

    def test_party_2_role_canonical_order(self):
        f = next(f for f in self.tpl["fields"] if f["key"] == "party_2_role")
        self.assertEqual(f["label_gu"], "પક્ષકાર-૨ની ભૂમિકા")
        opts = [o["value"] for o in f["options"]]
        self.assertEqual(opts, ["આરોપી", "સામાવાળા", "પ્રતિવાદી"])

    def test_representing_party_metadata(self):
        f = next(f for f in self.tpl["fields"] if f["key"] == "representing_party")
        self.assertEqual(f["label_gu"], "કોના તરફે એડવોકેટ")
        self.assertEqual(f["type"], "select")
        self.assertTrue(f["required"])
        opts = [o["value"] for o in f["options"]]
        self.assertEqual(opts, ["party_1", "party_2"])

    def test_case_number_placeholder(self):
        f = next(f for f in self.tpl["fields"] if f["key"] == "case_number")
        self.assertEqual(f["placeholder"], "દા.ત. ૧૦૧/૨૦૨૪")

    def test_party_name_labels(self):
        p1 = next(f for f in self.tpl["fields"] if f["key"] == "party_1_name")
        self.assertEqual(p1["label_gu"], "પક્ષકાર - ૧ નું નામ")
        p2 = next(f for f in self.tpl["fields"] if f["key"] == "party_2_name")
        self.assertEqual(p2["label_gu"], "પક્ષકાર - ૨ નું નામ")

    def test_dynamic_role_resolution_complainant(self):
        user = {"id": "u1", "name": "Adv. Test"}
        values = {
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "representing_party": "party_1",
            "court": "City Civil Court",
            "taluka": "અમદાવાદ",
            "district": "અમદાવાદ",
        }
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["representing_party_role"], "ફરીયાદી")
        self.assertEqual(ctx["advocate_for_line"], "ફરીયાદી ના એડવોકેટ")

    def test_dynamic_role_resolution_accused(self):
        user = {"id": "u1", "name": "Adv. Test"}
        values = {
            "party_1_role": "ફરીયાદી",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "આરોપી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "representing_party": "party_2",
            "court": "City Civil Court",
            "taluka": "અમદાવાદ",
            "district": "અમદાવાદ",
        }
        ctx = asyncio.run(server.build_render_context(user, None, values, "gu"))
        self.assertEqual(ctx["representing_party_role"], "આરોપી")
        self.assertEqual(ctx["advocate_for_line"], "આરોપી ના એડવોકેટ")


if __name__ == "__main__":
    unittest.main()
