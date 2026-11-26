import base64
import io
import os
import sys
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from pdfminer.high_level import extract_text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server


class _Snap:
    def __init__(self, store, coll, doc_id, data):
        self.store = store
        self.coll = coll
        self.id = doc_id
        self._data = dict(data) if data is not None else None
        self.exists = data is not None

    @property
    def reference(self):
        return _DocRef(self.store, self.coll, self.id)

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store, coll, doc_id):
        self.store = store
        self.coll = coll
        self.id = doc_id

    @property
    def reference(self):
        return self

    async def get(self):
        return _Snap(self.store, self.coll, self.id, self.store.setdefault(self.coll, {}).get(self.id))

    async def set(self, data, merge=False):
        bucket = self.store.setdefault(self.coll, {})
        existing = dict(bucket.get(self.id) or {}) if merge else {}
        for k, v in data.items():
            if hasattr(v, "value"):  # firestore.Increment
                existing[k] = (existing.get(k) or 0) + v.value
            else:
                existing[k] = v
        bucket[self.id] = existing

    async def update(self, data):
        await self.set(data, merge=True)

    async def delete(self):
        self.store.setdefault(self.coll, {}).pop(self.id, None)


class _Query:
    def __init__(self, store, coll, filters=None, limit_val=None):
        self.store = store
        self.coll = coll
        self.filters = filters or []
        self.limit_val = limit_val

    def where(self, filter=None):
        new_filters = list(self.filters)
        if filter is not None:
            field = getattr(filter, "field_path", getattr(filter, "_field_path", None))
            op = getattr(filter, "op_string", getattr(filter, "_op_string", "=="))
            val = getattr(filter, "value", getattr(filter, "_value", None))
            new_filters.append((field, op, val))
        return _Query(self.store, self.coll, new_filters, self.limit_val)

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, n):
        return _Query(self.store, self.coll, self.filters, n)

    async def stream(self):
        count = 0
        for doc_id, data in list(self.store.get(self.coll, {}).items()):
            ok = True
            for field, op, val in self.filters:
                if op == "==" and data.get(field) != val:
                    ok = False
                    break
            if ok:
                yield _Snap(self.store, self.coll, doc_id, data)
                count += 1
                if self.limit_val and count >= self.limit_val:
                    break

    async def get(self):
        return [s async for s in self.stream()]


class _MemDB:
    def __init__(self, store):
        self.store = store

    def collection(self, name):
        store = self.store

        class _Coll:
            def document(self, doc_id):
                return _DocRef(store, name, doc_id)

            def where(self, filter=None):
                return _Query(store, name).where(filter=filter)

            def limit(self, n):
                return _Query(store, name).limit(n)

            async def stream(self):
                async for s in _Query(store, name).stream():
                    yield s

        return _Coll()


class TestVaultReEditAndUpdate(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.store = {
            "templates": {
                "adjournment": {
                    "id": "adjournment",
                    "template_id": "adjournment",
                    "name_en": "Adjournment Application",
                    "name_gu": "મુદ્દત અરજી",
                    "version": 1,
                    "is_published": True,
                    "fields": [
                        {"key": "next_date", "label_en": "Next Date", "label_gu": "આગળની તારીખ", "type": "date", "required": True},
                        {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "text", "required": True},
                    ],
                    "content_en": "Court: {{court}}\nCase: {{case_number}}\nNext Date: {{next_date}}\nReason: {{reason}}",
                    "content_gu": "કોર્ટ: {{court}}\nકેસ: {{case_number}}\nતારીખ: {{next_date}}\nકારણ: {{reason}}",
                    "settings": {"page_size": "A4"},
                }
            },
            "cases": {
                "c1": {
                    "id": "c1",
                    "user_id": "u1",
                    "case_number": "CS/101/2026",
                    "party_name": "Ramesh Patel",
                    "opposite_party": "Suresh Shah",
                    "court": "Civil Court, Ahmedabad",
                    "application_count": 0,
                },
                "c2": {
                    "id": "c2",
                    "user_id": "u1",
                    "case_number": "CS/202/2026",
                    "party_name": "Meena Desai",
                    "opposite_party": "Kiran Mehta",
                    "court": "Civil Court, Surat",
                    "application_count": 0,
                },
            },
            "wallets": {
                "w1": {"id": "w1", "user_id": "u1", "balance": 2, "total_used": 0},
                "w2": {"id": "w2", "user_id": "u2", "balance": 5, "total_used": 0},
            },
            "applications": {},
            "transactions": {},
            "drafts": {},
            "settings": {},
        }
        self.mem_db = _MemDB(self.store)

    async def test_application_saves_form_values_and_updates_without_duplicate(self):
        u1 = {"id": "u1", "name": "Adv. Ronak", "mobile": "9898000001"}
        u2 = {"id": "u2", "name": "Other User", "mobile": "9898000002"}

        with patch.object(server, "db", self.mem_db):
            # 1. Create initial application via download
            dl1 = await server.download_application(
                server.DownloadReq(
                    template_id="adjournment",
                    case_id="c1",
                    language="en",
                    format="pdf",
                    filename="Adjournment_1.pdf",
                    values={"next_date": "15-12-2026", "reason": "Medical rest"},
                    form_values={"next_date": "2026-12-15", "reason": "Medical rest"},
                ),
                user=u1,
            )
            app_id = dl1.get("application_id")
            self.assertTrue(app_id)
            self.assertEqual(self.store["wallets"]["w1"]["balance"], 1)
            self.assertEqual(self.store["cases"]["c1"]["application_count"], 1)
            self.assertEqual(len(self.store["applications"]), 1)

            # 2. Fetch saved application -> both values and form_values restored cleanly
            fetched = await server.get_application(app_id, user=u1)
            self.assertEqual(fetched["form_values"]["next_date"], "2026-12-15")
            self.assertEqual(fetched["form_values"]["reason"], "Medical rest")

            # Cross-user access must fail
            with self.assertRaises(HTTPException) as exc403:
                await server.get_application(app_id, user=u2)
            self.assertEqual(exc403.exception.status_code, 403)

            # 3. Update ONLY edited field via PUT -> updates same record, no duplicate, no credit consumed
            created_at = fetched["created_at"]
            upd = await server.update_application(
                app_id,
                server.ApplicationUpdateReq(
                    template_id="adjournment",
                    case_id="c1",
                    language="en",
                    filename="Adjournment_1",
                    values={"next_date": "15-12-2026", "reason": "Attending High Court matter"},
                    form_values={"next_date": "2026-12-15", "reason": "Attending High Court matter"},
                ),
                user=u1,
            )
            self.assertTrue(upd["success"])
            self.assertEqual(len(self.store["applications"]), 1)
            self.assertEqual(self.store["wallets"]["w1"]["balance"], 1)
            self.assertEqual(self.store["cases"]["c1"]["application_count"], 1)

            # 4. Re-download / re-generate PDF for existing application_id -> updates same record + PDF reflects edit
            dl2 = await server.download_application(
                server.DownloadReq(
                    application_id=app_id,
                    template_id="adjournment",
                    case_id="c1",
                    language="en",
                    format="pdf",
                    filename="Adjournment_1.pdf",
                    values={"next_date": "22-12-2026", "reason": "Attending High Court matter"},
                    form_values={"next_date": "2026-12-22", "reason": "Attending High Court matter"},
                ),
                user=u1,
            )
            self.assertEqual(dl2["application_id"], app_id)
            self.assertEqual(len(self.store["applications"]), 1)
            self.assertEqual(self.store["wallets"]["w1"]["balance"], 1)
            self.assertEqual(self.store["cases"]["c1"]["application_count"], 1)
            self.assertEqual(self.store["applications"][app_id]["created_at"], created_at)
            self.assertEqual(self.store["applications"][app_id]["form_values"]["next_date"], "2026-12-22")

            raw_pdf = base64.b64decode(dl2["base64"])
            self.assertTrue(raw_pdf.startswith(b"%PDF"))
            pdf_text = extract_text(io.BytesIO(raw_pdf))
            self.assertIn("Attending High Court matter", pdf_text)
            self.assertIn("22-12-2026", pdf_text)

            # 5. Cross-case update rejected
            with self.assertRaises(HTTPException) as exc400:
                await server.download_application(
                    server.DownloadReq(
                        application_id=app_id,
                        template_id="adjournment",
                        case_id="c2",
                        language="en",
                        format="pdf",
                        values={"next_date": "22-12-2026", "reason": "Other case"},
                    ),
                    user=u1,
                )
            self.assertEqual(exc400.exception.status_code, 400)

            # 6. Normal new application WITHOUT application_id still consumes remaining credit -> 0, then 402
            dl_new = await server.download_application(
                server.DownloadReq(
                    template_id="adjournment",
                    case_id="c2",
                    language="en",
                    format="pdf",
                    values={"next_date": "23-12-2026", "reason": "Separate new filing"},
                ),
                user=u1,
            )
            self.assertNotEqual(dl_new["application_id"], app_id)
            self.assertEqual(len(self.store["applications"]), 2)
            self.assertEqual(self.store["wallets"]["w1"]["balance"], 0)

            with self.assertRaises(HTTPException) as exc402:
                await server.download_application(
                    server.DownloadReq(
                        template_id="adjournment",
                        case_id="c2",
                        language="en",
                        format="pdf",
                        values={"next_date": "24-12-2026", "reason": "No credit left"},
                    ),
                    user=u1,
                )
            self.assertEqual(exc402.exception.status_code, 402)


if __name__ == "__main__":
    unittest.main()
