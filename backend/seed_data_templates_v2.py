# -*- coding: utf-8 -*-
"""
NyaySetu Pro — Application template catalog v2.

These 21 templates are transcribed VERBATIM from the lawyer's final application
drafts (Downloads/Nyaysetu/Field for each template). The Gujarati legal wording,
paragraph order, punctuation and heading structure are preserved exactly.

Placeholder conventions
-----------------------
* Case/system placeholders (auto-filled, never asked again):
    {{court}}  {{taluka_place}} (taluka, district)  {{case_type}}  {{case_number}}
    {{party_role}} {{party_name}}  {{opposite_party_role}} {{opposite_party}}
    {{party_line}} = "<role> <name>"   {{opposite_party_line}}
    {{selected_party_role}} = role of the side the advocate represents
    {{advocate_name}}  {{date_display}} (DD/MM/YYYY, defaults to today)
    {{case_or_crime}}  = "કેસ નં. X" or "ગુન્હા રજી. નં. Y" (Jamin Bond)

* Application-specific fields are declared in `fields` and rendered by the
  lawyer-facing form. A field with `source: "case_parties"` is rendered as a
  select whose options are the two parties of the linked case (value is
  "party" / "opposite"). A field with `depends_on` + `show_when: "other"`
  is a conditional text field revealed when the parent select/radio value is
  "other" (the "અન્ય" pattern from the source documents).

* `date` is always the LAST field — the lawyer only needs to confirm it.
"""

TEMPLATES_V2 = [
    {
        "id": "aanke_padvani_arji",
        "name_en": "Application to Exhibit Document",
        "name_gu": "દસ્તાવેજને આંકે પાડવાની અરજી",
        "category": "General",
        "aliases": ["aanke", "exhibit", "દસ્તાવેજને આંકે પાડવાની અરજી", "આંક"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "document_details", "label_en": "Document details to be exhibited", "label_gu": "ક્યા દસ્તાવેજને આંક પાડવાના તેની વિગત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO GIVE EXHIBIT NUMBER TO DOCUMENT

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that......

The said case is pending before this Hon'ble Court. In the said case, {{document_details}} has been produced as documentary evidence. As the said document is in the interest of justice, this Hon'ble Court may be pleased to take the said document on record, give a proper exhibit number and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

દસ્તાવેજને આંકે પાડવાની અરજી

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{document_details}} દસ્તાવેજી પુરાવા તરીકે રજૂ કરવામાં આવેલ છે. સદર દસ્તાવેજ ન્યાયના હિતમાં હોય, સદર દસ્તાવેજને રેકોર્ડ પર લઈ યોગ્ય આંક આપી યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}} ના એડવોકેટ
""",
    },
    {
        "id": "certified_report",
        "name_en": "Application for Certified Copy",
        "name_gu": "પ્રમાણિત નકલ માટે અરજી",
        "category": "General",
        "aliases": ["certified copy", "પ્રમાણિત નકલ", "pramanit nakal", "નકલ"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ / ત્રાહિત વકીલ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
                 {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
             ]},
            {"key": "advocate_other", "label_en": "If Other — person requesting copies", "label_gu": "અન્ય હોય તો તેઓની વિગત", "type": "text", "required": False, "depends_on": "advocate_side", "show_when": "other"},
            {"key": "documents_details", "label_en": "Details of documents/copies required", "label_gu": "દસ્તાવેજોની વિગત", "type": "textarea", "required": True},
            {"key": "recipient", "label_en": "Copies to be given to (if other person)", "label_gu": "નકલ કોને આપવાની છે (અલગ વ્યક્તિ હોય તો)", "type": "text", "required": False},
            {"key": "deposit_amount", "label_en": "Deposit amount (₹)", "label_gu": "ડિપોઝિટ પેટે રકમ (રૂ.)", "type": "text", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION FOR CERTIFIED COPY

In the said case, we, advocate of {{selected_party_role}}{{advocate_other}}, most respectfully submit this application to this Hon'ble Court that......

Certified copies of the documents mentioned below are required from the said case; for the said purpose this Hon'ble Court may be pleased to give us the certified copies mentioned below at the earliest.

{{documents_details}}

The said copies shall be given by us to the undersigned / {{recipient}}. Deposit of Rs. {{deposit_amount}} has been paid.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

પ્રમાણિત નકલ માટે અરજી

સદર કેસમાં અમો {{selected_party_role}}ના એડવોકેટ{{advocate_other}}ની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે....

સદર કેસમાંથી નીચે જણાવેલ દસ્તાવેજની પ્રમાણિત નકલની જરૂરિયાત હોય, સદર કામે અમોને નીચે મુજબની સર્ટીફાઈડ નકલ તાત્કાલીક આપવા મહેરબાની કરશોજી.

{{documents_details}}

સદર નકલ અમો નીચે સહી કરનાર/{{recipient}}ને આપશોજી. ડિપોઝિટ પેટે રૂ. {{deposit_amount}} જમા કરાવેલ છે.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "dd_karavani_arji",
        "name_en": "Application to Dismiss the Case / Suit",
        "name_gu": "કેસ/દાવો ડિસમિસ કરવાની અરજી",
        "category": "General",
        "aliases": ["dismiss", "ડિસમિસ", "ડી.ડી.", "dd", "કેસ ડિસમિસ"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "dismiss_reason", "label_en": "Reason for dismissal of the case", "label_gu": "કેસ/દાવો ડિસમિસ કરવાનું કારણ", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION FOR DISMISSAL OF THE CASE / SUIT

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that......

The said case is pending before this Hon'ble Court. As {{dismiss_reason}} in the said case, there is no need to proceed further with the said case.

Moreover, it would be in the interest of justice that the said case be dismissed; it is therefore appropriate that the said case be dismissed. This Hon'ble Court may be pleased to dismiss the said case and complete the further proceedings by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

કેસ/દાવો ડિસમિસ કરવાની અરજી

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{dismiss_reason}} હોવાથી સદર કેસ આગળ ચલાવવાની જરૂરિયાત રહેલ નથી.

વધુમા સદર કેસ ડિસમિસ કરવામાં આવે તે ન્યાયના હિતમાં હોય, જેથી સદર કેસ ડિસમિસ કરવો યોગ્ય હોય, સદર કેસ ડિસમિસ કરી આગળની કાર્યવાહી પૂર્ણ કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "document_return",
        "name_en": "Application for Return of Document",
        "name_gu": "દસ્તાવેજ પરત મેળવવાની અરજી",
        "category": "General",
        "aliases": ["return of document", "દસ્તાવેજ પરત", "પરત મેળવવાની અરજી"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "case_status", "label_en": "Case Status", "label_gu": "કેસ ચાલુ છે કે ડિસ્પોઝ્ડ થયેલ છે", "type": "select", "required": True,
             "options": [
                 {"value": "ચાલુ", "label_en": "Ongoing", "label_gu": "ચાલુ"},
                 {"value": "ડિસ્પોઝ્ડ", "label_en": "Disposed", "label_gu": "ડિસ્પોઝ્ડ"},
             ]},
            {"key": "document_name", "label_en": "Document to be returned", "label_gu": "દસ્તાવેજનું નામ / વિગત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION FOR RETURN OF DOCUMENT

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is {{case_status_clause}} before this Hon'ble Court. In the said case, {{document_name}} was produced in the proceedings. The said document is no longer required for the purpose of the case, and it would be in the interest of justice to receive the document back; this Hon'ble Court may therefore be pleased to pass appropriate orders to return the said document.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

દસ્તાવેજ પરત મેળવવાની અરજી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ {{case_status_clause}} સદર કેસમાં {{document_name}} કામમા રજૂ કરવામાં આવેલ {{tense}}. સદર દસ્તાવેજની હવે કેસના હેતુ માટે જરૂરિયાત ન હોય તેમજ દસ્તાવેજ પરત મેળવવો ન્યાયના હિતમાં હોય, જેથી સદર દસ્તાવેજ પરત અપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "document_on_record",
        "name_en": "Application to Take Document on Record",
        "name_gu": "દસ્તાવેજ રેકર્ડ પર લેવા અરજી",
        "category": "General",
        "aliases": ["record par leva", "રેકર્ડ પર", "દસ્તાવેજ રેકર્ડ"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "annexure", "label_en": "Annexure (optional)", "label_gu": "બિડાણ :- (વૈકલ્પિક)", "type": "text", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO TAKE DOCUMENT ON RECORD

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. As the evidence produced with this application is required in the said case, it is produced with this application. The said evidence is in the interest of justice, and taking the said evidence on record will assist the judicial proceedings of the case. This Hon'ble Court may therefore be pleased to take the evidence produced with this application on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}

Annexure :- {{annexure}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

દસ્તાવેજ રેકર્ડ પર લેવા અરજી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં આ અરજી સાથે રજુ કરેલ પુરાવાની જરૂરિયાત હોવાથી આ અરજી સાથે રજૂ કરવામાં આવે છે. સદર પુરાવા ન્યાયના હિતમાં હોય, અને સદર પુરાવા રેકોર્ડ પર લેવાથી કેસની ન્યાયિક કાર્યવાહી કરવામાં સહાયરૂપ થશે. આથી આપ નામદાર કોર્ટ આ અરજી સાથે રજૂ કરેલ પુરાવા રેકોર્ડ પર લઈ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ

બિડાણ :- {{annexure}}
""",
    },
    {
        "id": "closing_purshish",
        "name_en": "Closing Purshis",
        "name_gu": "ક્લોઝિંગ પુરશીશ",
        "category": "General",
        "aliases": ["closing", "ક્લોઝિંગ", "પુરશીશ", "purushish"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

CLOSING PURSHIS

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this purshis to this Hon'ble Court that.....

The said matter is pending before this Hon'ble Court. From the side of {{selected_party_role}} in the said case, the necessary evidence and submissions have been completed, and there is no further evidence or submission to be made from our side; this Hon'ble Court may be pleased to treat the evidence/submission from the said party as closed and proceed further in the said case by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

ક્લોઝિંગ પુરશીશ

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કામ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{selected_party_role}} તરફથી જરૂરી પુરાવા તથા રજૂઆતો પૂર્ણ કરવામાં આવેલ છે અને હવે અમારા તરફથી વધુ કોઈ પુરાવા કે રજૂઆત કરવાની ન હોય, સદર પક્ષકાર તરફનો પુરાવો/રજૂઆત બંધ ગણાવી સદર કેસમાં આગળની કાર્યવાહી કરવા તથા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "hazari_mafi_arji",
        "name_en": "Application for Exemption from Personal Appearance",
        "name_gu": "હાજરી માફીની અરજી",
        "category": "General",
        "aliases": ["exemption", "હાજરી માફી", "exemption arji", "એક્ઝમ્શન"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "absence_reason", "label_en": "Reason for absence", "label_gu": "ગેરહાજર રહેવાનું કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "બહારગામ ગયેલ હોવાના", "label_en": "Being out of station", "label_gu": "બહારગામ ગયેલ હોવાના"},
                 {"value": "સામાજીક કાર્યમા રોકાયેલ હોવાના", "label_en": "Being engaged in social work", "label_gu": "સામાજીક કાર્યમા રોકાયેલ હોવાના"},
                 {"value": "ધાર્મિક કામમાં રોકાયેલ હોવાના", "label_en": "Being engaged in religious work", "label_gu": "ધાર્મિક કામમાં રોકાયેલ હોવાના"},
                 {"value": "માંદગીના", "label_en": "Due to illness", "label_gu": "માંદગીના"},
                 {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
             ]},
            {"key": "absence_reason_other", "label_en": "If Other — specify reason", "label_gu": "અન્ય હોય તો કારણ", "type": "text", "required": False, "depends_on": "absence_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION FOR EXEMPTION FROM PERSONAL APPEARANCE

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that......

The said case is pending before this Hon'ble Court, whose adjournment is fixed today, but the {{selected_party_role}} of the said matter is unable to remain present before this Hon'ble Court due to {{absence_reason}}. Therefore this Hon'ble Court may be pleased to exempt the personal appearance of the {{selected_party_role}} for today only and proceed further in the said case by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

હાજરી માફીની અરજી

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે, જેની મુદ્દત આજ રોજની છે પરંતુ સદર કામના {{selected_party_role}} {{absence_reason}} કારણોસર આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકે તેમ નથી. જેથી આજના દિવસ પૂરતી {{selected_party_role}} ની વ્યક્તિગત હાજરી માફ રાખી સદર કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "fs_haq_bandh",
        "name_en": "Application to Close Right of Further Statement",
        "name_gu": "એફ.એસ.નો હક બંધ કરવાની અરજી",
        "category": "Criminal",
        "aliases": ["fs", "એફ.એસ.", "ફર્ધર સ્ટેટમેન્ટ", "further statement"],
        "fields": [
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO CLOSE THE RIGHT OF FURTHER STATEMENT

In the above matter, we, advocate of {{party_role}}, most respectfully submit this application to this Hon'ble Court that......

The said case is pending before this Hon'ble Court. In the said case, although the {{opposite_party_role}} has the right to give a further statement, he has not remained present before this Hon'ble Court for giving the further statement since many adjournments; and although sufficient opportunity was given to give the further statement, the opportunity was not utilized; and as continuing the right of further statement is not proper in the interest of justice, this Hon'ble Court may be pleased to close the right of further statement of the {{opposite_party_role}} and proceed further by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

એફ.એસ.નો હક બંધ કરવાની અરજી

સદર કામમાં અમો {{party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{opposite_party_role}} નો એફ.એસ. કરવાનો હક હોવા છતાં ઘણી મુદ્દતોથી એફ.એસ. કરવા માટે આપ નામદાર કોર્ટ સમક્ષ ઉપસ્થિત થયેલ ન હોવાથી તેમજ એફ.એસ. કરવા માટે પૂરતી તક આપવામાં આવેલ હોવા છતાં તકનો ઉપયોગ કરવામાં આવેલ ન હોય તેમજ એફ.એસ. નો હક વધુ ચાલુ રાખવો ન્યાયના હિતમાં યોગ્ય ન હોવાથી {{opposite_party_role}} નો એફ.એસ. કરવાનો હક બંધ કરી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "fs_haq_khol",
        "name_en": "Application to Reopen Right of Further Statement",
        "name_gu": "એફ.એસ.નો હક ફરીથી ખોલવાની અરજી",
        "category": "Criminal",
        "aliases": ["fs khol", "એફ.એસ. ખોલવાની", "reopen further statement"],
        "fields": [
            {"key": "fs_reason", "label_en": "Reason why further statement could not be given", "label_gu": "એફ.એસ. ન થઈ શકવાનું યોગ્ય કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "અનિવાર્ય સંજોગો", "label_en": "Due to unavoidable circumstances", "label_gu": "અનિવાર્ય સંજોગો"},
                 {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
             ]},
            {"key": "fs_reason_other", "label_en": "If Other — specify reason", "label_gu": "અન્ય હોય તો વિશેષ કારણ", "type": "text", "required": False, "depends_on": "fs_reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO REOPEN THE RIGHT OF FURTHER STATEMENT

In the above matter, we, advocate of {{opposite_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. Our right to give a further statement has been closed by this Hon'ble Court. It could not be done due to {{fs_reason}}; and as the said reason is reasonable and proper, and as getting the opportunity to give a further statement is in the interest of justice, this Hon'ble Court may be pleased to reopen our right to give a further statement and give us the opportunity to give the further statement by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{opposite_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

એફ.એસ.નો હક ફરીથી ખોલવાની અરજી

સદર કામમા અમો {{opposite_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેમા અમોનો એફ.એસ. કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે. જે {{fs_reason}} હોવાના કારણોસર થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી તેમજ યોગ્ય હોવાથી તથા એફ.એસ. કરવાની તક મળવીએ ન્યાયના હિતમા હોય, અમોનો એફ.એસ. કરવાનો હક ફરીથી ખોલી અમોને એફ.એસ. કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "jamin_bond",
        "name_en": "Application to Accept Bail Bond",
        "name_gu": "જામીન બોન્ડ સ્વીકારવા અરજી",
        "category": "Criminal",
        "aliases": ["jamin", "જામીન", "bail bond", "જામીન બોન્ડ"],
        "fields": [
            {"key": "crime_reg_number", "label_en": "Crime Registration Number (when no case number)", "label_gu": "ગુન્હા રજી. નં. (કેસ નં ન હોય તો)", "type": "text", "required": False},
            {"key": "bail_court", "label_en": "Court which ordered bail release", "label_gu": "કઈ કોર્ટ દ્વારા જામીન મુક્ત કરવાનો આદેશ કરવામાં આવ્યો", "type": "text", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_or_crime}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO ACCEPT BAIL BOND

In the above matter, we, advocate of the accused, most respectfully submit this application to this Hon'ble Court that......

In the above-mentioned {{case_or_crime}}, the accused has been ordered to be released on bail by {{bail_court}}. Pursuant to this order, the necessary bail bond and surety bond are produced on behalf of the accused; this Hon'ble Court may be pleased to accept the said bail bond and surety bond and proceed further by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of the accused
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_or_crime}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

જામીન બોન્ડ સ્વીકારવા અરજી

સદર કામમાં અમો {{opposite_party_role}}ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

ઉપરોક્ત જણાવેલ {{case_or_crime}} ના કામે {{bail_court}} દ્વારા આરોપીને જામીન પર મુક્ત કરવાનો હુકમ કરવામાં આવેલ છે. આ હુકમના અનુસંધાને આરોપી તરફથી જરૂરી જામીન બોન્ડ તથા જામીનદારના બોન્ડ રજૂ કરવામા આવે છે તે જામીન બોન્ડ તથા જામીનદારના બોન્ડ સ્વીકારી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "kam_board",
        "name_en": "Application to Take Matter on Board",
        "name_gu": "કામ બોર્ડ પર લેવા અરજી",
        "category": "General",
        "aliases": ["kam board", "કામ બોર્ડ", "board par leva"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "next_date", "label_en": "Next date fixed by the court", "label_gu": "આગામી તારીખ જે કોર્ટ દ્વારા નીમવામાં આવેલ હોય", "type": "date", "required": True},
            {"key": "proceeding", "label_en": "Proceeding / submission for today", "label_gu": "કેસની કાર્યવાહી / રજુઆત / અન્ય કાર્યવાહીની વિગત", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO TAKE THE MATTER ON BOARD

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that......

The said case is pending before this Hon'ble Court and the next date of the case has been fixed as {{next_date}}, but today {{proceeding}} in the said matter, it is necessary that the matter be taken on board. As the said proceeding is in the interest of justice, this Hon'ble Court may be pleased to take the said matter on board today and carry out the necessary proceedings by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

કામ બોર્ડ પર લેવા અરજી

સદર કામમાં અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે......

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે તેમજ કેસની આગામી તા. {{next_date}} નીમવામાં આવેલ છે પરંતુ સદર કામમાં આજ રોજ {{proceeding}} જેથી કામ બોર્ડ પર લેવામાં આવે તે જરૂરી છે. સદર કાર્યવાહી ન્યાયના હિતમાં હોય, જેથી સદર કામને આજ રોજ બોર્ડ પર લઈ જરૂરી કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "mudat_arji",
        "name_en": "Adjournment Application",
        "name_gu": "મુદ્દત અરજી",
        "category": "General",
        "aliases": ["mudat", "adjournment", "મુદ્દત", "મુદત અરજી"],
        "fields": [
            {"key": "reason", "label_en": "Reason for adjournment", "label_gu": "કારણ", "type": "select", "required": True,
             "options": [
                 {"value": "પક્ષકાર બહારગામ ગયેલ હોવાના", "label_en": "Party being out of station", "label_gu": "પક્ષકાર બહારગામ ગયેલ હોવાના"},
                 {"value": "સામાજીક કાર્યમા રોકાયેલ હોવાના", "label_en": "Being engaged in social work", "label_gu": "સામાજીક કાર્યમા રોકાયેલ હોવાના"},
                 {"value": "ધાર્મિક કામમાં રોકાયેલ હોવાના", "label_en": "Being engaged in religious work", "label_gu": "ધાર્મિક કામમાં રોકાયેલ હોવાના"},
                 {"value": "માંદગીના", "label_en": "Due to illness", "label_gu": "માંદગીના"},
                 {"value": "પુરાવા તૈયાર કરવાના", "label_en": "To prepare evidence", "label_gu": "પુરાવા તૈયાર કરવાના"},
                 {"value": "સમાધાન થયેલ હોવાના", "label_en": "Due to compromise", "label_gu": "સમાધાન થયેલ હોવાના"},
                 {"value": "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલા હોવાના", "label_en": "Advocate being engaged in another court", "label_gu": "વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલા હોવાના"},
                 {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
             ]},
            {"key": "reason_other", "label_en": "If Other — specify reason", "label_gu": "અન્ય હોય તો કારણ", "type": "text", "required": False, "depends_on": "reason", "show_when": "other"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

SUBJECT :- ADJOURNMENT APPLICATION

In the above matter, we, advocate of {{opposite_party_role}}, most respectfully submit this application to this Hon'ble Court that....

Today the said matter is on board for adjournment. As {{reason}} in the said case, it is not possible to remain present before this Hon'ble Court today; this Hon'ble Court may be pleased, in the interest of justice, to pass an order granting one adjournment and not proceeding with the case today.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{opposite_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાબત :- મુદ્દત અરજી

સદરહુ કામમા અમો {{opposite_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને માનસરની નમ્ર અરજ છે કે....

આજ રોજ સદર કામ બોર્ડ પર મુદ્દતના કામે ચાલવા પર છે. સદર કેસમાં {{reason}} કારણોસર આજરોજ આપ નામદાર કોર્ટ સમક્ષ હાજર રહી શકે તેમ ન હોઈ, સદરહુ કામમાં આજરોજ કેસ આગળ ન ચલાવવા ન્યાયના હિતમાં એક મુદ્દત આપવાનો હુકમ કરવા મહેરબાની કરશોજી.

તા. {{date_display}}
{{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "saaxi_summons",
        "name_en": "Application to Issue Summons to Witness",
        "name_gu": "સાક્ષીને સમન્સ કાઢવાની અરજી",
        "category": "Criminal",
        "aliases": ["saaxi", "સાક્ષી", "summons", "સમન્સ"],
        "fields": [
            {"key": "witness_name", "label_en": "Name of the witness", "label_gu": "સાક્ષીનું નામ", "type": "text", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO ISSUE SUMMONS TO WITNESS

In the above matter, we, advocate of {{opposite_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. As the testimony of the witness named {{witness_name}} is required in the said case, and as the testimony of the said witness is in the interest of justice and will assist the proper proceedings of the case, this Hon'ble Court may be pleased to issue summons to the said {{witness_name}} to remain present before this Hon'ble Court by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{opposite_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

સાક્ષીને સમન્સ કાઢવાની અરજી

સદર કામમા અમો {{opposite_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{witness_name}} નામના સાક્ષીની જુબાનીની જરૂરિયાત હોવાથી તેમજ સદર સાક્ષીની જુબાની કેસના ન્યાયના હિતમાં હોય અને જેનાથી કેસની યોગ્ય કાર્યવાહી કરવામાં સહાયરૂપ થાય તેમ છે. જેથી સદર {{witness_name}} નાઓને આપ નામદાર કોર્ટ સમક્ષ હાજર રહેવા માટે સમન્સ કાઢી આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "samadhan_purshish",
        "name_en": "Compromise Purshis",
        "name_gu": "સમાધાન પુરશીશ",
        "category": "General",
        "aliases": ["samadhan", "સમાધાન", "compromise", "સમાધાન પુરશીશ"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "settlement_terms", "label_en": "Terms of settlement (if any)", "label_gu": "જો કોઈ શરતને આધીન સમાધાન થયેલ હોય તો તે શરતની વિગત", "type": "textarea", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

COMPROMISE PURSHIS

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this purshis to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. The parties of the said case have mutually compromised, subject to the terms {{settlement_terms}}. Both the parties have made the said compromise of their own free will and without any pressure, threat or inducement, and both the parties agree to proceed further according to the said compromise. This Hon'ble Court may be pleased to take the said compromise purshis on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

સમાધાન પુરશીશ

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસના પક્ષકારો વચ્ચે {{settlement_terms}} એવી શરત ને આધીન પરસ્પર સમાધાન થયેલ છે. બંને પક્ષકારોએ પોતાની સ્વતંત્ર ઇચ્છાથી તથા કોઈપણ જાતના દબાણ, ધાકધમકી કે લાલચ વગર સદર સમાધાન કરેલ છે અને સદર સમાધાન મુજબ આગળની કાર્યવાહી કરવા બંને પક્ષકારો સંમત છે. સદર સમાધાન પુરશીશ રેકોર્ડ પર લઈ યોગ્ય કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "ulat_tapas_bandh",
        "name_en": "Application to Close Right of Cross-Examination",
        "name_gu": "ઉલટતપાસનો હક બંધ કરવાની અરજી",
        "category": "General",
        "aliases": ["ulat tapas", "ઉલટતપાસ", "cross examination bandh", "ઉલટતપાસનો હક બંધ"],
        "fields": [
            {"key": "witness_name", "label_en": "Name of the witness / complainant", "label_gu": "સાક્ષી / ફરીયાદીનું નામ", "type": "text", "required": True},
            {"key": "since_when", "label_en": "Absent since", "label_gu": "ઘણી મુદ્દતથી / આજ દીન સુધી", "type": "radio", "required": True,
             "options": [
                 {"value": "ઘણી મુદ્દતથી", "label_en": "Since many adjournments", "label_gu": "ઘણી મુદ્દતથી"},
                 {"value": "આજ દીન સુધી", "label_en": "Until today", "label_gu": "આજ દીન સુધી"},
             ]},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO CLOSE THE RIGHT OF CROSS-EXAMINATION

In the above matter, we, advocate of {{party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court and although the written testimony of {{witness_name}} is complete, the cross-examination of {{witness_name}} has not been carried out by {{opposite_party_role}}. Although sufficient opportunity was given to the opposite side for cross-examination, they have not remained present before this Hon'ble Court since {{since_when}}; it is in the interest of justice to close the right of cross-examination of {{witness_name}}. Therefore this Hon'ble Court may be pleased to close the right of {{opposite_party_role}} to cross-examine {{witness_name}} and proceed further by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

ઉલટતપાસનો હક બંધ કરવાની અરજી

સદર કામમા અમો {{party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર અને કેસમાં {{witness_name}}નાઓની લેખિત જુબાની પૂર્ણ થયેલ હોવા છતાં {{opposite_party_role}} તરફથી {{witness_name}} ની ઉલટતપાસ કરવામાં આવેલ નથી. સામાવાળા ને ઉલટતપાસ માટે પૂરતી તક આપવામાં આવેલ હોવા છતાં {{since_when}} આપ નામદાર સાહેબશ્રીની કોર્ટ સમક્ષ ઊપસ્થિત રહેલ ન હોય, સદર {{witness_name}} નાઓની ઉલટતપાસનો હક બંધ કરવો ન્યાયના હિતમાં છે. આથી {{opposite_party_role}} નો {{witness_name}} નાઓની ઉલટતપાસ કરવાનો હક બંધ કરી આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "ulat_tapas_khol",
        "name_en": "Application to Reopen Right of Cross-Examination",
        "name_gu": "ઉલટતપાસનો હક ફરીથી ખોલવાની અરજી",
        "category": "General",
        "aliases": ["ulat tapas khol", "ઉલટતપાસનો હક ખોલવાની", "reopen cross"],
        "fields": [
            {"key": "cross_reason", "label_en": "Reason why cross-examination could not be done", "label_gu": "ઉલટતપાસ ન થઈ શકવાનું યોગ્ય કારણ", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO REOPEN THE RIGHT OF CROSS-EXAMINATION

In the above matter, we, advocate of {{opposite_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. Our right of cross-examination has been closed by this Hon'ble Court. It could not be done due to {{cross_reason}}; and as the said reason is reasonable and proper, and as getting the opportunity to cross-examine is in the interest of justice, this Hon'ble Court may be pleased to reopen our right of cross-examination and give us the opportunity to cross-examine by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{opposite_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

ઉલટતપાસનો હક ફરીથી ખોલવાની અરજી

સદર કામમા અમો {{opposite_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. જેમા અમોનો ઉલટતપાસ કરવાનો હક આપ નામદાર કોર્ટ દ્વારા બંધ કરવામાં આવેલ છે. જે {{cross_reason}} હોવાના કારણોસર થઈ શકેલ નહિ તેમજ સદર કારણ વાજબી તેમજ યોગ્ય હોવાથી તથા ઉલટતપાસ કરવાની તક મળવીએ ન્યાયના હિતમા હોય, અમોનો ઉલટતપાસ કરવાનો હક ફરીથી ખોલી અમોને ઉલટતપાસ કરવાની તક આપવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "undertaking",
        "name_en": "Undertaking",
        "name_gu": "બાંહેધરી",
        "category": "General",
        "aliases": ["undertaking", "બાંહેધરી", "અંડરટેકિંગ"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "undertaking_matter", "label_en": "Matter / condition of the undertaking", "label_gu": "બાંહેધરીની બાબત / શરત", "type": "text", "required": True},
            {"key": "undertaking_action", "label_en": "Details / action to be performed", "label_gu": "બાંહેધરીની વિગત / કરવાની કાર્યવાહી", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

UNDERTAKING

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. As per the order of this Hon'ble Court in the said case, regarding {{undertaking_matter}}, we, the undersigned, hereby give this undertaking that we shall comply with {{undertaking_action}} and shall comply with the other orders and directions of this Hon'ble Court in the said case. This Hon'ble Court may therefore be pleased to take the said undertaking on record and pass appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

બાંહેધરી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં આપ નામદાર કોર્ટના હુકમ મુજબ {{undertaking_matter}} જે અંગે અમો નીચે સહી કરનાર તરફથી આ બાંહેધરી આપવામાં આવે છે કે, {{undertaking_action}} નું પાલન કરીશું તથા સદર કેસમાં આપ નામદાર કોર્ટના અન્ય હુકમો તથા નિર્દેશોનું પાલન કરીશું. જેથી સદર બાંહેધરી રેકોર્ડ પર લઈ યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "vakilatnama_civil",
        "name_en": "Vakalatnama (Civil)",
        "name_gu": "વકીલાતનામું (સિવિલ)",
        "category": "General",
        "aliases": ["vakilatnama", "વકીલાતનામું", "vakalatnama civil"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "party_sign_name", "label_en": "Name of the party signing", "label_gu": "પક્ષકારનું નામ", "type": "text", "required": True},
            {"key": "advocate_qualification", "label_en": "Advocate qualification", "label_gu": "લાયકાત", "type": "text", "required": False},
            {"key": "advocate_address", "label_en": "Advocate address", "label_gu": "સરનામું", "type": "text", "required": False},
            {"key": "advocate_mobile", "label_en": "Advocate mobile number", "label_gu": "મોબાઈલ નં", "type": "mobile", "required": False},
            {"key": "advocate_sanad", "label_en": "Advocate sanad / enrollment number", "label_gu": "સનદ નં", "type": "text", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
{{advocate_mobile}}
{{advocate_sanad}}
----------------------------------------------------

VAKALATNAMA

IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

We, as {{selected_party_role}}, in the above-mentioned suit, hereby give Advocate Shri {{advocate_name}} the authority and power to accept service of process, to appear before the Court, to make documents, to deposit money, to take back money, to obtain court-fee refund in his name, to receive amounts, to withdraw the suit on our behalf, to file appeal and to carry out other legal proceedings, and to carry out all necessary legal proceedings in connection with the said suit.

We accept the legal proceedings carried out by the said Advocate Shri on our behalf, and they shall remain binding on us.

Date : {{date_display}}
Place : {{taluka_place}}

Party's signature :-                    Advocate's signature :-
Party's name :- {{party_sign_name}}      Advocate's name :- {{advocate_name}}
""",
        "content_gu": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
{{advocate_mobile}}
{{advocate_sanad}}
----------------------------------------------------

વકીલાતનામું

મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

અમો {{selected_party_role}} તરીકે ઉપર દર્શાવેલ દાવામાં એડવોકેટશ્રી {{advocate_name}}, ને અમારા વતી કરારદાદ કબુલ કરવા તથા કોર્ટમાં હાજર રહેવા, દસ્તાવેજો કરવા, પૈસા રજુ કરવા, પૈસા પરત લેવા, તેમના નામનો કોર્ટફીઝ રીફંડનો દાખલો લેવા, રકમો લેવા, અમારા વતી દાવો પરત ખેંચી લેવા, અપીલ કરવા તેમજ અન્ય કાયદેસરની કાર્યવાહી કરવા અને સદર દાવા સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.

અમો સદર એડવોકેટશ્રી દ્વારા કરવામાં આવતી અમારા વતીની કાયદેસરની કાર્યવાહીને સ્વીકારીએ છીએ અને તે અમારા માટે બંધનકર્તા રહેશે.

તા. {{date_display}}
સ્થળ. {{taluka_place}}

પક્ષકારની સહી :-                    એડવોકેટની સહી :-
પક્ષકારનું નામ :- {{party_sign_name}}      એડવોકેટનું નામ :- {{advocate_name}}
""",
    },
    {
        "id": "vakilatnama_criminal",
        "name_en": "Vakalatnama (Criminal)",
        "name_gu": "વકીલાતનામું (ક્રિમિનલ)",
        "category": "Criminal",
        "aliases": ["vakalatnama criminal", "વકીલાતનામું", "criminal vakalatnama"],
        "fields": [
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "party_sign_name", "label_en": "Name of the party signing", "label_gu": "પક્ષકારનું નામ", "type": "text", "required": True},
            {"key": "advocate_qualification", "label_en": "Advocate qualification", "label_gu": "લાયકાત", "type": "text", "required": False},
            {"key": "advocate_address", "label_en": "Advocate address", "label_gu": "સરનામું", "type": "text", "required": False},
            {"key": "advocate_mobile", "label_en": "Advocate mobile number", "label_gu": "મોબાઈલ નં", "type": "mobile", "required": False},
            {"key": "advocate_sanad", "label_en": "Advocate sanad / enrollment number", "label_gu": "સનદ નં", "type": "text", "required": False},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
{{advocate_mobile}}
{{advocate_sanad}}
----------------------------------------------------

VAKALATNAMA

IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

We, as {{selected_party_role}}, in the above-mentioned case, hereby give Advocate Shri {{advocate_name}} the authority and power to appear on our behalf, to make applications, to give purshis, to produce documents, to give evidence, to examine and cross-examine witnesses, to compromise, to obtain certified copies, to file appeal, to file revision and to carry out other legal proceedings, and to carry out all necessary legal proceedings in connection with the said case.

We accept the legal proceedings carried out by the said Advocate Shri on our behalf, and they shall remain binding on us.

Date : {{date_display}}
Place : {{taluka_place}}

Party's signature :-                    Advocate's signature :-
Party's name :- {{party_sign_name}}      Advocate's name :- {{advocate_name}}
""",
        "content_gu": """{{advocate_name}}
{{advocate_qualification}}
{{advocate_address}}
{{advocate_mobile}}
{{advocate_sanad}}
----------------------------------------------------

વકીલાતનામું

મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

અમો {{selected_party_role}} તરીકે ઉપર દર્શાવેલ કેસમાં એડવોકેટશ્રી {{advocate_name}}, ને અમારા વતી હાજર રહેવા, અરજીઓ કરવા, પુરશીશ આપવા, દસ્તાવેજો રજૂ કરવા, પુરાવા આપવા, સાક્ષીઓની તપાસ તથા ઉલટતપાસ કરવા, સમાધાન કરવા, પ્રમાણિત નકલ મેળવવા અપીલ કરવા, રિવિઝન કરવા તેમજ અન્ય કાયદેસરની કાર્યવાહી કરવા અને સદર કેસ સંબંધે જરૂરી તમામ કાયદેસર કાર્યવાહી કરવા માટે સત્તા અને અધિકાર આપીએ છીએ.

અમો સદર એડવોકેટશ્રી દ્વારા કરવામાં આવતી અમારા વતીની કાયદેસરની કાર્યવાહીને સ્વીકારીએ છીએ અને તે અમારા માટે બંધનકર્તા રહેશે.

તા. {{date_display}}
સ્થળ. {{taluka_place}}

પક્ષકારની સહી :-                    એડવોકેટની સહી :-
પક્ષકારનું નામ :- {{party_sign_name}}      એડવોકેટનું નામ :- {{advocate_name}}
""",
    },
    {
        "id": "warrant_hathbido",
        "name_en": "Application for Hand Delivery of Summons / Warrant",
        "name_gu": "સમન્સ/વોરંટનો હાથબીડો આપવા અરજી",
        "category": "Criminal",
        "aliases": ["hathbido", "હાથબીડો", "hand delivery", "warrant hand"],
        "fields": [
            {"key": "process_type", "label_en": "Process", "label_gu": "સમન્સ / વોરંટ", "type": "radio", "required": True,
             "options": [
                 {"value": "સમન્સ", "label_en": "Summons", "label_gu": "સમન્સ"},
                 {"value": "વોરંટ", "label_en": "Warrant", "label_gu": "વોરંટ"},
             ]},
            {"key": "process_target", "label_en": "Against whom", "label_gu": "આરોપી / સામાવાળા / સાક્ષી", "type": "radio", "required": True,
             "options": [
                 {"value": "આરોપી", "label_en": "Accused", "label_gu": "આરોપી"},
                 {"value": "સામાવાળા", "label_en": "Opposite party", "label_gu": "સામાવાળા"},
                 {"value": "સાક્ષી", "label_en": "Witness", "label_gu": "સાક્ષી"},
             ]},
            {"key": "advocate_side", "label_en": "Advocate acting on behalf of", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "source": "case_parties",
             "options": [
                 {"value": "party", "label_en": "Applicant / Plaintiff side", "label_gu": "ફરિયાદી / અરજદાર / વાદી તરફથી"},
                 {"value": "opposite", "label_en": "Opposite party side", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી તરફથી"},
             ]},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION FOR HAND DELIVERY OF {{process_type}}

In the above matter, we, advocate of {{selected_party_role}}, most respectfully submit this application to this Hon'ble Court that.....

The said case is pending before this Hon'ble Court. In the said case, {{process_type}} has been issued to {{process_target}} for service, the service of which is not being effected properly; and as proper service of the said {{process_type}} is in the interest of justice, it is necessary to give hand delivery for service of the said {{process_type}}. Therefore this Hon'ble Court may be pleased to give the necessary hand delivery of the summons/warrant and get it served by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{selected_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

સમન્સ/વોરંટનો હાથબીડો આપવા અરજી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{process_target}}ને બજવણી માટે {{process_type}} ઇશ્યુ કરવામા આવેલ છે જેની બજવણી યોગ્ય રીતે ન થતી હોય, તેમજ સદર {{process_type}} ની યોગ્ય રીતે બજવણી થવી ન્યાયના હિતમાં હોય, સદર {{process_type}} ની બજવણી કરાવવા માટે હાથબીડો આપવો જરૂરી છે. જેથી સમન્સ/વોરંટનો જરૂરી હાથબીડો આપી બજવણી કરાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
    {
        "id": "warrant_rad",
        "name_en": "Application to Cancel Warrant",
        "name_gu": "વોરંટ રદ કરવાની અરજી",
        "category": "Criminal",
        "aliases": ["warrant cancel", "વોરંટ રદ", "warrant rad"],
        "fields": [
            {"key": "warrant_date", "label_en": "Date the warrant was issued", "label_gu": "કઈ તારીખે વોરંટ કાઢવામાં આવેલ છે તે તારીખ", "type": "date", "required": True},
            {"key": "absence_reason", "label_en": "Reasonable cause of absence", "label_gu": "ગેરહાજરીનું યોગ્ય કારણ", "type": "textarea", "required": True},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}},
{{taluka_place}}

{{case_type}} No. {{case_number}}

{{party_line}}
Versus
{{opposite_party_line}}

APPLICATION TO CANCEL WARRANT

In the above matter, we, advocate of the accused, most respectfully submit this application to this Hon'ble Court that...

The said case is pending before this Hon'ble Court. In the said case, a warrant has been issued against {{opposite_party_role}} on {{warrant_date}}. Before the said warrant could be served, the {{opposite_party_role}} has remained present before this Hon'ble Court today, and was absent due to {{absence_reason}}. There is no intention to disrespect or to delay the proceedings of this Hon'ble Court. Moreover, the said {{opposite_party_role}} shall hereinafter remain regularly present on every date of the case and extend full cooperation in the proceedings of this Hon'ble Court. Therefore this Hon'ble Court may be pleased to cancel the warrant issued against the said {{opposite_party_role}} and proceed further in the case by passing appropriate orders.

Date : {{date_display}}
Place : {{taluka_place}}

Advocate of {{opposite_party_role}}
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,
{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{party_line}}
વિરુદ્ધ
{{opposite_party_line}}

વોરંટ રદ કરવાની અરજી

સદર કામમાં અમો {{opposite_party_role}}ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે...

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ ચાલવા પર છે. સદર કેસમાં {{opposite_party_role}} વિરુદ્ધ તા. {{warrant_date}}ના રોજ વોરંટ કાઢવામાં આવેલ છે. સદર વોરંટની બજવણી થઈ શકે તે પહેલાં {{opposite_party_role}} આજ રોજ આપ નામદાર કોર્ટ સમક્ષ હાજર થયેલ છે તથા {{absence_reason}} કારણોસર ગેરહાજર રહેલ છે. ગેરહાજર રહેવાનો કોઈ દુર્ભાવ કે આપ નામદાર કોર્ટની કાર્યવાહીમાં વિલંબ કરવાનો આશય નથી. વધુમાં સદર {{opposite_party_role}} હવે પછી કેસની દરેક તારીખે નિયમિત હાજર રહી આપ નામદાર કોર્ટની કાર્યવાહીમાં સંપૂર્ણ સહકાર આપશે. જેથી સદર {{opposite_party_role}} વિરુદ્ધ કાઢવામાં આવેલ વોરંટ રદ કરી કેસમાં આગળની કાર્યવાહી કરવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{taluka_place}}

{{opposite_party_role}}ના એડવોકેટ
""",
    },
]

# Default settings applied to every v2 template (page size + robust font stack).
for _t in TEMPLATES_V2:
    _t.setdefault("settings", {})
    _t["settings"].setdefault("page_size", "A4")
    _t["settings"].setdefault("gujarati_font", "Noto Sans Gujarati")

TEMPLATES_V2_IDS = {t["id"] for t in TEMPLATES_V2}
