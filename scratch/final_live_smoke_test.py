import urllib.request
import json

BASE = "https://nyaysetupro.in"

routes_to_test = [
    ("/", 200, "Lawyer Root", ["Anek Gujarati", "root"]),
    ("/admin", 200, "Admin Root", ["<title>NyaySetu Pro - Admin Portal</title>", "/admin/assets/index-"]),
    ("/admin/login", 200, "Admin Login", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/dashboard", 200, "Admin Dashboard", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/users", 200, "Admin Users", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/templates", 200, "Admin Templates", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/case-forms", 200, "Admin Case Forms", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/catalog", 200, "Admin Catalog", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/plans", 200, "Admin Plans", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/audit-logs", 200, "Admin Audit Logs", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/settings", 200, "Admin Settings", ["<title>NyaySetu Pro - Admin Portal</title>"]),
    ("/admin/nyaysetu-logo.png", 200, "Admin Logo Asset", []),
    ("/admin/assets/index-DKaBQchA.css", 200, "Admin Scoped CSS", []),
    ("/admin/assets/index-Zw1qS4eu.js", 200, "Admin Main Bundle (Session Persistence Enabled)", ["NyaySetu Pro", "admin_refresh_token", "case-forms"]),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

print("=" * 60)
print("NYAYSETU PRO - LIVE PRODUCTION SMOKE TEST REPORT")
print("=" * 60)

for path, expected_status, label, expected_strings in routes_to_test:
    url = BASE + path
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        assert resp.status == expected_status, f"{url} expected {expected_status}, got {resp.status}"
        
        # Verify body text if checking HTML/JS
        if expected_strings:
            text = body.decode("utf-8", errors="ignore")
            for exp in expected_strings:
                assert exp in text, f"{url} missing expected marker: {exp}"
                
        print(f"[OK] {path:<35} | HTTP {resp.status} | {label} (Bytes: {len(body)})")

print("\n" + "=" * 60)
print("ALL 14 PRODUCTION ENDPOINTS VERIFIED AND HEALTHY!")
print("=" * 60)
