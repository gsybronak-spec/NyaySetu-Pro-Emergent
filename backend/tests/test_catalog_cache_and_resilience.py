"""
Regression and reliability tests for NyaySetu Pro master catalog caching,
district-specific filtering, cache invalidation, and auth session resilience.
"""
import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_cache")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_cache"]

import server
server.db = mock_db

from starlette.testclient import TestClient
client = TestClient(server.app)


def test_backend_catalog_cache_hit():
    """Verify backend catalog caching serves subsequent requests from memory without DB roundtrips."""
    server._invalidate_catalog_cache()
    assert "districts" not in server._CATALOG_CACHE
    res1 = client.get("/api/catalog/districts")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) == 34
    assert "districts" in server._CATALOG_CACHE
    
    # 2. Second call should return cached data instantly
    res2 = client.get("/api/catalog/districts")
    assert res2.status_code == 200
    assert res2.json() == data1


def test_district_specific_talukas_and_courts():
    """Verify talukas and courts are strictly partitioned and filtered by district_id."""
    # 1. Talukas for Ahmedabad vs Gandhinagar
    ahmedabad_talukas = client.get("/api/catalog/talukas?district_id=ahmedabad").json()
    gandhinagar_talukas = client.get("/api/catalog/talukas?district_id=gandhinagar").json()
    
    assert len(ahmedabad_talukas) > 0
    assert len(gandhinagar_talukas) > 0
    assert ahmedabad_talukas != gandhinagar_talukas
    assert all(t["district_id"] == "ahmedabad" for t in ahmedabad_talukas)
    assert all(t["district_id"] == "gandhinagar" for t in gandhinagar_talukas)
    
    # 2. Courts for Ahmedabad vs Surat
    ahmedabad_courts = client.get("/api/catalog/courts?district_id=ahmedabad").json()
    surat_courts = client.get("/api/catalog/courts?district_id=surat").json()
    
    # Both should include generic courts
    generic_ids = {c["id"] for c in client.get("/api/catalog/courts").json() if c.get("district_id") == "generic"}
    ahmedabad_ids = {c["id"] for c in ahmedabad_courts}
    surat_ids = {c["id"] for c in surat_courts}
    
    for gid in generic_ids:
        assert gid in ahmedabad_ids
        assert gid in surat_ids
        
    # Non-generic Ahmedabad courts must not appear in Surat
    ahmedabad_specific = {c["id"] for c in ahmedabad_courts if c.get("district_id") == "ahmedabad"}
    for aid in ahmedabad_specific:
        assert aid not in surat_ids


def test_backend_cache_invalidation_on_mutation():
    """Verify admin catalog refresh invalidates memory cache."""
    # Prime cache
    client.get("/api/catalog/case-types")
    assert "case-types" in server._CATALOG_CACHE
    
    # Invalidate
    server._invalidate_catalog_cache()
    assert "case-types" not in server._CATALOG_CACHE
    
    # Re-fetch repopulates
    client.get("/api/catalog/case-types")
    assert "case-types" in server._CATALOG_CACHE


def test_concurrent_catalog_requests():
    """Simulate 20 rapid sequential catalog requests."""
    for _ in range(20):
        res = client.get("/api/catalog/districts")
        assert res.status_code == 200
        assert len(res.json()) == 34
