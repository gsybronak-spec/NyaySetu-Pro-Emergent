import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Ensure test environment
os.environ.setdefault("DB_NAME", "nyaysetu_test_sec")
os.environ.setdefault("TESTING", "true")

import server


class TestRazorpaySecurityAndIdempotency(unittest.TestCase):

    def test_01_admin_seed_password_has_no_hardcoded_fallback(self):
        """Verify ADMIN_SEED_PASSWORD does not contain any hardcoded fallback string in code."""
        import inspect
        source = inspect.getsource(server)
        self.assertNotIn('ADMIN_SEED_PASSWORD or "NyaySetu@Admin2026!"', source)
        self.assertNotIn('ADMIN_SEED_PASSWORD = os.environ.get("ADMIN_SEED_PASSWORD") or "NyaySetu@Admin2026!"', source)

    def test_02_cors_exception_handler_does_not_reflect_untrusted_origins(self):
        """Untrusted origin must NOT receive Access-Control-Allow-Origin or credentials."""
        req = MagicMock()
        req.headers = {"origin": "https://malicious-site.attacker.com"}
        headers = server._cors_headers_for_request(req)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertNotIn("Access-Control-Allow-Credentials", headers)

    def test_03_cors_exception_handler_allows_trusted_origins(self):
        """Trusted production origin receives exact CORS headers."""
        req = MagicMock()
        req.headers = {"origin": "https://nyaysetupro.in"}
        headers = server._cors_headers_for_request(req)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://nyaysetupro.in")
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")

    def test_04_cors_exception_handler_allows_trusted_preview_origins(self):
        """Trusted vercel.app preview origin receives exact CORS headers."""
        req = MagicMock()
        req.headers = {"origin": "https://nyay-setu-preview.vercel.app"}
        headers = server._cors_headers_for_request(req)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://nyay-setu-preview.vercel.app")
        self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")

    def test_05_rate_limit_prunes_stale_without_clearing_active(self):
        """Rate limit should not wipe active keys when table size grows."""
        server._rate_buckets.clear()
        # Add 1 active key
        server.rate_limit("active_user", 5, 60)
        self.assertIn("active_user", server._rate_buckets)

        # Populate with stale entries
        now_mono = server.time.monotonic()
        for i in range(10005):
            server._rate_buckets[f"stale_{i}"] = [now_mono - 120]

        # Trigger cleanup
        server.rate_limit("trigger_key", 5, 60)
        # Active user key must still exist!
        self.assertIn("active_user", server._rate_buckets)


if __name__ == "__main__":
    unittest.main()
