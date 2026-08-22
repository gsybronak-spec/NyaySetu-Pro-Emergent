import os
import sys
from pathlib import Path

dist_dir = Path("frontend/dist").resolve()
admin_dir = dist_dir / "admin"

print(f"Dist Dir: {dist_dir}")
print(f"Admin Dir: {admin_dir}")

assert dist_dir.exists(), "frontend/dist does not exist!"
assert (dist_dir / "index.html").exists(), "frontend/dist/index.html does not exist!"
assert admin_dir.exists(), "frontend/dist/admin does not exist!"
assert (admin_dir / "index.html").exists(), "frontend/dist/admin/index.html does not exist!"

admin_html = (admin_dir / "index.html").read_text(encoding="utf-8")
print("\n--- Admin index.html checks ---")
assert "<title>NyaySetu Pro - Admin Portal</title>" in admin_html, "Title mismatch in admin/index.html!"
assert '/admin/assets/index-' in admin_html, "Assets are not scoped with /admin/ in admin/index.html!"
print("[OK] admin/index.html title and scoped asset references verified!")

# Verify asset files physically exist
assets_dir = admin_dir / "assets"
assert assets_dir.exists(), "admin/assets dir missing!"
css_files = list(assets_dir.glob("*.css"))
js_files = list(assets_dir.glob("*.js"))
assert len(css_files) > 0, "No CSS files found in admin/assets!"
assert len(js_files) > 0, "No JS files found in admin/assets!"

print(f"[OK] Found {len(js_files)} JS file(s): {[f.name for f in js_files]}")
print(f"[OK] Found {len(css_files)} CSS file(s): {[f.name for f in css_files]}")

# Verify JS bundle contains old admin component names
js_content = js_files[0].read_text(encoding="utf-8")
assert "NyaySetu Pro Admin Portal" in js_content or "NyaySetu Pro" in js_content, "Brand missing from old admin bundle!"
assert "case-forms" in js_content or "Case Forms" in js_content, "Case Forms builder missing from old admin bundle!"
print("[OK] Old Admin bundle features verified!")

# Check lawyer app index.html
lawyer_html = (dist_dir / "index.html").read_text(encoding="utf-8")
assert "Anek Gujarati" in lawyer_html, "Lawyer index.html missing fonts!"
print("[OK] Lawyer index.html verified!")

print("\n==========================================")
print("ALL LOCAL ROUTE AND ASSET CHECKS PASSED!")
print("==========================================")
