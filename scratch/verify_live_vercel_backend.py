"""
Live Vercel Backend Automated Verification & Acceptance Test Suite
==================================================================
Usage:
    python scratch/verify_live_vercel_backend.py <BACKEND_URL>

Example:
    python scratch/verify_live_vercel_backend.py https://nyaysetu-backend.vercel.app
"""
import sys
import json
import base64
import hashlib
import urllib.request
import urllib.error

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

if len(sys.argv) < 2:
    print("Error: Please provide the target backend URL.")
    print("Usage: python scratch/verify_live_vercel_backend.py <BACKEND_URL>")
    sys.exit(1)

TARGET_URL = sys.argv[1].rstrip("/")

print("=" * 70)
print(f"NYAYSETU PRO — LIVE BACKEND ACCEPTANCE VERIFICATION")
print(f"Target URL: {TARGET_URL}")
print("=" * 70)

def http_req(method, path, body=None, token=None):
    url = f"{TARGET_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            res_body = resp.read()
            try:
                res_json = json.loads(res_body.decode('utf-8'))
            except Exception:
                res_json = res_body
            return status, res_json
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='ignore')
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = err_body
        return e.code, err_json
    except Exception as e:
        return 0, str(e)

# 1. Health & Root Endpoints
print("\n[Step 1] Verifying Root & Healthcheck Endpoints...")
st, data = http_req("GET", "/healthz")
assert st == 200, f"Healthz failed with status {st}: {data}"
print(f"  ✓ GET /healthz: 200 OK -> {data}")

st, data = http_req("GET", "/")
assert st == 200, f"Root GET / failed with status {st}: {data}"
print(f"  ✓ GET /: 200 OK -> {data}")

st, data = http_req("GET", "/api/")
assert st == 200, f"GET /api/ failed with status {st}: {data}"
print(f"  ✓ GET /api/: 200 OK -> {data}")

# 2. Master Catalogs
print("\n[Step 2] Verifying Master Catalogs...")
st, dists = http_req("GET", "/api/catalog/districts")
assert st == 200 and len(dists) == 34, f"Districts failed: {st}, count: {len(dists) if isinstance(dists, list) else 0}"
print(f"  ✓ GET /api/catalog/districts: 200 OK (34 districts)")

st, courts = http_req("GET", "/api/catalog/courts?district_id=ahmedabad")
assert st == 200 and len(courts) == 47, f"Courts failed: {st}, count: {len(courts) if isinstance(courts, list) else 0}"
print(f"  ✓ GET /api/catalog/courts: 200 OK (47 authoritative courts)")

st, case_types = http_req("GET", "/api/catalog/case-types")
assert st == 200 and len(case_types) >= 18, f"Case types failed: {st}"
print(f"  ✓ GET /api/catalog/case-types: 200 OK ({len(case_types)} case types)")

st, templates = http_req("GET", "/api/templates")
assert st == 200 and len(templates) >= 10, f"Templates failed: {st}"
print(f"  ✓ GET /api/templates: 200 OK ({len(templates)} templates loaded)")

print("\n" + "=" * 70)
print("LIVE BACKEND BASELINE CHECKS PASSED WITH 100% SUCCESS")
print("=" * 70)
