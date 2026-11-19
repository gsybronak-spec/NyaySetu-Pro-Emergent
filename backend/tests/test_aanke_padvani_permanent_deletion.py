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
from seed_data_templates_v2 import BASE_TEMPLATES as SEED_BASE_TEMPLATES
from authoritative_catalog_42 import BASE_TEMPLATES as AUTH_BASE_TEMPLATES
from test_seed_data_templates_v2 import TEMPLATES_V2


class TestCompleteTemplateDeletionPolicy(unittest.TestCase):
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

    def test_01_all_templates_are_deletable(self):
        """01. Verify template protection is removed and all templates are deletable by Super Admin."""
        self.assertFalse(server.ENABLE_TEMPLATE_PROTECTION)
        self.assertEqual(len(server.PROTECTED_TEMPLATE_IDS), 0)
        self.assertEqual(len(server.get_protected_template_ids()), 0)
        # Check all templates evaluate to False
        for tid in ["aanke_padvani_arji", "certified_report", "closing_purshish", "vakilatnama_civil"]:
            self.assertFalse(server.is_template_protected(tid))

    def test_02_super_admin_can_delete_all_canonical_templates(self):
        """02. Verify an authorized Super Admin can delete canonical templates without 403."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        targets = [
            "aanke_padvani_arji", "certified_report", "closing_purshish",
            "closing_argument_right_application", "reopen_right_to_argue_application",
            "dd_karavani_arji", "exemption_arji", "vakilatnama_civil", "vakilatnama_criminal"
        ]

        for tid in targets:
            asyncio.run(self.mock_db.collection("templates").document(tid).set({
                "id": tid, "name_en": tid, "status": "published"
            }))
            res = asyncio.run(server.admin_delete_template(tid, admin=admin))
            self.assertTrue(res.get("success"), f"{tid} deletion failed")
            self.assertFalse(asyncio.run(self.mock_db.collection("templates").document(tid).get()).exists)

    def test_03_super_admin_can_delete_unprotected_templates(self):
        """03. Verify Super Admin can permanently delete unprotected templates."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        unprotected = [
            "mudat_arji", "document_parat_levani_arji", "samadhan_purshish", "saaxi_ne_summons"
        ]
        for tid in unprotected:
            asyncio.run(self.mock_db.collection("templates").document(tid).set({
                "id": tid,
                "name_en": tid,
                "status": "published",
            }))
            res = asyncio.run(server.admin_delete_template(tid, admin=admin))
            self.assertTrue(res.get("success"), f"Deletion failed for unprotected template: {tid}")
            self.assertFalse(asyncio.run(self.mock_db.collection("templates").document(tid).get()).exists)
            # Tombstones created
            cat_tomb = asyncio.run(self.mock_db.collection("deleted_catalog_items").document(f"template:{tid}").get())
            self.assertTrue(cat_tomb.exists)
            del_tomb = asyncio.run(self.mock_db.collection("deleted_templates").document(tid).get())
            self.assertTrue(del_tomb.exists)

    def test_04_deletion_purges_template_revisions_and_versions(self):
        """04. Verify deleting a template permanently deletes its template_revisions and template_versions."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        target_tid = "mudat_arji"

        # Seed template doc
        asyncio.run(self.mock_db.collection("templates").document(target_tid).set({
            "id": target_tid, "name_en": "Adjournment Application", "status": "published"
        }))
        # Seed revision snapshots for target
        asyncio.run(self.mock_db.collection("template_revisions").document(f"{target_tid}_1").set({
            "template_id": target_tid, "version": 1, "content_gu": "v1 content"
        }))
        asyncio.run(self.mock_db.collection("template_revisions").document(f"{target_tid}_2").set({
            "template_id": target_tid, "version": 2, "content_gu": "v2 content"
        }))
        # Seed version records for target
        asyncio.run(self.mock_db.collection("template_versions").document(f"{target_tid}_1").set({
            "template_id": target_tid, "version": 1, "content_gu": "v1 content"
        }))
        # Seed another template's revision to verify it is untouched
        asyncio.run(self.mock_db.collection("template_revisions").document("other_template_1").set({
            "template_id": "other_template", "version": 1, "content_gu": "other content"
        }))

        res = asyncio.run(server.admin_delete_template(target_tid, admin=admin))
        self.assertTrue(res.get("success"))

        # Revisions and versions for target_tid must be deleted
        snap_rev1 = asyncio.run(self.mock_db.collection("template_revisions").document(f"{target_tid}_1").get())
        snap_rev2 = asyncio.run(self.mock_db.collection("template_revisions").document(f"{target_tid}_2").get())
        snap_ver1 = asyncio.run(self.mock_db.collection("template_versions").document(f"{target_tid}_1").get())
        self.assertFalse(snap_rev1.exists)
        self.assertFalse(snap_rev2.exists)
        self.assertFalse(snap_ver1.exists)

        # Unrelated template revision must remain intact
        snap_other = asyncio.run(self.mock_db.collection("template_revisions").document("other_template_1").get())
        self.assertTrue(snap_other.exists)

    def test_05_unauthorized_users_cannot_delete(self):
        """05. Verify unauthenticated users and non-super-admins cannot delete templates."""
        with self.assertRaises(server.HTTPException) as ctx:
            asyncio.run(server.require_super_admin(authorization=None))
        self.assertEqual(ctx.exception.status_code, 401)

        with self.assertRaises(server.HTTPException) as ctx:
            asyncio.run(server.require_super_admin(authorization="Bearer invalid-token"))
        self.assertEqual(ctx.exception.status_code, 401)

    def test_06_bulk_delete_all_templates(self):
        """06. Verify bulk deletion successfully deletes all templates including canonical ones."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        ids_to_delete = ["closing_purshish", "aanke_padvani_arji", "custom_user_template"]

        for tid in ids_to_delete:
            asyncio.run(self.mock_db.collection("templates").document(tid).set({
                "id": tid, "name_en": tid, "status": "published"
            }))
            asyncio.run(self.mock_db.collection("template_revisions").document(f"{tid}_1").set({
                "template_id": tid, "version": 1
            }))
            asyncio.run(self.mock_db.collection("template_versions").document(f"{tid}_1").set({
                "template_id": tid, "version": 1
            }))

        req = server.TemplateBulkDeleteReq(ids=ids_to_delete)
        res = asyncio.run(server.admin_bulk_delete_templates(req, admin=admin))
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("deleted_count"), 3)
        self.assertEqual(res.get("failed_count"), 0)

        # All templates must be deleted
        self.assertFalse(asyncio.run(self.mock_db.collection("templates").document("closing_purshish").get()).exists)
        self.assertFalse(asyncio.run(self.mock_db.collection("templates").document("aanke_padvani_arji").get()).exists)
        self.assertFalse(asyncio.run(self.mock_db.collection("templates").document("custom_user_template").get()).exists)

    def test_07_anti_resurrection_after_seeding_and_restart(self):
        """07. Verify deletion tombstones prevent seed initialization from recreating deleted template."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        target_tid = "mudat_arji"

        asyncio.run(self.mock_db.collection("templates").document(target_tid).set({
            "id": target_tid, "name_en": "Adjournment Application", "status": "published"
        }))
        res = asyncio.run(server.admin_delete_template(target_tid, admin=admin))
        self.assertTrue(res.get("success"))

        deleted_ids = asyncio.run(server._get_deleted_template_ids())
        self.assertIn(target_tid, deleted_ids)

        # Seeding skips it
        seed_res = asyncio.run(server.seed_templates(force=True))
        self.assertNotIn(target_tid, seed_res.get("created_ids", []))
        snap = asyncio.run(self.mock_db.collection("templates").document(target_tid).get())
        self.assertFalse(snap.exists, "Deleted canonical template was resurrected by seed!")

        # Published templates excludes it
        server.invalidate_published_templates_cache()
        published = asyncio.run(server._get_published_templates())
        self.assertFalse(any(t.get("id") == target_tid for t in published))

        # _get_template_by_id returns None
        self.assertIsNone(asyncio.run(server._get_template_by_id(target_tid)))

        # admin_get_template raises 404
        with self.assertRaises(server.HTTPException) as ctx:
            asyncio.run(server.admin_get_template(target_tid, admin=admin))
        self.assertEqual(ctx.exception.status_code, 404)

        # get_catalog_template_order excludes it
        order_res = asyncio.run(server.get_catalog_template_order())
        self.assertNotIn(target_tid, order_res.get("template_order", []))

    def test_08_tombstones_contain_no_content(self):
        """08. Verify tombstones retain only minimal deletion markers without template content."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        target_tid = "document_parat_levani_arji"

        asyncio.run(self.mock_db.collection("templates").document(target_tid).set({
            "id": target_tid,
            "name_en": "Document Parat Levani",
            "content_gu": "ખાનગી કાનૂની લખાણ",
            "content_en": "Private legal text",
            "fields": [{"key": "court", "label_en": "Court"}],
            "settings": {"page_size": "Legal"},
            "status": "published"
        }))
        res = asyncio.run(server.admin_delete_template(target_tid, admin=admin))
        self.assertTrue(res.get("success"))

        cat_tomb = asyncio.run(self.mock_db.collection("deleted_catalog_items").document(f"template:{target_tid}").get()).to_dict()
        del_tomb = asyncio.run(self.mock_db.collection("deleted_templates").document(target_tid).get()).to_dict()

        for tomb in [cat_tomb, del_tomb]:
            self.assertIsNotNone(tomb)
            self.assertEqual(tomb.get("id"), target_tid)
            self.assertIn("deleted_at", tomb)
            self.assertIn("deleted_by", tomb)
            # Must NOT retain template body/fields/settings
            self.assertNotIn("content_gu", tomb)
            self.assertNotIn("content_en", tomb)
            self.assertNotIn("fields", tomb)
            self.assertNotIn("settings", tomb)

    def test_09_unrelated_records_untouched(self):
        """09. Verify deleting one template never affects unrelated templates, cases, or users."""
        admin = {"id": "super_admin_test", "role": "super_admin"}

        asyncio.run(self.mock_db.collection("templates").document("samadhan_purshish").set({
            "id": "samadhan_purshish", "name_en": "Samadhan Purshis", "status": "published"
        }))
        asyncio.run(self.mock_db.collection("templates").document("warrant_rad_karvani_arji").set({
            "id": "warrant_rad_karvani_arji", "name_en": "Warrant Rad", "status": "published"
        }))
        asyncio.run(self.mock_db.collection("cases").document("case_123").set({
            "id": "case_123", "title": "State vs Shah", "status": "active"
        }))

        res = asyncio.run(server.admin_delete_template("samadhan_purshish", admin=admin))
        self.assertTrue(res.get("success"))

        # Other template and case record must still exist
        self.assertTrue(asyncio.run(self.mock_db.collection("templates").document("warrant_rad_karvani_arji").get()).exists)
        self.assertTrue(asyncio.run(self.mock_db.collection("cases").document("case_123").get()).exists)

    def test_10_repeated_deletion_is_safe_and_idempotent(self):
        """10. Verify repeated deletion calls succeed idempotently."""
        admin = {"id": "super_admin_test", "role": "super_admin"}
        target = "document_parat_levani_arji"

        asyncio.run(self.mock_db.collection("templates").document(target).set({
            "id": target, "name_en": "Document Parat Levani", "status": "published"
        }))
        res1 = asyncio.run(server.admin_delete_template(target, admin=admin))
        self.assertTrue(res1.get("success"))

        res2 = asyncio.run(server.admin_delete_template(target, admin=admin))
        self.assertTrue(res2.get("success"))
        self.assertIn("already permanently deleted", res2.get("message"))

    def test_11_aanke_padvani_arji_and_catalogs_restored(self):
        """11. Verify aanke_padvani_arji is restored in all catalogs (21 base = 42 total, 25 canonical IDs)."""
        self.assertEqual(len(SEED_BASE_TEMPLATES), 21)
        self.assertTrue(any(t.get("base_key") == "aanke_padvani_arji" for t in SEED_BASE_TEMPLATES))
        self.assertEqual(len(AUTH_BASE_TEMPLATES), 21)
        self.assertTrue(any(t.get("base_key") == "aanke_padvani_arji" for t in AUTH_BASE_TEMPLATES))
        self.assertEqual(len(TEMPLATES_V2), 21)
        self.assertTrue(any(t.get("id") == "aanke_padvani_arji" for t in TEMPLATES_V2))
        self.assertEqual(len(server.CANONICAL_TEMPLATE_IDS), 25)
        self.assertIn("aanke_padvani_arji", server.CANONICAL_TEMPLATE_IDS)


if __name__ == '__main__':
    unittest.main()

