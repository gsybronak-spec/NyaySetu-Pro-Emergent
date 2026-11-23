# -*- coding: utf-8 -*-
"""Verification tests for the LAUNCH50 coupon system:
1. First 100 new users receive 50 free template credits.
2. Claim tracking in coupons/LAUNCH50 and coupon_claims collection.
3. Strict limit of 100: 101st user receives default 5 signup credits.
4. Idempotency & anti-abuse checks.
5. GET /api/coupon/status returns accurate remaining slots and active status.
6. Regular user referrals (+10 credits to referrer) remain completely unaffected.
"""

import asyncio
import unittest
import uuid
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import server
from server import (
    LAUNCH_COUPON_CODES,
    LAUNCH_COUPON_MAX_CLAIMS,
    LAUNCH_COUPON_CREDITS,
    apply_launch_coupon,
    apply_referral,
    get_coupon_status,
)


class MockDocRef:
    def __init__(self, data=None):
        self._data = data or {}

    async def get(self):
        m = MagicMock()
        m.exists = bool(self._data)
        m.to_dict.return_value = dict(self._data)
        return m

    async def set(self, data, merge=False):
        if merge:
            self._data.update(data)
        else:
            self._data = dict(data)

    async def update(self, data):
        for k, v in data.items():
            if hasattr(v, "value"): # Mock firestore.Increment
                self._data[k] = self._data.get(k, 0) + v.value
            elif str(type(v)).find("Increment") != -1:
                self._data[k] = self._data.get(k, 0) + 1
            else:
                self._data[k] = v


class MockCollection:
    def __init__(self):
        self._docs = {}

    def document(self, doc_id):
        if doc_id not in self._docs:
            self._docs[doc_id] = MockDocRef()
        return self._docs[doc_id]

    def where(self, filter=None):
        return self

    def limit(self, n):
        return self

    async def stream(self):
        for doc_id, doc_ref in self._docs.items():
            snap = MagicMock()
            snap.id = doc_id
            snap.to_dict.return_value = dict(doc_ref._data)
            snap.reference = doc_ref
            yield snap

    async def get(self):
        results = []
        async for s in self.stream():
            results.append(s)
        return results


class MockFirestore:
    def __init__(self):
        self._cols = {}

    def collection(self, name):
        if name not in self._cols:
            self._cols[name] = MockCollection()
        return self._cols[name]


class TestLaunchCoupon50(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_db = MockFirestore()
        server.db = self.mock_db

    async def test_01_constants(self):
        """Verify launch coupon configuration parameters."""
        self.assertIn("LAUNCH50", LAUNCH_COUPON_CODES)
        self.assertEqual(LAUNCH_COUPON_MAX_CLAIMS, 100)
        self.assertEqual(LAUNCH_COUPON_CREDITS, 50)

    async def test_02_first_new_user_grants_50_credits(self):
        """First new user using LAUNCH50 gets 50 template credits and claim is recorded."""
        user_id = "user_new_1"
        new_user = {
            "id": user_id,
            "name": "Advocate Test One",
            "mobile": "9998887771",
            "email": "test1@nyaysetu.in",
        }
        # Initially user has wallet with 5 signup credits
        wallet_ref = self.mock_db.collection("wallets").document(f"w_{user_id}")
        await wallet_ref.set({
            "user_id": user_id,
            "balance": 5,
            "free_credits_granted": 5,
            "total_used": 0,
        })
        user_doc_ref = self.mock_db.collection("users").document(user_id)
        await user_doc_ref.set(new_user)

        # Apply launch coupon via apply_referral
        await apply_referral("LAUNCH50", new_user)

        # 1. Wallet balance must be updated to 50
        wallet_snap = await wallet_ref.get()
        self.assertEqual(wallet_snap.to_dict()["balance"], 50)
        self.assertEqual(wallet_snap.to_dict()["free_credits_granted"], 50)

        # 2. Coupon claim must be recorded
        claim_snap = await self.mock_db.collection("coupon_claims").document(f"LAUNCH50_{user_id}").get()
        self.assertTrue(claim_snap.exists)
        self.assertEqual(claim_snap.to_dict()["credits_granted"], 50)

        # 3. Coupon claimed_count must be 1
        coupon_snap = await self.mock_db.collection("coupons").document("LAUNCH50").get()
        self.assertTrue(coupon_snap.exists)
        self.assertEqual(coupon_snap.to_dict()["claimed_count"], 1)

        # 4. User doc has coupon marked
        u_snap = await user_doc_ref.get()
        self.assertEqual(u_snap.to_dict()["coupon_code"], "LAUNCH50")
        self.assertTrue(u_snap.to_dict()["launch_promo_applied"])

    async def test_03_case_insensitivity(self):
        """Lowercase 'launch50' works identically."""
        user_id = "user_new_2"
        new_user = {"id": user_id, "name": "Advocate Lowercase", "mobile": "9998887772"}
        wallet_ref = self.mock_db.collection("wallets").document(f"w_{user_id}")
        await wallet_ref.set({"user_id": user_id, "balance": 5, "free_credits_granted": 5})

        await apply_referral("launch50", new_user)
        wallet_snap = await wallet_ref.get()
        self.assertEqual(wallet_snap.to_dict()["balance"], 50)

    async def test_04_idempotent_double_claim_prevented(self):
        """Calling apply_referral multiple times for same user does not increment count or duplicate credits."""
        user_id = "user_new_3"
        new_user = {"id": user_id, "name": "Advocate Idempotent", "mobile": "9998887773"}
        wallet_ref = self.mock_db.collection("wallets").document(f"w_{user_id}")
        await wallet_ref.set({"user_id": user_id, "balance": 5, "free_credits_granted": 5})

        await apply_referral("LAUNCH50", new_user)
        snap1 = await self.mock_db.collection("coupons").document("LAUNCH50").get()
        count1 = snap1.to_dict()["claimed_count"]

        # Re-apply
        await apply_referral("LAUNCH50", new_user)
        snap2 = await self.mock_db.collection("coupons").document("LAUNCH50").get()
        self.assertEqual(snap2.to_dict()["claimed_count"], count1)

    async def test_05_exhaustion_at_100_claims(self):
        """When claimed_count reaches 100, 101st user does NOT get 50 credits and retains default 5."""
        # Pre-set coupon to 100 claims
        coupon_ref = self.mock_db.collection("coupons").document("LAUNCH50")
        await coupon_ref.set({
            "code": "LAUNCH50",
            "credit_reward": 50,
            "max_claims": 100,
            "claimed_count": 100,
            "active": False,
        })

        user_101 = {"id": "user_101", "name": "Advocate 101", "mobile": "9998887101"}
        wallet_ref = self.mock_db.collection("wallets").document("w_user_101")
        await wallet_ref.set({"user_id": "user_101", "balance": 5, "free_credits_granted": 5})

        applied = await apply_launch_coupon("LAUNCH50", user_101)
        self.assertFalse(applied, "apply_launch_coupon must return False when 100 slots are exhausted")

        # User 101 must remain with 5 default credits
        w_snap = await wallet_ref.get()
        self.assertEqual(w_snap.to_dict()["balance"], 5)
        self.assertEqual(w_snap.to_dict()["free_credits_granted"], 5)

        # Claimed count must not exceed 100
        c_snap = await coupon_ref.get()
        self.assertEqual(c_snap.to_dict()["claimed_count"], 100)

    async def test_06_coupon_status_endpoint(self):
        """GET /api/coupon/status returns accurate remaining and active flag."""
        coupon_ref = self.mock_db.collection("coupons").document("LAUNCH50")
        await coupon_ref.set({
            "code": "LAUNCH50",
            "credit_reward": 50,
            "max_claims": 100,
            "claimed_count": 42,
        })

        res = await get_coupon_status("LAUNCH50")
        self.assertEqual(res["code"], "LAUNCH50")
        self.assertEqual(res["credit_reward"], 50)
        self.assertEqual(res["max_claims"], 100)
        self.assertEqual(res["claimed_count"], 42)
        self.assertEqual(res["remaining"], 58)
        self.assertTrue(res["is_active"])

    async def test_07_regular_referral_unaffected(self):
        """A user's personal referral code (NSXXXXXX) rewards the referrer with 10 credits as usual."""
        referrer_id = "ref_user_a"
        ref_code = "NSABC123"
        await self.mock_db.collection("users").document(referrer_id).set({
            "id": referrer_id,
            "referral_code": ref_code,
        })
        await self.mock_db.collection("wallets").document(f"w_{referrer_id}").set({
            "user_id": referrer_id,
            "balance": 20,
        })

        new_user = {"id": "ref_user_b", "name": "Referred User"}
        await apply_referral(ref_code, new_user)

        # Referrer wallet must have +10 credits (20 + 10 = 30)
        ref_wallet = await self.mock_db.collection("wallets").document(f"w_{referrer_id}").get()
        self.assertEqual(ref_wallet.to_dict()["balance"], 30)


if __name__ == "__main__":
    unittest.main()
