import os
import sys
import unittest
from unittest.mock import MagicMock, patch
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

    async def set(self, data, merge=False):
        bucket = self.store.setdefault(self.coll, {})
        if merge and self.id in bucket:
            bucket[self.id].update(data)
        else:
            bucket[self.id] = dict(data)

    async def delete(self):
        self.store.get(self.coll, {}).pop(self.id, None)


class _Query:
    def __init__(self, store, coll, field, value):
        self.store = store
        self.coll = coll
        self.field = field
        self.value = value

    def limit(self, *args, **kwargs):
        return self

    async def stream(self):
        for doc_id, data in list(self.store.get(self.coll, {}).items()):
            if data.get(self.field) == self.value:
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
                return _Query(store, name, getattr(filter, "field", "user_id"), getattr(filter, "value", None))

        return _Coll()


class TestAccountDeletion(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = {
            "settings": {"app": {"signup_credits": 5}},
            "users": {
                "u1": {"id": "u1", "mobile": "9876543210", "email": "adv1@example.com", "name": "Adv One", "referral_code": "ADV1"},
                "u2": {"id": "u2", "mobile": "9999999999", "email": "adv2@example.com", "name": "Adv Two", "referral_code": "ADV2"},
            },
            "wallets": {
                "w1": {"id": "w1", "user_id": "u1", "balance": 10},
                "w2": {"id": "w2", "user_id": "u2", "balance": 5},
            },
            "cases": {
                "c1": {"id": "c1", "user_id": "u1", "party_name": "Client A"},
                "c2": {"id": "c2", "user_id": "u2", "party_name": "Client B"},
            },
            "drafts": {
                "d1": {"id": "d1", "user_id": "u1", "template_id": "mudat_arji"},
                "d2": {"id": "d2", "user_id": "u2", "template_id": "mudat_arji"},
            },
            "applications": {
                "a1": {"id": "a1", "user_id": "u1", "template_name": "Mudat Arji"},
                "a2": {"id": "a2", "user_id": "u2", "template_name": "Mudat Arji"},
            },
            "notifications": {"n1": {"id": "n1", "user_id": "u1", "title": "Hi"}},
            "user_sessions": {"s1": {"id": "s1", "user_id": "u1", "token_hash": "h1"}},
            "otps": {"9876543210": {"otp": "123456"}},
            "coupon_claims": {
                "LAUNCH50_u1": {
                    "id": "LAUNCH50_u1",
                    "code": "LAUNCH50",
                    "user_id": "u1",
                    "user_name": "Adv One",
                    "user_mobile": "9876543210",
                    "user_email": "adv1@example.com",
                    "credits_granted": 50,
                }
            },
        }
        self.mem_db = _MemDB(self.store)

    async def test_delete_account_erases_pii_preserves_other_users_and_blocks_free_credit_farming(self):
        with patch.object(server, "db", self.mem_db):
            token_u1 = server.make_token("u1", 0)
            res = await server.delete_my_account(response=MagicMock(), user=dict(self.store["users"]["u1"]))
            self.assertTrue(res["success"])

            # u1 personal collections & user doc deleted
            self.assertNotIn("u1", self.store["users"])
            self.assertNotIn("w1", self.store["wallets"])
            self.assertNotIn("c1", self.store["cases"])
            self.assertNotIn("d1", self.store["drafts"])
            self.assertNotIn("a1", self.store["applications"])
            self.assertNotIn("n1", self.store["notifications"])
            self.assertNotIn("s1", self.store["user_sessions"])
            self.assertNotIn("9876543210", self.store["otps"])

            # coupon claim PII wiped while count record remains
            claim = self.store["coupon_claims"]["LAUNCH50_u1"]
            self.assertIsNone(claim["user_name"])
            self.assertIsNone(claim["user_mobile"])
            self.assertIsNone(claim["user_email"])

            # u2 untouched
            self.assertIn("u2", self.store["users"])
            self.assertIn("c2", self.store["cases"])
            self.assertIn("d2", self.store["drafts"])
            self.assertIn("a2", self.store["applications"])

            # Existing JWT for u1 fails cleanly (401)
            with self.assertRaises(HTTPException) as ctx:
                await server.get_user(authorization=f"Bearer {token_u1}")
            self.assertEqual(ctx.exception.status_code, 401)

            # Re-registering with deleted mobile grants 0 free signup credits; brand new mobile gets 5
            re_user = await server.create_new_user(mobile="9876543210", provider="mobile")
            re_wallet = next(w for w in self.store["wallets"].values() if w["user_id"] == re_user["id"])
            self.assertEqual(re_wallet["balance"], 0)

            fresh_user = await server.create_new_user(mobile="9123456789", provider="mobile")
            fresh_wallet = next(w for w in self.store["wallets"].values() if w["user_id"] == fresh_user["id"])
            self.assertEqual(fresh_wallet["balance"], 5)

    async def test_partial_child_failure_does_not_orphan_user(self):
        with patch.object(server, "db", self.mem_db), \
             patch.object(server, "_delete_collection_by_user", side_effect=RuntimeError("transient error")):
            with self.assertRaises(HTTPException) as ctx:
                await server.delete_my_account(response=MagicMock(), user=dict(self.store["users"]["u1"]))
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("u1", self.store["users"])


if __name__ == "__main__":
    unittest.main()
