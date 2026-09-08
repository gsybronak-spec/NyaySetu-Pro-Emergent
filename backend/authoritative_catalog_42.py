# -*- coding: utf-8 -*-
"""
NyaySetu Pro — 42-Template Authoritative Legal Catalog Builder.
Derived strictly from the 21 authoritative OpenDocument Text (.odt) source specifications
in Downloads/Nyay Templates/.

Produces exactly 42 production templates:
  - 21 Gujarati templates (<key>_gu)
  - 21 English templates (<key>_en)

All templates adhere to:
  1. Exact field definitions, types, dropdowns, conditional "Other" (અન્ય) inputs.
  2. Case-owned fields omitted from form (inherited automatically from linked Case).
  3. Date ordered as the LAST field.
  4. Authoritative Gujarati legal draft with {{placeholders}}.
  5. Accurate, legally sound English court translations.
  6. Standard layout settings (A4, margins, HarfBuzz fonts).
"""
import copy
from datetime import datetime, timezone

NOW_ISO = datetime.now(timezone.utc).isoformat()

DEFAULT_SETTINGS = {
    "page_size": "A4",
    "margin_top_cm": 2.0,
    "margin_bottom_cm": 2.0,
    "margin_left_cm": 3.5,
    "margin_right_cm": 3.5,
    "gujarati_font": "Noto Sans Gujarati",
    "english_font": "Times-Roman",
    "gujarati_font_docx": "Lohit Gujarati",
    "english_font_docx": "Times New Roman",
    "body_size": 13,
    "heading_size": 14,
    "line_spacing": 18,
    "paragraph_spacing": 6,
    "alignment": "justify",
}

# The 21 Authoritative Template Definitions (Base Specifications)
BASE_TEMPLATES = [
    # 1. Aanke Padvani Arji
    {
        "base_key": "aanke_padvani_arji",
        "aliases": ["aanke", "exhibit", "દસ્તાવેજને આંકે પાડવાની અરજી", "આંક", "આંક પાડવાની અરજી"],
        "name_gu": "આંક પાડવાની અરજી",
        "name_en": "Application to Exhibit Document",
        "category": "General",
        "description": "Application to mark/assign exhibit numbers to documents produced on record.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "document_details", "label_en": "Document details to be exhibited", "label_gu": "ક્યા દસ્તાવેજને આંક પાડવાના તેની વિગત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- દસ્તાવેજને આંક પાડવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{document_details}} ખુબ જ મહત્વ ધરાવે છે અને કેસના યોગ્ય નિર્ણય માટે જરૂરી છે. તેમજ સદર દસ્તાવેજને પુરાવા તરીકે રેકર્ડ પર લેવા ન્યાયના હિતમાં હોય, સદર દસ્તાવેજને રેકર્ડ પર લઈ તેને યોગ્ય આંક આપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO EXHIBIT DOCUMENT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending for hearing before this Hon'ble Court. In the said case, {{document_details}} is of immense importance and necessary for the proper adjudication of the matter. It is in the interest of justice that the said document be taken on record as evidence. Therefore, it is prayed that this Hon'ble Court may be pleased to take the said document on record and assign a proper exhibit number to it.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 2. Certified Report / Nakal
    {
        "base_key": "certified_report",
        "aliases": ["certified copy", "પ્રમાણિત નકલ", "pramanit nakal", "નકલ", "સર્ટિફાઇડ રિપોર્ટ", "inspection"],
        "name_gu": "સર્ટિફાઇડ રિપોર્ટ / નકલ મેળવવાની અરજી",
        "name_en": "Application for Certified Copy / Inspection Report",
        "category": "General",
        "description": "Application for certified copies of judicial orders, evidence, or inspection reports.",
        "fields": [
            {"key": "presiding_officer", "label_en": "Court / Presiding Judge details", "label_gu": "કયા સાહેબની કોર્ટનો કેસ છે તેની વિગત", "type": "text", "required": False},
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ / ત્રાહિત વકીલ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
                 {"value": "other", "label_en": "Other (Third Party)", "label_gu": "અન્ય (ત્રાહિત પક્ષ)"},
             ]},
            {"key": "advocate_other", "label_en": "If Other — details of person requesting copies", "label_gu": "અન્ય હોય તો તેઓની વિગત", "type": "text", "required": False, "depends_on": "advocate_side", "show_when": "other"},
            {"key": "copy_type", "label_en": "Type of copy requested", "label_gu": "નકલ માંગેલ બાબત", "type": "select", "required": True,
             "options": [
                 {"value": "સર્ટિફાઇડ નકલ", "label_en": "Certified Copy", "label_gu": "સર્ટિફાઇડ નકલ"},
                 {"value": "ઇન્સ્પેક્શન રિપોર્ટ", "label_en": "Inspection Report", "label_gu": "ઇન્સ્પેક્શન રિપોર્ટ"},
                 {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
             ]},
            {"key": "copy_type_other", "label_en": "Specify other copy type", "label_gu": "અન્ય નકલ પ્રકાર જણાવો", "type": "text", "required": False, "depends_on": "copy_type", "show_when": "other"},
            {"key": "document_details", "label_en": "Details of documents/copies required", "label_gu": "માંગેલ નકલના દસ્તાવેજોની વિગત", "type": "textarea", "required": True},
            {"key": "urgency", "label_en": "Mode of copy", "label_gu": "નકલનો પ્રકાર", "type": "select", "required": True,
             "options": [
                 {"value": "સાદી", "label_en": "Ordinary", "label_gu": "સાદી"},
                 {"value": "અર્જન્ટ", "label_en": "Urgent", "label_gu": "અર્જન્ટ"},
             ]},
            {"key": "reason_for_copy", "label_en": "Reason for obtaining copy", "label_gu": "નકલ મેળવવાનું કારણ", "type": "text", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}
{{presiding_officer}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- સર્ટિફાઇડ નકલ / રિપોર્ટ મેળવવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ પેન્ડિંગ / ફેસલ થયેલ છે. સદર કેસમાં અમારે {{copy_type}} ની જરૂરિયાત હોય, નીચે મુજબના દસ્તાવેજોની સર્ટિફાઇડ નકલ તૈયાર કરાવી {{urgency}} ધોરણે આપવા હુકમ કરવા મહેરબાની કરશોજી.

નકલ મેળવવાની વિગત:
{{document_details}}

કારણ : {{reason_for_copy}}

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}
{{presiding_officer}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR CERTIFIED COPY / INSPECTION REPORT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending / disposed of before this Hon'ble Court. In the said matter, {{copy_type}} is required on behalf of the applicant. Therefore, it is prayed that this Hon'ble Court may be pleased to issue certified copies of the documents specified below on {{urgency}} basis in the interest of justice.

Details of copies required:
{{document_details}}

Reason : {{reason_for_copy}}

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 3. Closing Purshish
    {
        "base_key": "closing_purshish",
        "aliases": ["closing", "purshis", "પુરાવો બંધ", "પુરશીશ", "closure of evidence"],
        "name_gu": "પુરાવો બંધ પુરશિસ",
        "name_en": "Closing Purshis (Closure of Evidence)",
        "category": "General",
        "description": "Purshis submitted to formally close oral and documentary evidence on behalf of a party.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "closing_note", "label_en": "Special note / reason (optional)", "label_gu": "વિશેષ નોંધ / કારણ (મરજિયાત)", "type": "textarea", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- પુરાવો બંધ અંગેની પુરશિસ...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કામમાં અમો {{selected_party_role}} તરફથી અમારો મૌખિક તેમજ દસ્તાવેજી પુરાવો પૂરો થયેલ હોવાથી હવે પછી અમારે કોઈ વધુ પુરાવો રજૂ કરવાનો રહેતો ન હોય, સદર કામમાં અમારો પુરાવો બંધ રાખવા બાબતે આ પુરાવા બંધની પુરશિસ રજૂ કરીએ છીએ, જે રેકર્ડ પર લઈ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

{{closing_note}}

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: PURSHIS CLOSING ORAL AND DOCUMENTARY EVIDENCE

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

In the said case, oral as well as documentary evidence on behalf of {{selected_party_role}} has been concluded. The applicant does not wish to lead any further evidence in this matter. Therefore, this closing purshis is submitted to close the evidence on behalf of {{selected_party_role}}. It is prayed that the same be taken on record and appropriate orders be passed.

{{closing_note}}

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 4. DD Karavani Arji (Dismissal in Default)
    {
        "base_key": "dd_karavani_arji",
        "aliases": ["dd", "dismiss in default", "ડિસમિસ", "ડિસમિસ ઇન ડિફોલ્ટ", "ડી.ડી."],
        "name_gu": "ડી.ડી. કરાવવા અંગેની અરજી (ડિસમિસ ઇન ડિફોલ્ટ)",
        "name_en": "Application for Dismissal in Default (D.D.)",
        "category": "Civil",
        "description": "Application to dismiss case due to non-prosecution or absence of complainant/plaintiff.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Defendant / Accused side", "label_gu": "પ્રતિવાદી / આરોપી તરફથી"},
                 {"value": "party", "label_en": "Plaintiff / Complainant side", "label_gu": "વાદી / ફરિયાદી તરફથી"},
             ]},
            {"key": "absence_period", "label_en": "Duration/period of continuous absence", "label_gu": "કેટલા સમયથી ગેરહાજર રહે છે તેની વિગત", "type": "text", "required": True},
            {"key": "dd_grounds", "label_en": "Grounds for dismissal", "label_gu": "ડિસમિસ કરવાના કારણો", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- કેસ ડિસમિસ ઇન ડિફોલ્ટ (ડી.ડી.) કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં સામા પક્ષકાર છેલ્લા ઘણા સમયથી એટલે કે {{absence_period}} થી આપ નામદાર કોર્ટ સમક્ષ હાજર રહેતા નથી કે કેસ આગળ ચલાવવામાં રસ ધરાવતા નથી. {{dd_grounds}}

આમ, સામા પક્ષકારની સતત ગેરહાજરીના કારણે અમારા પક્ષકારને બિનજરૂરી હેરાનગતિ ભોગવવી પડે છે. જેથી સદર કેસને ડિસમિસ ઇન ડિફોલ્ટ કરી યોગ્ય તે ન્યાયિક હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR DISMISSAL IN DEFAULT (D.D.)

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The opposite party has failed to appear before this Hon'ble Court for a considerable period, namely {{absence_period}}, and shows no interest in prosecuting the case diligently. {{dd_grounds}}

Due to the continuous and unexplained absence of the opposite party, our client is subjected to undue hardship and prejudice. It is therefore prayed that this Hon'ble Court may be pleased to dismiss the case in default in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 5. Document Parat Levani Arji (Return of Documents)
    {
        "base_key": "document_parat_levani_arji",
        "aliases": ["document_return", "parat", "return document", "દસ્તાવેજ પરત", "પરત મેળવવા"],
        "name_gu": "દસ્તાવેજ પરત મેળવવા બાબતની અરજી",
        "name_en": "Application for Return of Documents",
        "category": "General",
        "description": "Application to return original documents produced on court record with undertaking.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "case_status", "label_en": "Case Status", "label_gu": "કેસની સ્થિતિ", "type": "select", "required": True,
             "options": [
                 {"value": "ચાલુ", "label_en": "Pending / Ongoing", "label_gu": "ચાલુ"},
                 {"value": "ડિસ્પોસ્ડ", "label_en": "Disposed", "label_gu": "ડિસ્પોસ્ડ"},
             ]},
            {"key": "documents_list", "label_en": "Details of documents to be returned", "label_gu": "પરત મેળવવાના દસ્તાવેજોની વિગત", "type": "textarea", "required": True},
            {"key": "reason_for_return", "label_en": "Reason for return of documents", "label_gu": "દસ્તાવેજ પરત મેળવવાનું કારણ", "type": "text", "required": True},
            {"key": "undertaking_text", "label_en": "Undertaking statement", "label_gu": "કોર્ટ ફરમાવે ત્યારે રજૂ કરવાની બાંહેધરી", "type": "text", "required": False, "default_value": "જ્યારે પણ નામદાર કોર્ટ દ્વારા માંગણી કરવામાં આવશે ત્યારે અસલ દસ્તાવેજ રજૂ કરવાની બાંહેધરી આપીએ છીએ."},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- દસ્તાવેજો પરત મેળવવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ {{case_status_clause}} {{tense}}. સદર કામમાં અમારા પક્ષકાર તરફથી અસલ દસ્તાવેજો રજૂ કરવામાં આવેલ હતા. જે પૈકી નીચે મુજબના દસ્તાવેજોની અમારા પક્ષકારને જરૂરિયાત હોવાથી પરત મેળવવા જરૂરી છે:

દસ્તાવેજોની વિગત:
{{documents_list}}

કારણ : {{reason_for_return}}

{{undertaking_text}}

તેથી ન્યાયના હિતમાં સદર દસ્તાવેજોની પ્રમાણિત નકલ રેકર્ડ પર રાખી અસલ દસ્તાવેજો પરત સોંપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR RETURN OF DOCUMENTS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case {{case_status_clause}} before this Hon'ble Court. In the said proceedings, original documents were produced on behalf of our client. Out of the same, our client urgently requires the return of the following documents:

Details of Documents:
{{documents_list}}

Reason : {{reason_for_return}}

Undertaking: The applicant hereby undertakes to produce the said original documents as and when directed by this Hon'ble Court.

Therefore, it is prayed that this Hon'ble Court may be pleased to return the said original documents after retaining certified copies on record, in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 6. Document Swikaravani Arji (Production and Acceptance)
    {
        "base_key": "document_swikaravani_arji",
        "aliases": ["document_on_record", "production", "દસ્તાવેજ રજૂ", "દસ્તાવેજ સ્વીકારવા", "record par"],
        "name_gu": "દસ્તાવેજ રજૂ કરવા / સ્વીકારવાની અરજી",
        "name_en": "Application for Production and Acceptance of Documents",
        "category": "General",
        "description": "Application to produce and accept documents on court record as evidence.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "documents_produced", "label_en": "Details of documents produced", "label_gu": "રજૂ કરેલ દસ્તાવેજોની વિગત", "type": "textarea", "required": True},
            {"key": "relevance_reason", "label_en": "Relevance and reason for production", "label_gu": "દસ્તાવેજ રજૂ કરવાનું કારણ / મહત્વ", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- દસ્તાવેજો રજૂ કરી રેકર્ડ પર સ્વીકારવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં અમારા પક્ષકારના હિત અને કેસના સાચા ન્યાયિક નિર્ણય માટે નીચે મુજબના દસ્તાવેજો રજૂ કરવા અત્યંત જરૂરી છે:

રજૂ કરેલ દસ્તાવેજોની વિગત:
{{documents_produced}}

કારણ : {{relevance_reason}}

સદર દસ્તાવેજો કેસના પુરાવા માટે અનિવાર્ય હોઈ, તેને કોર્ટ રેકર્ડ પર સ્વીકારી યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR PRODUCTION AND ACCEPTANCE OF DOCUMENTS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. For the proper adjudication of the matter and in the interest of justice, it is necessary to produce the following documents on record:

Details of Documents Produced:
{{documents_produced}}

Reason and Relevance: {{relevance_reason}}

The said documents are indispensable for establishing the facts of the case. It is therefore prayed that this Hon'ble Court may be pleased to take the said documents on record in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 7. Exemption Arji (Hazari Mafi)
    {
        "base_key": "exemption_arji",
        "aliases": ["hazari_mafi_arji", "exemption", "હાજરી માફી", "mafi", "hazari mafi"],
        "name_gu": "હાજરી માફી અરજી",
        "name_en": "Application for Exemption from Personal Appearance",
        "category": "Criminal",
        "description": "Application seeking exemption from personal appearance for the accused on the date of hearing.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Accused side", "label_gu": "આરોપી તરફથી"},
                 {"value": "party", "label_en": "Applicant side", "label_gu": "અરજદાર તરફથી"},
             ]},
            {"key": "applicant_person", "label_en": "Name of person seeking exemption", "label_gu": "કોની હાજરી માફી જોઈએ છે તેનું નામ", "type": "text", "required": True},
            {"key": "reason", "label_en": "Reason for absence", "label_gu": "ગેરહાજરીનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "માંદગીના કારણોસર", "label_en": "Due to sudden illness", "label_gu": "માંદગીના કારણોસર / બિમાર હોવાથી"},
                 {"value": "કામ સબબ બહારગામ ગયેલ હોવાથી", "label_en": "Out of station for urgent work", "label_gu": "કામ સબબ બહારગામ ગયેલ હોવાથી"},
                 {"value": "other", "label_en": "Other reason", "label_gu": "અન્ય કારણ"},
             ]},
            {"key": "reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "reason", "show_when": "other"},
            {"key": "undertaking_next_date", "label_en": "Undertaking for next date", "label_gu": "આગામી તારીખે હાજર રહેવાની બાંહેધરી", "type": "text", "required": False, "default_value": "આગામી મુદ્દતે અમારા પક્ષકાર અચૂક હાજર રહેશે તેવી બાંહેધરી આપીએ છીએ."},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- આજ રોજની મુદ્દત પૂરતી હાજરી માફી મળવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કામમાં અમારા પક્ષકાર {{applicant_person}} આજ રોજની મુદ્દતે હાજર રહી શકે તેમ નથી, કારણ કે {{reason}}.

અમારા પક્ષકાર જાણીબુઝીને ગેરહાજર રહેલ નથી. {{undertaking_next_date}}

આજ રોજ અમારા વકીલશ્રી મારફત કાર્યવાહી ચલાવવા તૈયાર છીએ. જેથી ન્યાયના હિતમાં અમારા પક્ષકારની આજ રોજની મુદ્દત પૂરતી હાજરી માફ રાખવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR EXEMPTION FROM PERSONAL APPEARANCE FOR THE DAY

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

In the said case, our client {{applicant_person}} is unable to remain present in person before this Hon'ble Court today because {{reason}}.

The absence of the applicant is neither deliberate nor intentional, but due to bona fide reasons beyond control. {{undertaking_next_date}}

The advocate on behalf of the applicant is present to proceed with the matter. It is therefore prayed that this Hon'ble Court may be pleased to grant exemption from personal appearance for today only in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 8. FS no haq bandh karvani arji (Close Further Statement)
    {
        "base_key": "fs_no_haq_bandh_karvani_arji",
        "aliases": ["fs_haq_bandh", "further statement", "એફ.એસ.", "હક બંધ", "fs close"],
        "name_gu": "ફર્ધર સ્ટેટમેન્ટ (F.S.) હક્ક બંધ કરવાની અરજી",
        "name_en": "Application to Close Further Statement (F.S.) Right",
        "category": "Criminal",
        "description": "Application to close the right of accused to give further statement under section 313 Cr.P.C.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Complainant side", "label_gu": "ફરિયાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "સામાવાળા તરફથી"},
             ]},
            {"key": "accused_target", "label_en": "Name of accused whose F.S. right is to be closed", "label_gu": "જે આરોપીનું F.S. બંધ કરવાનું હોય તેનું નામ", "type": "text", "required": False},
            {"key": "ground_notes", "label_en": "Grounds / remarks", "label_gu": "હક્ક બંધ કરવાના કારણો / નોંધ", "type": "textarea", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- આરોપીનું ફર્ધર સ્ટેટમેન્ટ (F.S.) લેવાનો હક્ક બંધ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં પુરાવાનો તબક્કો પૂર્ણ થયેલ છે અને કેસ આરોપીના ફર્ધર સ્ટેટમેન્ટ (F.S.) માટે મુલતવી રાખવામાં આવેલ છે. આપ નામદાર કોર્ટે પૂરતી તકો આપવા છતાં આરોપી હાજર રહી પોતાનું ફર્ધર સ્ટેટમેન્ટ નોંધાવતા નથી અને કેસ બિનજરૂરી લંબાવવાનો પ્રયાસ કરે છે. {{ground_notes}}

આથી ન્યાયના હિતમાં આરોપી {{accused_target}} નું ફર્ધર સ્ટેટમેન્ટ (F.S.) લેવાનો હક્ક બંધ કરી કેસ આગળ ચલાવવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO CLOSE RIGHT OF FURTHER STATEMENT (F.S.) OF ACCUSED

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The evidence stage has concluded, and the matter was posted for recording the further statement (F.S.) of the accused under Section 313 Cr.P.C. Despite sufficient opportunities granted by this Hon'ble Court, the accused has failed to record statement and is deliberately delaying the proceedings. {{ground_notes}}

It is therefore prayed in the interest of justice that this Hon'ble Court may be pleased to close the right of further statement (F.S.) of the accused {{accused_target}} and proceed further with the case.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 9. FS no haq kholvani arji (Reopen Further Statement)
    {
        "base_key": "fs_no_haq_kholvani_arji",
        "aliases": ["fs_haq_khol", "reopen fs", "એફ.એસ. ખોલવા", "fs khol", "reopen further statement"],
        "name_gu": "ફર્ધર સ્ટેટમેન્ટ (F.S.) હક્ક ખોલવાની અરજી",
        "name_en": "Application to Reopen Further Statement (F.S.) Right",
        "category": "Criminal",
        "description": "Application to reopen the closed right of accused to record further statement under section 313 Cr.P.C.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Accused side", "label_gu": "આરોપી તરફથી"},
                 {"value": "party", "label_en": "Applicant side", "label_gu": "અરજદાર તરફથી"},
             ]},
            {"key": "reopen_reason", "label_en": "Reason for previous absence / closure", "label_gu": "હક્ક બંધ થવાનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "અનિવાર્ય માંદગીના કારણોસર", "label_en": "Bona fide illness", "label_gu": "અનિવાર્ય માંદગીના કારણોસર"},
                 {"value": "મુદ્દતની જાણ ન હોવાના કારણે", "label_en": "Lack of knowledge of the date", "label_gu": "મુદ્દતની જાણ ન હોવાના કારણે"},
                 {"value": "other", "label_en": "Other unavoidable reason", "label_gu": "અન્ય અનિવાર્ય કારણ"},
             ]},
            {"key": "reopen_reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "reopen_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- આરોપીનું ફર્ધર સ્ટેટમેન્ટ (F.S.) આપવાનો હક્ક ફરીથી ખોલવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસમાં અમારા પક્ષકાર {{reopen_reason}} આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકેલ ન હતા, જેથી આપ નામદાર કોર્ટે અમારા પક્ષકારનું ફર્ધર સ્ટેટમેન્ટ નોંધાવવાનો હક્ક બંધ કરેલ છે. અમારા પક્ષકાર જાણીબુઝીને ગેરહાજર રહેલ નથી.

જો ફર્ધર સ્ટેટમેન્ટનો હક્ક ફરીથી ખોલવામાં નહીં આવે તો અમારા પક્ષકારને કાયમી અન્યાય થશે. અમારા પક્ષકાર આજ રોજ કોર્ટ સમક્ષ હાજર છે અને ફર્ધર સ્ટેટમેન્ટ નોંધાવવા તૈયાર છે. જેથી ન્યાયના હિતમાં ફર્ધર સ્ટેટમેન્ટ (F.S.) નો હક્ક ફરીથી ખોલવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO REOPEN RIGHT OF FURTHER STATEMENT (F.S.) OF ACCUSED

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

In the said case, the applicant could not remain present before this Hon'ble Court due to {{reopen_reason}}, on account of which the right to record further statement (F.S.) came to be closed. The absence was neither intentional nor deliberate.

If the right to record further statement is not reopened, irreparable loss and prejudice will be caused to the applicant. The applicant is present today and is ready to record statement. It is therefore prayed that this Hon'ble Court may be pleased to reopen the right of further statement (F.S.) in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 10. Jamin Bond Swikarvani Arji (Bail Bond Acceptance)
    {
        "base_key": "jamin_bond_swikarvani_arji",
        "aliases": ["jamin_bond", "bail bond", "જામીન બોન્ડ", "મુચરકો", "surety bond"],
        "name_gu": "જામીન બોન્ડ સ્વીકારવા બાબતની અરજી",
        "name_en": "Application for Acceptance of Bail Bond and Surety",
        "category": "Criminal",
        "description": "Application to accept bail bond and surety pursuant to bail order and issue release warrant.",
        "fields": [
            {"key": "bail_order_date", "label_en": "Bail Order Date", "label_gu": "જામીન મંજૂર થયા તારીખ", "type": "text", "required": True},
            {"key": "bail_order_court", "label_en": "Court that granted bail", "label_gu": "જામીન મંજૂર કરનાર કોર્ટ", "type": "text", "required": True},
            {"key": "surety_name", "label_en": "Name of Surety", "label_gu": "જામીનદારનું નામ", "type": "text", "required": True},
            {"key": "bond_amount", "label_en": "Bail bond amount (Rs.)", "label_gu": "જામીન રકમ (રૂ.)", "type": "text", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_or_crime}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- જામીન મુચરકો / બોન્ડ સ્વીકારવા બાબત...

સદર કામમાં અમો આરોપીના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસમાં આપ નામદાર કોર્ટ / {{bail_order_court}} દ્વારા તારીખ {{bail_order_date}} ના રોજ આરોપીને જામીન પર મુક્ત કરવાનો હુકમ ફરમાવેલ છે. સદર હુકમની શરતો મુજબ આરોપી તરફથી જામીનદાર {{surety_name}} નો રૂ. {{bond_amount}} નો જામીન મુચરકો તેમજ સોલવન્સી પુરાવા સાથે રજૂ કરીએ છીએ.

જેથી આપ નામદાર કોર્ટના હુકમ મુજબનો જામીન મુચરકો સ્વીકારી આરોપીને મુક્ત કરવા યોગ્ય તે હુકમ તથા રિલીઝ વોરંટ કાઢી આપવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

આરોપીના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_or_crime}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR ACCEPTANCE OF BAIL BOND AND SURETY

In the above matter, we, the advocate for the Accused, most respectfully submit before this Hon'ble Court that:

In the said case, this Hon'ble Court / {{bail_order_court}} was pleased to enlarge the accused on bail vide order dated {{bail_order_date}}. In compliance with the bail conditions, the accused is submitting a bail bond of Rs. {{bond_amount}} along with surety of {{surety_name}} and necessary solvency documents.

It is therefore prayed that this Hon'ble Court may be pleased to accept the bail bond and surety, and issue necessary release order / release warrant for the release of the accused in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for the Accused
""",
    },

    # 11. Kam Board Par Levani Arji (Preponement)
    {
        "base_key": "kam_board_par_levani_arji",
        "aliases": ["kam_board", "preponement", "board par", "કામ બોર્ડ પર", "કામ બોર્ડ"],
        "name_gu": "કામ બોર્ડ પર લેવાની અરજી",
        "name_en": "Application to Take Matter on Board (Preponement)",
        "category": "General",
        "description": "Application to prepone the hearing and take the case on board on urgent grounds.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "scheduled_date", "label_en": "Scheduled / next date of hearing", "label_gu": "હાલની મુદતની તારીખ", "type": "text", "required": True},
            {"key": "urgent_reason", "label_en": "Reason to take on board", "label_gu": "કામ બોર્ડ પર લેવાનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "સમાધાન પુરશિસ રજૂ કરવી હોવાથી", "label_en": "To submit compromise purshis", "label_gu": "સમાધાન પુરશિસ રજૂ કરવી હોવાથી"},
                 {"value": "અર્જન્ટ હુકમ મેળવવા સારુ", "label_en": "For urgent orders", "label_gu": "અર્જન્ટ હુકમ મેળવવા સારુ"},
                 {"value": "other", "label_en": "Other urgent grounds", "label_gu": "અન્ય અર્જન્ટ કારણ"},
             ]},
            {"key": "urgent_reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "urgent_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- કામ આજ રોજ બોર્ડ પર લેવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ આગામી તારીખ {{scheduled_date}} ના રોજ નિયત થયેલ છે. પરંતુ સદર કામમાં {{urgent_reason}} હોવાથી આજ રોજ કામ બોર્ડ પર લેવું અત્યંત જરૂરી અને અનિવાર્ય છે.

જેથી ન્યાયના હિતમાં સદર કામનું રોજકામ તથા કેસની ફાઇલ આજ રોજ બોર્ડ પર લઈ યોગ્ય તે કાર્યવાહી કરવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO TAKE MATTER ON BOARD TODAY

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is scheduled for hearing on {{scheduled_date}}. However, it is urgently necessary to take the matter on board today because {{urgent_reason}}.

Therefore, it is respectfully prayed that this Hon'ble Court may be pleased to call for the case record and take the matter on board today for appropriate proceedings in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 12. Mudat Arji (Adjournment)
    {
        "base_key": "mudat_arji",
        "aliases": ["mudat", "adjournment", "મુદ્દત", "મુદત અરજી", "adjourn"],
        "name_gu": "મુદ્દત અરજી (Adjournment Application)",
        "name_en": "Application for Adjournment (Mudat Arji)",
        "category": "General",
        "description": "Application seeking postponement/adjournment of today's court hearing date.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "reason", "label_en": "Grounds for adjournment", "label_gu": "મુદ્દત માંગવાનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "માંદગીના કારણોસર", "label_en": "Illness of party / advocate", "label_gu": "પક્ષકાર/વકીલશ્રી માંદગીના કારણોસર"},
                 {"value": "દસ્તાવેજી પુરાવા એકત્રિત કરવા સારુ", "label_en": "To gather documentary evidence", "label_gu": "દસ્તાવેજી પુરાવા એકત્રિત કરવા સારુ"},
                 {"value": "સમાધાનની વાતચીત ચાલુ હોવાથી", "label_en": "Settlement talks are in progress", "label_gu": "સમાધાનની વાતચીત ચાલુ હોવાથી"},
                 {"value": "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ હોવાથી", "label_en": "Advocate engaged in another court", "label_gu": "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ હોવાથી"},
                 {"value": "other", "label_en": "Other reason", "label_gu": "અન્ય કારણ"},
             ]},
            {"key": "reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- આજ રોજની મુદ્દત મુલતવી રાખવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ આજ રોજ ચાલવા પર છે. સદર કામમાં {{reason}} હોવાથી આજ રોજ કેસ ચલાવી શકાય તેમ નથી.

અમો જાણીબુઝીને મુદ્દત માંગતા નથી. જેથી ન્યાયના હિતમાં આજ રોજની મુદ્દત મુલતવી રાખી યોગ્ય તે આગળની લાંબી મુદ્દત ફરમાવવા આપ નામદાર કોર્ટને નમ્ર વિનંતી છેજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR ADJOURNMENT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said matter is listed today before this Hon'ble Court. The applicant is unable to proceed with the matter today because {{reason}}.

The adjournment is sought bona fide and not with any intent to cause delay. It is therefore prayed that this Hon'ble Court may be pleased to adjourn today's hearing and grant a suitable next date in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 13. Saaxi ne Summons (Witness Summons)
    {
        "base_key": "saaxi_ne_summons",
        "aliases": ["saaxi_summons", "witness summons", "સાક્ષી", "સમન્સ", "witness"],
        "name_gu": "સાક્ષીને સમન્સ કાઢવા બાબતની અરજી",
        "name_en": "Application for Issuance of Witness Summons",
        "category": "General",
        "description": "Application to issue court summons to call a witness for deposition or production of documents.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "witness_name", "label_en": "Witness Name", "label_gu": "સાક્ષીનું નામ", "type": "text", "required": True},
            {"key": "witness_address", "label_en": "Witness Address", "label_gu": "સાક્ષીનું સરનામું", "type": "textarea", "required": True},
            {"key": "witness_purpose", "label_en": "Purpose of witness / documents to produce", "label_gu": "સાક્ષીને બોલાવવાનો હેતુ / દસ્તાવેજ રજૂ કરવા બાબત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- સાક્ષીને સમન્સ કાઢવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં નીચે જણાવેલ સાક્ષીની જુબાની કેસના સત્ય ન્યાયિક નિર્ણય માટે ખૂબ જ જરૂરી અને મહત્વપૂર્ણ છે:

સાક્ષીનું નામ : {{witness_name}}
સરનામું : {{witness_address}}
જુબાની / દસ્તાવેજનો હેતુ : {{witness_purpose}}

સદર સાક્ષી કોર્ટના સમન્સ વગર હાજર રહે તેમ ન હોવાથી, ન્યાયના હિતમાં સદર સાક્ષીને નિયત તારીખે જુબાની આપવા તેમજ જરૂરી દસ્તાવેજો સાથે હાજર રહેવા અંગે સમન્સ કાઢી આપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR ISSUANCE OF WITNESS SUMMONS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The testimony of the witness mentioned below is indispensable and material for the fair and just adjudication of this case:

Witness Name : {{witness_name}}
Address : {{witness_address}}
Purpose / Documents to Produce : {{witness_purpose}}

The said witness cannot attend this Hon'ble Court without the issuance of summons. It is therefore prayed that this Hon'ble Court may be pleased to issue witness summons to the above-named witness to depose and/or produce documents in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 14. Samadhan Purshish (Compromise Purshis)
    {
        "base_key": "samadhan_purshish",
        "aliases": ["samadhan", "compromise", "settlement", "સમાધાન", "પુરશિસ સમાધાન"],
        "name_gu": "સમાધાન પુરશિસ (Compromise Purshis)",
        "name_en": "Compromise Purshis (Settlement Terms)",
        "category": "Civil",
        "description": "Joint purshis submitted by both parties recording amicable settlement and terms of compromise.",
        "fields": [
            {"key": "settlement_terms", "label_en": "Terms and conditions of compromise", "label_gu": "સમાધાનની શરતો તથા વિગતો", "type": "textarea", "required": True},
            {"key": "prayer_disposal", "label_en": "Prayer for disposal / acquittal", "label_gu": "કેસ નિકાલ અંગેની માંગણી", "type": "text", "required": False, "default_value": "સદર કેસ સમાધાનના આધારે આખરી નિકાલ કરવાનો હુકમ કરવા વિનંતી છે."},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- બંને પક્ષકારો વચ્ચે સમાધાન થયેલ હોવા અંગેની પુરશિસ...

સદર કામમાં બંને પક્ષકારો તેમજ તેઓના એડવોકેટશ્રીઓ આપ નામદાર કોર્ટ સમક્ષ નમ્રતાપૂર્વક સંયુક્ત પુરશિસ રજૂ કરે છે કે...

સદર કામમાં બંને પક્ષકારો વચ્ચે વડીલો તથા મિત્રોની દરમિયાનગીરીથી સુખદ સમાધાન થઈ ગયેલ છે. બંને પક્ષકારો હવે એકબીજા સામે કોઈ પ્રકારનો વાંધો કે તકરાર ધરાવતા નથી. સમાધાનની શરતો નીચે મુજબ છે:

સમાધાનની શરતો:
{{settlement_terms}}

બંને પક્ષકારોએ કોઈપણ જાતના ડર, ધાકધમકી કે અયોગ્ય દબાણ વગર પોતાની રાજીખુશીથી આ સમાધાન સ્વીકારેલ છે. {{prayer_disposal}}

તેથી ન્યાયના હિતમાં આ સમાધાન પુરશિસ રેકર્ડ પર લઈ સદર કેસનો સુખદ નિકાલ કરવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{party_role}} / એડવોકેટ               {{opposite_party_role}} / એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: COMPROMISE PURSHIS / SETTLEMENT TERMS

In the above matter, both the parties and their respective advocates most respectfully submit this joint purshis before this Hon'ble Court that:

Through the intervention of elders, common friends and well-wishers, both the parties have arrived at an amicable and full settlement of all disputes involved in this matter. Neither party has any grievance or claim against the other. The terms of compromise are as follows:

Terms of Settlement:
{{settlement_terms}}

The parties have entered into this compromise voluntarily, with free consent and without any force, coercion or undue influence. {{prayer_disposal}}

It is therefore prayed that this Hon'ble Court may be pleased to record this compromise purshis and dispose of the proceedings in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

{{party_role}} / Advocate             {{opposite_party_role}} / Advocate
""",
    },

    # 15. Ulat Tapas no Haq Bandh Karavani Arji
    {
        "base_key": "ulat_tapas_no_haq_bandh_karavani_arji",
        "aliases": ["ulat_tapas_bandh", "close cross examination", "ઉલટતપાસ બંધ", "હક બંધ ઉલટતપાસ"],
        "name_gu": "ઉલટતપાસનો હક્ક બંધ કરવાની અરજી",
        "name_en": "Application to Close Cross-Examination Right",
        "category": "General",
        "description": "Application to close the right of cross-examination due to repeated delay and absence of opposite party.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Plaintiff / Complainant side", "label_gu": "વાદી / ફરિયાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "સામાવાળા તરફથી"},
             ]},
            {"key": "witness_name", "label_en": "Name of witness whose cross-examination right to close", "label_gu": "જે સાક્ષીની ઉલટતપાસનો હક બંધ કરવાનો છે તેનું નામ", "type": "text", "required": True},
            {"key": "delay_reasons", "label_en": "Grounds and delays", "label_gu": "હક્ક બંધ કરવાના કારણો (વિગત)", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- સાક્ષીની ઉલટતપાસ કરવાનો હક્ક બંધ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં સાક્ષી {{witness_name}} ની સરતપાસ પૂર્ણ થયેલ છે અને કેસ ઉલટતપાસ માટે નિયત થયેલ છે. સામા પક્ષકારને પૂરતી તકો આપવા છતાં તેઓ વારંવાર મુદ્દતો માંગી ઉલટતપાસ કરતા નથી અને કેસ વિલંબિત કરવાનો પ્રયાસ કરે છે. {{delay_reasons}}

સાક્ષી વારંવાર કોર્ટમાં હાજર રહેવા છતાં સામા પક્ષકાર ઉલટતપાસ કરતા ન હોવાથી સાક્ષીનો કિંમતી સમય વેડફાય છે. જેથી ન્યાયના હિતમાં સાક્ષી {{witness_name}} ની ઉલટતપાસ કરવાનો સામા પક્ષકારનો હક્ક બંધ કરવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO CLOSE RIGHT OF CROSS-EXAMINATION

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The examination-in-chief of witness {{witness_name}} has been completed, and the matter was posted for cross-examination. Despite repeated opportunities, the opposite party has failed to cross-examine the witness and is continuously taking adjournments with a view to delay the proceedings. {{delay_reasons}}

The witness has attended the court repeatedly at considerable personal inconvenience. It is therefore prayed in the interest of justice that this Hon'ble Court may be pleased to close the right of cross-examination of witness {{witness_name}}.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 16. Ulat Tapas no Haq Kholvani Arji (Reopen Cross-Examination)
    {
        "base_key": "ulat_tapas_no_haq_kholvani_arji",
        "aliases": ["ulat_tapas_khol", "reopen cross examination", "ઉલટતપાસ ખોલવા", "હક ખોલવો ઉલટતપાસ"],
        "name_gu": "ઉલટતપાસનો હક્ક ખોલવાની અરજી",
        "name_en": "Application to Reopen Cross-Examination Right",
        "category": "General",
        "description": "Application to reopen the closed right of cross-examination and recall witness.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "સામાવાળા / આરોપી તરફથી"},
                 {"value": "party", "label_en": "Plaintiff / Complainant side", "label_gu": "વાદી / ફરિયાદી તરફથી"},
             ]},
            {"key": "witness_name", "label_en": "Name of witness to cross-examine", "label_gu": "જે સાક્ષીની ઉલટતપાસ કરવાની છે તેનું નામ", "type": "text", "required": True},
            {"key": "reopen_reason", "label_en": "Reason for default in cross-examination", "label_gu": "ઉલટતપાસ ન થઈ શકવાનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "વકીલશ્રીની અચાનક માંદગીના કારણે", "label_en": "Sudden illness of advocate", "label_gu": "વકીલશ્રીની અચાનક માંદગીના કારણે"},
                 {"value": "કુટુંબમાં અવસાન / શોકના કારણે", "label_en": "Bereavement in family", "label_gu": "કુટુંબમાં અવસાન / શોકના કારણે"},
                 {"value": "અનિવાર્ય સંજોગોમાં બહારગામ હોવાના કારણે", "label_en": "Unavoidably out of station", "label_gu": "અનિવાર્ય સંજોગોમાં બહારગામ હોવાના કારણે"},
                 {"value": "other", "label_en": "Other material reason", "label_gu": "અન્ય અગત્યનું કારણ"},
             ]},
            {"key": "reopen_reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "reopen_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- સાક્ષીની ઉલટતપાસ કરવાનો હક્ક ફરીથી ખોલવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસમાં આપ નામદાર કોર્ટે સાક્ષી {{witness_name}} ની ઉલટતપાસ કરવાનો અમારો હક્ક બંધ કરેલ છે. પાછલી મુદતે {{reopen_reason}} અમારાથી ઉલટતપાસ થઈ શકેલ ન હતી. ગેરહાજરી જાણીબુઝીને ન હતી પરંતુ અનિવાર્ય સંજોગોના કારણે હતી.

સદર સાક્ષીની ઉલટતપાસ કેસના ન્યાયિક નિર્ણય અને અમારા પક્ષકારના બચાવ માટે અતિ મહત્વપૂર્ણ છે. અમો સાક્ષીને સમન્સનો ખર્ચ ભોગવવા તૈયાર છીએ. જેથી ન્યાયના હિતમાં સાક્ષી {{witness_name}} ની ઉલટતપાસ કરવાનો હક્ક ફરીથી ખોલવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO REOPEN RIGHT OF CROSS-EXAMINATION

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

In the said case, this Hon'ble Court was pleased to close our right to cross-examine witness {{witness_name}}. On the previous date, cross-examination could not be conducted due to {{reopen_reason}}. The default was neither intentional nor deliberate.

Cross-examination of the said witness is crucial and indispensable for establishing the defense of the applicant. The applicant is willing to bear any costs for recalling the witness. It is therefore prayed that this Hon't Court may be pleased to recall witness {{witness_name}} and reopen our right of cross-examination in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 17. Undertaking
    {
        "base_key": "undertaking",
        "aliases": ["bahedhari", "undertaking purshis", "બાંહેધરી", "બાહેધરી પત્રક"],
        "name_gu": "બાંહેધરી પત્રક (Undertaking)",
        "name_en": "Written Undertaking / Purshis",
        "category": "General",
        "description": "Formal written undertaking submitted to the court promising compliance with judicial conditions.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "undertaking_subject", "label_en": "Subject / condition of undertaking", "label_gu": "બાંહેધરીની બાબત / શરત", "type": "text", "required": True},
            {"key": "undertaking_details", "label_en": "Full details of undertaking / action to perform", "label_gu": "કરવાની કાર્યવાહી / બાંહેધરીની સંપૂર્ણ વિગત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- બાંહેધરી પત્રક રજૂ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટ આપ નામદાર કોર્ટ સમક્ષ નમ્રતાપૂર્વક આ બાંહેધરી પત્રક રજૂ કરીએ છીએ કે...

સદર કામમાં આપ નામદાર કોર્ટ દ્વારા ફરમાવેલ શરત / {{undertaking_subject}} ના અનુસંધાને અમારા પક્ષકાર તરફથી આપ નામદાર કોર્ટ સમક્ષ નીચે મુજબની બાંહેધરી આપવામાં આવે છે:

બાંહેધરીની વિગતો:
{{undertaking_details}}

અમો ખાતરી આપીએ છીએ કે ઉપર જણાવેલ બાંહેધરીનું ચુસ્તપણે પાલન કરવામાં આવશે. તેથી ન્યાયના હિતમાં આ બાંહેધરી પત્રક રેકર્ડ પર સ્વીકારવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: WRITTEN UNDERTAKING / PURSHIS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit this written undertaking before this Hon'ble Court that:

In compliance with the directions of this Hon'ble Court regarding {{undertaking_subject}}, the applicant hereby gives the following unconditional undertaking:

Details of Undertaking:
{{undertaking_details}}

The applicant assures this Hon'ble Court that the undertaking stated herein shall be scrupulously adhered to. It is therefore prayed that this written undertaking be taken on record in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 18. Vakilatnama Civil
    {
        "base_key": "vakilatnama_civil",
        "aliases": ["vakalatnama", "civil vakalatnama", "વકીલાતનામું", "સિવિલ વકીલાતનામું"],
        "name_gu": "વકીલાતનામું (સિવિલ)",
        "name_en": "Vakalatnama (Civil Matters)",
        "category": "Civil",
        "description": "Formal legal vakalatnama empowering an advocate to represent a client in civil proceedings.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે વકીલાતનામું", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Plaintiff / Applicant side", "label_gu": "વાદી / અરજદાર તરફથી"},
                 {"value": "opposite", "label_en": "Defendant / Opponent side", "label_gu": "પ્રતિવાદી / સામાવાળા તરફથી"},
             ]},
            {"key": "advocate_name", "label_en": "Advocate Name", "label_gu": "વકીલશ્રીનું નામ", "type": "text", "required": True},
            {"key": "advocate_qualification", "label_en": "Advocate Qualification", "label_gu": "લાયકાત", "type": "text", "required": False, "default_value": "B.Com., LL.B., Advocate"},
            {"key": "advocate_address", "label_en": "Office Address", "label_gu": "ઓફિસનું સરનામું", "type": "textarea", "required": True},
            {"key": "advocate_mobile", "label_en": "Mobile Number", "label_gu": "મોબાઇલ નંબર", "type": "text", "required": False},
            {"key": "advocate_enrollment_no", "label_en": "Bar Council Enrollment No.", "label_gu": "સનદ નંબર", "type": "text", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
મોબાઇલ નં. {{advocate_mobile}}  |  સનદ નં. {{advocate_enrollment_no}}

મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

વકીલાતનામું (સિવિલ)

જાણો કે સદરહુ કામમાં અમો નીચે સહી કરનાર {{selected_party_role}} અમારા તરફથી સદર કામ ચલાવવા તથા દલીલ કરવા સારું આ કામમાં વકીલ તરીકે શ્રી {{advocate_name}} ને રોકીએ છીએ. સદરહુ વકીલશ્રી આ કામમાં અમારા તરફથી હાજર થઈ દાવાઅરજી, જવાબ, એફિડેવિટ, અપીલ, રિવિઝન, દસ્તાવેજો રજૂ કરવા તથા પરત લેવા, સમાધાન કરવા, પૈસા મેળવવા તથા પાવતી આપવા બાબતે અમારા કાયદેસરના તમામ અધિકારો ભોગવશે અને તેઓ જે કંઈ કામ કરશે તે જાણે અમોએ રૂબરૂ હાજર રહીને કર્યું હોય તેટલું જ અમને કબૂલ અને મંજૂર રહેશે. જેની ખાતરી બદલ આ વકીલાતનામું સહી કરી આપ્યું છે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

પક્ષકારની સહી : ________________________

હું સદર વકીલાતનામું સ્વીકારું છું.
{{advocate_name}}
એડવોકેટ
""",
        "content_en": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
Mobile: {{advocate_mobile}}  |  Enrollment No.: {{advocate_enrollment_no}}

IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

VAKALATNAMA (CIVIL)

Know all men by these presents that I/we, the undersigned {{selected_party_role}}, do hereby appoint, nominate and constitute Shri {{advocate_name}}, Advocate, to be our true and lawful advocate in the above matter. The said advocate is empowered to appear, plead, act, file plaints, written statements, affidavits, appeals, revisions, produce and withdraw documents, enter into compromise, receive money and grant receipts, and perform all necessary legal acts on our behalf. All acts done by the said advocate shall be ratified and confirmed as if done by us personally.

In witness whereof, we have executed this Vakalatnama.

Date : {{date_display}}
Place : {{taluka_place}}

Signature of Client: ________________________

I accept this Vakalatnama.
{{advocate_name}}
Advocate
""",
    },

    # 19. Vakilatnama Criminal
    {
        "base_key": "vakilatnama_criminal",
        "aliases": ["criminal vakalatnama", "ક્રિમિનલ વકીલાતનામું"],
        "name_gu": "વકીલાતનામું (ક્રિમિનલ)",
        "name_en": "Vakalatnama (Criminal Matters)",
        "category": "Criminal",
        "description": "Formal legal vakalatnama empowering an advocate to defend or represent a party in criminal proceedings.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે વકીલાતનામું", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Accused side", "label_gu": "આરોપી તરફથી"},
                 {"value": "party", "label_en": "Complainant side", "label_gu": "ફરિયાદી તરફથી"},
             ]},
            {"key": "advocate_name", "label_en": "Advocate Name", "label_gu": "વકીલશ્રીનું નામ", "type": "text", "required": True},
            {"key": "advocate_qualification", "label_en": "Advocate Qualification", "label_gu": "લાયકાત", "type": "text", "required": False, "default_value": "B.Com., LL.B., Advocate"},
            {"key": "advocate_address", "label_en": "Office Address", "label_gu": "ઓફિસનું સરનામું", "type": "textarea", "required": True},
            {"key": "advocate_mobile", "label_en": "Mobile Number", "label_gu": "મોબાઇલ નંબર", "type": "text", "required": False},
            {"key": "advocate_enrollment_no", "label_en": "Bar Council Enrollment No.", "label_gu": "સનદ નંબર", "type": "text", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
મોબાઇલ નં. {{advocate_mobile}}  |  સનદ નં. {{advocate_enrollment_no}}

મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

વકીલાતનામું (ક્રિમિનલ)

જાણો કે સદરહુ ફોજદારી કામમાં અમો નીચે સહી કરનાર {{selected_party_role}} અમારા તરફથી સદર કામ ચલાવવા સારું વકીલ તરીકે શ્રી {{advocate_name}} ને રોકીએ છીએ. સદરહુ વકીલશ્રી આ કામમાં અમારા તરફથી હાજર થઈ જામીન અરજી, હાજરી માફી, પુરાવો રજૂ કરવા, ઉલટતપાસ કરવા, અપીલ, રિવિઝન કરવા તથા અમારા બચાવ માટે કાયદેસરના તમામ કાર્યો કરવા અધિકૃત રહેશે. તેઓ જે કંઈ કાર્ય કરશે તે અમને કબૂલ અને મંજૂર રહેશે. જેની ખાતરી બદલ આ વકીલાતનામું સહી કરી આપ્યું છે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

પક્ષકારની સહી : ________________________

હું સદર વકીલાતનામું સ્વીકારું છું.
{{advocate_name}}
એડવોકેટ
""",
        "content_en": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
Mobile: {{advocate_mobile}}  |  Enrollment No.: {{advocate_enrollment_no}}

IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

VAKALATNAMA (CRIMINAL)

Know all men by these presents that I/we, the undersigned {{selected_party_role}}, do hereby appoint, nominate and constitute Shri {{advocate_name}}, Advocate, to be our true and lawful advocate in the above criminal proceedings. The said advocate is empowered to appear, plead, act, file bail applications, exemption applications, lead evidence, cross-examine witnesses, file appeals/revisions, and do all lawful acts necessary for our defense. All acts done by the said advocate shall be ratified and confirmed as if done by us personally.

In witness whereof, we have executed this Vakalatnama.

Date : {{date_display}}
Place : {{taluka_place}}

Signature of Client: ________________________

I accept this Vakalatnama.
{{advocate_name}}
Advocate
""",
    },

    # 20. Warrant no Hath-bido Apvani Arji
    {
        "base_key": "warrant_no_hath_bido_apvani_arji",
        "aliases": ["warrant_hathbido", "hathbido", "direct service", "હાથબીડો", "સમન્સ હાથબીડો"],
        "name_gu": "સમન્સ / વોરંટનો હાથબીડો આપવા બાબતની અરજી",
        "name_en": "Application for Direct Service / Handing Over Summons or Warrant",
        "category": "Criminal",
        "description": "Application to hand over summons or warrant directly to advocate/complainant for prompt service through police.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Complainant / Applicant side", "label_gu": "ફરિયાદી / અરજદાર તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "સામાવાળા તરફથી"},
             ]},
            {"key": "warrant_kind", "label_en": "Type of process / warrant", "label_gu": "ક્યા પ્રકારનો હાથબીડો જોઈએ છે", "type": "select", "required": True,
             "options": [
                 {"value": "સમન્સ", "label_en": "Summons", "label_gu": "સમન્સ"},
                 {"value": "જામીનપાત્ર (બેલેબલ) વોરંટ", "label_en": "Bailable Warrant", "label_gu": "જામીનપાત્ર (બેલેબલ) વોરંટ"},
                 {"value": "બિનજામીનપાત્ર (નોન-બેલેબલ) વોરંટ", "label_en": "Non-Bailable Warrant", "label_gu": "બિનજામીનપાત્ર (નોન-બેલેબલ) વોરંટ"},
             ]},
            {"key": "target_party", "label_en": "Person against whom process is issued", "label_gu": "કોનો સમન્સ/વોરંટ લેવાનો છે તેની વિગત", "type": "text", "required": True},
            {"key": "service_reason", "label_en": "Grounds for direct service / handing over", "label_gu": "હાથબીડો આપવાનું કારણ", "type": "textarea", "required": False, "default_value": "પોલીસ સ્ટેશન મારફતે ત્વરિત બજવણી કરાવી શકાય તે સારું હાથબીડો આપવો જરૂરી છે."},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- {{warrant_kind}} નો હાથબીડો આપવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં {{target_party}} સામે {{warrant_kind}} કાઢવાનો હુકમ ફરમાવેલ છે. સદર {{warrant_kind}} ની સંબંધિત પોલીસ સ્ટેશન મારફતે યોગ્ય અને ત્વરિત બજવણી થઈ શકે તે સારૂ અમારા પક્ષકારને તેનો હાથબીડો આપવો અત્યંત જરૂરી છે. {{service_reason}}

જેથી ન્યાયના હિતમાં {{target_party}} સામેનો {{warrant_kind}} અમારા પક્ષકાર/વકીલશ્રીને હાથબીડા મારફત આપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR HANDING OVER SUMMONS / WARRANT FOR DIRECT SERVICE

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. An order has been passed for the issuance of {{warrant_kind}} against {{target_party}}. In order to ensure effective, expeditious and direct service through the concerned police station, it is necessary that the process be handed over directly to our client / advocate. {{service_reason}}

It is therefore prayed in the interest of justice that this Hon'ble Court may be pleased to hand over the {{warrant_kind}} issued against {{target_party}} to our client / advocate for service.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },

    # 21. Warrant Rad Karvani Arji (Cancellation of Warrant)
    {
        "base_key": "warrant_rad_karvani_arji",
        "aliases": ["warrant_rad", "cancel warrant", "recall warrant", "વોરંટ રદ", "વોરંટ રીકોલ"],
        "name_gu": "વોરંટ રદ કરવાની અરજી",
        "name_en": "Application for Cancellation / Recall of Warrant",
        "category": "Criminal",
        "description": "Application to cancel or recall a warrant issued against the accused on showing bona fide cause.",
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "opposite", "label_en": "Accused side", "label_gu": "આરોપી તરફથી"},
                 {"value": "party", "label_en": "Applicant side", "label_gu": "અરજદાર તરફથી"},
             ]},
            {"key": "warrant_date", "label_en": "Date of warrant issuance", "label_gu": "વોરંટ નીકળ્યા તારીખ", "type": "text", "required": True},
            {"key": "absence_reason", "label_en": "Reason for absence", "label_gu": "ગેરહાજરીનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "સમન્સ / નોટિસની બજવણી થયેલ ન હોવાથી", "label_en": "No service of summons or notice", "label_gu": "સમન્સ / નોટિસની બજવણી થયેલ ન હોવાથી"},
                 {"value": "અનિવાર્ય માંદગીના કારણોસર", "label_en": "Unavoidable illness", "label_gu": "અનિવાર્ય માંદગીના કારણોસર"},
                 {"value": "કામ સબબ બહારગામ હોવાથી", "label_en": "Out of station for urgent work", "label_gu": "કામ સબબ બહારગામ હોવાથી"},
                 {"value": "other", "label_en": "Other grounds", "label_gu": "અન્ય અગત્યનું કારણ"},
             ]},
            {"key": "absence_reason_other", "label_en": "Specify other reason", "label_gu": "અન્ય કારણ જણાવો", "type": "text", "required": False, "depends_on": "absence_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- વોરંટ રદ / રીકોલ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસમાં આપ નામદાર કોર્ટ દ્વારા તારીખ {{warrant_date}} ના રોજ અમારા પક્ષકાર સામે વોરંટ કાઢવાનો હુકમ ફરમાવેલ છે. અમારા પક્ષકાર {{absence_reason}} આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકેલ ન હતા. અમારા પક્ષકાર કાયદાનું સન્માન કરનાર નાગરિક છે અને જાણીબુઝીને ગેરહાજર રહેલ નથી.

અમારા પક્ષકાર આજ રોજ કોર્ટ સમક્ષ રૂબરૂ હાજર થયેલ છે અને કેસની તમામ મુદ્દતોએ નિયમિત હાજર રહેવાની બાંહેધરી આપે છે. જેથી ન્યાયના હિતમાં અમારા પક્ષકાર સામે નીકળેલ વોરંટ રદ / રીકોલ કરવાનો દયાળુ હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR CANCELLATION / RECALL OF WARRANT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

In the said case, this Hon'ble Court was pleased to issue a warrant against the applicant on {{warrant_date}}. The applicant was unable to attend the court due to {{absence_reason}}. The absence was neither willful nor intentional.

The applicant is a law-abiding citizen, has voluntarily surrendered before this Hon'ble Court today, and undertakes to remain present on all future dates of hearing. It is therefore prayed that this Hon'ble Court may be pleased to cancel / recall the warrant issued against the applicant in the interest of justice.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate for {{selected_party_role}}
""",
    },
]


def build_42_templates():
    """Generate all 42 templates (21 Gujarati + 21 English)."""
    templates = []
    
    for item in BASE_TEMPLATES:
        base_key = item["base_key"]
        
        # 1. Gujarati Template (<base_key>_gu)
        gu_tpl = {
            "id": f"{base_key}_gu",
            "slug": f"{base_key}_gu",
            "base_key": base_key,
            "language": "gu",
            "name_gu": item["name_gu"],
            "name_en": item["name_en"],
            "category": item["category"],
            "sub_category": item.get("sub_category"),
            "description": item["description"],
            "tags": [item["category"].lower(), "gujarati", "court", "application"],
            "aliases": item["aliases"] + [base_key, f"{base_key}_gu"],
            "case_types": [],
            "courts": [],
            "jurisdiction": "gujarat",
            "fields": copy.deepcopy(item["fields"]),
            "content_gu": item["content_gu"],
            "content_en": item["content_en"],
            "settings": copy.deepcopy(DEFAULT_SETTINGS),
            "status": "published",
            "version": 1,
            "locked": False,
            "source": "system",
            "created_by": "system",
            "updated_by": "system",
            "created_at": NOW_ISO,
            "updated_at": NOW_ISO,
            "published_at": NOW_ISO,
        }
        templates.append(gu_tpl)
        
        # 2. English Template (<base_key>_en)
        en_fields = copy.deepcopy(item["fields"])
        en_tpl = {
            "id": f"{base_key}_en",
            "slug": f"{base_key}_en",
            "base_key": base_key,
            "language": "en",
            "name_gu": item["name_gu"],
            "name_en": item["name_en"],
            "category": item["category"],
            "sub_category": item.get("sub_category"),
            "description": item["description"],
            "tags": [item["category"].lower(), "english", "court", "application"],
            "aliases": item["aliases"] + [base_key, f"{base_key}_en"],
            "case_types": [],
            "courts": [],
            "jurisdiction": "all",
            "fields": en_fields,
            "content_gu": item["content_gu"],
            "content_en": item["content_en"],
            "settings": copy.deepcopy(DEFAULT_SETTINGS),
            "status": "published",
            "version": 1,
            "locked": False,
            "source": "system",
            "created_by": "system",
            "updated_by": "system",
            "created_at": NOW_ISO,
            "updated_at": NOW_ISO,
            "published_at": NOW_ISO,
        }
        templates.append(en_tpl)
        
    return templates


TEMPLATES_42 = build_42_templates()

if __name__ == "__main__":
    print(f"Total templates generated: {len(TEMPLATES_42)}")
    for i, t in enumerate(TEMPLATES_42, 1):
        print(f"{i:2d}. {t['id']:35s} | lang={t['language']} | fields={len(t['fields'])} | name_gu={t['name_gu'][:20]} | name_en={t['name_en'][:25]}")
