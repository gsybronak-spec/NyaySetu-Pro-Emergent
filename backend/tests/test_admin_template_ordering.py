# -*- coding: utf-8 -*-
import os
import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    def dict(self, *args, **kwargs):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    def model_dump(self, *args, **kwargs):
        return self.dict(*args, **kwargs)

sys.modules['pydantic'].BaseModel = _PydanticBaseModel

class _MockDocSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = data is not None
    def to_dict(self):
        return dict(self._data) if self._data else None

class _MockDocRef:
    def __init__(self, collection, doc_id):
        self.collection = collection
        self.id = doc_id
    async def get(self):
        data = self.collection._store.get(self.id)
        return _MockDocSnapshot(self.id, data)
    async def set(self, data, merge=False):
        if merge and self.id in self.collection._store and isinstance(self.collection._store[self.id], dict):
            self.collection._store[self.id].update(data)
        else:
            self.collection._store[self.id] = dict(data)
    async def update(self, data):
        if self.id in self.collection._store and isinstance(self.collection._store[self.id], dict):
            self.collection._store[self.id].update(data)
        else:
            self.collection._store[self.id] = dict(data)
    async def delete(self):
        self.collection._store.pop(self.id, None)

class _MockCollection:
    def __init__(self, name):
        self.name = name
        self._store = {}
    def document(self, doc_id):
        return _MockDocRef(self, doc_id)
    def where(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self
    async def stream(self):
        for doc_id, data in list(self._store.items()):
            yield _MockDocSnapshot(doc_id, data)

class _MockBatch:
    def __init__(self, db):
        self.db = db
        self.ops = []
    def delete(self, doc_ref):
        self.ops.append(('delete', doc_ref))
    def set(self, doc_ref, data, merge=False):
        self.ops.append(('set', doc_ref, data, merge))
    async def commit(self):
        for op in self.ops:
            if op[0] == 'delete':
                await op[1].delete()
            elif op[0] == 'set':
                await op[1].set(op[2], merge=op[3])

class _MockFirestoreDB:
    def __init__(self):
        self._collections = {}
    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = _MockCollection(name)
        return self._collections[name]
    def batch(self):
        return _MockBatch(self)

# Import server after mock setup
import server
from server import TemplateOrderReq, admin_update_template_order, admin_list_templates


class TestAdminTemplateOrdering(unittest.TestCase):
    def setUp(self):
        self.mock_db = _MockFirestoreDB()
        self.orig_db = server.db
        server.db = self.mock_db
        self.admin = {"id": "test_super_admin", "role": "super_admin", "email": "admin@nyaysetu.in"}

    def tearDown(self):
        server.db = self.orig_db

    def test_admin_update_template_order_syncs_variants(self):
        """PUT /template-order must sync sort_order across existing base, _gu, and _en documents without creating ghosts."""
        # Pre-seed existing templates
        for tid in ["order_test_alpha", "order_test_alpha_gu", "order_test_alpha_en", "order_test_beta",
                    "order_test_gamma", "order_test_gamma_gu", "order_test_gamma_en"]:
            asyncio.run(self.mock_db.collection("templates").document(tid).set({
                "id": tid, "name_en": tid, "status": "published"
            }))

        req = TemplateOrderReq(template_order=["order_test_alpha", "order_test_beta", "non_existent_ghost_id"])
        res = asyncio.run(admin_update_template_order(req, admin=self.admin))
        self.assertTrue(res["success"])
        self.assertIn("order_test_alpha", res["template_order"])

        # Check alpha base, _gu, and _en
        doc_base = asyncio.run(self.mock_db.collection("templates").document("order_test_alpha").get()).to_dict()
        doc_gu = asyncio.run(self.mock_db.collection("templates").document("order_test_alpha_gu").get()).to_dict()
        doc_en = asyncio.run(self.mock_db.collection("templates").document("order_test_alpha_en").get()).to_dict()

        self.assertEqual(doc_base.get("sort_order"), 0)
        self.assertEqual(doc_gu.get("sort_order"), 0)
        self.assertEqual(doc_en.get("sort_order"), 0)

        # Check beta
        doc_beta = asyncio.run(self.mock_db.collection("templates").document("order_test_beta").get()).to_dict()
        self.assertEqual(doc_beta.get("sort_order"), 1)

        # Verify non_existent_ghost_id was NEVER created in db.templates
        doc_ghost = asyncio.run(self.mock_db.collection("templates").document("non_existent_ghost_id").get())
        self.assertFalse(doc_ghost.exists, "Ordering payload created a missing document in db.templates!")

        # Updating with suffixed ID (e.g. order_test_gamma_gu) also syncs base and sibling
        req_suffixed = TemplateOrderReq(template_order=["order_test_gamma_gu"])
        res_suffixed = asyncio.run(admin_update_template_order(req_suffixed, admin=self.admin))
        self.assertTrue(res_suffixed["success"])

        doc_gamma_gu = asyncio.run(self.mock_db.collection("templates").document("order_test_gamma_gu").get()).to_dict()
        doc_gamma_base = asyncio.run(self.mock_db.collection("templates").document("order_test_gamma").get()).to_dict()
        doc_gamma_en = asyncio.run(self.mock_db.collection("templates").document("order_test_gamma_en").get()).to_dict()

        self.assertEqual(doc_gamma_gu.get("sort_order"), 0)
        self.assertEqual(doc_gamma_base.get("sort_order"), 0)
        self.assertEqual(doc_gamma_en.get("sort_order"), 0)

    def test_admin_list_templates_order_map_fallback(self):
        """admin_list_templates falls back to template_display_order in settings when doc has no sort_order."""
        test_order = ["first_tpl", "second_tpl", "third_tpl"]
        asyncio.run(self.mock_db.collection("settings").document("template_display_order").set({
            "value": test_order,
            "updated_at": server.now().isoformat(),
            "updated_by": self.admin["id"],
        }))
        server.invalidate_settings_cache("template_display_order")

        # Create docs without sort_order
        asyncio.run(self.mock_db.collection("templates").document("third_tpl").set({"id": "third_tpl", "name_en": "Third", "status": "published"}))
        asyncio.run(self.mock_db.collection("templates").document("first_tpl").set({"id": "first_tpl", "name_en": "First", "status": "published"}))
        asyncio.run(self.mock_db.collection("templates").document("second_tpl").set({"id": "second_tpl", "name_en": "Second", "status": "published"}))

        res = asyncio.run(admin_list_templates(admin=self.admin))
        items = res if isinstance(res, list) else res.get("templates") or res.get("items") or []
        ids = [t["id"] for t in items if t.get("id") in test_order]
        self.assertEqual(ids, ["first_tpl", "second_tpl", "third_tpl"])


if __name__ == '__main__':
    unittest.main()
