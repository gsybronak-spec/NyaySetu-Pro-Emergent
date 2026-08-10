import os
import time
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_forms")

import mongomock_motor
mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_forms"]

import server
server.db = mock_db

from starlette.testclient import TestClient
app_client = TestClient(server.app)

API = "/api"

@pytest.fixture(scope="module")
def user_token():
    mobile = "9998887776"
    app_client.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    res = app_client.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    return res.json()["token"]

def test_client_lookup_existing(user_token):
    res = app_client.get(f"{API}/clients/lookup?mobile=9998887776", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["client"]["mobile"] == "9998887776"

def test_client_lookup_unknown(user_token):
    res = app_client.get(f"{API}/clients/lookup?mobile=0000000000", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["client"] is None
    assert "not found" in data["message"].lower()

def test_client_lookup_invalid_mobile(user_token):
    res = app_client.get(f"{API}/clients/lookup?mobile=123", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 400

def test_get_all_case_forms():
    res = app_client.get(f"{API}/catalog/case-forms")
    assert res.status_code == 200
    forms = res.json()
    assert isinstance(forms, list)
    assert len(forms) >= 3

def test_get_specific_case_form():
    res = app_client.get(f"{API}/catalog/case-forms/civil")
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["case_type_id"] == "civil"
    assert "fields" in cfg
