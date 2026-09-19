# -*- coding: utf-8 -*-
"""
Unit tests for Admin Test Case Cleanup / Controlled Cascade Delete.

Tests:
1. Normal admin_delete_case blocks deletion when applications exist (preserves existing protection).
2. Normal admin_delete_case blocks deletion when drafts exist (preserves existing protection).
3. Controlled admin_cascade_delete_case successfully deletes test case and its linked applications and drafts.
4. Cascade delete is strictly scoped: unrelated cases, applications, drafts, templates, users remain untouched.
5. admin_cascade_delete_case logs audit trail with action="case_cascade_delete" and full metadata.
6. admin_cascade_delete_case returns 404 for nonexistent case.
7. Normal admin_bulk_delete_cases preserves protection and blocks cases with documents.
8. Controlled admin_bulk_cascade_delete_cases deletes multiple cases and all their linked data transactionally.
9. Controlled admin_bulk_cascade_delete_cases logs audit trail with action="case_bulk_cascade_delete".
10. Controlled admin_bulk_cascade_delete_cases handles empty or invalid IDs safely.
11. Admin API client (api.ts) and UI components (Cases.tsx) verify required confirmation texts and endpoints.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock third-party dependencies if not installed in current python environment
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

import server


class MockFirestoreDoc:
    def __init__(self, doc_id, data, exists=True):
        self.id = doc_id
        self._data = data
        self.exists = exists
        self.reference = self

    def to_dict(self):
        return self._data.copy() if self._data else None

    async def get(self):
        return self


class MockFirestoreCollection:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def document(self, doc_id):
        return MockFirestoreDocRef(self.store, self.name, doc_id)

    def where(self, filter=None):
        return MockFirestoreQuery(self.store, self.name, filter)


class MockFirestoreDocRef:
    def __init__(self, store, coll_name, doc_id):
        self.store = store
        self.coll_name = coll_name
        self.id = doc_id

    async def get(self):
        coll_data = self.store.setdefault(self.coll_name, {})
        if self.id in coll_data:
            return MockFirestoreDoc(self.id, coll_data[self.id], exists=True)
        return MockFirestoreDoc(self.id, None, exists=False)

    async def set(self, data, merge=False):
        coll_data = self.store.setdefault(self.coll_name, {})
        if merge and self.id in coll_data:
            coll_data[self.id].update(data)
        else:
            coll_data[self.id] = data.copy()

    async def delete(self):
        coll_data = self.store.setdefault(self.coll_name, {})
        if self.id in coll_data:
            del coll_data[self.id]


class MockFirestoreQuery:
    def __init__(self, store, coll_name, query_filter, limit_n=None):
        self.store = store
        self.coll_name = coll_name
        self.query_filter = query_filter
        self.limit_n = limit_n

    def limit(self, n):
        self.limit_n = n
        return self

    async def stream(self):
        coll_data = self.store.setdefault(self.coll_name, {})
        field = getattr(self.query_filter, 'field', 'case_id')
        val = getattr(self.query_filter, 'value', None)
        if not val and hasattr(self.query_filter, 'args'):
            val = self.query_filter.args[2] if len(self.query_filter.args) > 2 else None

        yielded = 0
        for doc_id, doc_dict in list(coll_data.items()):
            if doc_dict.get('case_id') == val or doc_dict.get(field) == val:
                yield MockFirestoreDoc(doc_id, doc_dict, exists=True)
                yielded += 1
                if self.limit_n and yielded >= self.limit_n:
                    break


class MockFirestoreDB:
    def __init__(self):
        self.store = {}
        self.committed_batches = []

    def collection(self, name):
        return MockFirestoreCollection(self.store, name)

    def batch(self):
        return MockFirestoreBatch(self)


class MockFirestoreBatch:
    def __init__(self, db):
        self.db = db
        self.ops = []

    def delete(self, doc_ref):
        self.ops.append(('delete', doc_ref))
        return self

    def set(self, doc_ref, data, merge=False):
        self.ops.append(('set', doc_ref, data, merge))
        return self

    async def commit(self):
        for op in self.ops:
            if op[0] == 'delete':
                ref = op[1]
                coll = self.db.store.get(ref.coll_name, {})
                if ref.id in coll:
                    del coll[ref.id]
            elif op[0] == 'set':
                ref, data, merge = op[1], op[2], op[3]
                coll = self.db.store.setdefault(ref.coll_name, {})
                if merge and ref.id in coll:
                    coll[ref.id].update(data)
                else:
                    coll[ref.id] = data.copy()
        self.db.committed_batches.append(list(self.ops))
        self.ops.clear()


class TestCaseCascadeDelete(unittest.TestCase):
    def setUp(self):
        self.mock_db = MockFirestoreDB()
        self.admin = {
            "id": "admin_super_1",
            "email": "superadmin@nyaysetu.in",
            "name": "Super Admin",
            "role": "super_admin",
        }
        # Patch server.db and server.create_admin_audit_log
        self.db_patch = patch.object(server, 'db', self.mock_db)
        self.db_patch.start()
        self.audit_logs = []

        async def _mock_audit_log(admin, action, entity_type, entity_id=None, metadata=None, reason=None):
            self.audit_logs.append({
                "admin": admin,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "metadata": metadata or {},
                "reason": reason,
            })

        self.audit_patch = patch.object(server, 'create_admin_audit_log', side_effect=_mock_audit_log)
        self.audit_patch.start()

    def tearDown(self):
        self.audit_patch.stop()
        self.db_patch.stop()

    def test_normal_admin_delete_case_blocks_when_applications_exist(self):
        """Standard delete endpoint MUST block case deletion if applications exist."""
        self.mock_db.store['cases'] = {
            'case_prod_1': {'id': 'case_prod_1', 'case_number': 'CIVIL/101/2026', 'application_count': 2}
        }
        self.mock_db.store['applications'] = {
            'app_1': {'id': 'app_1', 'case_id': 'case_prod_1'}
        }
        self.mock_db.store['drafts'] = {}

        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(server.admin_delete_case('case_prod_1', admin=self.admin))
            self.assertIn("Cases with document history cannot be deleted", str(ctx.exception.detail))

        # Case was NOT deleted
        self.assertIn('case_prod_1', self.mock_db.store['cases'])

    def test_normal_admin_delete_case_blocks_when_drafts_exist(self):
        """Standard delete endpoint MUST block case deletion if drafts exist."""
        self.mock_db.store['cases'] = {
            'case_prod_2': {'id': 'case_prod_2', 'case_number': 'CRIM/202/2026', 'application_count': 0}
        }
        self.mock_db.store['applications'] = {}
        self.mock_db.store['drafts'] = {
            'draft_1': {'id': 'draft_1', 'case_id': 'case_prod_2'}
        }

        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(server.admin_delete_case('case_prod_2', admin=self.admin))
            self.assertIn("Cases with document history cannot be deleted", str(ctx.exception.detail))

        self.assertIn('case_prod_2', self.mock_db.store['cases'])

    def test_normal_admin_bulk_delete_cases_blocks_protected_cases(self):
        """Standard bulk delete endpoint MUST protect cases that have linked documents."""
        self.mock_db.store['cases'] = {
            'case_clean_1': {'id': 'case_clean_1', 'case_number': 'CLEAN/1'},
            'case_busy_2': {'id': 'case_busy_2', 'case_number': 'BUSY/2'},
        }
        self.mock_db.store['applications'] = {
            'app_busy_1': {'id': 'app_busy_1', 'case_id': 'case_busy_2'}
        }
        self.mock_db.store['drafts'] = {}

        req = server.CaseBulkActionReq(ids=['case_clean_1', 'case_busy_2'])

        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            res = asyncio.run(server.admin_bulk_delete_cases(req, admin=self.admin))

        # clean case was deleted
        self.assertEqual(res['deleted_count'], 1)
        self.assertNotIn('case_clean_1', self.mock_db.store['cases'])

        # busy case was BLOCKED and NOT deleted
        self.assertEqual(res['blocked_count'], 1)
        self.assertIn('case_busy_2', self.mock_db.store['cases'])
        self.assertEqual(res['blocked_cases'][0]['case_id'], 'case_busy_2')

    def test_admin_cascade_delete_single_test_case(self):
        """Cascade delete endpoint removes test case AND its linked applications and drafts."""
        self.mock_db.store['cases'] = {
            'test_case_1': {'id': 'test_case_1', 'case_number': 'TEST/001/2026', 'nickname': 'My Test Case'},
            'prod_case_2': {'id': 'prod_case_2', 'case_number': 'REAL/200/2026', 'nickname': 'Live Client Case'},
        }
        self.mock_db.store['applications'] = {
            'app_test_1': {'id': 'app_test_1', 'case_id': 'test_case_1', 'template_id': 'document_exhibit'},
            'app_test_2': {'id': 'app_test_2', 'case_id': 'test_case_1', 'template_id': 'document_return'},
            'app_prod_1': {'id': 'app_prod_1', 'case_id': 'prod_case_2', 'template_id': 'document_exhibit'},
        }
        self.mock_db.store['drafts'] = {
            'draft_test_1': {'id': 'draft_test_1', 'case_id': 'test_case_1'},
            'draft_prod_1': {'id': 'draft_prod_1', 'case_id': 'prod_case_2'},
        }

        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            res = asyncio.run(server.admin_cascade_delete_case('test_case_1', admin=self.admin))

        self.assertTrue(res['success'])
        self.assertEqual(res['deleted_case_id'], 'test_case_1')
        self.assertEqual(res['deleted_applications_count'], 2)
        self.assertEqual(res['deleted_drafts_count'], 1)

        # Confirm test records deleted
        self.assertNotIn('test_case_1', self.mock_db.store['cases'])
        self.assertNotIn('app_test_1', self.mock_db.store['applications'])
        self.assertNotIn('app_test_2', self.mock_db.store['applications'])
        self.assertNotIn('draft_test_1', self.mock_db.store['drafts'])

        # ISOLATION: Confirm unrelated production records are completely untouched!
        self.assertIn('prod_case_2', self.mock_db.store['cases'])
        self.assertIn('app_prod_1', self.mock_db.store['applications'])
        self.assertIn('draft_prod_1', self.mock_db.store['drafts'])

        # AUDIT LOG: Check that audit log was generated
        self.assertEqual(len(self.audit_logs), 1)
        audit = self.audit_logs[0]
        self.assertEqual(audit['action'], 'case_cascade_delete')
        self.assertEqual(audit['entity_id'], 'test_case_1')
        self.assertEqual(audit['metadata']['deleted_applications_count'], 2)
        self.assertEqual(audit['metadata']['deleted_drafts_count'], 1)

    def test_admin_cascade_delete_nonexistent_case_raises_404(self):
        """Nonexistent case raises 404."""
        self.mock_db.store['cases'] = {}
        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(server.admin_cascade_delete_case('missing_case_999', admin=self.admin))
            self.assertEqual(ctx.exception.status_code, 404)

    def test_admin_bulk_cascade_delete_multiple_test_cases(self):
        """Bulk cascade delete removes multiple test cases and their linked documents."""
        self.mock_db.store['cases'] = {
            'test_c1': {'id': 'test_c1', 'case_number': 'T1'},
            'test_c2': {'id': 'test_c2', 'case_number': 'T2'},
            'prod_c3': {'id': 'prod_c3', 'case_number': 'PROD3'},
        }
        self.mock_db.store['applications'] = {
            'app_c1_1': {'id': 'app_c1_1', 'case_id': 'test_c1'},
            'app_c2_1': {'id': 'app_c2_1', 'case_id': 'test_c2'},
            'app_c2_2': {'id': 'app_c2_2', 'case_id': 'test_c2'},
            'app_prod_3': {'id': 'app_prod_3', 'case_id': 'prod_c3'},
        }
        self.mock_db.store['drafts'] = {
            'draft_c1_1': {'id': 'draft_c1_1', 'case_id': 'test_c1'},
            'draft_prod_3': {'id': 'draft_prod_3', 'case_id': 'prod_c3'},
        }

        req = server.CaseBulkActionReq(ids=['test_c1', 'test_c2'])

        with patch.object(server.firestore, 'FieldFilter', side_effect=lambda f, op, v: MagicMock(field=f, value=v)):
            res = asyncio.run(server.admin_bulk_cascade_delete_cases(req, admin=self.admin))

        self.assertTrue(res['success'])
        self.assertEqual(res['deleted_cases_count'], 2)
        self.assertCountEqual(res['deleted_case_ids'], ['test_c1', 'test_c2'])
        self.assertEqual(res['deleted_applications_count'], 3)
        self.assertEqual(res['deleted_drafts_count'], 1)

        # Test cases and their linked records removed
        self.assertNotIn('test_c1', self.mock_db.store['cases'])
        self.assertNotIn('test_c2', self.mock_db.store['cases'])
        self.assertNotIn('app_c1_1', self.mock_db.store['applications'])
        self.assertNotIn('app_c2_1', self.mock_db.store['applications'])
        self.assertNotIn('app_c2_2', self.mock_db.store['applications'])
        self.assertNotIn('draft_c1_1', self.mock_db.store['drafts'])

        # ISOLATION: Unrelated prod_c3 and its app/draft completely untouched!
        self.assertIn('prod_c3', self.mock_db.store['cases'])
        self.assertIn('app_prod_3', self.mock_db.store['applications'])
        self.assertIn('draft_prod_3', self.mock_db.store['drafts'])

        # AUDIT LOG: Check that bulk audit log was created
        self.assertEqual(len(self.audit_logs), 1)
        audit = self.audit_logs[0]
        self.assertEqual(audit['action'], 'case_bulk_cascade_delete')
        self.assertEqual(audit['metadata']['deleted_cases_count'], 2)
        self.assertEqual(audit['metadata']['total_deleted_applications'], 3)
        self.assertEqual(audit['metadata']['total_deleted_drafts'], 1)

    def test_admin_bulk_cascade_delete_empty_ids(self):
        """Bulk cascade delete handles empty list gracefully."""
        req = server.CaseBulkActionReq(ids=[])
        res = asyncio.run(server.admin_bulk_cascade_delete_cases(req, admin=self.admin))
        self.assertTrue(res['success'])
        self.assertEqual(res['deleted_cases_count'], 0)
        self.assertEqual(res['deleted_applications_count'], 0)
        self.assertEqual(res['deleted_drafts_count'], 0)

    def test_frontend_api_and_ui_contracts(self):
        """Verify frontend api client and React page code contain all required bindings."""
        api_path = ROOT_DIR / 'admin' / 'src' / 'lib' / 'api.ts'
        cases_page_path = ROOT_DIR / 'admin' / 'src' / 'pages' / 'Cases.tsx'

        self.assertTrue(api_path.exists(), "admin/src/lib/api.ts must exist")
        self.assertTrue(cases_page_path.exists(), "admin/src/pages/Cases.tsx must exist")

        api_code = api_path.read_text(encoding='utf-8')
        self.assertIn("cascadeDeleteCase", api_code)
        self.assertIn("bulkCascadeDeleteCases", api_code)
        self.assertIn("/cases/${id}/cascade", api_code)
        self.assertIn("/cases/bulk-cascade-delete", api_code)

        cases_code = cases_page_path.read_text(encoding='utf-8')
        # Check single case triggers
        self.assertIn("Delete + Test Data", cases_code)
        self.assertIn("Delete Case + Linked Test Data", cases_code)
        # Check bulk trigger
        self.assertIn("Delete Cases + Linked Test Data", cases_code)
        # Check strong confirmation requirements
        self.assertIn("DELETE", cases_code)
        self.assertIn("DELETE TEST DATA", cases_code)
        self.assertIn("confirm-single-cascade-checkbox", cases_code)
        self.assertIn("confirm-bulk-cascade-checkbox", cases_code)


if __name__ == '__main__':
    unittest.main()
