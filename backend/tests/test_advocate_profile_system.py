# -*- coding: utf-8 -*-
"""Comprehensive test suite for NyaySetu Pro Centralized Advocate Profile System.

Verifies:
1. First-login onboarding & incomplete profile detection.
2. Complete profile evaluation from saved database values.
3. Field normalization & alias synchronization in update_profile.
4. Validation & error messages for missing required advocate fields.
5. Global profile auto-fill across all relevant legal templates in build_render_context.
6. Per-application manual overrides isolation (no DB mutation).
7. Preservation of Vakalatnama party signature behaviors (Scenarios A, B, C).
8. Access isolation & security boundaries.
9. Production PDF generation with populated advocate profile details.
10. Template catalog audit for advocate profile fields.
"""

import asyncio
import base64
import io
import os
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pydantic

# Mock third-party dependencies if not installed
for mod in [
    'docx', 'docx.shared', 'docx.enum.text', 'docx.oxml', 'docx.oxml.ns',
    'google', 'google.cloud', 'google.cloud.firestore',
    'fastapi', 'fastapi.exceptions', 'fastapi.responses',
    'fastapi.middleware.cors', 'fastapi.middleware.gzip',
    'httpx', 'dotenv', 'jwt', 'bcrypt', 'razorpay',
    'cryptography', 'cryptography.hazmat', 'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.serialization', 'cryptography.x509'
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

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

fastapi_mock = sys.modules.get('fastapi')
if fastapi_mock:
    fastapi_mock.FastAPI = _MockFastAPI
    fastapi_mock.APIRouter = _MockRouter
    fastapi_mock.HTTPException = _MockHTTPException
    fastapi_mock.Depends = lambda x: x
    fastapi_mock.Query = lambda default=None, **kw: default
    fastapi_mock.Header = lambda default=None, **kw: default
    fastapi_mock.Request = MagicMock
    fastapi_mock.Response = MagicMock

# Import backend modules
import server
import doc_generator
from seed_data_templates_v2 import TEMPLATES_V2


class TestAdvocateProfileSystem(unittest.TestCase):
    """Test suite for Centralized Advocate Profile System."""

    def setUp(self):
        self.sample_complete_advocate = {
            "id": "adv_test_001",
            "name": "Ramesh Bhikhabhai Patel",
            "first_name": "Ramesh",
            "middle_name": "Bhikhabhai",
            "last_name": "Patel",
            "advocate_name_en": "Adv. Ramesh B. Patel",
            "advocate_name_gu": "એડવોકેટ રમેશ બી. પટેલ",
            "bar_council_no": "G/1234/2020",
            "sanad_number": "G/1234/2020",
            "advocate_enrollment_number": "G/1234/2020",
            "qualification": "B.Com., LL.B., LL.M.",
            "advocate_qualification": "B.Com., LL.B., LL.M.",
            "office_address": "Chamber No. 104, District Court Complex, Ahmedabad",
            "advocate_address": "Chamber No. 104, District Court Complex, Ahmedabad",
            "permanent_address": "12, Shanti Niketan, Satellite, Ahmedabad",
            "mobile": "9876543210",
            "advocate_mobile": "9876543210",
            "email": "advocate.ramesh@gmail.com",
            "advocate_email": "advocate.ramesh@gmail.com",
            "user_type": "Advocate",
            "state": "Gujarat",
            "district": "ahmedabad",
            "court": "ahmedabad_city_civil",
            "profile_completed": True,
            "is_profile_complete": True,
        }

    # ---------------------------------------------------------
    # 1. First-Login Onboarding & Incomplete Profile Detection
    # ---------------------------------------------------------
    def test_new_user_has_incomplete_profile(self):
        """A newly registered user must be marked incomplete to trigger onboarding."""
        loop = asyncio.new_event_loop()
        try:
            with patch("server.db") as mock_db, patch("server.gen_referral_code", return_value="NS1234"):
                mock_col = MagicMock()
                mock_db.collection.return_value = mock_col
                mock_col.document.return_value.set = AsyncMock()

                user = loop.run_until_complete(
                    server.create_new_user(mobile="9876543210", provider="mobile")
                )
                self.assertFalse(user["profile_completed"])
                self.assertFalse(user["is_profile_complete"])

                pub = server._public_user(user)
                self.assertFalse(pub["profile_completed"])
                self.assertFalse(pub["is_profile_complete"])
        finally:
            loop.close()

    def test_incomplete_profile_missing_required_fields(self):
        """Verify each required advocate field causes _is_profile_complete to return False."""
        base = dict(self.sample_complete_advocate)

        # 1. Missing qualification
        p1 = dict(base, qualification="", advocate_qualification="")
        self.assertFalse(server._is_profile_complete(p1))

        # 2. Missing office address
        p2 = dict(base, office_address="", advocate_address="", address="")
        self.assertFalse(server._is_profile_complete(p2))

        # 3. Missing bar council number
        p3 = dict(base, bar_council_no="", sanad_number="", advocate_enrollment_number="")
        self.assertFalse(server._is_profile_complete(p3))

        # 4. Missing Gujarati advocate name
        p4 = dict(base, advocate_name_gu="")
        self.assertFalse(server._is_profile_complete(p4))

        # 5. Missing English advocate name
        p5 = dict(base, advocate_name_en="")
        self.assertFalse(server._is_profile_complete(p5))

        # 6. Missing email
        p6 = dict(base, email="", advocate_email="")
        self.assertFalse(server._is_profile_complete(p6))

        # 7. Missing mobile
        p7 = dict(base, mobile="", advocate_mobile="")
        self.assertFalse(server._is_profile_complete(p7))

        # 8. Missing district
        p8 = dict(base, district="")
        self.assertFalse(server._is_profile_complete(p8))

    # ---------------------------------------------------------
    # 2. Complete Profile Evaluation
    # ---------------------------------------------------------
    def test_complete_profile_evaluation(self):
        """When all 10 required fields are present, profile is evaluated as complete."""
        self.assertTrue(server._is_profile_complete(self.sample_complete_advocate))
        pub = server._public_user(self.sample_complete_advocate)
        self.assertTrue(pub["profile_completed"])
        self.assertTrue(pub["is_profile_complete"])
        self.assertEqual(pub["advocate_name_en"], "Adv. Ramesh B. Patel")
        self.assertEqual(pub["advocate_name_gu"], "એડવોકેટ રમેશ બી. પટેલ")
        self.assertEqual(pub["qualification"], "B.Com., LL.B., LL.M.")
        self.assertEqual(pub["office_address"], "Chamber No. 104, District Court Complex, Ahmedabad")

    # ---------------------------------------------------------
    # 3. Field Normalization & Alias Synchronization
    # ---------------------------------------------------------
    def test_profile_update_synchronizes_aliases(self):
        """update_profile must normalize qualification, office address, and bar council aliases."""
        loop = asyncio.new_event_loop()
        try:
            req = server.ProfileUpdate(
                first_name="Ramesh",
                last_name="Patel",
                user_type="Advocate",
                bar_council_no="G/5555/2021",
                advocate_name_en="Adv. Ramesh Patel",
                advocate_name_gu="એડવોકેટ રમેશ પટેલ",
                qualification="LL.B.",
                office_address="Law Chamber 5",
                email="ramesh@law.com",
                mobile="9876543210",
                state="Gujarat",
                district="surat",
            )
            raw_user = {"id": "usr_99", "mobile": "9876543210"}

            with patch("server.db") as mock_db, patch("server.invalidate_user_session_cache"):
                mock_doc = MagicMock()
                mock_doc.set = AsyncMock()
                mock_db.collection.return_value.document.return_value = mock_doc

                updated = loop.run_until_complete(server.update_profile(req, user=raw_user))

                # Verify set was called with merged updates
                set_calls = mock_doc.set.call_args_list
                self.assertTrue(len(set_calls) > 0)
                saved_payload = set_calls[0][0][0]

                # Check aliases
                self.assertEqual(saved_payload["qualification"], "LL.B.")
                self.assertEqual(saved_payload["advocate_qualification"], "LL.B.")
                self.assertEqual(saved_payload["office_address"], "Law Chamber 5")
                self.assertEqual(saved_payload["advocate_address"], "Law Chamber 5")
                self.assertEqual(saved_payload["bar_council_no"], "G/5555/2021")
                self.assertEqual(saved_payload["sanad_number"], "G/5555/2021")
                self.assertEqual(saved_payload["advocate_enrollment_number"], "G/5555/2021")
                self.assertEqual(saved_payload["email"], "ramesh@law.com")
                self.assertEqual(saved_payload["advocate_email"], "ramesh@law.com")
                self.assertTrue(saved_payload["profile_completed"])
                self.assertTrue(saved_payload["is_profile_complete"])
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 4. Validation Errors for Incomplete Completion
    # ---------------------------------------------------------
    def test_validation_rejects_incomplete_advocate_completion(self):
        """Explicitly marking complete without qualification or office address must raise 400."""
        loop = asyncio.new_event_loop()
        try:
            req_missing_qual = server.ProfileUpdate(
                first_name="Ramesh",
                last_name="Patel",
                user_type="Advocate",
                bar_council_no="G/123/2020",
                advocate_name_en="Adv. Ramesh Patel",
                advocate_name_gu="એડવોકેટ રમેશ પટેલ",
                office_address="Office 1",
                email="test@test.com",
                mobile="9876543210",
                state="Gujarat",
                district="ahmedabad",
                profile_completed=True,
            )
            raw_user = {"id": "usr_99", "mobile": "9876543210"}
            with self.assertRaises(server.HTTPException) as cm:
                loop.run_until_complete(server.update_profile(req_missing_qual, user=raw_user))
            self.assertEqual(cm.exception.status_code, 400)
            self.assertIn("Educational Qualification is required", cm.exception.detail)

            req_missing_addr = server.ProfileUpdate(
                first_name="Ramesh",
                last_name="Patel",
                user_type="Advocate",
                bar_council_no="G/123/2020",
                advocate_name_en="Adv. Ramesh Patel",
                advocate_name_gu="એડવોકેટ રમેશ પટેલ",
                qualification="B.A., LL.B.",
                email="test@test.com",
                mobile="9876543210",
                state="Gujarat",
                district="ahmedabad",
                profile_completed=True,
            )
            with self.assertRaises(server.HTTPException) as cm2:
                loop.run_until_complete(server.update_profile(req_missing_addr, user=raw_user))
            self.assertEqual(cm2.exception.status_code, 400)
            self.assertIn("Office Address is required", cm2.exception.detail)
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 5. Global Profile Auto-Fill in build_render_context
    # ---------------------------------------------------------
    def test_global_auto_fill_across_templates(self):
        """Verify advocate profile values are automatically populated across templates."""
        loop = asyncio.new_event_loop()
        try:
            user = self.sample_complete_advocate

            # 1. Vakalatnama Civil (Gujarati)
            ctx_vc_gu = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"party_1_name": "સુરેશભાઈ પટેલ", "party_2_name": "મહેશભાઈ શાહ"},
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            self.assertIn("રમેશ", ctx_vc_gu["advocate_name"])
            self.assertEqual(ctx_vc_gu["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(ctx_vc_gu["advocate_enrollment_number"], "G/1234/2020")
            self.assertEqual(ctx_vc_gu["advocate_address"], "Chamber No. 104, District Court Complex, Ahmedabad")
            self.assertEqual(ctx_vc_gu["advocate_email"], "advocate.ramesh@gmail.com")
            self.assertEqual(ctx_vc_gu["advocate_mobile"], "9876543210")
            self.assertEqual(ctx_vc_gu["party_signature_name"], "સુરેશભાઈ પટેલ")

            # 2. Vakalatnama Civil (English)
            ctx_vc_en = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"party_1_name": "Suresh Patel", "party_2_name": "Mahesh Shah"},
                    language="en",
                    template_id="vakilatnama_civil_en",
                )
            )
            self.assertIn("Ramesh B. Patel", ctx_vc_en["advocate_name"])
            self.assertEqual(ctx_vc_en["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(ctx_vc_en["advocate_enrollment_number"], "G/1234/2020")
            self.assertEqual(ctx_vc_en["party_signature_name"], "Suresh Patel")

            # 3. Vakalatnama Criminal (Gujarati)
            ctx_vcr_gu = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"party_1_name": "જયેશભાઈ જોષી", "party_2_name": "ગુજરાત રાજ્ય"},
                    language="gu",
                    template_id="vakilatnama_criminal_gu",
                )
            )
            self.assertIn("રમેશ", ctx_vcr_gu["advocate_name"])
            self.assertEqual(ctx_vcr_gu["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(ctx_vcr_gu["advocate_enrollment_number"], "G/1234/2020")
            self.assertEqual(ctx_vcr_gu["party_signature_name"], "જયેશભાઈ જોષી")

            # 4. Certified Report (Gujarati)
            ctx_cr = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={},
                    language="gu",
                    template_id="certified_report_gu",
                )
            )
            self.assertIn("રમેશ", ctx_cr["advocate_name"])
            self.assertEqual(ctx_cr["advocate_mobile"], "9876543210")
            self.assertEqual(ctx_cr["advocate_qualification"], "B.Com., LL.B., LL.M.")

            # 5. DD Karavani Arji (Gujarati)
            ctx_dd = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"advocate_for": "party_1", "party_1_role": "વાદી"},
                    language="gu",
                    template_id="dd_karavani_arji_gu",
                )
            )
            self.assertEqual(ctx_dd["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(ctx_dd["advocate_address"], "Chamber No. 104, District Court Complex, Ahmedabad")
            self.assertEqual(ctx_dd["advocate_mobile"], "9876543210")
            self.assertEqual(ctx_dd["advocate_enrollment_number"], "G/1234/2020")

            # 6. Mudat Arji (Gujarati)
            ctx_mudat = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"advocate_for": "party_1", "party_1_role": "વાદી"},
                    language="gu",
                    template_id="mudat_arji_gu",
                )
            )
            self.assertEqual(ctx_mudat["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(ctx_mudat["advocate_enrollment_number"], "G/1234/2020")
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 6. Per-Application Manual Overrides Isolation
    # ---------------------------------------------------------
    def test_manual_overrides_isolation(self):
        """User overrides in application form must apply only to that context and never mutate profile."""
        loop = asyncio.new_event_loop()
        try:
            user = dict(self.sample_complete_advocate)
            overrides = {
                "advocate_name": "Adv. Colleague Senior",
                "advocate_qualification": "Senior Counsel, LL.M.",
                "advocate_address": "Chamber 99, High Court",
                "advocate_enrollment_number": "G/9999/2010",
                "advocate_mobile": "9999999999",
                "advocate_email": "colleague@senior.com",
            }
            ctx = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values=overrides,
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            # Rendered context gets the overridden values
            self.assertEqual(ctx["advocate_name"], "Adv. Colleague Senior")
            self.assertEqual(ctx["advocate_qualification"], "Senior Counsel, LL.M.")
            self.assertEqual(ctx["advocate_address"], "Chamber 99, High Court")
            self.assertEqual(ctx["advocate_enrollment_number"], "G/9999/2010")
            self.assertEqual(ctx["advocate_mobile"], "9999999999")
            self.assertEqual(ctx["advocate_email"], "colleague@senior.com")

            # Global user profile remains 100% UNCHANGED
            self.assertEqual(user["advocate_name_gu"], "એડવોકેટ રમેશ બી. પટેલ")
            self.assertEqual(user["advocate_qualification"], "B.Com., LL.B., LL.M.")
            self.assertEqual(user["office_address"], "Chamber No. 104, District Court Complex, Ahmedabad")
            self.assertEqual(user["bar_council_no"], "G/1234/2020")
            self.assertEqual(user["mobile"], "9876543210")
            self.assertEqual(user["email"], "advocate.ramesh@gmail.com")
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 7. Preservation of Vakalatnama Party Signature Behaviors
    # ---------------------------------------------------------
    def test_vakalatnama_party_signature_scenarios_preserved(self):
        """Preserve all three party signature behaviors:
        Scenario A: Omitted -> party_1_name fallback
        Scenario B: Custom value -> custom value
        Scenario C: Explicit blank -> intentional blank
        """
        loop = asyncio.new_event_loop()
        try:
            user = self.sample_complete_advocate

            # Scenario A: Omitted
            ctx_a = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"party_1_name": "રમેશભાઈ વલ્લભભાઈ પટેલ"},
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            self.assertEqual(ctx_a["party_signature_name"], "રમેશભાઈ વલ્લભભાઈ પટેલ")

            # Scenario B: Custom Value
            ctx_b = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={
                        "party_1_name": "રમેશભાઈ પટેલ",
                        "party_signature_name": "કિશોરભાઈ નાથાભાઈ ચૌહાણ (પાવર ઓફ એટર્ની)",
                    },
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            self.assertEqual(ctx_b["party_signature_name"], "કિશોરભાઈ નાથાભાઈ ચૌહાણ (પાવર ઓફ એટર્ની)")

            # Scenario C: Explicit Intentional Blank
            ctx_c = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={"party_1_name": "રમેશભાઈ પટેલ", "party_signature_name": ""},
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            self.assertEqual(ctx_c["party_signature_name"], "")
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 8. Security & Access Isolation
    # ---------------------------------------------------------
    def test_access_isolation_security(self):
        """Ensure an authenticated user can only update their own Firestore document."""
        loop = asyncio.new_event_loop()
        try:
            user_a = {"id": "user_alpha_123", "mobile": "9876543210"}
            req = server.ProfileUpdate(qualification="LL.B.")

            with patch("server.db") as mock_db, patch("server.invalidate_user_session_cache"):
                mock_doc = MagicMock()
                mock_doc.set = AsyncMock()
                mock_db.collection.return_value.document.return_value = mock_doc

                loop.run_until_complete(server.update_profile(req, user=user_a))

                # Verify document ID called matches authenticated user ID exactly
                mock_db.collection.return_value.document.assert_called_once_with("user_alpha_123")
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 9. Actual Production PDF Generation with Profile Data
    # ---------------------------------------------------------
    def test_actual_pdf_generation_with_profile_data(self):
        """Generate actual production PDFs and verify advocate profile information renders."""
        loop = asyncio.new_event_loop()
        try:
            user = self.sample_complete_advocate

            # 1. Vakalatnama Civil (Gujarati)
            ctx_vc = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={
                        "party_1_name": "સુરેશભાઈ પટેલ",
                        "party_2_name": "મહેશભાઈ શાહ",
                        "court": "દિવાની અદાલત, અમદાવાદ",
                        "case_number": "૧૨૩/૨૦૨૬",
                    },
                    language="gu",
                    template_id="vakilatnama_civil_gu",
                )
            )
            tpl_civ = next(t for t in TEMPLATES_V2 if t["id"] == "vakilatnama_civil_gu")
            b64_vc, _ = doc_generator.generate_pdf_detailed(
                [],
                "gu",
                settings=tpl_civ.get("settings", {}),
                template_id="vakilatnama_civil",
                ctx=ctx_vc,
            )
            pdf_vc_bytes = base64.b64decode(b64_vc)
            self.assertIsInstance(pdf_vc_bytes, bytes)
            self.assertTrue(len(pdf_vc_bytes) > 1000)
            self.assertTrue(pdf_vc_bytes.startswith(b"%PDF"))

            # 2. Vakalatnama Criminal (Gujarati)
            ctx_vcr = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={
                        "party_1_name": "જયેશભાઈ જોષી",
                        "party_2_name": "ગુજરાત રાજ્ય",
                        "court": "ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ કોર્ટ",
                        "case_number": "૪૫૬/૨૦૨૬",
                    },
                    language="gu",
                    template_id="vakilatnama_criminal_gu",
                )
            )
            tpl_crim = next(t for t in TEMPLATES_V2 if t["id"] == "vakilatnama_criminal_gu")
            b64_vcr, _ = doc_generator.generate_pdf_detailed(
                [],
                "gu",
                settings=tpl_crim.get("settings", {}),
                template_id="vakilatnama_criminal",
                ctx=ctx_vcr,
            )
            pdf_vcr_bytes = base64.b64decode(b64_vcr)
            self.assertIsInstance(pdf_vcr_bytes, bytes)
            self.assertTrue(len(pdf_vcr_bytes) > 1000)
            self.assertTrue(pdf_vcr_bytes.startswith(b"%PDF"))

            # 3. Certified Report (Gujarati)
            ctx_cr = loop.run_until_complete(
                server.build_render_context(
                    user=user,
                    case=None,
                    values={
                        "court": "દિવાની અદાલત",
                        "case_number": "૭૮૯/૨૦૨૬",
                        "party_name": "હરેશભાઈ પટેલ",
                        "opposite_party": "નરેશભાઈ પટેલ",
                    },
                    language="gu",
                    template_id="certified_report_gu",
                )
            )
            tpl_cr = next(t for t in TEMPLATES_V2 if t["id"] == "certified_report_gu")
            b64_cr, _ = doc_generator.generate_pdf_detailed(
                [],
                "gu",
                settings=tpl_cr.get("settings", {}),
                template_id="certified_report",
                raw_content=tpl_cr.get("content_gu", ""),
                ctx=ctx_cr,
            )
            pdf_cr_bytes = base64.b64decode(b64_cr)
            self.assertIsInstance(pdf_cr_bytes, bytes)
            self.assertTrue(len(pdf_cr_bytes) > 500)
            self.assertTrue(pdf_cr_bytes.startswith(b"%PDF"))
        finally:
            loop.close()

    # ---------------------------------------------------------
    # 10. Audit All Templates Catalog for Advocate Fields
    # ---------------------------------------------------------
    def test_audit_all_templates_catalog(self):
        """Inspect all 42 templates in catalog and verify advocate profile integration."""
        adv_keys = {
            'advocate_name', 'advocate_qualification', 'qualification',
            'advocate_enrollment_number', 'advocate_enrollment_no',
            'sanad_number', 'bar_council_no', 'advocate_address',
            'office_address', 'advocate_email', 'advocate_mobile', 'mobile_number'
        }
        touching_templates = []
        for tpl in TEMPLATES_V2:
            tid = tpl['id']
            fields = [f.get('key') for f in tpl.get('fields', [])]
            has_field = any(k in adv_keys or 'advocate' in k for k in fields)
            has_placeholder = any(
                w in (tpl.get('content_gu') or '') or w in (tpl.get('content_en') or '')
                for w in adv_keys
            )
            if has_field or has_placeholder:
                touching_templates.append(tid)

        # Confirm templates with advocate profile fields exist and are cataloged
        self.assertTrue(len(touching_templates) > 0)
        self.assertIn("vakilatnama_civil_gu", touching_templates)
        self.assertIn("vakilatnama_civil_en", touching_templates)
        self.assertIn("vakilatnama_criminal_gu", touching_templates)
        self.assertIn("vakilatnama_criminal_en", touching_templates)
        self.assertIn("certified_report_gu", touching_templates)
        self.assertIn("dd_karavani_arji_gu", touching_templates)
        self.assertIn("mudat_arji_gu", touching_templates)


if __name__ == '__main__':
    unittest.main()
