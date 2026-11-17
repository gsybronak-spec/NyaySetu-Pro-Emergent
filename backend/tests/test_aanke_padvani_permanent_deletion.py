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

# In-memory mock Firestore DB
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

class _MockFirestoreDB:
    def __init__(self):
        self._collections = {}
    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = _MockCollection(name)
        return self._collections[name]

# Import server after mock setup
import server
from seed_data_templates_v2 import BASE_TEMPLATES as SEED_BASE_TEMPLATES
from authoritative_catalog_42 import BASE_TEMPLATES as AUTH_BASE_TEMPLATES
from test_seed_data_templates_v2 import TEMPLATES_V2


class TestPermanentTemplateDeletion(unittest.TestCase):
    def setUp(self):
        self.mock_db = _MockFirestoreDB()
        self.orig_db = server.db
        server.db = self.mock_db
        server.invalidate_published_templates_cache()
        server._invalidate_catalog_cache()

    def tearDown(self):
        server.db = self.orig_db
        server.invalidate_published_templates_cache()
        server._invalidate_catalog_cache()

    def test_01_protected_template_ids_configuration(self):
        """01. Verify aanke_padvani_arji is NOT in PROTECTED_TEMPLATE_IDS and remaining 8 canonical templates ARE."""
        self.assertNotIn("aanke_padvani_arji", server.PROTECTED_TEMPLATE_IDS)
        self.assertNotIn("aanke_padvani_arji_gu", server.PROTECTED_TEMPLATE_IDS)
        self.assertNotIn("aanke_padvani_arji_en", server.PROTECTED_TEMPLATE_IDS)

        expected_protected = {
            "certified_copy_application",
            "closing_purshish",
            "closing_argument_right_application",
            "reopen_right_to_argue_application",
            "exemption_arji",
            "dd_karavani_arji",
            "mudat_arji",
            "vakilatnama_criminal",
            "vakilatnama_civil",
        }
        for pid in expected_protected:
            self.assertIn(pid, server.PROTECTED_TEMPLATE_IDS, f"{pid} must be in PROTECTED_TEMPLATE_IDS")

    def test_02_admin_delete_protected_templates_strictly_forbidden(self):
        """02. Verify deleting any of the remaining 8 protected templates raises HTTP 403 Forbidden."""
        admin = {"id": "super_admin_test"}
        for pid in server.PROTECTED_TEMPLATE_IDS:
            with self.assertRaises(server.HTTPException) as ctx:
                asyncio.run(server.admin_delete_template(pid, admin=admin))
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("protected canonical template", ctx.exception.detail)

    def test_03_admin_delete_aanke_padvani_arji_creates_double_tombstones(self):
        """03. Verify deleting aanke_padvani_arji deletes active doc and writes double tombstones."""
        admin = {"id": "super_admin_1"}
        # Prepopulate active template in db.templates
        asyncio.run(self.mock_db.collection("templates").document("aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "name_en": "Application to Exhibit Document",
            "name_gu": "આંક પાડવાની અરજી",
            "status": "published",
        }))

        res = asyncio.run(server.admin_delete_template("aanke_padvani_arji", admin=admin))
        self.assertTrue(res.get("success"))

        # Active doc must be deleted
        snap = asyncio.run(self.mock_db.collection("templates").document("aanke_padvani_arji").get())
        self.assertFalse(snap.exists)

        # Tombstone in deleted_catalog_items
        cat_tomb = asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").get())
        self.assertTrue(cat_tomb.exists)
        self.assertEqual(cat_tomb.to_dict().get("kind"), "template")

        # Tombstone in deleted_templates
        del_tomb = asyncio.run(self.mock_db.collection("deleted_templates").document("aanke_padvani_arji").get())
        self.assertTrue(del_tomb.exists)
        self.assertEqual(del_tomb.to_dict().get("id"), "aanke_padvani_arji")

    def test_04_admin_delete_is_idempotent(self):
        """04. Verify repeated deletion calls succeed idempotently without error."""
        admin = {"id": "super_admin_1"}
        # Pre-seed tombstone
        asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "kind": "template",
        }))
        res = asyncio.run(server.admin_delete_template("aanke_padvani_arji", admin=admin))
        self.assertTrue(res.get("success"))

    def test_05_deleted_template_ids_includes_aanke_padvani_and_variants(self):
        """05. Verify _get_deleted_template_ids includes aanke_padvani_arji and _gu / _en variants."""
        asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "kind": "template",
        }))
        deleted_ids = asyncio.run(server._get_deleted_template_ids())
        self.assertIn("aanke_padvani_arji", deleted_ids)
        self.assertIn("aanke_padvani_arji_gu", deleted_ids)
        self.assertIn("aanke_padvani_arji_en", deleted_ids)

    def test_06_published_templates_and_get_by_id_exclude_deleted(self):
        """06. Verify _get_published_templates and _get_template_by_id never return tombstoned template."""
        asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "kind": "template",
        }))
        server.invalidate_published_templates_cache()

        # By ID returns None
        t1 = asyncio.run(server._get_template_by_id("aanke_padvani_arji"))
        self.assertIsNone(t1)
        t2 = asyncio.run(server._get_template_by_id("aanke_padvani_arji_gu"))
        self.assertIsNone(t2)
        t3 = asyncio.run(server._get_template_by_id("aanke_padvani_arji_en"))
        self.assertIsNone(t3)

        # Published list excludes it
        all_pub = asyncio.run(server._get_published_templates())
        self.assertFalse(any(t.get("id") == "aanke_padvani_arji" for t in all_pub))
        self.assertFalse(any(t.get("base_key") == "aanke_padvani_arji" for t in all_pub))

    def test_07_catalog_template_order_excludes_deleted(self):
        """07. Verify get_catalog_template_order and admin_get_template_order exclude aanke_padvani_arji."""
        asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "kind": "template",
        }))
        order_res = asyncio.run(server.get_catalog_template_order())
        order = order_res.get("template_order", [])
        self.assertNotIn("aanke_padvani_arji", order)
        self.assertNotIn("aanke_padvani_arji_gu", order)
        self.assertNotIn("aanke_padvani_arji_en", order)

    def test_08_seed_templates_skips_tombstoned_ids(self):
        """08. Verify seed_templates skips tombstoned aanke_padvani_arji and never recreates it."""
        asyncio.run(self.mock_db.collection("deleted_catalog_items").document("template:aanke_padvani_arji").set({
            "id": "aanke_padvani_arji",
            "kind": "template",
        }))
        # Run seed_templates
        res = asyncio.run(server.seed_templates(force=True))
        self.assertNotIn("aanke_padvani_arji", res.get("created_ids", []))
        snap = asyncio.run(self.mock_db.collection("templates").document("aanke_padvani_arji").get())
        self.assertFalse(snap.exists)

    def test_09_canonical_catalogs_count_and_absence(self):
        """09. Verify canonical seed catalogs have 20 templates and do not contain aanke_padvani_arji."""
        self.assertEqual(len(SEED_BASE_TEMPLATES), 20)
        self.assertFalse(any(t.get("base_key") == "aanke_padvani_arji" for t in SEED_BASE_TEMPLATES))

        self.assertEqual(len(AUTH_BASE_TEMPLATES), 20)
        self.assertFalse(any(t.get("base_key") == "aanke_padvani_arji" for t in AUTH_BASE_TEMPLATES))

        self.assertEqual(len(TEMPLATES_V2), 20)
        self.assertFalse(any(t.get("id") == "aanke_padvani_arji" for t in TEMPLATES_V2))

if __name__ == '__main__':
    unittest.main()
