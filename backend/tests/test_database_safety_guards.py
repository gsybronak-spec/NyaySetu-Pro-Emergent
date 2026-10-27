"""Unit tests verifying database safety guards in backend/server.py.

Covers:
1. get_user when db is None raises 503 Service Unavailable.
2. get_user when user is cached succeeds even if db is None.
3. get_user when db is available retrieves user properly.
4. resolve_template_for_draft when db is None and unversioned draft falls back to _get_template_by_id.
5. resolve_template_for_draft when db is None and explicit version requested raises 503 instead of silent substitution.
6. resolve_template_for_draft when db is available and revision found returns historical revision.
7. resolve_template_for_draft when db is available and revision not found falls back to published template.
8. download_application exception handling does not crash with AttributeError when db is None.
"""

import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import server


class TestDatabaseSafetyGuards(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.orig_db = server.db
        self.orig_gen_pdf = server.generate_pdf_detailed
        self.test_user_id = "test_guard_user_123"
        self.token = server.make_token(self.test_user_id)
        self.auth_header = f"Bearer {self.token}"
        # Ensure session cache is clean for this test user
        server.invalidate_user_session_cache(self.test_user_id)

    def tearDown(self):
        server.db = self.orig_db
        server.generate_pdf_detailed = self.orig_gen_pdf
        server.invalidate_user_session_cache(self.test_user_id)

    async def test_get_user_db_none_raises_503(self):
        """When db is None and user is not cached, get_user raises 503 instead of AttributeError."""
        server.db = None
        server.invalidate_user_session_cache(self.test_user_id)

        with self.assertRaises(HTTPException) as ctx:
            await server.get_user(self.auth_header)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Database service unavailable", ctx.exception.detail)

    async def test_get_user_cached_succeeds_even_when_db_none(self):
        """When user is in _USER_SESSION_CACHE, get_user returns user without accessing db."""
        server.db = None
        user_data = {"id": self.test_user_id, "active": True, "token_version": 0, "name": "Cached Lawyer"}
        with server._USER_SESSION_LOCK:
            server._USER_SESSION_CACHE[self.test_user_id] = (dict(user_data), time.time() + 60.0)

        result = await server.get_user(self.auth_header)
        self.assertEqual(result["id"], self.test_user_id)
        self.assertEqual(result["name"], "Cached Lawyer")

    async def test_get_user_db_available_returns_user(self):
        """When db is available, get_user queries Firestore and returns user."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "id": self.test_user_id,
            "active": True,
            "token_version": 0,
            "name": "Live Lawyer",
        }

        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get = AsyncMock(return_value=mock_doc)
        server.db = mock_db

        result = await server.get_user(self.auth_header)
        self.assertEqual(result["id"], self.test_user_id)
        self.assertEqual(result["name"], "Live Lawyer")

    async def test_resolve_template_for_draft_unversioned_db_none_fallback(self):
        """When db is None and no explicit version is requested, resolve_template_for_draft falls back to _get_template_by_id."""
        server.db = None
        # Call with explicit template_version=None
        tpl = await server.resolve_template_for_draft("mudat_arji", template_version=None)
        self.assertIsNotNone(tpl)
        self.assertIn(tpl.get("id"), ("mudat_arji", "mudat_arji_gu", "mudat_arji_en"))

        # Call with draft dict without template_version
        tpl_dict = await server.resolve_template_for_draft({"template_id": "mudat_arji"})
        self.assertIsNotNone(tpl_dict)
        self.assertIn(tpl_dict.get("id"), ("mudat_arji", "mudat_arji_gu", "mudat_arji_en"))

    async def test_resolve_template_for_draft_explicit_version_db_none_raises_503(self):
        """When db is None and an explicit version is requested, raises 503 instead of silently substituting published template."""
        server.db = None
        # Call with explicit template_version=2
        with self.assertRaises(HTTPException) as ctx:
            await server.resolve_template_for_draft("mudat_arji", template_version=2)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Database service unavailable", ctx.exception.detail)

        # Call with draft dict with template_version=2
        with self.assertRaises(HTTPException) as ctx_dict:
            await server.resolve_template_for_draft({"template_id": "mudat_arji", "template_version": 2})
        self.assertEqual(ctx_dict.exception.status_code, 503)
        self.assertIn("Database service unavailable", ctx_dict.exception.detail)

    async def test_resolve_template_for_draft_explicit_version_found_when_db_available(self):
        """When db is available and requested revision exists in template_revisions, returns that revision."""
        mock_snap = MagicMock()
        mock_snap.exists = True
        mock_snap.to_dict.return_value = {
            "template_id": "mudat_arji",
            "version": 2,
            "name_gu": "મુદત અરજી v2",
        }
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.get = AsyncMock(return_value=mock_snap)
        server.db = mock_db

        tpl = await server.resolve_template_for_draft("mudat_arji", template_version=2)
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl["id"], "mudat_arji")
        self.assertEqual(tpl["version"], 2)
        self.assertEqual(tpl["name_gu"], "મુદત અરજી v2")

    async def test_resolve_template_for_draft_explicit_version_not_found_fallback(self):
        """When db is available but requested revision does not exist, falls back to db.templates per contract."""
        class MockAsyncStream:
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration

        mock_missing_snap = MagicMock(exists=False)
        mock_tpl_snap = MagicMock(exists=True)
        mock_tpl_snap.to_dict.return_value = {
            "id": "mudat_arji",
            "name_gu": "મુદત અરજી કાયમી",
            "content_gu": "ટેસ્ટ લખાણ",
            "format_version": "nyaysetu_v1"
        }

        def mock_collection(col_name):
            col = MagicMock()
            if col_name in ("template_revisions", "template_versions"):
                col.document.return_value.get = AsyncMock(return_value=mock_missing_snap)
                col.where.return_value.where.return_value.limit.return_value.stream.return_value = MockAsyncStream()
            elif col_name == "templates":
                col.document.return_value.get = AsyncMock(return_value=mock_tpl_snap)
            return col

        mock_db = MagicMock()
        mock_db.collection.side_effect = mock_collection
        server.db = mock_db

        tpl = await server.resolve_template_for_draft("mudat_arji", template_version=99)
        self.assertIsNotNone(tpl)
        self.assertEqual(tpl["id"], "mudat_arji")
        self.assertEqual(tpl["name_gu"], "મુદત અરજી કાયમી")

    async def test_download_application_exception_handling_when_db_none(self):
        """When db is None and document generation fails, download_application raises 500 without AttributeError in refund block."""
        server.db = None
        server.generate_pdf_detailed = MagicMock(side_effect=RuntimeError("Simulated ReportLab crash"))

        user_data = {"id": self.test_user_id, "active": True, "role": "advocate"}
        req = server.DownloadReq(
            template_id="mudat_arji",
            values={"court_name": "Test Court"},
            language="gu",
            format="pdf",
        )

        with self.assertRaises(HTTPException) as ctx:
            await server.download_application(req, user=user_data)
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "Document generation failed.")


if __name__ == "__main__":
    unittest.main()
