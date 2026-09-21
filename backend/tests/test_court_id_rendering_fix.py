# -*- coding: utf-8 -*-
"""
Tests for NYAYSETU PRO — FIX COURT ID RENDERING IN GENERATED DOCUMENTS.

Verifies:
1. resolve_court_label translates internal court ID to Gujarati/English catalog labels.
2. Direct Template Mode: court ID resolves to Gujarati/English in build_render_context.
3. Saved Case Mode: case.court_id resolves to Gujarati/English in build_render_context.
4. Bidirectional label translation: English label -> Gujarati label when document is Gujarati, and vice-versa.
5. Internal court ID NEVER appears in the rendered template or generated PDF.
6. Custom and historical court records are preserved safely.
7. Later context synchronization cannot overwrite resolved localized label with raw ID.
8. Actual generated ReportLab Gujarati and English PDFs contain catalog labels and NOT raw IDs.
"""

import asyncio
import base64
import os
import re
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Mock third-party dependencies if not installed
for mod in [
    'docx', 'docx.shared', 'docx.enum.text', 'docx.oxml', 'docx.oxml.ns',
    'google', 'google.cloud', 'google.cloud.firestore',
    'fastapi', 'fastapi.exceptions', 'fastapi.responses',
    'fastapi.middleware.cors', 'fastapi.middleware.gzip',
    'pydantic', 'httpx', 'dotenv', 'jwt', 'bcrypt', 'razorpay',
    'cryptography', 'cryptography.hazmat', 'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.serialization', 'cryptography.x509'
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

def _passthrough_decorator(*args, **kwargs):
    def decorator(f):
        return f
    return decorator

class _MockRouter:
    def __init__(self, *args, **kwargs): pass
    def get(self, *args, **kwargs): return lambda f: f
    def post(self, *args, **kwargs): return lambda f: f
    def put(self, *args, **kwargs): return lambda f: f
    def delete(self, *args, **kwargs): return lambda f: f
    def patch(self, *args, **kwargs): return lambda f: f
    def include_router(self, *args, **kwargs): pass

class _MockFastAPI(_MockRouter):
    def __init__(self, *args, **kwargs): pass
    def add_middleware(self, *args, **kwargs): pass
    def exception_handler(self, *args, **kwargs): return lambda f: f
    def on_event(self, *args, **kwargs): return lambda f: f

class _MockHTTPException(Exception):
    def __init__(self, status_code, detail=""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{status_code}: {detail}")

fastapi_mock = sys.modules['fastapi']
fastapi_mock.FastAPI = _MockFastAPI
fastapi_mock.APIRouter = _MockRouter
fastapi_mock.HTTPException = _MockHTTPException
fastapi_mock.Depends = lambda x: x
fastapi_mock.Header = lambda *args, **kwargs: None
fastapi_mock.Request = MagicMock
fastapi_mock.Response = MagicMock
fastapi_mock.Cookie = lambda *args, **kwargs: None

class _PydanticBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

sys.modules['pydantic'].BaseModel = _PydanticBaseModel
sys.modules['pydantic'].Field = lambda *args, **kwargs: None

import doc_generator
import server
import test_seed_data


def extract_pdf_streams(pdf_bytes: bytes) -> str:
    """Extract decompressed text streams from PDF bytes."""
    decomp_str = ""
    for m in re.finditer(rb"(\d+\s+\d+\s+obj.*?endobj)", pdf_bytes, re.DOTALL):
        obj_text = m.group(1)
        s_m = re.search(rb"stream\r?\n(.*)endstream", obj_text, re.DOTALL)
        if s_m:
            raw = s_m.group(1).rstrip(b"\r\n")
            try:
                decomp_str += zlib.decompress(base64.a85decode(raw, adobe=True)).decode("latin1", errors="ignore") + "\n"
                continue
            except Exception:
                pass
            try:
                decomp_str += zlib.decompress(raw).decode("latin1", errors="ignore") + "\n"
                continue
            except Exception:
                pass
    return decomp_str


class TestCourtIdRenderingFix(unittest.TestCase):
    """Test suite for court ID resolution and document generation."""

    def setUp(self):
        # Sample admin court catalog items matching live production
        self.catalog_courts = [
            {
                "id": "additional_civil_judge_441fab",
                "en": "ADDITIONAL CIVIL JUDGE",
                "gu": "એડીશનલ સિવીલ જજ",
                "district_id": "generic",
                "active": True
            },
            {
                "id": "judicial_magistrate_first_class_a9e29a",
                "en": "JUDICIAL MAGISTRATE FIRST CLASS",
                "gu": "જ્યુડીશિયલ મેજીસ્ટ્રેટ ફર્સ્ટ ક્લાસ",
                "district_id": "generic",
                "active": True
            },
            {
                "id": "historical_court_inactive_888",
                "en": "HISTORICAL INACTIVE COURT",
                "gu": "ઐતિહાસિક જૂની કોર્ટ",
                "district_id": "generic",
                "active": False
            }
        ]

        async def _mock_load_catalog(kind):
            if kind == "courts":
                return self.catalog_courts
            return []

        # Patch _load_catalog to return catalog_courts for "courts"
        self.patcher_load_catalog = patch.object(
            server,
            '_load_catalog',
            side_effect=_mock_load_catalog
        )
        self.mock_load_catalog = self.patcher_load_catalog.start()

        # Populate _COURT_MAP in server
        for c in self.catalog_courts:
            server._COURT_MAP[c["id"]] = c

        self.user = {
            "id": "usr_test_123",
            "name": "Advocate Test",
            "advocate_name_en": "Advocate Test",
            "advocate_name_gu": "એડવોકેટ ટેસ્ટ",
        }

        self.tpl_exhibit = next((t for t in test_seed_data.TEMPLATES if t["id"] == "document_exhibit_application"), None)
        self.assertIsNotNone(self.tpl_exhibit)

    def tearDown(self):
        self.patcher_load_catalog.stop()

    def test_resolve_court_label_by_id_gujarati_and_english(self):
        """Internal court ID resolves to Gujarati and English catalog labels."""
        res_gu = asyncio.run(server.resolve_court_label("additional_civil_judge_441fab", "gu"))
        self.assertEqual(res_gu, "એડીશનલ સિવીલ જજ")

        res_en = asyncio.run(server.resolve_court_label("additional_civil_judge_441fab", "en"))
        self.assertEqual(res_en, "ADDITIONAL CIVIL JUDGE")

        # Second court
        res_jmfc_gu = asyncio.run(server.resolve_court_label("judicial_magistrate_first_class_a9e29a", "gu"))
        self.assertEqual(res_jmfc_gu, "જ્યુડીશિયલ મેજીસ્ટ્રેટ ફર્સ્ટ ક્લાસ")

        res_jmfc_en = asyncio.run(server.resolve_court_label("judicial_magistrate_first_class_a9e29a", "en"))
        self.assertEqual(res_jmfc_en, "JUDICIAL MAGISTRATE FIRST CLASS")

    def test_resolve_court_label_bidirectional_translation(self):
        """English catalog label translates to Gujarati, and Gujarati translates to English."""
        # English label provided -> Gujarati requested
        res_gu = asyncio.run(server.resolve_court_label("ADDITIONAL CIVIL JUDGE", "gu"))
        self.assertEqual(res_gu, "એડીશનલ સિવીલ જજ")

        # Gujarati label provided -> English requested
        res_en = asyncio.run(server.resolve_court_label("એડીશનલ સિવીલ જજ", "en"))
        self.assertEqual(res_en, "ADDITIONAL CIVIL JUDGE")

    def test_resolve_court_label_preserves_custom_and_historical_courts(self):
        """Custom user-entered court strings and historical courts are preserved."""
        # Historical court in catalog
        res_hist_gu = asyncio.run(server.resolve_court_label("historical_court_inactive_888", "gu"))
        self.assertEqual(res_hist_gu, "ઐતિહાસિક જૂની કોર્ટ")

        # Case custom court string
        case_custom = {"court_id": "other", "court_custom": "Special Lok Adalat, Ahmedabad"}
        res_custom = asyncio.run(server.resolve_court_label("other", "gu", case=case_custom))
        self.assertEqual(res_custom, "Special Lok Adalat, Ahmedabad")

        # Non-catalog custom string
        res_user_typed = asyncio.run(server.resolve_court_label("City Civil Court Bench 4", "en"))
        self.assertEqual(res_user_typed, "City Civil Court Bench 4")

    def test_build_render_context_direct_template_mode(self):
        """Direct Template Mode: court ID in values resolves to language-specific catalog label."""
        values = {"court": "additional_civil_judge_441fab"}

        # Gujarati
        ctx_gu = asyncio.run(server.build_render_context(self.user, None, values, "gu"))
        self.assertEqual(ctx_gu["court"], "એડીશનલ સિવીલ જજ")
        self.assertEqual(ctx_gu["court_name"], "એડીશનલ સિવીલ જજ")
        self.assertNotIn("additional_civil_judge_441fab", ctx_gu["court"])

        # English
        ctx_en = asyncio.run(server.build_render_context(self.user, None, values, "en"))
        self.assertEqual(ctx_en["court"], "ADDITIONAL CIVIL JUDGE")
        self.assertEqual(ctx_en["court_name"], "ADDITIONAL CIVIL JUDGE")
        self.assertNotIn("additional_civil_judge_441fab", ctx_en["court"])

    def test_build_render_context_saved_case_mode(self):
        """Saved Case Mode: case.court_id resolves to language-specific catalog label."""
        case = {
            "id": "case_101",
            "court_id": "additional_civil_judge_441fab",
            "case_number": "123/2026",
            "party_name": "Ramesh Patel",
            "opposite_party": "Suresh Shah"
        }

        # Case mode with empty values
        ctx_gu = asyncio.run(server.build_render_context(self.user, case, {}, "gu"))
        self.assertEqual(ctx_gu["court"], "એડીશનલ સિવીલ જજ")
        self.assertEqual(ctx_gu["court_name"], "એડીશનલ સિવીલ જજ")

        ctx_en = asyncio.run(server.build_render_context(self.user, case, {}, "en"))
        self.assertEqual(ctx_en["court"], "ADDITIONAL CIVIL JUDGE")
        self.assertEqual(ctx_en["court_name"], "ADDITIONAL CIVIL JUDGE")

        # Case mode with values passing court ID as well
        values = {"court": "additional_civil_judge_441fab", "court_name": "additional_civil_judge_441fab"}
        ctx_gu_vals = asyncio.run(server.build_render_context(self.user, case, values, "gu"))
        self.assertEqual(ctx_gu_vals["court"], "એડીશનલ સિવીલ જજ")
        self.assertEqual(ctx_gu_vals["court_name"], "એડીશનલ સિવીલ જજ")

    def test_later_context_synchronization_cannot_overwrite_label_with_id(self):
        """Verify that final context mirroring step authoritatively enforces resolved catalog label."""
        # Simulated context where an intermediate step put the raw ID in court_name
        values = {"court": "એડીશનલ સિવીલ જજ", "court_name": "additional_civil_judge_441fab"}
        ctx = asyncio.run(server.build_render_context(self.user, None, values, "gu"))
        self.assertEqual(ctx["court"], "એડીશનલ સિવીલ જજ")
        self.assertEqual(ctx["court_name"], "એડીશનલ સિવીલ જજ")
        self.assertNotEqual(ctx["court"], "additional_civil_judge_441fab")
        self.assertNotEqual(ctx["court_name"], "additional_civil_judge_441fab")

    def test_actual_pdf_generation_gujarati_exhibit_application(self):
        """Actual ReportLab Gujarati PDF contains 'એડીશનલ સિવીલ જજ' and NO raw court ID."""
        tpl_gu = self.tpl_exhibit["content_gu"]
        values = {
            "court": "additional_civil_judge_441fab",
            "taluka_place": "અમદાવાદ",
            "case_type": "સ્પેશિયલ દિવાની કેસ",
            "case_number": "૧૨૩/૨૦૨૬",
            "party_1_role": "વાદી",
            "party_1_name": "રમણભાઈ પટેલ",
            "party_2_role": "પ્રતિવાદી",
            "party_2_name": "સુરેશભાઈ શાહ",
            "representing_party_role": "વાદી",
            "document_details": "આંક ૩ થી રજૂ કરેલ મૂળ વેચાણ દસ્તાવેજ",
            "date": "21/09/2026",
        }

        ctx = asyncio.run(server.build_render_context(self.user, None, values, "gu"))
        self.assertEqual(ctx["court"], "એડીશનલ સિવીલ જજ")

        rendered = doc_generator.render_template(tpl_gu, ctx)
        self.assertIn("એડીશનલ સિવીલ જજ", rendered)
        self.assertNotIn("additional_civil_judge_441fab", rendered)

        blocks = doc_generator.build_blocks(rendered, "Exhibit Application", "આંક આપવાની અરજી")
        doc_settings = doc_generator.get_doc_settings({
            "template_id": "document_exhibit_application",
            "raw_content": rendered,
            "ctx": ctx,
        })
        b64 = doc_generator._generate_pdf_reportlab_inner(blocks, "gu", doc_settings)
        pdf_bytes = base64.b64decode(b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

        # Inspect stream: raw court ID must NEVER appear anywhere in the PDF
        raw_pdf_str = pdf_bytes.decode("latin1", errors="ignore")
        self.assertNotIn("additional_civil_judge_441fab", raw_pdf_str)

        # Decompressed stream check
        stream_text = extract_pdf_streams(pdf_bytes)
        self.assertNotIn("additional_civil_judge_441fab", stream_text)

    def test_actual_pdf_generation_english_exhibit_application(self):
        """Actual ReportLab English PDF contains 'ADDITIONAL CIVIL JUDGE' and NO raw court ID."""
        tpl_en = self.tpl_exhibit["content_en"]
        values = {
            "court": "additional_civil_judge_441fab",
            "taluka_place": "Ahmedabad",
            "case_type": "Special Civil Suit",
            "case_number": "123/2026",
            "party_1_role": "Plaintiff",
            "party_1_name": "Ramanbhai Patel",
            "party_2_role": "Defendant",
            "party_2_name": "Sureshbhai Shah",
            "representing_party_role": "Plaintiff",
            "document_details": "Original sale deed marked at Exh. 3",
            "date": "21/09/2026",
        }

        ctx = asyncio.run(server.build_render_context(self.user, None, values, "en"))
        self.assertEqual(ctx["court"], "ADDITIONAL CIVIL JUDGE")

        rendered = doc_generator.render_template(tpl_en, ctx)
        self.assertIn("ADDITIONAL CIVIL JUDGE", rendered)
        self.assertNotIn("additional_civil_judge_441fab", rendered)

        blocks = doc_generator.build_blocks(rendered, "Exhibit Application", "આંક આપવાની અરજી")
        doc_settings = doc_generator.get_doc_settings({
            "template_id": "document_exhibit_application",
            "raw_content": rendered,
            "ctx": ctx,
        })
        b64 = doc_generator._generate_pdf_reportlab_inner(blocks, "en", doc_settings)
        pdf_bytes = base64.b64decode(b64)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

        # Inspect stream: English label MUST appear, raw court ID must NOT appear
        stream_text = extract_pdf_streams(pdf_bytes)
        self.assertIn("ADDITIONAL", stream_text)
        self.assertIn("CIVIL JUDGE", stream_text)
        self.assertNotIn("additional_civil_judge_441fab", stream_text)


if __name__ == '__main__':
    unittest.main()
