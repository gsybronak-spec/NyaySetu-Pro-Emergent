# -*- coding: utf-8 -*-
"""
Comprehensive Regression Test Suite for NyaySetu Pro
Case Draft Validation Architecture (ZERO mandatory-field blocking on Case Create/Edit/Update)

Verifies all 14 required cases:
1. Case Create succeeds with only case_number.
2. Case Create succeeds with only party_name.
3. Case Create succeeds for Private Complaint without Police Station.
4. Case Create succeeds for Private Complaint without FIR Number.
5. Case Create succeeds without Investigating Officer.
6. Case Update succeeds for existing incomplete case.
7. Case Update succeeds with all Admin Configured Case Fields empty.
8. Reopening incomplete saved case succeeds and displays correctly.
9. Template generation succeeds for template that does NOT require Police Station (e.g. Adjournment Application / mudat_arji) from an incomplete case lacking Police Station.
10. Template generation validation works correctly when a specific template requires a field and that field is missing.
11. "Other / અન્ય કોર્ટ" custom court functionality preserved.
12. Catalog court functionality preserved.
13. Template generation from case preserved.
14. Case Edit -> Update Case persistence preserved.
"""

import asyncio
import sys
import unittest
import uuid
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
from test_seed_data_templates_v2 import TEMPLATES_V2
from doc_generator import render_template


class MockFirestoreDoc:
    def __init__(self, doc_id, data=None):
        self.id = doc_id
        self._data = dict(data or {})
        self.exists = bool(data)

    def to_dict(self):
        return dict(self._data)

    async def get(self):
        return self

    async def set(self, data, merge=False):
        if merge:
            self._data.update(data)
        else:
            self._data = dict(data)
        self.exists = True
        return self

    async def update(self, data):
        self._data.update(data)
        return self


class MockFirestoreCollection:
    def __init__(self):
        self._docs = {}

    def document(self, doc_id=None):
        if not doc_id:
            doc_id = str(uuid.uuid4())
        if doc_id not in self._docs:
            self._docs[doc_id] = MockFirestoreDoc(doc_id, None)
        return self._docs[doc_id]

    def where(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def get(self):
        return [doc for doc in self._docs.values() if doc.exists]

    async def stream(self):
        for doc in self._docs.values():
            if doc.exists:
                yield doc


class MockFirestoreDB:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = MockFirestoreCollection()
        return self._collections[name]


class TestCaseDraftValidationArchitecture(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.mock_db = MockFirestoreDB()
        server.db = self.mock_db
        self.test_user = {
            "id": "adv_user_123",
            "name": "Advocate Ronak Solanki",
            "advocate_name_en": "Adv. Ronak Solanki",
            "advocate_name_gu": "એડવોકેટ રોનક સોલંકી",
            "district": "ahmedabad",
            "court": "City Civil Court, Ahmedabad",
        }

    def tearDown(self):
        self.loop.close()

    # 1. Case Create succeeds with only case_number
    def test_01_case_create_with_only_case_number(self):
        async def _run():
            req = server.CaseCreate(case_number="CR-123/2026")
            res = await server.create_case(req, user=self.test_user)
            self.assertIsNotNone(res.get("id"))
            self.assertEqual(res.get("case_number"), "CR-123/2026")
            self.assertEqual(res.get("user_id"), self.test_user["id"])
            self.assertEqual(res.get("status"), "active")
        self.loop.run_until_complete(_run())

    # 2. Case Create succeeds with only party_name
    def test_02_case_create_with_only_party_name(self):
        async def _run():
            req = server.CaseCreate(party_name="Jaydeep Solanki")
            res = await server.create_case(req, user=self.test_user)
            self.assertIsNotNone(res.get("id"))
            self.assertEqual(res.get("party_name"), "Jaydeep Solanki")
            self.assertEqual(res.get("client_name"), "Jaydeep Solanki")
        self.loop.run_until_complete(_run())

    # 3. Case Create succeeds for Private Complaint without Police Station
    def test_03_case_create_private_complaint_without_police_station(self):
        async def _run():
            req = server.CaseCreate(
                case_type_id="criminal_case",
                complaint_type="private",
                party_name="Hitesh Patel",
                opposite_party="Mukesh Shah",
                police_station=None,
                police_station_id=None,
                police_station_custom=None,
                custom_fields={},
            )
            res = await server.create_case(req, user=self.test_user)
            self.assertIsNotNone(res.get("id"))
            self.assertEqual(res.get("case_type_id"), "criminal_case")
            self.assertEqual(res.get("complaint_type"), "private")
            self.assertIsNone(res.get("police_station"))
        self.loop.run_until_complete(_run())

    # 4. Case Create succeeds for Private Complaint without FIR Number
    def test_04_case_create_private_complaint_without_fir_number(self):
        async def _run():
            req = server.CaseCreate(
                case_type_id="criminal_case",
                complaint_type="private",
                party_name="Hitesh Patel",
                custom_fields={"sections": "138 NI Act"},  # No fir_number
            )
            res = await server.create_case(req, user=self.test_user)
            self.assertIsNotNone(res.get("id"))
            self.assertNotIn("fir_number", res.get("custom_fields", {}))
        self.loop.run_until_complete(_run())

    # 5. Case Create succeeds without Investigating Officer
    def test_05_case_create_without_investigating_officer(self):
        async def _run():
            req = server.CaseCreate(
                case_type_id="criminal_case",
                party_name="Prakash Sharma",
                custom_fields={"fir_number": "I-CR 10/2026"},  # No investigating_officer
            )
            res = await server.create_case(req, user=self.test_user)
            self.assertIsNotNone(res.get("id"))
            self.assertNotIn("investigating_officer", res.get("custom_fields", {}))
        self.loop.run_until_complete(_run())

    # 6. Case Update succeeds for existing incomplete case
    def test_06_case_update_existing_incomplete_case(self):
        async def _run():
            # Setup existing incomplete case
            case_id = "inc_case_001"
            existing = {
                "id": case_id,
                "user_id": self.test_user["id"],
                "case_number": "555/2026",
                "party_name": "Incomplete Client",
                "status": "active",
            }
            await self.mock_db.collection("cases").document(case_id).set(existing)

            # Update with notes and nickname, leaving everything else incomplete
            update_req = server.CaseUpdate(
                nickname="Private NI Act Matter",
                notes="Initial client consultation completed.",
            )
            res = await server.update_case(case_id, update_req, user=self.test_user)
            self.assertEqual(res.get("id"), case_id)
            self.assertEqual(res.get("nickname"), "Private NI Act Matter")
            self.assertEqual(res.get("notes"), "Initial client consultation completed.")
            self.assertEqual(res.get("party_name"), "Incomplete Client")
        self.loop.run_until_complete(_run())

    # 7. Case Update succeeds with all Admin Configured Case Fields empty
    def test_07_case_update_with_all_admin_configured_fields_empty(self):
        async def _run():
            case_id = "inc_case_002"
            existing = {
                "id": case_id,
                "user_id": self.test_user["id"],
                "case_type_id": "criminal_case",
                "status": "active",
                "custom_fields": {},
            }
            await self.mock_db.collection("cases").document(case_id).set(existing)

            # Update with empty custom_fields
            update_req = server.CaseUpdate(
                custom_fields={},
                party_name="Complainant Only",
            )
            res = await server.update_case(case_id, update_req, user=self.test_user)
            self.assertEqual(res.get("party_name"), "Complainant Only")
            self.assertNotIn("fir_number", res.get("custom_fields", {}))
            self.assertNotIn("police_station", res.get("custom_fields", {}))
        self.loop.run_until_complete(_run())

    # 8. Reopening incomplete saved case succeeds and displays correctly
    def test_08_reopening_incomplete_saved_case_succeeds(self):
        async def _run():
            case_id = "inc_case_003"
            doc = {
                "id": case_id,
                "user_id": self.test_user["id"],
                "case_number": "999/2026",
                "party_name": "Applicant A",
                "opposite_party": None,
                "status": "active",
            }
            await self.mock_db.collection("cases").document(case_id).set(doc)

            res = await server.get_case(case_id, user=self.test_user)
            self.assertEqual(res["id"], case_id)
            self.assertEqual(res["case_number"], "999/2026")
            self.assertEqual(res["party_name"], "Applicant A")
            self.assertIsNone(res.get("opposite_party"))
        self.loop.run_until_complete(_run())

    # 9. Template generation succeeds for template that does NOT require Police Station (mudat_arji) from incomplete case
    def test_09_template_generation_without_police_station_succeeds(self):
        async def _run():
            case_id = "inc_case_004"
            case_doc = {
                "id": case_id,
                "user_id": self.test_user["id"],
                "case_number": "100/2026",
                "party_name": "Rameshbhai Patel",
                "opposite_party": "Sureshbhai Shah",
                "court_id": "gen_district",
                "district_id": "ahmedabad",
                "police_station": None,
                "police_station_id": None,
                "custom_fields": {},
            }
            mudat_tpl = next(t for t in TEMPLATES_V2 if t["id"] == "mudat_arji")
            ctx = await server.build_render_context(
                self.test_user,
                case_doc,
                {"reason": "અગત્યના સરકારી કામે બહારગામ હોવાથી", "advocate_side": "party"},
                language="gu"
            )
            # Verify validate_template_requirements does NOT raise any error
            server.validate_template_requirements(mudat_tpl, ctx, language="gu")
            rendered = render_template(mudat_tpl["content_gu"], ctx)
            self.assertIn("મુદ્દત અરજી", rendered)
            self.assertIn("Rameshbhai Patel", rendered)
            self.assertIn("અગત્યના સરકારી કામે બહારગામ હોવાથી", rendered)
        self.loop.run_until_complete(_run())

    # 10. Template generation validation works correctly when a specific template requires a field and that field is missing
    def test_10_template_generation_validation_blocks_when_template_requires_field(self):
        # Create a mock template that specifically requires police_station
        mock_template_with_required_ps = {
            "id": "bail_custom",
            "name_en": "Bail Application",
            "name_gu": "જામીન અરજી",
            "fields": [
                {"key": "police_station", "label_en": "Police Station", "label_gu": "પોલીસ સ્ટેશન", "required": True},
                {"key": "reason", "label_en": "Grounds", "label_gu": "કારણો", "required": True},
            ]
        }
        # Context missing police_station
        ctx_missing = {"reason": "Medical grounds"}
        with self.assertRaises(_MockHTTPException) as ctx_err:
            server.validate_template_requirements(mock_template_with_required_ps, ctx_missing, language="en")
        self.assertEqual(ctx_err.exception.status_code, 400)
        self.assertIn("Police Station", ctx_err.exception.detail)

        # Context having police_station
        ctx_complete = {"police_station": "Navrangpura Police Station", "reason": "Medical grounds"}
        try:
            server.validate_template_requirements(mock_template_with_required_ps, ctx_complete, language="en")
        except Exception as e:
            self.fail(f"validate_template_requirements should have passed with complete context: {e}")

    # 11. "Other / અન્ય કોર્ટ" custom court functionality preserved
    def test_11_other_custom_court_functionality_preserved(self):
        async def _run():
            # Providing custom court names
            req_custom = server.CaseCreate(
                party_name="Custom Court Party",
                court_id="other",
                court_source="custom",
                custom_court_name_gu="મહે. સિવિલ કોર્ટ, ગાંધીનગર",
                custom_court_name_en="Hon. Civil Court, Gandhinagar",
                language="gu",
            )
            res = await server.create_case(req_custom, user=self.test_user)
            self.assertEqual(res.get("court_source"), "custom")
            self.assertIsNone(res.get("court_id"))
            self.assertEqual(res.get("custom_court_name_gu"), "મહે. સિવિલ કોર્ટ, ગાંધીનગર")
            self.assertEqual(res.get("custom_court_name_en"), "Hon. Civil Court, Gandhinagar")
            self.assertEqual(res.get("court"), "મહે. સિવિલ કોર્ટ, ગાંધીનગર")

            # Missing both names should raise HTTPException(400)
            req_invalid = server.CaseCreate(
                party_name="Missing Names",
                court_id="other",
                court_source="custom",
                custom_court_name_gu=None,
                custom_court_name_en=None,
            )
            with self.assertRaises(_MockHTTPException):
                await server.create_case(req_invalid, user=self.test_user)
        self.loop.run_until_complete(_run())

    # 12. Catalog court functionality preserved
    def test_12_catalog_court_functionality_preserved(self):
        async def _run():
            req_catalog = server.CaseCreate(
                party_name="Catalog Court Party",
                court_id="gen_district",
                language="en",
            )
            res = await server.create_case(req_catalog, user=self.test_user)
            self.assertEqual(res.get("court_source"), "catalog")
            self.assertEqual(res.get("court_id"), "gen_district")
            self.assertIsNone(res.get("custom_court_name_gu"))
            self.assertIsNone(res.get("custom_court_name_en"))
        self.loop.run_until_complete(_run())

    # 13. Template generation from case preserved
    def test_13_template_generation_from_case_preserved(self):
        async def _run():
            case_doc = {
                "id": "case_full_13",
                "user_id": self.test_user["id"],
                "case_number": "789/2026",
                "party_name": "Bharat Patel",
                "opposite_party": "Dinesh Shah",
                "court_id": "principal_district_judge",
                "district_id": "ahmedabad",
                "party_role": "plaintiff",
                "opposite_party_role": "defendant",
            }
            aanke_tpl = next(t for t in TEMPLATES_V2 if t["id"] == "aanke_padvani_arji")
            ctx = await server.build_render_context(
                self.test_user,
                case_doc,
                {"advocate_side": "party", "document_details": "બાનાખતની અસલ નકલ"},
                language="gu"
            )
            server.validate_template_requirements(aanke_tpl, ctx, language="gu")
            rendered = render_template(aanke_tpl["content_gu"], ctx)
            self.assertIn("દસ્તાવેજને આંકે પાડવાની અરજી", rendered)
            self.assertIn("789/2026", rendered)
            self.assertIn("Bharat Patel", rendered)
            self.assertIn("બાનાખતની અસલ નકલ", rendered)
        self.loop.run_until_complete(_run())

    # 14. Case Edit -> Update Case persistence preserved
    def test_14_case_edit_update_persistence_preserved(self):
        async def _run():
            case_id = "case_persist_14"
            initial_doc = {
                "id": case_id,
                "user_id": self.test_user["id"],
                "case_number": "111/2026",
                "party_name": "Initial Name",
                "nickname": "Initial Nickname",
                "status": "active",
            }
            await self.mock_db.collection("cases").document(case_id).set(initial_doc)

            # Advocate edits Case Nickname and Primary Party Name
            update_req = server.CaseUpdate(
                party_name="Edited Persisted Name",
                nickname="Edited Persisted Nickname",
            )
            updated_res = await server.update_case(case_id, update_req, user=self.test_user)
            self.assertEqual(updated_res.get("party_name"), "Edited Persisted Name")
            self.assertEqual(updated_res.get("nickname"), "Edited Persisted Nickname")

            # Verify persisted in database upon reload
            reloaded_snap = await self.mock_db.collection("cases").document(case_id).get()
            reloaded_doc = reloaded_snap.to_dict()
            self.assertEqual(reloaded_doc["party_name"], "Edited Persisted Name")
            self.assertEqual(reloaded_doc["nickname"], "Edited Persisted Nickname")
        self.loop.run_until_complete(_run())


if __name__ == "__main__":
    unittest.main()
