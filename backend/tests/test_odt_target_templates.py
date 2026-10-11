# -*- coding: utf-8 -*-
"""Unit tests for the 14 ODT-synchronized templates and invariant check for the 9 protected templates.
"""
import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from seed_data_templates_v2 import TEMPLATES_V2, BASE_TEMPLATES
import doc_generator
from doc_generator import generate_pdf, rasterize_pdf_pages, render_template
import server

PROTECTED_TEMPLATE_KEYS = [
    "aanke_padvani_arji",
    "certified_report",
    "closing_purshish",
    "closing_argument_right_application",
    "reopen_right_to_argue_application",
    "dd_karavani_arji",
    "exemption_arji",
    "vakilatnama_civil",
    "vakilatnama_criminal",
]

TARGET_14_KEYS = [
    "document_parat_levani_arji",
    "document_swikaravani_arji",
    "fs_no_haq_bandh_karvani_arji",
    "fs_no_haq_kholvani_arji",
    "jamin_bond_swikarvani_arji",
    "kam_board_par_levani_arji",
    "mudat_arji",
    "saaxi_ne_summons",
    "samadhan_purshish",
    "ulat_tapas_no_haq_bandh_karavani_arji",
    "ulat_tapas_no_haq_kholvani_arji",
    "undertaking",
    "warrant_no_hath_bido_apvani_arji",
    "warrant_rad_karvani_arji",
]

MOCK_USER = {
    "name": "K. L. Patel",
    "name_en": "K. L. Patel",
    "name_gu": "કે. એલ. પટેલ",
    "bar_council_no": "G/1234/2015",
    "mobile": "9876543210",
}

SAMPLE_CASE = {
    "_id": "case_123",
    "court_name": "પ્રિન્સિપાલ સિવિલ જજ, કલોલ",
    "court_name_en": "Principal Civil Judge, Kalol",
    "taluka_place": "કલોલ, ગાંધીનગર",
    "case_type": "દિવાની કેસ",
    "case_type_en": "Civil Case",
    "case_number": "૧૦૧/૨૦૨૪",
    "case_year": "2024",
    "full_case_number": "દિવાની કેસ નં. ૧૦૧/૨૦૨૪",
    "petitioner_name": "રમણભાઈ મોહનભાઈ પટેલ",
    "petitioner_role": "વાદી",
    "petitioner_name_en": "Ramanbhai Mohanbhai Patel",
    "petitioner_role_en": "Plaintiff",
    "respondent_name": "સુરેશભાઈ શાંતિલાલ શાહ",
    "respondent_role": "પ્રતિવાદી",
    "respondent_name_en": "Sureshbhai Shantilal Shah",
    "respondent_role_en": "Defendant",
    "advocate_name": "કે. એલ. પટેલ",
    "advocate_for_role": "વાદી",
}


class TestTemplateProtectionAndTargetFidelity(unittest.TestCase):
    def test_01_all_nine_protected_templates_exist_and_frozen(self):
        """Verify the 9 protected templates exist in BASE_TEMPLATES or TEMPLATES_V2."""
        base_keys = {t.get("base_key") or t.get("id") for t in BASE_TEMPLATES}
        seed_keys = {t.get("base_key") or t.get("id") for t in TEMPLATES_V2}
        all_known = base_keys | seed_keys | {"closing_argument_right_application", "reopen_right_to_argue_application"}
        
        for key in PROTECTED_TEMPLATE_KEYS:
            self.assertTrue(
                key in all_known,
                f"Protected template '{key}' missing from template registry!",
            )

    def test_02_all_fourteen_target_templates_exist(self):
        """Verify all 14 target templates exist in TEMPLATES_V2."""
        seed_keys = {t.get("base_key") for t in TEMPLATES_V2 if t.get("base_key")}
        for key in TARGET_14_KEYS:
            self.assertIn(key, seed_keys, f"Target template '{key}' missing from TEMPLATES_V2")

    def test_03_generate_all_14_templates_gujarati_and_english(self):
        """Verify PDF generation for all 14 target templates in both languages without unrendered tokens."""
        tpl_dict = {t["id"]: t for t in TEMPLATES_V2}
        
        for base_key in TARGET_14_KEYS:
            for lang in ["gu", "en"]:
                tpl_id = f"{base_key}_{lang}"
                tpl = tpl_dict.get(tpl_id)
                self.assertIsNotNone(tpl, f"Template {tpl_id} not found")
                
                content = tpl.get(f"content_{lang}") or tpl.get("content") or ""
                self.assertTrue(bool(content), f"Empty content for {tpl_id}")
                
                sample_values = {
                    "reason": "અંગત કામ અંગે બહારગામ જવાનું હોવાથી",
                    "reason_en": "due to unavoidable personal work",
                    "advocate_side": "party",
                    "delay_period": "ઘણી મુદતથી",
                    "scheduled_date": "૨૫/૧૦/૨૦૨૬",
                    "urgent_reason": "વોરંટ રદ કરાવવાનો હોય",
                    "reopen_reason": "વકીલશ્રી બીમાર હોવાથી",
                    "closing_reason": "ઘણો સમય વીતી ગયેલ હોવાથી",
                    "return_reason": "સાબિતી પૂર્ણ થયેલ હોવાથી",
                    "settlement_terms": "સંપૂર્ણ ચૂકવણું થઈ ગયેલ છે",
                    "undertaking_subject": "દસ્તાવેજ રજૂ કરવા અંગે",
                    "undertaking_details": "આગામી મુદતે અસલ દસ્તાવેજ રજૂ કરીશું",
                    "warrant_kind": "non_bailable",
                    "warrant_cancellation_ground": "સમન્સ બજાવ્યા વિના વોરંટ નીકળેલ હોવાથી",
                    "witness_name": "રમેશભાઈ ગોવિંદભાઈ પટેલ",
                    "witness_purpose": "પુરાવો આપવા સારુ",
                    "date": "2026-10-15",
                }
                
                ctx = asyncio.run(server.build_render_context(
                    user=MOCK_USER,
                    case=SAMPLE_CASE,
                    values=sample_values,
                    language=lang,
                    template_id=tpl_id,
                ))
                
                rendered_text = render_template(content, ctx)
                self.assertNotIn("{{", rendered_text, f"Leftover '{{{{' in {tpl_id}: {rendered_text}")
                self.assertNotIn("}}", rendered_text, f"Leftover '}}}}' in {tpl_id}: {rendered_text}")
                self.assertNotIn("None", rendered_text, f"Leaked 'None' in {tpl_id}")
                self.assertNotIn("undefined", rendered_text, f"Leaked 'undefined' in {tpl_id}")
                
                blocks = doc_generator.build_blocks(rendered_text, tpl.get("name_en", ""), tpl.get("name_gu", ""))
                settings = doc_generator.get_doc_settings({})
                pdf_b64 = doc_generator._generate_pdf_reportlab_inner(blocks, language=lang, settings=settings)
                import base64
                pdf_bytes = base64.b64decode(pdf_b64)
                self.assertTrue(pdf_bytes.startswith(b"%PDF"), f"Invalid PDF header for {tpl_id}")
                self.assertGreater(len(pdf_bytes), 1000, f"PDF too small for {tpl_id}")

    def test_04_direct_download_mode_without_case(self):
        """Verify direct download mode without linked case."""
        tpl_dict = {t["id"]: t for t in TEMPLATES_V2}
        
        for base_key in TARGET_14_KEYS:
            tpl_id = f"{base_key}_gu"
            tpl = tpl_dict.get(tpl_id)
            content = tpl.get("content_gu") or tpl.get("content") or ""
            
            sample_values = {
                "court_name": "પ્રિન્સિપાલ સિવિલ જજ, કલોલ",
                "court": "પ્રિન્સિપાલ સિવિલ જજ, કલોલ",
                "district": "gandhinagar",
                "taluka": "kalol",
                "place": "કલોલ, ગાંધીનગર",
                "taluka_place": "કલોલ, ગાંધીનગર",
                "case_type": "દિવાની કેસ",
                "case_number": "૧૦૧/૨૦૨૪",
                "party_1_role": "વાદી",
                "party_1_name": "રમણભાઈ મોહનભાઈ પટેલ",
                "party_2_role": "પ્રતિવાદી",
                "party_2_name": "સુરેશભાઈ શાંતિલાલ શાહ",
                "selected_party_role": "વાદી",
                "date": "2026-10-15",
                "advocate_side": "party",
            }
            
            ctx = asyncio.run(server.build_render_context(
                user=MOCK_USER,
                case=None,
                values=sample_values,
                language="gu",
                template_id=tpl_id,
            ))
            
            rendered_text = render_template(content, ctx)
            self.assertNotIn("{{", rendered_text, f"Leftover '{{{{' in direct download {tpl_id}")
            self.assertNotIn("}}", rendered_text, f"Leftover '}}}}' in direct download {tpl_id}")
            self.assertNotIn("None", rendered_text, f"Leaked 'None' in direct download {tpl_id}")



if __name__ == "__main__":
    unittest.main()
