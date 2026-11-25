import os
import sys
import unittest
from unittest.mock import patch
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server


class _Snap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store, coll, doc_id):
        self.store = store
        self.coll = coll
        self.id = doc_id

    async def get(self):
        return _Snap(self.id, self.store.get(self.coll, {}).get(self.id))

    async def delete(self):
        self.store.get(self.coll, {}).pop(self.id, None)


class _Query:
    def __init__(self, store, coll, user_id):
        self.store = store
        self.coll = coll
        self.user_id = user_id

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def stream(self):
        for doc_id, data in list(self.store.get(self.coll, {}).items()):
            if data.get("user_id") == self.user_id:
                yield _Snap(doc_id, data)


class _MemDB:
    def __init__(self, store):
        self.store = store

    def collection(self, name):
        store = self.store

        class _Coll:
            def document(self, doc_id):
                return _DocRef(store, name, doc_id)

            def where(self, filter=None):
                user_id = getattr(filter, "value", None)
                return _Query(store, name, user_id)

        return _Coll()


class TestVaultDeletePersistence(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = {
            "drafts": {
                "legacy_mongo_doc_key": {
                    "id": "draft_u1_tpl1_case1",
                    "user_id": "u1",
                    "template_id": "tpl1",
                    "updated_at": "2026-11-26T00:00:00",
                },
                "doc_without_body_id": {
                    "user_id": "u1",
                    "template_id": "tpl2",
                    "updated_at": "2026-11-25T00:00:00",
                },
                "u2_draft": {
                    "id": "u2_draft",
                    "user_id": "u2",
                    "template_id": "tpl1",
                    "updated_at": "2026-11-26T00:00:00",
                },
            },
            "applications": {
                "legacy_app_key": {
                    "id": "app_uuid_1",
                    "user_id": "u1",
                    "template_name": "Exemption Application",
                    "created_at": "2026-11-26T00:00:00",
                },
                "u2_app": {
                    "id": "u2_app",
                    "user_id": "u2",
                    "template_name": "Other User App",
                    "created_at": "2026-11-26T00:00:00",
                },
            },
        }
        self.mem_db = _MemDB(self.store)

    async def test_draft_and_application_delete_handles_mismatched_and_missing_ids(self):
        u1 = {"id": "u1"}
        u2 = {"id": "u2"}

        with patch.object(server, "db", self.mem_db):
            # 1. list_drafts returns normalized `id` even when doc body lacks `id`
            drafts = await server.list_drafts(user=u1)
            self.assertEqual({d["id"] for d in drafts}, {"draft_u1_tpl1_case1", "doc_without_body_id"})

            # 2. Deleting draft by body `id` works even when Firestore doc key is different
            res1 = await server.delete_draft("draft_u1_tpl1_case1", user=u1)
            self.assertEqual(res1["deleted"], 1)
            self.assertNotIn("legacy_mongo_doc_key", self.store["drafts"])

            # 3. Deleting draft whose body had no `id` (resolved from snap.id) deletes cleanly
            res2 = await server.delete_draft("doc_without_body_id", user=u1)
            self.assertEqual(res2["deleted"], 1)
            self.assertEqual(await server.list_drafts(user=u1), [])

            # 4. Cross-user draft delete is forbidden
            with self.assertRaises(HTTPException) as ctx:
                await server.delete_draft("u2_draft", user=u1)
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("u2_draft", self.store["drafts"])

            # 5. Generated application delete works across mismatched doc key and disappears from history
            hist_before = await server.application_history(user=u1)
            self.assertEqual([h["id"] for h in hist_before], ["app_uuid_1"])
            res_app = await server.delete_application("app_uuid_1", user=u1)
            self.assertEqual(res_app["deleted"], 1)
            self.assertEqual(await server.application_history(user=u1), [])

            # 6. Cross-user application delete is forbidden and leaves u2 untouched
            with self.assertRaises(HTTPException) as ctx_app:
                await server.delete_application("u2_app", user=u1)
            self.assertEqual(ctx_app.exception.status_code, 403)
            self.assertEqual(len(await server.application_history(user=u2)), 1)


if __name__ == "__main__":
    unittest.main()
