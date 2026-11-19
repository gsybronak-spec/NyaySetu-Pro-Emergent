# -*- coding: utf-8 -*-
"""
Comprehensive End-to-End Test Suite for NyaaySetu Pro:
Final Three Requirements + Complete Deletion Authority (Zero Protection):
1. TEMPLATE DELETION:
   - Super Admin can permanently delete ANY template (including aanke_padvani_arji, vakilatnama_civil).
   - Zero protected templates, zero HTTP 403 deletion restrictions.
   - Deleted templates are tombstoned and NEVER resurrected by seed_templates(), force seeding, startup, or migrations.
   - aanke_padvani_arji never appears with status "seed" after deletion.
2. ADMIN-TO-FRONTEND SYNCHRONIZATION:
   - Admin create, edit, archive, publish, delete reflected in published templates API.
3. PERMANENT TEMPLATE ORDER:
   - Direct table drag-and-drop order persistence in settings & sort_order, preserved across cache clearing and restarts.
"""
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

class _MockFieldFilter:
    def __init__(self, field, op, val):
        self.field = field
        self.op = op
        self.val = val

firestore_mod = sys.modules['google.cloud.firestore']
firestore_mod.FieldFilter = _MockFieldFilter
sys.modules['google.cloud'].firestore = firestore_mod

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
    def __init__(self, name, filters=None):
        self.name = name
        self._store = {}
        self._filters = filters or []
    def document(self, doc_id):
        return _MockDocRef(self, doc_id)
    def where(self, *args, **kwargs):
        new_filters = list(self._filters)
        if 'filter' in kwargs:
            f = kwargs['filter']
            new_filters.append((getattr(f, 'field', None), getattr(f, 'op', '=='), getattr(f, 'val', None)))
        elif len(args) >= 3:
            new_filters.append((args[0], args[1], args[2]))
        sub = _MockCollection(self.name, filters=new_filters)
        sub._store = self._store
        return sub
    def limit(self, *args, **kwargs):
        return self
    async def stream(self):
        for doc_id, data in list(self._store.items()):
            match = True
            for field, op, val in self._filters:
                if field and op == '==' and data.get(field) != val:
                    match = False
                    break
            if match:
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

class _MockDB:
    def __init__(self):
        self.collections = {}
    def collection(self, name):
        if name not in self.collections:
            self.collections[name] = _MockCollection(name)
        return self.collections[name]
    def batch(self):
        return _MockBatch(self)

mock_db_instance = _MockDB()

# Import server after mocks
import server
server.db = mock_db_instance
server.ENABLE_AUTO_SEED = True
server.DELETED_OBSOLETE_TEMPLATE_IDS = set()

# Helper for async tests
def run_async(coro):
    return asyncio.run(coro)


class TestFinalThreeRequirements(unittest.TestCase):
    def setUp(self):
        server.db = mock_db_instance
        server.ENABLE_AUTO_SEED = True
        server.firestore.FieldFilter = _MockFieldFilter
        mock_db_instance.collections.clear()
        server.DELETED_OBSOLETE_TEMPLATE_IDS = set()
        server.invalidate_published_templates_cache()
        server.invalidate_settings_cache()
        self.admin = {"id": "super_admin_1", "role": "super_admin", "name": "Super Admin"}

    # =========================================================================
    # REQUIREMENT 1: COMPLETE TEMPLATE DELETION AUTHORITY (ZERO PROTECTION)
    # =========================================================================
    def test_req1_all_templates_deletable_by_super_admin(self):
        """Super Admin can permanently delete any canonical template without HTTP 403."""
        test_targets = [
            "aanke_padvani_arji",
            "vakilatnama_civil",
            "closing_purshish",
            "mudat_arji",
        ]
        for tid in test_targets:
            with self.subTest(template_id=tid):
                # Seed document in mock DB
                run_async(mock_db_instance.collection("templates").document(tid).set({
                    "id": tid,
                    "name_en": f"Name {tid}",
                    "name_gu": f"નામ {tid}",
                    "status": "published",
                }))
                # Deletion must succeed without 403
                res = run_async(server.admin_delete_template(tid, admin=self.admin))
                self.assertTrue(res.get("success"), f"Deletion failed for {tid}")
                # Confirm removed from templates collection
                snap = run_async(mock_db_instance.collection("templates").document(tid).get())
                self.assertFalse(snap.exists)
                # Confirm double tombstones
                tomb1 = run_async(mock_db_instance.collection("deleted_catalog_items").document(f"template:{tid}").get())
                self.assertTrue(tomb1.exists)
                tomb2 = run_async(mock_db_instance.collection("deleted_templates").document(tid).get())
                self.assertTrue(tomb2.exists)

    def test_req1_bulk_deletion_all_templates_successful(self):
        """Bulk deletion of any templates succeeds with full authority."""
        class BulkReq:
            ids = ["aanke_padvani_arji", "vakilatnama_civil"]
        res = run_async(server.admin_bulk_delete_templates(BulkReq(), admin=self.admin))
        self.assertEqual(res["deleted_count"], 2)
        self.assertEqual(res["failed_count"], 0)
        self.assertIn("aanke_padvani_arji", res["deleted_ids"])
        self.assertIn("vakilatnama_civil", res["deleted_ids"])

    def test_req1_aanke_padvani_permanent_deletion_and_no_seed_resurrection(self):
        """
        Exact regression test:
        1. Delete aanke_padvani_arji.
        2. Double tombstones recorded.
        3. admin_list_templates must NOT show aanke_padvani_arji with status 'seed' or any other status.
        4. seed_templates(force=True) must NOT resurrect it.
        5. _get_published_templates must NOT contain it.
        """
        tid = "aanke_padvani_arji"
        # Seed doc initially
        run_async(mock_db_instance.collection("templates").document(tid).set({
            "id": tid,
            "name_gu": "આંક પાડવાની અરજી",
            "name_en": "Application for Exhibit / Mark",
            "category": "General",
            "status": "published",
        }))

        # Delete via admin API
        del_res = run_async(server.admin_delete_template(tid, admin=self.admin))
        self.assertTrue(del_res.get("success"))

        # Verify tombstones
        tomb = run_async(mock_db_instance.collection("deleted_templates").document(tid).get())
        self.assertTrue(tomb.exists)

        # Call admin_list_templates (Admin panel load)
        admin_list = run_async(server.admin_list_templates(admin=self.admin))
        templates_in_admin = admin_list if isinstance(admin_list, list) else admin_list.get("templates", [])
        self.assertFalse(
            any(t.get("id") == tid for t in templates_in_admin),
            "Deleted aanke_padvani_arji must NOT appear in Admin list (especially not with status 'seed')"
        )

        # Force seed templates
        seed_res = run_async(server.seed_templates(force=True))
        self.assertTrue(seed_res.get("success"))

        # Verify it remains absent from db.templates
        snap_after_seed = run_async(mock_db_instance.collection("templates").document(tid).get())
        self.assertFalse(snap_after_seed.exists)

        # Verify it remains absent from Admin list after seed
        admin_list_after = run_async(server.admin_list_templates(admin=self.admin))
        self.assertFalse(any(t.get("id") == tid for t in (admin_list_after if isinstance(admin_list_after, list) else admin_list_after.get("templates", []))))

        # Verify absent from Lawyer Frontend published templates
        server.invalidate_published_templates_cache()
        pub = run_async(server._get_published_templates())
        self.assertFalse(any(t.get("id") == tid for t in pub))

    # =========================================================================
    # REQUIREMENT 2: ADMIN-TO-FRONTEND SYNCHRONIZATION
    # =========================================================================
    def test_req2_create_and_publish_synchronization(self):
        """Admin creates and publishes a template -> immediately appears in published templates."""
        class CreateReq:
            id = "custom_test_bail_app"
            name_en = "Custom Bail Application"
            name_gu = "કસ્ટમ જામીન અરજી"
            category = "Bail"
            sub_category = None
            description = ""
            tags = []
            aliases = []
            case_types = []
            courts = []
            jurisdiction = None
            fields = []
            saved_case_fields = []
            direct_template_fields = []
            placeholders = []
            content_gu = "જામીન મુક્ત કરવા બાબત"
            content_en = "Application for Bail"
            editor_content_gu = None
            editor_content_en = None
            settings = None

        c_res = run_async(server.admin_create_template(CreateReq(), admin=self.admin))
        self.assertEqual(c_res.get("id"), "custom_test_bail_app")

        # In draft, it should not be in published catalog
        server.invalidate_published_templates_cache()
        pub = run_async(server._get_published_templates())
        self.assertFalse(any(t["id"] == "custom_test_bail_app" for t in pub))

        # Admin publishes template
        p_res = run_async(server.admin_publish_template("custom_test_bail_app", admin=self.admin))
        self.assertTrue(p_res.get("success"))

        # Now it must appear in published templates
        server.invalidate_published_templates_cache()
        pub2 = run_async(server._get_published_templates())
        found = next((t for t in pub2 if t["id"] == "custom_test_bail_app"), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["name_en"], "Custom Bail Application")
        self.assertEqual(found["category"], "Bail")

    def test_req2_edit_synchronization(self):
        """Admin edits a draft template and publishes -> updated metadata immediately reflects in published catalog."""
        target_id = "custom_draft_template"
        # Seed an existing draft template doc
        run_async(mock_db_instance.collection("templates").document(target_id).set({
            "id": target_id,
            "name_gu": "મૂળ અરજી",
            "name_en": "Original Application",
            "category": "General",
            "status": "draft",
            "content_gu": "મૂળ લખાણ",
            "content_en": "Original Content",
            "fields": [],
        }))

        # Admin updates draft template
        class UpdateReq:
            name_en = "Updated Application Title"
            name_gu = "સુધારેલી અરજી શીર્ષક"
            category = "Criminal"
            sub_category = None
            description = "Special updated court application"
            tags = None
            aliases = None
            case_types = None
            courts = None
            jurisdiction = None
            fields = None
            saved_case_fields = None
            direct_template_fields = None
            placeholders = None
            content_en = None
            content_gu = None
            editor_content_en = None
            editor_content_gu = None
            settings = None
            version_reason = "Updated title"

        u_res = run_async(server.admin_update_template(target_id, UpdateReq(), admin=self.admin))
        self.assertEqual(u_res.get("name_en"), "Updated Application Title")

        # Admin publishes the updated draft
        p_res = run_async(server.admin_publish_template(target_id, admin=self.admin))
        self.assertTrue(p_res.get("success"))

        # Verify published templates reflect the edit
        server.invalidate_published_templates_cache()
        pub = run_async(server._get_published_templates())
        found = next((t for t in pub if t["id"] == target_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["name_en"], "Updated Application Title")
        self.assertEqual(found["name_gu"], "સુધારેલી અરજી શીર્ષક")
        self.assertEqual(found["category"], "Criminal")

    def test_req2_archive_synchronization(self):
        """Admin archives a template -> immediately disappears from published catalog."""
        run_async(mock_db_instance.collection("templates").document("test_archivable_tpl").set({
            "id": "test_archivable_tpl",
            "name_en": "Archivable Template",
            "name_gu": "આર્કાઇવ અરજી",
            "status": "published",
        }))

        # Verify it's initially published
        pub_before = run_async(server._get_published_templates())
        self.assertTrue(any(t["id"] == "test_archivable_tpl" for t in pub_before))

        # Admin archives it
        a_res = run_async(server.admin_archive_template("test_archivable_tpl", admin=self.admin))
        self.assertTrue(a_res.get("success"))

        # Verify excluded from published catalog
        server.invalidate_published_templates_cache()
        pub_after = run_async(server._get_published_templates())
        self.assertFalse(any(t["id"] == "test_archivable_tpl" for t in pub_after))

    # =========================================================================
    # REQUIREMENT 3: PERMANENT TEMPLATE ORDER
    # =========================================================================
    def test_req3_drag_and_drop_order_persistence_and_backend_alignment(self):
        """
        Direct table drag-and-drop order:
        1. Persists to settings.template_display_order.
        2. Updates sort_order on existing template docs.
        3. Never creates ghost documents for non-existent IDs.
        4. /templates published templates returns exact ordered sequence.
        5. Persists across cache invalidation, logout/login, and subsequent sessions.
        """
        # Pre-seed 3 templates
        t_ids = ["template_c", "template_a", "template_b"]
        for tid in t_ids:
            run_async(mock_db_instance.collection("templates").document(tid).set({
                "id": tid,
                "name_en": f"Name {tid}",
                "name_gu": f"ગુજરાતી {tid}",
                "status": "published",
                "sort_order": 999,
            }))

        # Reorder them to: template_a, template_b, template_c, and a non-existent ghost_id
        desired_order = ["template_a", "template_b", "template_c", "non_existent_ghost"]
        class OrderReq:
            template_order = desired_order

        ord_res = run_async(server.admin_update_template_order(OrderReq(), admin=self.admin))
        self.assertTrue(ord_res.get("success"))

        # Verify settings document in Firestore has clean order
        setting_snap = run_async(mock_db_instance.collection("settings").document("template_display_order").get())
        self.assertTrue(setting_snap.exists)
        saved_order = setting_snap.to_dict().get("value")
        self.assertEqual(saved_order, desired_order)

        # Verify non_existent_ghost was NOT created as a ghost document
        ghost_snap = run_async(mock_db_instance.collection("templates").document("non_existent_ghost").get())
        self.assertFalse(ghost_snap.exists)

        # Verify sort_order was updated on existing docs
        doc_a = (run_async(mock_db_instance.collection("templates").document("template_a").get())).to_dict()
        doc_b = (run_async(mock_db_instance.collection("templates").document("template_b").get())).to_dict()
        doc_c = (run_async(mock_db_instance.collection("templates").document("template_c").get())).to_dict()
        self.assertEqual(doc_a.get("sort_order"), 0)
        self.assertEqual(doc_b.get("sort_order"), 1)
        self.assertEqual(doc_c.get("sort_order"), 2)

        # Verify published templates returned strictly in this order
        server.invalidate_published_templates_cache()
        pub = run_async(server._get_published_templates())
        filtered_ids = [t["id"] for t in pub if t["id"] in ["template_a", "template_b", "template_c"]]
        self.assertEqual(filtered_ids, ["template_a", "template_b", "template_c"])

        # Simulate subsequent session / reload / cache clearing
        server.invalidate_settings_cache("template_display_order")
        server.invalidate_published_templates_cache()
        pub_reloaded = run_async(server._get_published_templates())
        reloaded_ids = [t["id"] for t in pub_reloaded if t["id"] in ["template_a", "template_b", "template_c"]]
        self.assertEqual(reloaded_ids, ["template_a", "template_b", "template_c"])


if __name__ == "__main__":
    unittest.main()
