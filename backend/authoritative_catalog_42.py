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
  4. Authoritative Gujarati legal draft with {{placeholders}} character-for-character from source ODT.
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
    {
        "base_key": "aanke_padvani_arji",
        "aliases": ["aanke", "exhibit", "દસ્તાવેજને આંકે પાડવાની અરજી", "આંક", "આંક પાડવાની અરજી"],
        "name_gu": "આંક પાડવાની અરજી",
        "name_en": "Application to Exhibit Document",
        "category": "General",
        "description": "Application to mark/assign exhibit numbers to documents produced on record.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'document_details', 'label_en': 'Document details to be exhibited', 'label_gu': 'ક્યા દસ્તાવેજને આંક પાડવાના તેની વિગત', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
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

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO EXHIBIT DOCUMENT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. In the said case, {{document_details}} is of great significance and is necessary for the proper adjudication of the case. As it is in the interest of justice to take the said document on record as evidence, it is prayed that this Hon'ble Court may be pleased to take the said document on record and assign appropriate exhibit number to it.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "certified_report",
        "aliases": ["certified copy", "પ્રમાણિત નકલ", "pramanit nakal", "નકલ", "સર્ટિફાઇડ રિપોર્ટ", "inspection"],
        "name_gu": "સર્ટિફાઇડ રિપોર્ટ / નકલ મેળવવાની અરજી",
        "name_en": "Application for Certified Copy / Inspection Report",
        "category": "General",
        "description": "Application for certified copies of judicial orders, evidence, or inspection reports.",
        "fields": [
            {'key': 'presiding_officer', 'label_en': 'Presiding officer designation / name', 'label_gu': 'પીઠાશીન અધિકારીશ્રીનું નામ / હોદ્દો', 'type': 'text', 'required': False},
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'other', 'label_en': 'Third party / Other', 'label_gu': 'ત્રીજા પક્ષકાર / અન્ય'}]},
            {'key': 'advocate_other', 'label_en': 'If other, specify party', 'label_gu': 'અન્ય પક્ષકારની વિગત', 'type': 'text', 'required': False, 'depends_on': 'advocate_side=other'},
            {'key': 'copy_type', 'label_en': 'Type of copy requested', 'label_gu': 'માગેલ નકલનો પ્રકાર', 'type': 'select', 'required': True, 'options': [{'value': 'સર્ટિફાઇડ નકલ', 'label_en': 'Certified Copy', 'label_gu': 'સર્ટિફાઇડ નકલ'}, {'value': 'ઇન્સ્પેક્શન રિપોર્ટ', 'label_en': 'Inspection Report', 'label_gu': 'ઇન્સ્પેક્શન રિપોર્ટ'}, {'value': 'other', 'label_en': 'Other copy type', 'label_gu': 'અન્ય નકલનો પ્રકાર'}]},
            {'key': 'copy_type_other', 'label_en': 'If other, specify copy type', 'label_gu': 'અન્ય નકલ પ્રકારની વિગત', 'type': 'text', 'required': False, 'depends_on': 'copy_type=other'},
            {'key': 'document_details', 'label_en': 'Details of documents requested', 'label_gu': 'માંગેલ દસ્તાવેજની વિગત', 'type': 'textarea', 'required': True},
            {'key': 'representative_name', 'label_en': 'Representative authorized to collect copy (if any)', 'label_gu': 'નકલ મેળવવા અધિકૃત પ્રતિનિધિનું નામ (જો હોય તો)', 'type': 'text', 'required': False},
            {'key': 'urgency', 'label_en': 'Urgency', 'label_gu': 'અરજીનો પ્રકાર (તાકીદ)', 'type': 'select', 'required': True, 'options': [{'value': 'સાદી', 'label_en': 'Ordinary (સાદી)', 'label_gu': 'સાદી'}, {'value': 'અર્જન્ટ', 'label_en': 'Urgent (અર્જન્ટ)', 'label_gu': 'અર્જન્ટ'}]},
            {'key': 'reason_for_copy', 'label_en': 'Reason for requiring copy', 'label_gu': 'નકલ મેળવવાનું કારણ', 'type': 'text', 'required': False},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}
{{presiding_officer}}
{{case_type}} નં. : {{case_number}}
{{police_station_crime_no}}
{{hearing_or_disposal_date}}
{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત : પ્રમાણિત નકલ મેળવવા બાબત...

અમો નીચે સહી કરનાર એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે....

સદર કેસમાંથી અમોને નીચે જણાવેલ દસ્તાવેજની સહી-સિક્કાવાળી પ્રમાણિત નકલની અભ્યાસ તેમજ ન્યાયિક કાર્યવાહી અર્થે જરૂરિયાત હોય, નીચે મુજબની સહિ-સિક્કાવાળી પ્રમાણિત નકલ કુલ નંગ તાત્કાલીક આપવા મહેરબાની કરશોજી.

માંગેલ દસ્તાવેજ ની વિગત
{{document_details}}

સદર નકલ અમો નીચે સહી કરનારને અથવા અમારા વતી {{representative_name}} ને આપશોજી. જે નકલ માટે ડિપોઝિટ પેટે રૂ. જમા કરાવેલ છે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

-------------------
{{advocate_name}}
{{advocate_mobile}}""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}
{{presiding_officer}}
{{case_type}} No. : {{case_number}}
{{police_station_crime_no}}
{{hearing_or_disposal_date}}
{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR OBTAINING CERTIFIED COPY

We, the undersigned advocate, most respectfully submit before this Hon'ble Court that:

In the said case, the certified copy with official seal and signature of the documents mentioned below is required for study and judicial proceedings. It is therefore prayed that this Hon'ble Court may be pleased to urgently issue certified copies with official seal and signature of the following documents:

Details of Documents Requested:
{{document_details}}

The said certified copy may kindly be delivered to the undersigned or to {{representative_name}} on our behalf. Towards deposit for the copy, Rs. has been deposited.

Date : {{date_display}}
Place : {{taluka_place}}

-------------------
{{advocate_name}}
{{advocate_mobile}}""",
    },
    {
        "base_key": "closing_purshish",
        "aliases": ["closing", "purshis", "પુરાવો બંધ", "પુરશીશ", "closure of evidence"],
        "name_gu": "પુરાવો બંધ પુરશિસ",
        "name_en": "Closing Purshis (Closure of Evidence)",
        "category": "General",
        "description": "Purshis submitted to formally close oral and documentary evidence on behalf of a party.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

ક્લોઝિંગ પુરસીસ

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટ પુરસીસ થી જાહેર કરીએ છીએ કે...

સદર કામ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{selected_party_role}} તરફથી જરૂરી પુરાવા તથા રજૂઆતો પૂર્ણ કરવામાં આવેલ છે અને હવે અમારા તરફથી વધુ કોઈ પુરાવા કે રજૂઆત કરવાની ન હોય, સદર પક્ષકાર તરફનો પુરાવાનો સ્ટેજ બંધ ગણાવી સદર કેસમાં આગળની કાર્યવાહી કરવા તથા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

CLOSING PURSHIS

In the above matter, we, the advocate for {{selected_party_role}}, hereby declare by this purshis before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. On behalf of {{selected_party_role}}, the necessary evidence and submissions have been completed and no further evidence or submissions are to be made on our behalf. It is therefore prayed that this Hon'ble Court may be pleased to close the stage of evidence on behalf of the said party and pass appropriate orders to proceed further in the case.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "dd_karavani_arji",
        "aliases": ["dd", "dismiss in default", "ડિસમિસ", "ડિસમિસ ઇન ડિફોલ્ટ", "ડી.ડી."],
        "name_gu": "ડી.ડી. કરાવવા અંગેની અરજી (ડિસમિસ ઇન ડિફોલ્ટ)",
        "name_en": "Application for Dismissal in Default (D.D.)",
        "category": "Civil",
        "description": "Application to dismiss case due to non-prosecution or absence of complainant/plaintiff.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Opposite party / Respondent side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}]},
            {'key': 'case_or_suit', 'label_en': 'Case or Suit', 'label_gu': 'કેસ અથવા દાવો', 'type': 'select', 'required': True, 'options': [{'value': 'કેસ', 'label_en': 'Case', 'label_gu': 'કેસ'}, {'value': 'દાવો', 'label_en': 'Suit', 'label_gu': 'દાવો'}]},
            {'key': 'dismiss_reason', 'label_en': 'Reason / grounds for dismissal', 'label_gu': 'ડિસમીસ કરવાના કારણો (દા.ત. ફરીયાદી મુદ્દતે હાજર રહેતા નથી...)', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- {{case_or_suit}} ડિસમીસ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કામમાં {{dismiss_reason}} હોવાથી સદર કેસ આગળ ચલાવવાની જરૂરિયાત રહેતી નથી.

વધુમા આવા ખોટા કેસ ડિસમીસ કરવામાં આવે તે ન્યાયના હિતમાં હોય, જેથી સદર કેસ ડિસમીસ કરી આગળની કાર્યવાહી પૂર્ણ કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO DISMISS {{case_or_suit}}

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. In the said matter, as {{dismiss_reason}}, there remains no necessity to proceed further with the said case.

Furthermore, it is in the interest of justice that such false cases be dismissed. It is therefore prayed that this Hon'ble Court may be pleased to dismiss the said case and pass appropriate orders to conclude further proceedings.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "document_parat_levani_arji",
        "aliases": ["document_return", "parat", "return document", "દસ્તાવેજ પરત", "પરત મેળવવા"],
        "name_gu": "દસ્તાવેજ પરત મેળવવા બાબતની અરજી",
        "name_en": "Application for Return of Documents",
        "category": "General",
        "description": "Application to return original documents produced on court record with undertaking.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'case_status_phrase', 'label_en': 'Case Status (Ongoing / Completed)', 'label_gu': 'કેસની સ્થિતિ (ચાલુ / પૂર્ણ થયેલ)', 'type': 'select', 'required': True, 'options': [{'value': 'ચાલુ', 'label_en': 'Ongoing', 'label_gu': 'ચાલુ'}, {'value': 'પૂર્ણ થયેલ', 'label_en': 'Completed / Disposed', 'label_gu': 'પૂર્ણ થયેલ'}]},
            {'key': 'document_details', 'label_en': 'Details of documents to be returned', 'label_gu': 'પરત મેળવવાના મૂળ દસ્તાવેજોની વિગત', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- દસ્તાવેજ પરત મેળવવા બાબત...

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટમા {{case_status_phrase}}. સદર કામમાં {{document_details}} રજૂ કરવામાં આવેલ, જે દસ્તાવેજની હવે કેસના હેતુ માટે જરૂરીયાત ન હોય અને અમોને તે દસ્તાવેજની ખુબ જ જરૂરીયાત હોય તેમજ દસ્તાવેજ પરત મેળવવો ન્યાયના હિતમાં હોય, જેથી સદર દસ્તાવેજ પરત આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR RETURN OF ORIGINAL DOCUMENTS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court, in which {{document_details}} have been produced. The said case being {{case_status_phrase}}, it is necessary for our client to obtain back the said documents. It is therefore prayed that this Hon'ble Court may be pleased to pass an appropriate order returning the said documents to our client.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "document_swikaravani_arji",
        "aliases": ["document_on_record", "production", "દસ્તાવેજ રજૂ", "દસ્તાવેજ સ્વીકારવા", "record par"],
        "name_gu": "દસ્તાવેજ રજૂ કરવા / સ્વીકારવાની અરજી",
        "name_en": "Application for Production and Acceptance of Documents",
        "category": "General",
        "description": "Application to produce and accept documents on court record as evidence.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'documents_produced', 'label_en': 'List of documents produced', 'label_gu': 'રજૂ કરેલ દસ્તાવેજી પુરાવાની યાદી', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- દસ્તાવેજી પુરાવા સ્વીકારી રેકર્ડ પર લેવા બાબતે...

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં આ અરજી સાથે રજુ કરેલ દસ્તાવેજી પુરાવાની જરૂરિયાત હોવાથી રજૂ કરવામાં આવે છે. સદર દસ્તાવેજી પુરાવા ન્યાયના હિતમાં હોય, અને સદર પુરાવા રેકર્ડ પર લેવાથી કેસની ન્યાયિક કાર્યવાહી કરવામાં સહાયરૂપ થશે. આથી આપ નામદાર કોર્ટ આ અરજી સાથે રજૂ કરેલ પુરાવા રેકર્ડ પર લઈ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ

બિડાણ :- {{documents_produced}}""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO ACCEPT DOCUMENTARY EVIDENCE ON RECORD

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The documentary evidence produced along with this application is necessary for the case and is being produced herewith. As the said documentary evidence is in the interest of justice and taking the said evidence on record will assist in the judicial proceedings of the case, it is therefore prayed that this Hon'ble Court may be pleased to take the evidence produced along with this application on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}

Enclosure :- {{documents_produced}}""",
    },
    {
        "base_key": "exemption_arji",
        "aliases": ["hazari_mafi_arji", "exemption", "હાજરી માફી", "mafi", "hazari mafi"],
        "name_gu": "હાજરી માફી અરજી",
        "name_en": "Application for Exemption from Personal Appearance",
        "category": "Criminal",
        "description": "Application seeking exemption from personal appearance for the accused on the date of hearing.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Accused / Respondent side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'party', 'label_en': 'Applicant / Complainant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}]},
            {'key': 'reason', 'label_en': 'Reason for absence', 'label_gu': 'ગેરહાજરીનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'અનિવાર્ય સંજોગોના', 'label_en': 'Unavoidable circumstances', 'label_gu': 'અનિવાર્ય સંજોગોના'}, {'value': 'બહારગામ ગયેલ હોવાના', 'label_en': 'Out of station', 'label_gu': 'બહારગામ ગયેલ હોવાના'}, {'value': 'માંદગીના', 'label_en': 'Due to illness', 'label_gu': 'માંદગીના'}, {'value': 'સામાજીક કાર્યોમા રોકાયેલ હોવાના', 'label_en': 'Engaged in social functions', 'label_gu': 'સામાજીક કાર્યોમા રોકાયેલ હોવાના'}, {'value': 'બીજી કોર્ટમા પણ મુદ્દત હોય જેથી બીજી કોર્ટમા ગયેલ હોવાના', 'label_en': 'Attending hearing in another court', 'label_gu': 'બીજી કોર્ટમા પણ મુદ્દત હોય જેથી બીજી કોર્ટમા ગયેલ હોવાના'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય'}]},
            {'key': 'reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- હાજરી મુક્તિ આપવા બાબત... (એક્ઝામ્પ્શન રીપોર્ટ)

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેની મુદ્દત આજ રોજની છે પરંતુ સદર કામના {{selected_party_role}} આજરોજ {{reason}} કારણોસર આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકે તેમ નથી. જેથી આજના દિવસ પૂરતી {{selected_party_role}}ની વ્યક્તિગત હાજરી માફ રાખી સદર કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR EXEMPTION FROM PERSONAL ATTENDANCE (EXEMPTION REPORT)

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The date of hearing is today, but {{selected_party_role}} is unable to remain present before this Hon'ble Court today due to {{reason}}. It is therefore prayed that this Hon'ble Court may be pleased to exempt the personal attendance of {{selected_party_role}} for today and pass appropriate orders to proceed further in the case.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "fs_no_haq_bandh_karvani_arji",
        "aliases": ["fs_haq_bandh", "further statement", "એફ.એસ.", "હક બંધ", "fs close"],
        "name_gu": "ફર્ધર સ્ટેટમેન્ટ (F.S.) હક્ક બંધ કરવાની અરજી",
        "name_en": "Application to Close Further Statement (F.S.) Right",
        "category": "Criminal",
        "description": "Application to close the right of accused to give further statement under section 313 Cr.P.C.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Complainant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'target_party_role', 'label_en': 'Party whose F.S. right to close (e.g. Accused)', 'label_gu': 'જેનો એફ.એસ. હક બંધ કરવાનો છે તે (દા.ત. આરોપી)', 'type': 'text', 'required': True, 'default': 'આરોપી'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- એફ.એસ.નો હક બંધ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{target_party_role}} નો એફ.એસ. કરવાનો હક હોવા છતાં ઘણી મુદ્દતોથી એફ. એસ. કરવા માટે આપ નામદાર કોર્ટ સમક્ષ ઉપસ્થિત થયેલ ન હોવાથી તેમજ એફ.એસ. કરવા માટે પૂરતી તક આપવામાં આવેલ હોવા છતાં તકનો ઉપયોગ કરવામાં આવેલ ન હોય તેમજ એફ. એસ. નો હક વધુ ચાલુ રાખવો ન્યાયના હિતમાં યોગ્ય ન હોવાથી {{target_party_role}} નો એફ. એસ. કરવાનો હક બંધ કરી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO CLOSE RIGHT OF FURTHER STATEMENT (F.S.)

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. Despite the right of {{target_party_role}} to give further statement (F.S.), they have not appeared before this Hon'ble Court for several dates for giving F.S., and despite sufficient opportunity having been granted to give F.S., the opportunity has not been availed. As it is not proper in the interest of justice to keep the right of F.S. continuing further, it is prayed that this Hon'ble Court may be pleased to close the right of {{target_party_role}} to give F.S. and pass appropriate orders to proceed further.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "fs_no_haq_kholvani_arji",
        "aliases": ["fs_haq_khol", "reopen fs", "એફ.એસ. ખોલવા", "fs khol", "reopen further statement"],
        "name_gu": "ફર્ધર સ્ટેટમેન્ટ (F.S.) હક્ક ખોલવાની અરજી",
        "name_en": "Application to Reopen Further Statement (F.S.) Right",
        "category": "Criminal",
        "description": "Application to reopen the closed right of accused to record further statement under section 313 Cr.P.C.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Accused / Respondent side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'party', 'label_en': 'Applicant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}]},
            {'key': 'reopen_reason', 'label_en': 'Reason for reopening F.S.', 'label_gu': 'એફ.એસ. ન થઈ શકવાનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'આરોપીના દાદા ગુજરી ગયેલ હોવાના', 'label_en': 'Bereavement in family', 'label_gu': 'આરોપીના દાદા ગુજરી ગયેલ હોવાના'}, {'value': 'આરોપીને વ્યવસાયના કામ અર્થે વિદેશ જવાનુ થયેલ હોવાના', 'label_en': 'Travelled abroad for business', 'label_gu': 'આરોપીને વ્યવસાયના કામ અર્થે વિદેશ જવાનુ થયેલ હોવાના'}, {'value': 'આરોપીના વકીલશ્રી માંદગીના કારણોસર આપ નામદાર કોર્ટમા આવી શકે તેમ ન હોવાના', 'label_en': 'Advocate was indisposed due to illness', 'label_gu': 'આરોપીના વકીલશ્રી માંદગીના કારણોસર આપ નામદાર કોર્ટમા આવી શકે તેમ ન હોવાના'}, {'value': 'આરોપી બીજા ગુન્હાના કામ અર્થે જેલ મા હોય', 'label_en': 'Accused was in custody in another matter', 'label_gu': 'આરોપી બીજા ગુન્હાના કામ અર્થે જેલ મા હોય'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય કારણ'}]},
            {'key': 'reopen_reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'reopen_reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- એફ.એસ.નો હક ફરીથી ખોલવા બાબત...

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેમા અમોનો એફ. એસ. કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે. જે {{reopen_reason}} કારણોસર એફ. એસ. થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી તેમજ યોગ્ય હોવાથી તથા એફ. એસ. કરવાની તક મળવીએ ન્યાયના હિતમા હોય, અમોનો એફ. એસ. કરવાનો હક ફરીથી ખોલી અમોને એફ.એસ. કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO REOPEN RIGHT OF FURTHER STATEMENT (F.S.)

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court, wherein our right to give further statement (F.S.) was closed by this Hon'ble Court. F.S. could not be recorded due to {{reopen_reason}}, and as the said reason is reasonable and genuine and getting an opportunity to give F.S. is in the interest of justice, it is prayed that this Hon'ble Court may be pleased to reopen our right to give F.S. and grant us an opportunity to give F.S.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "jamin_bond_swikarvani_arji",
        "aliases": ["jamin_bond", "bail bond", "જામીન બોન્ડ", "મુચરકો", "surety bond"],
        "name_gu": "જામીન બોન્ડ સ્વીકારવા બાબતની અરજી",
        "name_en": "Application for Acceptance of Bail Bond and Surety",
        "category": "Criminal",
        "description": "Application to accept bail bond and surety pursuant to bail order and issue release warrant.",
        "fields": [
            {'key': 'case_or_crime', 'label_en': 'Case No. / Police Station Crime Register No.', 'label_gu': 'કેસ / પો.સ્ટે. ગુન્હા રજીસ્ટર નંબર', 'type': 'text', 'required': True},
            {'key': 'bail_order_court', 'label_en': "Court that granted bail (Hon'ble Court / Sessions Court / High Court)", 'label_gu': 'જામીન મંજૂર કરનાર કોર્ટ (આપ નામદાર કોર્ટ / નામદાર સેસન્સ કોર્ટ / હાઈકોર્ટ)', 'type': 'text', 'required': True, 'default': 'આપ નામદાર કોર્ટ'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}
{{police_station_crime_no}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત : જામીન બોન્ડ સ્વીકારવા બાબત...

સદર કામમાં અમો આરોપીના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

ઉપરોક્ત જણાવેલ {{case_or_crime}} ના કામે {{bail_order_court}} મુજબ આરોપીને જામીન પર મુક્ત કરવાનો હુકમ કરવામાં આવેલ છે. આ હુકમના અનુસંધાને આરોપી તરફે જરૂરી જામીન બોન્ડ તથા જામીનદારના બોન્ડ રજૂ કરવામા આવે છે તે જામીન બોન્ડ તથા જામીનદારના બોન્ડ સ્વીકારી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- આરોપી ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}
{{case_type}} No. : {{case_number}}
{{police_station_crime_no}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO ACCEPT BAIL BOND

In the above matter, we, the advocate for the Accused, most respectfully submit before this Hon'ble Court that:

In connection with the abovementioned {{case_or_crime}}, an order has been passed by {{bail_order_court}} releasing the accused on bail. In pursuance of this order, the required bail bond and surety bond are submitted herewith on behalf of the accused. It is therefore prayed that this Hon'ble Court may be pleased to accept the said bail bond and surety bond and pass appropriate orders for further proceedings.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for the Accused""",
    },
    {
        "base_key": "kam_board_par_levani_arji",
        "aliases": ["kam_board", "preponement", "board par", "કામ બોર્ડ પર", "કામ બોર્ડ"],
        "name_gu": "કામ બોર્ડ પર લેવાની અરજી",
        "name_en": "Application to Take Matter on Board (Preponement)",
        "category": "General",
        "description": "Application to prepone the hearing and take the case on board on urgent grounds.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'scheduled_date', 'label_en': 'Previously scheduled next date', 'label_gu': 'કેસની આગામી નીમેલ તારીખ (દા.ત. ૨૫/૧૦/૨૦૨૬)', 'type': 'text', 'required': True},
            {'key': 'urgent_reason', 'label_en': 'Urgent reason for taking matter on board', 'label_gu': 'કામ બોર્ડ પર લેવાનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'વોરંટ રદ કરાવવાનો હોય', 'label_en': 'For cancellation of warrant', 'label_gu': 'વોરંટ રદ કરાવવાનો હોય'}, {'value': 'સમાધાન પુરશિસ રજૂ કરવી હોવાથી', 'label_en': 'For presenting compromise purshis', 'label_gu': 'સમાધાન પુરશિસ રજૂ કરવી હોવાથી'}, {'value': 'અર્જન્ટ હુકમ મેળવવા સારુ', 'label_en': 'For urgent order', 'label_gu': 'અર્જન્ટ હુકમ મેળવવા સારુ'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય કારણ'}]},
            {'key': 'urgent_reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'urgent_reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- કામ બોર્ડ પર લેવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે તેમજ કેસની આગામી તા. {{scheduled_date}} નીમવામાં આવેલ છે પરંતુ સદર કામમાં આજ રોજ {{urgent_reason}} જેથી કામ બોર્ડ પર લેવામાં આવે તે જરૂરી છે. સદર કાર્યવાહી ન્યાયના હિતમાં હોય, જેથી સદર કામને આજ રોજ બોર્ડ પર લઈ જરૂરી કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO TAKE UP MATTER ON BOARD

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court and the next date is fixed on {{scheduled_date}}. However, in the said matter today {{urgent_reason}}, hence it is necessary that the matter be taken up on board. As the said proceeding is in the interest of justice, it is prayed that this Hon'ble Court may be pleased to take up the matter on board today and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "mudat_arji",
        "aliases": ["mudat", "adjournment", "મુદ્દત", "મુદત અરજી", "adjourn"],
        "name_gu": "મુદ્દત અરજી (Adjournment Application)",
        "name_en": "Application for Adjournment (Mudat Arji)",
        "category": "General",
        "description": "Application seeking postponement/adjournment of today's court hearing date.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'reason', 'label_en': 'Reason for adjournment', 'label_gu': 'મુદ્દત માંગવાનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'માંદગીના', 'label_en': 'Due to illness', 'label_gu': 'માંદગીના'}, {'value': 'અનિવાર્ય સંજોગોના', 'label_en': 'Unavoidable circumstances', 'label_gu': 'અનિવાર્ય સંજોગોના'}, {'value': 'દસ્તાવેજી પુરાવા એકત્રિત કરવાના', 'label_en': 'Collecting documentary evidence', 'label_gu': 'દસ્તાવેજી પુરાવા એકત્રિત કરવાના'}, {'value': 'સમાધાનની વાતચીત ચાલુ હોવાના', 'label_en': 'Compromise talks ongoing', 'label_gu': 'સમાધાનની વાતચીત ચાલુ હોવાના'}, {'value': 'વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ હોવાના', 'label_en': 'Advocate busy in another court', 'label_gu': 'વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ હોવાના'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય કારણ'}]},
            {'key': 'reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- મુદ્દત આપવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેની મુદ્દત આજ રોજની છે પરંતુ સદર કામના {{selected_party_role}} આજરોજ {{reason}} કારણોસર આજરોજ આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકે તેમ ન હોઈ, સદરહુ કામમાં આજરોજ કેસ આગળ ન ચલાવવા ન્યાયના હિતમાં એક મુદ્દત આપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

------------ {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR ADJOURNMENT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. The date of hearing is today, but the {{selected_party_role}} is unable to remain present before this Hon'ble Court today due to {{reason}}, hence in the interest of justice an order may be pleased to grant an adjournment not to proceed further with the case today.

Date : {{date_display}}
Place : {{taluka_place}}

------------ Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "saaxi_ne_summons",
        "aliases": ["saaxi_summons", "witness summons", "સાક્ષી", "સમન્સ", "witness"],
        "name_gu": "સાક્ષીને સમન્સ કાઢવા બાબતની અરજી",
        "name_en": "Application for Issuance of Witness Summons",
        "category": "General",
        "description": "Application to issue court summons to call a witness for deposition or production of documents.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'witness_name', 'label_en': 'Name of witness to be summoned', 'label_gu': 'સાક્ષીનું નામ', 'type': 'text', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- સાક્ષીને સમન્સ કાઢવા બાબત...

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{witness_name}} નામના સાક્ષીની જુબાનીની જરૂરિયાત હોવાથી તેમજ સદર સાક્ષીની જુબાની કેસના ન્યાયના હિતમાં હોય અને જેનાથી કેસની યોગ્ય કાર્યવાહી કરવામાં સહાયરૂપ થાય તેમ છે. જેથી સદર {{witness_name}} નાઓને આપ નામદાર કોર્ટ સમક્ષ હાજર રહેવા માટે સમન્સ કાઢી આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO ISSUE SUMMONS TO WITNESS

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. In the said case, the testimony of witness named {{witness_name}} is required, and the testimony of the said witness is in the interest of justice and will assist in the proper conduct of the case. It is therefore prayed that this Hon'ble Court may be pleased to issue summons directing the said {{witness_name}} to remain present before this Hon'ble Court.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "samadhan_purshish",
        "aliases": ["samadhan", "compromise", "settlement", "સમાધાન", "પુરશિસ સમાધાન"],
        "name_gu": "સમાધાન પુરશિસ (Compromise Purshis)",
        "name_en": "Compromise Purshis (Settlement Terms)",
        "category": "Civil",
        "description": "Joint purshis submitted by both parties recording amicable settlement and terms of compromise.",
        "fields": [
            {'key': 'settlement_terms', 'label_en': 'Settlement terms / conditions (e.g. subject to conditions...)', 'label_gu': 'સમાધાનની શરતો (દા.ત. શરતો ને આધીન / એવી શરત ને આધીન)', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

સમાધાન પુરસીસ

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટ પુરસીસ થી જાહેર કરીએ છીએ કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસના પક્ષકારો વચ્ચે {{settlement_terms}} પરસ્પર સમાધાન થયેલ છે. બંને પક્ષકારોએ પોતાની સ્વતંત્ર ઇચ્છાથી તથા કોઈપણ જાતના દબાણ, ધાકધમકી કે લાલચ વગર સદર સમાધાન કરેલ છે અને સદર સમાધાન મુજબ આગળની કાર્યવાહી કરવા બંને પક્ષકારો સંમત છે. સદર સમાધાન પુરસીસ રેકોર્ડ પર લઈ યોગ્ય કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

COMPROMISE PURSHIS

In the above matter, we, the advocate for {{selected_party_role}}, hereby declare by this purshis before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. A mutual compromise has been arrived at between the parties {{settlement_terms}}. Both parties have entered into the said compromise voluntarily of their own free will and without any coercion, threat or undue influence, and both parties agree to proceed further in terms of the said compromise. It is therefore prayed that this Hon'ble Court may be pleased to take this compromise purshis on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "ulat_tapas_no_haq_bandh_karavani_arji",
        "aliases": ["ulat_tapas_bandh", "close cross examination", "ઉલટતપાસ બંધ", "હક બંધ ઉલટતપાસ"],
        "name_gu": "ઉલટતપાસનો હક્ક બંધ કરવાની અરજી",
        "name_en": "Application to Close Cross-Examination Right",
        "category": "General",
        "description": "Application to close the right of cross-examination due to repeated delay and absence of opposite party.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Complainant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'witness_name', 'label_en': 'Name of witness whose cross-examination was pending', 'label_gu': 'જે સાક્ષીની ઉલટતપાસ કરવાની છે તેમનું નામ', 'type': 'text', 'required': True},
            {'key': 'target_party_role', 'label_en': 'Party failing to cross-examine (e.g. Accused)', 'label_gu': 'જેનો હક્ક બંધ કરવાનો છે તે (દા.ત. આરોપી)', 'type': 'text', 'required': True, 'default': 'આરોપી'},
            {'key': 'delay_period', 'label_en': 'Period of default / delay', 'label_gu': 'વિલંબનો સમયગાળો (ઘણી મુદ્દતથી / આજ દીન સુધી)', 'type': 'select', 'required': True, 'options': [{'value': 'ઘણી મુદ્દતથી', 'label_en': 'Since several dates', 'label_gu': 'ઘણી મુદ્દતથી'}, {'value': 'આજ દીન સુધી', 'label_en': 'Till today', 'label_gu': 'આજ દીન સુધી'}]},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- ઉલટતપાસનો હક બંધ કરવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર અને કેસમાં {{witness_name}} નાઓની લેખીત જુબાની પૂર્ણ થયેલ હોવા છતાં {{target_party_role}} તરફથી {{witness_name}} ની ઉલટતપાસ કરવામાં આવેલ નથી. સામાવાળા ને ઉલટતપાસ માટે પૂરતી તક આપવામાં આવેલ હોવા છતાં {{delay_period}} આપ નામદાર સાહેબશ્રીની કોર્ટ સમક્ષ ઊપસ્થિત રહેલ ન હોય, તેમજ નામદાર કોર્ટનો સમય ખુબ જ કિંમતી છે. જેથી સદર {{target_party_role}} નાઓનો ઉલટતપાસનો હક બંધ કરવો ન્યાયના હિતમાં છે. આથી {{target_party_role}} નો {{witness_name}} નાઓની ઉલટતપાસ કરવાનો હક બંધ કરી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO CLOSE RIGHT OF CROSS-EXAMINATION

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court, and though the examination-in-chief of {{witness_name}} has been completed, cross-examination of {{witness_name}} has not been conducted by {{target_party_role}}. Despite sufficient opportunity having been granted for cross-examination, {{target_party_role}} has not remained present before this Hon'ble Court {{delay_period}}, and the time of the Hon'ble Court is very precious. Therefore, it is in the interest of justice to close the right of {{target_party_role}} to cross-examine. It is therefore prayed that this Hon'ble Court may be pleased to close the right of {{target_party_role}} to cross-examine {{witness_name}} and pass appropriate orders to proceed further.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "ulat_tapas_no_haq_kholvani_arji",
        "aliases": ["ulat_tapas_khol", "reopen cross examination", "ઉલટતપાસ ખોલવા", "હક ખોલવો ઉલટતપાસ"],
        "name_gu": "ઉલટતપાસનો હક્ક ખોલવાની અરજી",
        "name_en": "Application to Reopen Cross-Examination Right",
        "category": "General",
        "description": "Application to reopen the closed right of cross-examination and recall witness.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Accused / Respondent side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'party', 'label_en': 'Applicant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}]},
            {'key': 'reopen_reason', 'label_en': 'Reason for reopening cross-examination', 'label_gu': 'ઉલટતપાસ ન થઈ શકવાનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'આરોપીના દાદા ગુજરી ગયેલ હોવાના', 'label_en': 'Bereavement in family', 'label_gu': 'આરોપીના દાદા ગુજરી ગયેલ હોવાના'}, {'value': 'આરોપીને વ્યવસાયના કામ અર્થે વિદેશ જવાનુ થયેલ હોવાના', 'label_en': 'Travelled abroad for business', 'label_gu': 'આરોપીને વ્યવસાયના કામ અર્થે વિદેશ જવાનુ થયેલ હોવાના'}, {'value': 'આરોપીના વકીલશ્રી માંદગીના કારણોસર આપ નામદાર કોર્ટમા આવી શકે તેમ ન હોવાના', 'label_en': 'Advocate was indisposed due to illness', 'label_gu': 'આરોપીના વકીલશ્રી માંદગીના કારણોસર આપ નામદાર કોર્ટમા આવી શકે તેમ ન હોવાના'}, {'value': 'આરોપી બીજા ગુન્હાના કામ અર્થે જેલ મા હોય', 'label_en': 'Accused was in custody in another matter', 'label_gu': 'આરોપી બીજા ગુન્હાના કામ અર્થે જેલ મા હોય'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય કારણ'}]},
            {'key': 'reopen_reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'reopen_reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- ઉલટતપાસનો હક ફરીથી ખોલી આપવા બાબત...

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેમા અમોનો ઉલટતપાસ કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે. જે {{reopen_reason}} હોવાના કારણોસર થઈ શકેલ નહી તેમજ સદર કારણ વાજબી હોવાથી તથા ઉલટતપાસ કરવાની તક મળવી એ ન્યાયના હિતમા હોય, અમોનો ઉલટતપાસ કરવાનો હક ફરીથી ખોલી અમોને ઉલટતપાસ કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO REOPEN RIGHT OF CROSS-EXAMINATION

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court, wherein our right of cross-examination was closed by this Hon'ble Court. Cross-examination could not be conducted on account of {{reopen_reason}}, and as the said reason is reasonable and genuine and getting an opportunity to cross-examine is in the interest of justice, it is prayed that this Hon'ble Court may be pleased to reopen our right of cross-examination and grant us an opportunity to cross-examine.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "undertaking",
        "aliases": ["bahedhari", "undertaking purshis", "બાંહેધરી", "બાહેધરી પત્રક"],
        "name_gu": "બાંહેધરી પત્રક (Undertaking)",
        "name_en": "Written Undertaking / Purshis",
        "category": "General",
        "description": "Formal written undertaking submitted to the court promising compliance with judicial conditions.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Plaintiff side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'undertaking_subject', 'label_en': 'Subject / court condition for undertaking', 'label_gu': 'બાંહેધરીની બાબત / શરત', 'type': 'text', 'required': True},
            {'key': 'undertaking_details', 'label_en': 'Details of undertaking / action to be taken', 'label_gu': 'બાંહેધરીની વિગત / કરવાની કાર્યવાહી', 'type': 'textarea', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાંહેધરી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં આપ નામદાર કોર્ટના હુકમ મુજબ {{undertaking_subject}} જે અંગે અમો નીચે સહી કરનાર તરફથી આ બાંહેધરી આપવામાં આવે છે કે, {{undertaking_details}} નું પાલન કરીશું તથા સદર કેસમાં આપ નામદાર કોર્ટના અન્ય હુકમો તથા નિર્દેશોનું પાલન કરીશું. જેથી સદર બાંહેધરી રેકોર્ડ પર લઈ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

UNDERTAKING

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. Pursuant to the order of this Hon'ble Court regarding {{undertaking_subject}}, the undersigned hereby gives this undertaking that we shall comply with {{undertaking_details}} and shall comply with other orders and directions of this Hon'ble Court in the said case. It is therefore prayed that this Hon'ble Court may be pleased to take the said undertaking on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "vakilatnama_civil",
        "aliases": ["vakalatnama", "civil vakalatnama", "વકીલાતનામું", "સિવિલ વકીલાતનામું"],
        "name_gu": "વકીલાતનામું (સિવિલ)",
        "name_en": "Vakalatnama (Civil Matters)",
        "category": "Civil",
        "description": "Formal legal vakalatnama empowering an advocate to represent a client in civil proceedings.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફથી છો તેની વિગત', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Plaintiff / Applicant', 'label_gu': 'વાદી / અરજદાર'}, {'value': 'opposite', 'label_en': 'Defendant / Respondent', 'label_gu': 'પ્રતિવાદી / સામાવાળા'}]},
            {'key': 'advocate_name', 'label_en': 'Advocate Name', 'label_gu': 'વકીલનું નામ', 'type': 'text', 'required': True},
            {'key': 'advocate_qualification', 'label_en': 'Advocate Qualification', 'label_gu': 'વકીલની લાયકાત (દા.ત. B.Com., LL.B.)', 'type': 'text', 'required': False},
            {'key': 'advocate_address', 'label_en': 'Advocate Office Address', 'label_gu': 'વકીલની ઓફિસનું સરનામું', 'type': 'textarea', 'required': False},
            {'key': 'advocate_mobile', 'label_en': 'Advocate Mobile No.', 'label_gu': 'વકીલનો મોબાઇલ નં.', 'type': 'text', 'required': False},
            {'key': 'advocate_enrollment_no', 'label_en': 'Bar Council Enrollment No.', 'label_gu': 'સનદ / એનરોલમેન્ટ નં.', 'type': 'text', 'required': False},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

-------------------------------------------------------------------------------------------

અમો {{selected_party_role}} તરીકે ઉપર દર્શાવેલ દાવામાં એડવોકેટશ્રી {{advocate_name}}, ને અમારા વતી કરારદાદ કબુલ કરવા તથા કોર્ટમાં હાજર રહેવા, દસ્તાવેજો કરવા, પૈસા રજુ કરવા, પૈસા પરત લેવા, તેમના નામનો કોર્ટફીઝ રીફંડનો દાખલો લેવા, રકમો લેવા, અમારા વતી દાવો પરત ખેંચી લેવા, અપીલ કરવા તેમજ સદર દાવા સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.

અમો સદર એડવોકેટશ્રી દ્વારા કરવામાં આવતી અમારા વતીની કાયદેસરની કાર્યવાહીને સ્વીકારીએ છીએ અને તે અમારા માટે બંધનકર્તા રહેશે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

પક્ષકારની સહી :-  એડવોકેટની સહી :-
પક્ષકારનુ નામ :-  એડવોકેટનુ નામ :-""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

-------------------------------------------------------------------------------------------

We, as {{selected_party_role}}, do hereby appoint and authorize Advocate {{advocate_name}} to appear in court, consent to compromise, submit documents, deposit and withdraw money, obtain court fee refund certificates, withdraw the suit on our behalf, file appeals, and take all necessary lawful proceedings in connection with the said suit on our behalf.

We accept all lawful acts done by the said Advocate on our behalf and the same shall be binding upon us.

Date : {{date_display}}
Place : {{taluka_place}}

Signature of Client :-  Signature of Advocate :-
Name of Client :-       Name of Advocate :-""",
    },
    {
        "base_key": "vakilatnama_criminal",
        "aliases": ["criminal vakalatnama", "ક્રિમિનલ વકીલાતનામું"],
        "name_gu": "વકીલાતનામું (ક્રિમિનલ)",
        "name_en": "Vakalatnama (Criminal Matters)",
        "category": "Criminal",
        "description": "Formal legal vakalatnama empowering an advocate to defend or represent a party in criminal proceedings.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફથી છો તેની વિગત', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Accused / Respondent', 'label_gu': 'આરોપી / સામાવાળા'}, {'value': 'party', 'label_en': 'Complainant / Applicant', 'label_gu': 'ફરિયાદી / અરજદાર'}]},
            {'key': 'advocate_name', 'label_en': 'Advocate Name', 'label_gu': 'વકીલનું નામ', 'type': 'text', 'required': True},
            {'key': 'advocate_qualification', 'label_en': 'Advocate Qualification', 'label_gu': 'વકીલની લાયકાત (દા.ત. B.Com., LL.B.)', 'type': 'text', 'required': False},
            {'key': 'advocate_address', 'label_en': 'Advocate Office Address', 'label_gu': 'વકીલની ઓફિસનું સરનામું', 'type': 'textarea', 'required': False},
            {'key': 'advocate_mobile', 'label_en': 'Advocate Mobile No.', 'label_gu': 'વકીલનો મોબાઇલ નં.', 'type': 'text', 'required': False},
            {'key': 'advocate_enrollment_no', 'label_en': 'Bar Council Enrollment No.', 'label_gu': 'સનદ / એનરોલમેન્ટ નં.', 'type': 'text', 'required': False},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

-------------------------------------------------------------------------------------------

અમો {{selected_party_role}} તરીકે ઉપર દર્શાવેલ કેસમાં એડવોકેટશ્રી {{advocate_name}}, ને અમારા વતી હાજર રહેવા, અરજીઓ કરવા, પુરશીશ આપવા, દસ્તાવેજો રજૂ કરવા, પુરાવા આપવા, સાક્ષીઓની તપાસ તથા ઉલટતપાસ કરવા, સમાધાન કરવા, પ્રમાણિત નકલ મેળવવા અપીલ કરવા, રિવિઝન કરવા તેમજ અન્ય કાયદેસરની કાર્યવાહી કરવા અને સદર કેસ સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.

અમો સદર એડવોકેટશ્રી દ્વારા કરવામાં આવતી અમારા વતીની કાયદેસરની કાર્યવાહીને સ્વીકારીએ છીએ અને તે અમારા માટે બંધનકર્તા રહેશે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

પક્ષકારની સહી :-  એડવોકેટની સહી :-
પક્ષકારનુ નામ :-  એડવોકેટનુ નામ :-""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

-------------------------------------------------------------------------------------------

We, as {{selected_party_role}}, do hereby appoint and authorize Advocate {{advocate_name}} to appear in court, submit applications, file purshis, produce documents, lead evidence, examine and cross-examine witnesses, enter into compromise, obtain certified copies, file appeals and revisions, and take all necessary lawful proceedings in connection with the said case on our behalf.

We accept all lawful acts done by the said Advocate on our behalf and the same shall be binding upon us.

Date : {{date_display}}
Place : {{taluka_place}}

Signature of Client :-  Signature of Advocate :-
Name of Client :-       Name of Advocate :-""",
    },
    {
        "base_key": "warrant_no_hath_bido_apvani_arji",
        "aliases": ["warrant_hathbido", "hathbido", "direct service", "હાથબીડો", "સમન્સ હાથબીડો"],
        "name_gu": "સમન્સ / વોરંટનો હાથબીડો આપવા બાબતની અરજી",
        "name_en": "Application for Direct Service / Handing Over Summons or Warrant",
        "category": "Criminal",
        "description": "Application to hand over summons or warrant directly to advocate/complainant for prompt service through police.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'party', 'label_en': 'Applicant / Complainant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}, {'value': 'opposite', 'label_en': 'Opposite party side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}]},
            {'key': 'warrant_kind', 'label_en': 'Process Type', 'label_gu': 'પ્રક્રિયા પ્રકાર (સમન્સ / વોરંટ / નોટીસ)', 'type': 'select', 'required': True, 'options': [{'value': 'સમન્સ', 'label_en': 'Summons', 'label_gu': 'સમન્સ'}, {'value': 'વોરંટ', 'label_en': 'Warrant', 'label_gu': 'વોરંટ'}, {'value': 'નોટીસ', 'label_en': 'Notice', 'label_gu': 'નોટીસ'}]},
            {'key': 'target_party', 'label_en': 'Name of party to be served', 'label_gu': 'જેની સામે બજવણી કરવાની હોય તેનું નામ (સાક્ષી / સામાવાળા)', 'type': 'text', 'required': True},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- {{warrant_kind}}નો હાથબીડો આપવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{target_party}}ને બજવણી માટે {{warrant_kind}} ઇશ્યુ કરવામા આવેલ છે જેની બજવણી યોગ્ય રીતે ન થતી હોય, તેમજ સદર {{warrant_kind}} ની યોગ્ય રીતે બજવણી થવી ન્યાયના હિતમાં હોય, સદર {{warrant_kind}} ની બજવણી કરાવવા માટે હાથબીડો આપવો જરૂરી છે. જેથી સમન્સ/વોરંટનો જરૂરી હાથબીડો આપી બજવણી કરાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION FOR HAND DELIVERY OF {{warrant_kind}}

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. In the said case, {{warrant_kind}} has been issued for service upon {{target_party}}, but the service is not taking place properly, and proper service of the said {{warrant_kind}} is in the interest of justice, for which hand delivery is necessary to effect service of the said {{warrant_kind}}. It is therefore prayed that this Hon'ble Court may be pleased to grant necessary hand delivery of summons/warrant to effect service and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
    },
    {
        "base_key": "warrant_rad_karvani_arji",
        "aliases": ["warrant_rad", "cancel warrant", "recall warrant", "વોરંટ રદ", "વોરંટ રીકોલ"],
        "name_gu": "વોરંટ રદ કરવાની અરજી",
        "name_en": "Application for Cancellation / Recall of Warrant",
        "category": "Criminal",
        "description": "Application to cancel or recall a warrant issued against the accused on showing bona fide cause.",
        "fields": [
            {'key': 'advocate_side', 'label_en': 'Advocate acting on behalf of', 'label_gu': 'કોના તરફે એડવોકેટ', 'type': 'select', 'required': True, 'source': 'case_parties', 'options': [{'value': 'opposite', 'label_en': 'Accused / Respondent side', 'label_gu': 'આરોપી / સામાવાળા / પ્રતિવાદી તરફથી'}, {'value': 'party', 'label_en': 'Applicant side', 'label_gu': 'ફરિયાદી / અરજદાર / વાદી તરફથી'}]},
            {'key': 'warrant_date', 'label_en': 'Date warrant was issued', 'label_gu': 'વોરંટ કાઢ્યાની તારીખ (દા.ત. ૨૦/૦૮/૨૦૨૬)', 'type': 'text', 'required': True},
            {'key': 'absence_reason', 'label_en': 'Reason for prior absence', 'label_gu': 'ગેરહાજર રહેવાનું કારણ', 'type': 'select', 'required': True, 'options': [{'value': 'સમન્સ / નોટિસની બજવણી થયેલ ન હોવાથી', 'label_en': 'Summons/notice was not served', 'label_gu': 'સમન્સ / નોટિસની બજવણી થયેલ ન હોવાથી'}, {'value': 'અનિવાર્ય માંદગીના કારણોસર', 'label_en': 'Due to unavoidable illness', 'label_gu': 'અનિવાર્ય માંદગીના કારણોસર'}, {'value': 'કામ સબબ બહારગામ હોવાથી', 'label_en': 'Out of station for urgent work', 'label_gu': 'કામ સબબ બહારગામ હોવાથી'}, {'value': 'other', 'label_en': 'Other reason', 'label_gu': 'અન્ય કારણ'}]},
            {'key': 'absence_reason_other', 'label_en': 'If other, specify reason', 'label_gu': 'અન્ય કારણની વિગત', 'type': 'text', 'required': False, 'depends_on': 'absence_reason=other'},
            {'key': 'date', 'label_en': 'Date', 'label_gu': 'તારીખ', 'type': 'date', 'required': True},
        ],
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
મુકામ :- {{taluka_place}}

{{case_type}} નં. : {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- વોરંટ રદ કરાવવા બાબત...

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં આરોપી વિરુદ્ધ તા. {{warrant_date}}ના રોજ વોરંટ કાઢવામાં આવેલ છે. સદર વોરંટની બજવણી થઈ શકે તે પહેલાં આરોપી આજ રોજ આપ નામદાર કોર્ટ સમક્ષ હાજર થયેલ છે તથા {{absence_reason}} કારણોસર ગેરહાજર રહેલ છે. ગેરહાજર રહેવાનો કોઈ દુર્ભાવ કે આપ નામદાર કોર્ટની કાર્યવાહીમાં વિલંબ કરવાનો આશય નથી. વધુમાં સદર આરોપી હવે પછી કેસની દરેક તારીખે નિયમિત હાજર રહી આપ નામદાર કોર્ટની કાર્યવાહીમાં સંપૂર્ણ સહકાર આપશે. જેથી સદર આરોપી વિરુદ્ધ કાઢવામાં આવેલ વોરંટ રદ કરી કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

--------------------------- {{selected_party_role}} ના એડવોકેટ""",
        "content_en": """IN THE COURT OF {{court}},
AT {{taluka_place}}

{{case_type}} No. : {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT: APPLICATION TO CANCEL / RECALL WARRANT

In the above matter, we, the advocate for {{selected_party_role}}, most respectfully submit before this Hon'ble Court that:

The said case is pending before this Hon'ble Court. In the said case, a warrant was issued against the accused on {{warrant_date}}. Before service of the said warrant could be effected, the accused has appeared before this Hon'ble Court today and had remained absent due to {{absence_reason}}. There was no mala fide intention to remain absent or to cause delay in the proceedings of this Hon'ble Court. Furthermore, the said accused shall remain regularly present on every date of hearing of the case hereafter and shall fully cooperate with the proceedings of this Hon'ble Court. It is therefore prayed that this Hon'ble Court may be pleased to cancel the warrant issued against the said accused and pass appropriate orders to proceed further in the case.

Date : {{date_display}}
Place : {{taluka_place}}

--------------------------- Advocate for {{selected_party_role}}""",
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
