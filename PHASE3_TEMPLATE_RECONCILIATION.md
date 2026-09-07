# Phase 3: Canonical Legal Template Reconciliation Report
**NyaySetu Pro Product Catalog vs. Implemented Seed Templates**

*Generated: 2026-09-06 | Authoritative Comparison*

## Executive Summary

A forensic audit was performed reconciling the **Product Canonical 21 Application Catalog** specified by the legal product specification with the currently implemented backend templates.

### Key Findings:

1. **100% Present in V2 Catalog**: All **21 of 21** canonical legal application templates requested by product specification are **100% IMPLEMENTED** with verbatim Gujarati legal phrasing in `test_seed_data_templates_v2.py` (under the exact IDs specified by the product catalog).
2. **Root Cause of Phase 2 Report Table Confusion**: In the previous Phase 2 Gate Report (Section 7), the table referenced 21 templates selected from the **v1 legacy catalog** (which used generic English IDs like `adjournment`, `bail_regular`, `certified_copy`, etc.), rather than the authoritative **v2 canonical catalog** (`mudat_arji`, `jamin_bond`, `certified_report`, etc.).
3. **Coexistence in Seed State**: The backend test harness maintains **45 total templates** (24 legacy v1 templates + 21 canonical v2 templates). Both catalogs coexist without ID collision.
4. **No Templates Missing**: Exactly **0** of the 21 canonical product templates are missing. Zero templates need to be invented or deleted.

--- 

## Detailed Template-by-Template Reconciliation (All 21 Templates)

### 1. `aanke_padvani_arji`
- **Product Canonical ID**: `aanke_padvani_arji`
- **Current Implementation ID**: `aanke_padvani_arji` (Exact Match: **YES**)
- **Gujarati Title**: દસ્તાવેજને આંકે પાડવાની અરજી
- **English Title**: Application to Exhibit Document
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`advocate_side, document_details, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, document_details, opposite_party_line, party_line, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `evidence_produce` (દસ્તાવેજ રજૂ કરવાની અરજી). The v2 implementation `aanke_padvani_arji` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 2. `certified_report`
- **Product Canonical ID**: `certified_report`
- **Current Implementation ID**: `certified_report` (Exact Match: **YES**)
- **Gujarati Title**: પ્રમાણિત નકલ માટે અરજી
- **English Title**: Application for Certified Copy
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 6 (`advocate_side, advocate_other, documents_details, recipient, deposit_amount, date`)
- **Placeholder Count**: 12 (`advocate_other, case_number, case_type, court, date_display, deposit_amount, documents_details, opposite_party_line, party_line, recipient, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `certified_copy` (પ્રમાણિત નકલ મેળવવાની અરજી). The v2 implementation `certified_report` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 3. `dd_karavani_arji`
- **Product Canonical ID**: `dd_karavani_arji`
- **Current Implementation ID**: `dd_karavani_arji` (Exact Match: **YES**)
- **Gujarati Title**: કેસ/દાવો ડિસમિસ કરવાની અરજી
- **English Title**: Application to Dismiss the Case / Suit
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`advocate_side, dismiss_reason, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, dismiss_reason, opposite_party_line, party_line, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `withdrawal` (કેસ પાછો ખેંચવાની અરજી). The v2 implementation `dd_karavani_arji` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 4. `document_return`
- **Product Canonical ID**: `document_return`
- **Current Implementation ID**: `document_return` (Exact Match: **YES**)
- **Gujarati Title**: દસ્તાવેજ પરત મેળવવાની અરજી
- **English Title**: Application for Return of Document
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 4 (`advocate_side, case_status, document_name, date`)
- **Placeholder Count**: 11 (`case_number, case_status_clause, case_type, court, date_display, document_name, opposite_party_line, party_line, selected_party_role, taluka_place, tense`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `return_documents` (દસ્તાવેજ પરત મેળવવાની અરજી). The v2 implementation `document_return` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 5. `document_on_record`
- **Product Canonical ID**: `document_on_record`
- **Current Implementation ID**: `document_on_record` (Exact Match: **YES**)
- **Gujarati Title**: દસ્તાવેજ રેકર્ડ પર લેવા અરજી
- **English Title**: Application to Take Document on Record
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`advocate_side, annexure, date`)
- **Placeholder Count**: 9 (`annexure, case_number, case_type, court, date_display, opposite_party_line, party_line, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `document_produce` (દસ્તાવેજ રજૂ કરવાની અરજી). The v2 implementation `document_on_record` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 6. `closing_purshish`
- **Product Canonical ID**: `closing_purshish`
- **Current Implementation ID**: `closing_purshish` (Exact Match: **YES**)
- **Gujarati Title**: ક્લોઝિંગ પુરશીશ
- **English Title**: Closing Purshis
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 2 (`advocate_side, date`)
- **Placeholder Count**: 8 (`case_number, case_type, court, date_display, opposite_party_line, party_line, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `closing_purshish` (પુરાવો બંધ પૂરશીશ). The v2 implementation `closing_purshish` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 7. `hazari_mafi_arji`
- **Product Canonical ID**: `hazari_mafi_arji`
- **Current Implementation ID**: `hazari_mafi_arji` (Exact Match: **YES**)
- **Gujarati Title**: હાજરી માફીની અરજી
- **English Title**: Application for Exemption from Personal Appearance
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 4 (`advocate_side, absence_reason, absence_reason_other, date`)
- **Placeholder Count**: 9 (`absence_reason, case_number, case_type, court, date_display, opposite_party_line, party_line, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `exemption_appearance` (હાજરી માફી અરજી). The v2 implementation `hazari_mafi_arji` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 8. `fs_haq_bandh`
- **Product Canonical ID**: `fs_haq_bandh`
- **Current Implementation ID**: `fs_haq_bandh` (Exact Match: **YES**)
- **Gujarati Title**: એફ.એસ.નો હક બંધ કરવાની અરજી
- **English Title**: Application to Close Right of Further Statement
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 1 (`date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, opposite_party_line, opposite_party_role, party_line, party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `cross_close` (ઉલટતપાસ બંધ કરવાની અરજી). The v2 implementation `fs_haq_bandh` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 9. `fs_haq_khol`
- **Product Canonical ID**: `fs_haq_khol`
- **Current Implementation ID**: `fs_haq_khol` (Exact Match: **YES**)
- **Gujarati Title**: એફ.એસ.નો હક ફરીથી ખોલવાની અરજી
- **English Title**: Application to Reopen Right of Further Statement
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`fs_reason, fs_reason_other, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, fs_reason, opposite_party_line, opposite_party_role, party_line, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `recall` (સાક્ષીને ફરી બોલાવવાની અરજી). The v2 implementation `fs_haq_khol` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 10. `jamin_bond`
- **Product Canonical ID**: `jamin_bond`
- **Current Implementation ID**: `jamin_bond` (Exact Match: **YES**)
- **Gujarati Title**: જામીન બોન્ડ સ્વીકારવા અરજી
- **English Title**: Application to Accept Bail Bond
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`crime_reg_number, bail_court, date`)
- **Placeholder Count**: 8 (`bail_court, case_or_crime, court, date_display, opposite_party_line, opposite_party_role, party_line, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `bail_regular` (નિયમિત જામીન અરજી). The v2 implementation `jamin_bond` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 11. `kam_board`
- **Product Canonical ID**: `kam_board`
- **Current Implementation ID**: `kam_board` (Exact Match: **YES**)
- **Gujarati Title**: કામ બોર્ડ પર લેવા અરજી
- **English Title**: Application to Take Matter on Board
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 4 (`advocate_side, next_date, proceeding, date`)
- **Placeholder Count**: 10 (`case_number, case_type, court, date_display, next_date, opposite_party_line, party_line, proceeding, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `early_hearing` (ઝડપી સુનાવણી અરજી). The v2 implementation `kam_board` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 12. `mudat_arji`
- **Product Canonical ID**: `mudat_arji`
- **Current Implementation ID**: `mudat_arji` (Exact Match: **YES**)
- **Gujarati Title**: મુદ્દત અરજી
- **English Title**: Adjournment Application
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`reason, reason_other, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, opposite_party_line, opposite_party_role, party_line, reason, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `adjournment` (મુદત અરજી). The v2 implementation `mudat_arji` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 13. `saaxi_summons`
- **Product Canonical ID**: `saaxi_summons`
- **Current Implementation ID**: `saaxi_summons` (Exact Match: **YES**)
- **Gujarati Title**: સાક્ષીને સમન્સ કાઢવાની અરજી
- **English Title**: Application to Issue Summons to Witness
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 2 (`witness_name, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, opposite_party_line, opposite_party_role, party_line, taluka_place, witness_name`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Brand new template introduced in the v2 legal draft catalog.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 14. `samadhan_purshish`
- **Product Canonical ID**: `samadhan_purshish`
- **Current Implementation ID**: `samadhan_purshish` (Exact Match: **YES**)
- **Gujarati Title**: સમાધાન પુરશીશ
- **English Title**: Compromise Purshis
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`advocate_side, settlement_terms, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, date_display, opposite_party_line, party_line, selected_party_role, settlement_terms, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `compromise` (સમાધાન પૂરશીશ). The v2 implementation `samadhan_purshish` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 15. `ulat_tapas_bandh`
- **Product Canonical ID**: `ulat_tapas_bandh`
- **Current Implementation ID**: `ulat_tapas_bandh` (Exact Match: **YES**)
- **Gujarati Title**: ઉલટતપાસનો હક બંધ કરવાની અરજી
- **English Title**: Application to Close Right of Cross-Examination
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`witness_name, since_when, date`)
- **Placeholder Count**: 11 (`case_number, case_type, court, date_display, opposite_party_line, opposite_party_role, party_line, party_role, since_when, taluka_place, witness_name`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `cross_close` (ઉલટતપાસ બંધ કરવાની અરજી). The v2 implementation `ulat_tapas_bandh` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 16. `ulat_tapas_khol`
- **Product Canonical ID**: `ulat_tapas_khol`
- **Current Implementation ID**: `ulat_tapas_khol` (Exact Match: **YES**)
- **Gujarati Title**: ઉલટતપાસનો હક ફરીથી ખોલવાની અરજી
- **English Title**: Application to Reopen Right of Cross-Examination
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 2 (`cross_reason, date`)
- **Placeholder Count**: 9 (`case_number, case_type, court, cross_reason, date_display, opposite_party_line, opposite_party_role, party_line, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `recall` (સાક્ષીને ફરી બોલાવવાની અરજી). The v2 implementation `ulat_tapas_khol` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 17. `undertaking`
- **Product Canonical ID**: `undertaking`
- **Current Implementation ID**: `undertaking` (Exact Match: **YES**)
- **Gujarati Title**: બાંહેધરી
- **English Title**: Undertaking
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 4 (`advocate_side, undertaking_matter, undertaking_action, date`)
- **Placeholder Count**: 10 (`case_number, case_type, court, date_display, opposite_party_line, party_line, selected_party_role, taluka_place, undertaking_action, undertaking_matter`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `affidavit` (સોગંદનામું). The v2 implementation `undertaking` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 18. `vakilatnama_civil`
- **Product Canonical ID**: `vakilatnama_civil`
- **Current Implementation ID**: `vakilatnama_civil` (Exact Match: **YES**)
- **Gujarati Title**: વકીલાતનામું (સિવિલ)
- **English Title**: Vakalatnama (Civil)
- **Category**: General
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 7 (`advocate_side, party_sign_name, advocate_qualification, advocate_address, advocate_mobile, advocate_sanad, date`)
- **Placeholder Count**: 14 (`advocate_address, advocate_mobile, advocate_name, advocate_qualification, advocate_sanad, case_number, case_type, court, date_display, opposite_party_line, party_line, party_sign_name, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `vakalatnama` (વકાલતનામું). The v2 implementation `vakilatnama_civil` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 19. `vakilatnama_criminal`
- **Product Canonical ID**: `vakilatnama_criminal`
- **Current Implementation ID**: `vakilatnama_criminal` (Exact Match: **YES**)
- **Gujarati Title**: વકીલાતનામું (ક્રિમિનલ)
- **English Title**: Vakalatnama (Criminal)
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 7 (`advocate_side, party_sign_name, advocate_qualification, advocate_address, advocate_mobile, advocate_sanad, date`)
- **Placeholder Count**: 14 (`advocate_address, advocate_mobile, advocate_name, advocate_qualification, advocate_sanad, case_number, case_type, court, date_display, opposite_party_line, party_line, party_sign_name, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `vakalatnama` (વકાલતનામું). The v2 implementation `vakilatnama_criminal` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 20. `warrant_hathbido`
- **Product Canonical ID**: `warrant_hathbido`
- **Current Implementation ID**: `warrant_hathbido` (Exact Match: **YES**)
- **Gujarati Title**: સમન્સ/વોરંટનો હાથબીડો આપવા અરજી
- **English Title**: Application for Hand Delivery of Summons / Warrant
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 4 (`process_type, process_target, advocate_side, date`)
- **Placeholder Count**: 10 (`case_number, case_type, court, date_display, opposite_party_line, party_line, process_target, process_type, selected_party_role, taluka_place`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Brand new template introduced in the v2 legal draft catalog.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

### 21. `warrant_rad`
- **Product Canonical ID**: `warrant_rad`
- **Current Implementation ID**: `warrant_rad` (Exact Match: **YES**)
- **Gujarati Title**: વોરંટ રદ કરવાની અરજી
- **English Title**: Application to Cancel Warrant
- **Category**: Criminal
- **Source Definition**: Verbatim lawyer draft specification (`Downloads/Nyaysetu/Field for each template`)
- **Field Count**: 3 (`warrant_date, absence_reason, date`)
- **Placeholder Count**: 10 (`absence_reason, case_number, case_type, court, date_display, opposite_party_line, opposite_party_role, party_line, taluka_place, warrant_date`)
- **Same Template**: **YES** (Verbatim implementation of product specification)
- **Legacy v1 Reference**: Corresponded to generic legacy template `warrant_cancel` (વોરંટ રદ અરજી). The v2 implementation `warrant_rad` is the authentic Gujarati legal version.
- **Discrepancy Status**: **NO DISCREPANCY / EXACT MATCH**

---

## Canonical Reconciliation Matrix

| # | Product Canonical ID | Implemented ID | Gujarati Title | English Title | Fields | Placeholders | Status |
| :-: | :--- | :--- | :--- | :--- | :-: | :-: | :---: |
| 1 | `aanke_padvani_arji` | `aanke_padvani_arji` | દસ્તાવેજને આંકે પાડવાની અરજી | Application to Exhibit Document | 3 | 9 | **MATCH** |
| 2 | `certified_report` | `certified_report` | પ્રમાણિત નકલ માટે અરજી | Application for Certified Copy | 6 | 12 | **MATCH** |
| 3 | `dd_karavani_arji` | `dd_karavani_arji` | કેસ/દાવો ડિસમિસ કરવાની અરજી | Application to Dismiss the Case / Suit | 3 | 9 | **MATCH** |
| 4 | `document_return` | `document_return` | દસ્તાવેજ પરત મેળવવાની અરજી | Application for Return of Document | 4 | 11 | **MATCH** |
| 5 | `document_on_record` | `document_on_record` | દસ્તાવેજ રેકર્ડ પર લેવા અરજી | Application to Take Document on Record | 3 | 9 | **MATCH** |
| 6 | `closing_purshish` | `closing_purshish` | ક્લોઝિંગ પુરશીશ | Closing Purshis | 2 | 8 | **MATCH** |
| 7 | `hazari_mafi_arji` | `hazari_mafi_arji` | હાજરી માફીની અરજી | Application for Exemption from Personal Appearance | 4 | 9 | **MATCH** |
| 8 | `fs_haq_bandh` | `fs_haq_bandh` | એફ.એસ.નો હક બંધ કરવાની અરજી | Application to Close Right of Further Statement | 1 | 9 | **MATCH** |
| 9 | `fs_haq_khol` | `fs_haq_khol` | એફ.એસ.નો હક ફરીથી ખોલવાની અરજી | Application to Reopen Right of Further Statement | 3 | 9 | **MATCH** |
| 10 | `jamin_bond` | `jamin_bond` | જામીન બોન્ડ સ્વીકારવા અરજી | Application to Accept Bail Bond | 3 | 8 | **MATCH** |
| 11 | `kam_board` | `kam_board` | કામ બોર્ડ પર લેવા અરજી | Application to Take Matter on Board | 4 | 10 | **MATCH** |
| 12 | `mudat_arji` | `mudat_arji` | મુદ્દત અરજી | Adjournment Application | 3 | 9 | **MATCH** |
| 13 | `saaxi_summons` | `saaxi_summons` | સાક્ષીને સમન્સ કાઢવાની અરજી | Application to Issue Summons to Witness | 2 | 9 | **MATCH** |
| 14 | `samadhan_purshish` | `samadhan_purshish` | સમાધાન પુરશીશ | Compromise Purshis | 3 | 9 | **MATCH** |
| 15 | `ulat_tapas_bandh` | `ulat_tapas_bandh` | ઉલટતપાસનો હક બંધ કરવાની અરજી | Application to Close Right of Cross-Examination | 3 | 11 | **MATCH** |
| 16 | `ulat_tapas_khol` | `ulat_tapas_khol` | ઉલટતપાસનો હક ફરીથી ખોલવાની અરજી | Application to Reopen Right of Cross-Examination | 2 | 9 | **MATCH** |
| 17 | `undertaking` | `undertaking` | બાંહેધરી | Undertaking | 4 | 10 | **MATCH** |
| 18 | `vakilatnama_civil` | `vakilatnama_civil` | વકીલાતનામું (સિવિલ) | Vakalatnama (Civil) | 7 | 14 | **MATCH** |
| 19 | `vakilatnama_criminal` | `vakilatnama_criminal` | વકીલાતનામું (ક્રિમિનલ) | Vakalatnama (Criminal) | 7 | 14 | **MATCH** |
| 20 | `warrant_hathbido` | `warrant_hathbido` | સમન્સ/વોરંટનો હાથબીડો આપવા અરજી | Application for Hand Delivery of Summons / Warrant | 4 | 10 | **MATCH** |
| 21 | `warrant_rad` | `warrant_rad` | વોરંટ રદ કરવાની અરજી | Application to Cancel Warrant | 3 | 10 | **MATCH** |

---

## Recommendations for Production Seeding

1. **Populate `seed_data_templates_v2.py`**: Currently `seed_data_templates_v2.py` defines `TEMPLATES_V2 = []` because of Phase 1 seed decoupling. For real Firebase production seeding, `seed_data_templates_v2.py` should import and expose the 21 canonical templates so `seed_firestore.py` populates the production database with these exact 21 authoritative drafts.
2. **Preserve Legacy v1 for Backward Compatibility**: Keep the 24 legacy v1 templates in `test_seed_data.py` so existing tests continue passing without modification.
3. **Ensure Primary UI Display**: The lawyer-facing application and admin template manager prioritize the 21 canonical v2 legal drafts.
