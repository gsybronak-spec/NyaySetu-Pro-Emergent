import urllib.request
import re
import json
import time

BASE_URL = "https://nyaysetupro.in"

urls = [
    ("/", "Lawyer App"),
    ("/admin", "Admin Root"),
    ("/admin/login", "Admin Login"),
    ("/admin/dashboard", "Admin Dashboard"),
    ("/admin/users", "Admin Users"),
    ("/admin/templates", "Admin Templates"),
    ("/admin/case-forms", "Admin Case Forms"),
    ("/admin/catalog", "Admin Catalog"),
    ("/admin/plans", "Admin Plans"),
    ("/admin/audit-logs", "Admin Audit Logs"),
    ("/admin/settings", "Admin Settings"),
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_live():
    print(f"Testing live deployment at {BASE_URL}...\n")
    results = {}
    
    # 1. Test lawyer root
    req = urllib.request.Request(BASE_URL + "/", headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode("utf-8")
        results["/"] = {"status": resp.status, "len": len(content)}
        print(f"[OK] / -> HTTP {resp.status} (length: {len(content)})")
        assert "Anek Gujarati" in content or "expo" in content or "root" in content
    
    # 2. Test admin root
    req = urllib.request.Request(BASE_URL + "/admin", headers=headers)
    with urllib.request.urlopen(req) as resp:
        admin_html = resp.read().decode("utf-8")
        results["/admin"] = {"status": resp.status, "len": len(admin_html)}
        print(f"[OK] /admin -> HTTP {resp.status} (length: {len(admin_html)})")
        assert "<title>NyaySetu Pro - Admin Portal</title>" in admin_html, "Title mismatch in live /admin!"
        assert "/admin/assets/index-" in admin_html, "Asset script paths missing /admin/ prefix!"

    # 3. Test nested admin routes (SPA fallback)
    for path, label in urls[2:]:
        req = urllib.request.Request(BASE_URL + path, headers=headers)
        with urllib.request.urlopen(req) as resp:
            nested_html = resp.read().decode("utf-8")
            results[path] = {"status": resp.status, "len": len(nested_html)}
            print(f"[OK] {path} ({label}) -> HTTP {resp.status}")
            assert "<title>NyaySetu Pro - Admin Portal</title>" in nested_html, f"Title mismatch on {path}!"

    # 4. Fetch the admin JS asset bundle
    match = re.search(r'src="(/admin/assets/index-[^"]+\.js)"', admin_html)
    if not match:
        # Check without quotes or src attribute variations
        match = re.search(r'/admin/assets/index-[a-zA-Z0-9_-]+\.js', admin_html)
        js_path = match.group(0) if match else None
    else:
        js_path = match.group(1)

    print(f"\nDiscovered Admin JS Bundle: {js_path}")
    assert js_path is not None, "Could not find JS bundle URL in /admin HTML!"

    js_url = BASE_URL + js_path
    req = urllib.request.Request(js_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        js_content = resp.read().decode("utf-8")
        print(f"[OK] Fetched Admin JS ({len(js_content)} bytes) -> HTTP {resp.status}")
        
        # Verify Old Admin Markers
        assert "NyaySetu Pro" in js_content, "Missing brand marker in JS bundle!"
        assert "case-forms" in js_content or "Case Forms" in js_content, "Missing Case Forms in JS bundle!"
        
        # Verify New Super Admin is absent
        assert "SUPER ADMIN CONTROL CENTER" not in js_content, "New Super Admin text still present in JS bundle!"
        print("[OK] Verified: JS bundle contains ORIGINAL Old Admin Portal components!")
        print("[OK] Verified: NEW Dark Super Admin Portal is 100% ABSENT!")

    print("\n========================================================")
    print("ALL LIVE PRODUCTION VERIFICATIONS PASSED WITH 100% SUCCESS!")
    print("========================================================")
    return results

if __name__ == "__main__":
    test_live()
