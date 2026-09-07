"""
Test-only Firestore collection adapter.
Maps Mongo-style test helpers (insert_one, find_one, find, update_one, delete_one)
to native Firestore AsyncClient operations.
This is NOT production code — it only lives in the test suite so existing test
setup/verification code works against the Firestore emulator.
"""
import uuid
from google.cloud import firestore


def _apply_projection(d, projection):
    if not d or not projection:
        return d
    include_keys = {k for k, v in projection.items() if v}
    exclude_keys = {k for k, v in projection.items() if not v}
    if include_keys:
        return {k: v for k, v in d.items() if k in include_keys and k not in exclude_keys}
    return {k: v for k, v in d.items() if k not in exclude_keys}


class _FirestoreCollectionProxy:
    """Wraps db.collection(name) to provide Mongo-like helpers for tests."""

    def __init__(self, client, name):
        self._client = client
        self._name = name

    async def insert_one(self, doc):
        doc = dict(doc)  # shallow copy
        if self._name == "otps" and "mobile" in doc:
            doc_id = doc["mobile"]
        elif doc.get("id") == "":
            doc_id = "empty_id_doc"
        else:
            doc_id = doc.get("id") or str(uuid.uuid4())
        if "id" not in doc:
            doc["id"] = doc_id
        await self._client.collection(self._name).document(doc_id).set(doc)

        class _Result:
            inserted_id = doc_id
        return _Result()

    async def find_one(self, query=None, projection=None):
        if query is None:
            query = {}
        # Simple case: query by id
        if "id" in query and isinstance(query["id"], str):
            doc_key = "empty_id_doc" if query["id"] == "" else query["id"]
            snap = await self._client.collection(self._name).document(doc_key).get()
            d = snap.to_dict() if snap.exists else None
            return _apply_projection(d, projection)
        # Query by field filters
        ref = self._client.collection(self._name)
        for k, v in query.items():
            if k == "_id":
                continue
            if isinstance(v, dict):
                # Handle operators like $ne
                for op, val in v.items():
                    if op == "$ne":
                        ref = ref.where(filter=firestore.FieldFilter(k, "!=", val))
            else:
                ref = ref.where(filter=firestore.FieldFilter(k, "==", v))
        ref = ref.limit(1)
        results = ref.stream()
        async for doc in results:
            d = doc.to_dict()
            if projection:
                d = {k: v for k, v in d.items() if k not in projection}
            return d
        return None

    def find(self, query=None, projection=None):
        return _FindCursor(self._client, self._name, query or {}, projection)

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if doc:
            doc_id = doc["id"]
            data = {}
            if "$set" in update:
                data.update(update["$set"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    data[k] = firestore.Increment(v)
            if "$push" in update:
                for k, v in update["$push"].items():
                    data[k] = firestore.ArrayUnion([v])
            if "$pull" in update:
                for k, v in update["$pull"].items():
                    data[k] = firestore.ArrayRemove([v])
            # If update has no operators, treat entire update dict as $set
            if not any(k.startswith("$") for k in update):
                data.update(update)
            await self._client.collection(self._name).document(doc_id).set(data, merge=True)
        elif upsert:
            merged = dict(query)
            if "$set" in update:
                merged.update(update["$set"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    merged[k] = v  # initial value for upsert
            await self.insert_one(merged)

    async def delete_one(self, query):
        doc = await self.find_one(query)

        class _Result:
            deleted_count = 0
        r = _Result()
        if doc:
            await self._client.collection(self._name).document(doc["id"]).delete()
            r.deleted_count = 1
        return r

    async def count_documents(self, query=None):
        results = self.find(query or {})
        items = await results.to_list(None)
        return len(items)

    async def drop(self):
        """Delete all documents in the collection."""
        async for doc in self._client.collection(self._name).stream():
            await doc.reference.delete()


class _FindCursor:
    """Mimics a Motor cursor with .to_list(), .sort(), .skip(), .limit()."""

    def __init__(self, client, coll_name, query, projection=None):
        self._client = client
        self._coll_name = coll_name
        self._query = query
        self._projection = projection
        self._sort_field = None
        self._sort_dir = None
        self._skip_n = 0
        self._limit_n = None

    def sort(self, field, direction=1):
        if isinstance(field, list):
            # list of tuples: [(field, dir), ...]
            if field:
                self._sort_field = field[0][0]
                self._sort_dir = field[0][1]
        else:
            self._sort_field = field
            self._sort_dir = direction
        return self

    def skip(self, n):
        self._skip_n = n
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    async def to_list(self, length=None):
        ref = self._client.collection(self._coll_name)
        for k, v in self._query.items():
            if k == "_id":
                continue
            if isinstance(v, dict):
                for op, val in v.items():
                    if op == "$ne":
                        ref = ref.where(filter=firestore.FieldFilter(k, "!=", val))
                    elif op == "$gte":
                        ref = ref.where(filter=firestore.FieldFilter(k, ">=", val))
                    elif op == "$lte":
                        ref = ref.where(filter=firestore.FieldFilter(k, "<=", val))
                    elif op == "$gt":
                        ref = ref.where(filter=firestore.FieldFilter(k, ">", val))
                    elif op == "$lt":
                        ref = ref.where(filter=firestore.FieldFilter(k, "<", val))
                    elif op == "$in":
                        ref = ref.where(filter=firestore.FieldFilter(k, "in", val))
            else:
                ref = ref.where(filter=firestore.FieldFilter(k, "==", v))

        if self._sort_field:
            direction = firestore.Query.DESCENDING if self._sort_dir == -1 else firestore.Query.ASCENDING
            ref = ref.order_by(self._sort_field, direction=direction)

        results = []
        async for doc in ref.stream():
            d = doc.to_dict()
            results.append(_apply_projection(d, self._projection))

        if self._skip_n:
            results = results[self._skip_n:]
        if self._limit_n:
            results = results[:self._limit_n]
        if length and length > 0:
            results = results[:length]
        return results


class FirestoreDBSurrogate:
    """
    Drop-in replacement for the _DBSurrogate pattern used across test files.
    Usage in tests:
        from firestore_test_utils import FirestoreDBSurrogate
        db = FirestoreDBSurrogate()
    Then db.wallets.insert_one(...), db.users.find_one(...), etc. all work.
    """

    def __init__(self):
        pass

    def collection(self, name):
        import server
        target = server.db
        if target is self:
            from conftest import _global_firestore_proxy
            target = _global_firestore_proxy
        if hasattr(target, "_get_client"):
            return target._get_client().collection(name)
        return target.collection(name)

    def batch(self):
        import server
        target = server.db
        if target is self:
            from conftest import _global_firestore_proxy
            target = _global_firestore_proxy
        if hasattr(target, "_get_client"):
            return target._get_client().batch()
        return target.batch()

    def __getattr__(self, name):
        import server
        if name.startswith("_"):
            raise AttributeError(name)
        # Pass through native AsyncClient methods (collection, batch, etc.)
        if hasattr(server.db, name):
            attr = getattr(server.db, name)
            if callable(attr):
                return attr
        # Otherwise treat as a collection name (Mongo-style db.users, db.wallets, etc.)
        return _FirestoreCollectionProxy(server.db, name)

    def __getitem__(self, name):
        import server
        return _FirestoreCollectionProxy(server.db, name)
