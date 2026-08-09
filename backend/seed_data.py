"""Seed data for NyaySetu Pro - case types, laws, districts, templates."""

CASE_TYPES = [
    {"id": "civil_suit", "en": "Civil Suit", "gu": "સિવિલ સૂટ", "cat": "Civil"},
    {"id": "regular_civil_suit", "en": "Regular Civil Suit", "gu": "રેગ્યુલર સિવિલ સૂટ", "cat": "Civil"},
    {"id": "special_civil_suit", "en": "Special Civil Suit", "gu": "સ્પેશિયલ સિવિલ સૂટ", "cat": "Civil"},
    {"id": "commercial_suit", "en": "Commercial Suit", "gu": "કોમર્શિયલ સૂટ", "cat": "Civil"},
    {"id": "civil_appeal", "en": "Civil Appeal", "gu": "સિવિલ અપીલ", "cat": "Civil"},
    {"id": "civil_revision", "en": "Civil Revision", "gu": "સિવિલ રિવિઝન", "cat": "Civil"},
    {"id": "execution", "en": "Execution", "gu": "એક્ઝિક્યુશન", "cat": "Civil"},
    {"id": "misc_civil_app", "en": "Miscellaneous Civil Application", "gu": "મિસલેનિયસ સિવિલ અરજી", "cat": "Civil"},
    {"id": "interim_app", "en": "Interim Application", "gu": "ઇન્ટરિમ અરજી", "cat": "Civil"},
    {"id": "other_civil", "en": "Other Civil Matter", "gu": "અન્ય સિવિલ બાબત", "cat": "Civil"},
    {"id": "criminal_case", "en": "Criminal Case", "gu": "ક્રિમિનલ કેસ", "cat": "Criminal"},
    {"id": "criminal_complaint", "en": "Criminal Complaint", "gu": "ક્રિમિનલ ફરિયાદ", "cat": "Criminal"},
    {"id": "criminal_appeal", "en": "Criminal Appeal", "gu": "ક્રિમિનલ અપીલ", "cat": "Criminal"},
    {"id": "criminal_revision", "en": "Criminal Revision", "gu": "ક્રિમિનલ રિવિઝન", "cat": "Criminal"},
    {"id": "criminal_misc_app", "en": "Criminal Miscellaneous Application", "gu": "ક્રિમિનલ મિસ. અરજી", "cat": "Criminal"},
    {"id": "bail_application", "en": "Bail Application", "gu": "જામીન અરજી", "cat": "Criminal"},
    {"id": "regular_bail", "en": "Regular Bail", "gu": "રેગ્યુલર બેલ", "cat": "Criminal"},
    {"id": "anticipatory_bail", "en": "Anticipatory Bail", "gu": "એન્ટિસિપેટરી બેલ", "cat": "Criminal"},
    {"id": "sessions_case", "en": "Sessions Case", "gu": "સેશન્સ કેસ", "cat": "Criminal"},
    {"id": "summons_case", "en": "Summons Case", "gu": "સમન્સ કેસ", "cat": "Criminal"},
    {"id": "warrant_case", "en": "Warrant Case", "gu": "વોરંટ કેસ", "cat": "Criminal"},
    {"id": "other_criminal", "en": "Other Criminal Matter", "gu": "અન્ય ક્રિમિનલ બાબત", "cat": "Criminal"},
    {"id": "other", "en": "Other", "gu": "અન્ય", "cat": "Other"},
]

LAWS = [
    {
        "id": "ni_act",
        "en": "Negotiable Instruments Act",
        "gu": "નેગોશિએબલ ઇન્સ્ટ્રુમેન્ટ્સ એક્ટ",
        "sections": [
            {"id": "138", "label": "Section 138 - Dishonour of cheque"},
            {"id": "141", "label": "Section 141 - Offences by companies"},
            {"id": "142", "label": "Section 142 - Cognizance of offences"},
        ],
    },
    {
        "id": "dv_act",
        "en": "Domestic Violence Act",
        "gu": "ડોમેસ્ટિક વાયોલન્સ એક્ટ",
        "sections": [
            {"id": "12", "label": "Section 12 - Application to Magistrate"},
            {"id": "18", "label": "Section 18 - Protection order"},
            {"id": "19", "label": "Section 19 - Residence order"},
            {"id": "20", "label": "Section 20 - Monetary relief"},
        ],
    },
    {
        "id": "consumer",
        "en": "Consumer Protection",
        "gu": "કન્ઝ્યુમર પ્રોટેક્શન",
        "sections": [
            {"id": "35", "label": "Section 35 - Complaint by consumer"},
            {"id": "38", "label": "Section 38 - Procedure on admission"},
        ],
    },
    {
        "id": "defamation",
        "en": "Defamation",
        "gu": "ડિફેમેશન",
        "sections": [
            {"id": "499", "label": "Section 499 IPC - Defamation"},
            {"id": "500", "label": "Section 500 IPC - Punishment"},
        ],
    },
    {
        "id": "maintenance",
        "en": "Maintenance",
        "gu": "મેન્ટેનન્સ",
        "sections": [
            {"id": "125", "label": "Section 125 CrPC - Maintenance of wife/children"},
        ],
    },
    {
        "id": "family_related",
        "en": "Family Related",
        "gu": "કૌટુંબિક બાબત",
        "sections": [
            {"id": "hma_9", "label": "Section 9 HMA - Restitution of conjugal rights"},
            {"id": "hma_13", "label": "Section 13 HMA - Divorce"},
            {"id": "hma_26", "label": "Section 26 HMA - Custody of children"},
        ],
    },
    {
        "id": "property_related",
        "en": "Property Related",
        "gu": "મિલકત સંબંધિત",
        "sections": [
            {"id": "spa_5", "label": "Section 5 SRA - Recovery of possession"},
            {"id": "tpa_54", "label": "Section 54 TPA - Sale of property"},
            {"id": "cpc_o39", "label": "Order 39 CPC - Temporary injunction"},
        ],
    },
    {
        "id": "other_law",
        "en": "Other",
        "gu": "અન્ય",
        "sections": [],
    },
]

DISTRICTS = [
    {"id": "ahmedabad", "en": "Ahmedabad", "gu": "અમદાવાદ"},
    {"id": "gandhinagar", "en": "Gandhinagar", "gu": "ગાંધીનગર"},
    {"id": "surat", "en": "Surat", "gu": "સુરત"},
    {"id": "vadodara", "en": "Vadodara", "gu": "વડોદરા"},
    {"id": "rajkot", "en": "Rajkot", "gu": "રાજકોટ"},
    {"id": "bhavnagar", "en": "Bhavnagar", "gu": "ભાવનગર"},
    {"id": "jamnagar", "en": "Jamnagar", "gu": "જામનગર"},
    {"id": "junagadh", "en": "Junagadh", "gu": "જૂનાગઢ"},
    {"id": "anand", "en": "Anand", "gu": "આણંદ"},
    {"id": "kutch", "en": "Kutch", "gu": "કચ્છ"},
    {"id": "mehsana", "en": "Mehsana", "gu": "મહેસાણા"},
    {"id": "patan", "en": "Patan", "gu": "પાટણ"},
]

# Templates use placeholder {{field}} for substitution.
# fields: list of {key, label_en, label_gu, type, required}
TEMPLATES = [
    {
        "id": "adjournment",
        "name_en": "Adjournment Application",
        "name_gu": "મુદત અરજી",
        "category": "General",
        "aliases": ["mudat", "mudat arji", "adjournment", "adjournment application", "date application", "મુદત", "મુદત અરજી"],
        "fields": [
            {"key": "next_date", "label_en": "Next Requested Date", "label_gu": "આગામી માંગેલ તારીખ", "type": "date", "required": True},
            {"key": "reason", "label_en": "Reason for Adjournment", "label_gu": "મુદત માટેનું કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

{{party_name}} ...Applicant
Versus
Opposite Party ...Respondent

APPLICATION FOR ADJOURNMENT

Most Respectfully Sheweth:

1. That the above-noted matter is fixed for hearing today.

2. That due to {{reason}}, the applicant is unable to proceed with the matter today.

3. It is therefore most humbly prayed that this Hon'ble Court may be pleased to adjourn the matter to {{next_date}} in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

{{party_name}} ...અરજદાર
વિરુદ્ધ
સામાવાળા પક્ષ ...પ્રતિવાદી

મુદત અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ આજ રોજ સુનાવણી માટે નિર્ધારિત છે.

૨. {{reason}} ના કારણે અરજદાર આજે કેસ ચલાવવા અસમર્થ છે.

૩. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય કૃપા કરીને {{next_date}} ના રોજ સુધી મુદત આપવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "certified_copy",
        "name_en": "Certified Copy Application",
        "name_gu": "પ્રમાણિત નકલ માટે અરજી",
        "category": "General",
        "aliases": ["certified copy", "certified copy application", "pramanit nakal", "પ્રમાણિત નકલ", "certified", "copy"],
        "fields": [
            {"key": "document_desc", "label_en": "Document/Order Description", "label_gu": "દસ્તાવેજ / હુકમનું વર્ણન", "type": "textarea", "required": True},
            {"key": "order_date", "label_en": "Order Date", "label_gu": "હુકમની તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR CERTIFIED COPY

Most Respectfully Sheweth:

1. That the above matter is pending before this Hon'ble Court.

2. The applicant requires a certified copy of the following document/order dated {{order_date}}:

{{document_desc}}

3. It is therefore prayed that this Hon'ble Court may be pleased to grant a certified copy of the said document/order at the earliest.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

પ્રમાણિત નકલ માટે અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ આ માનનીય ન્યાયાલય સમક્ષ ચાલુ છે.

૨. અરજદારને નીચે જણાવેલ તારીખ {{order_date}} ના દસ્તાવેજ / હુકમની પ્રમાણિત નકલની જરૂર છે:

{{document_desc}}

૩. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય કૃપા કરીને ઉક્ત દસ્તાવેજ / હુકમની પ્રમાણિત નકલ સત્વરે આપવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "exemption_appearance",
        "name_en": "Exemption from Personal Appearance",
        "name_gu": "હાજરી માફીની અરજી",
        "category": "General",
        "aliases": ["exemption", "hajri mafi", "હાજરી માફી", "personal appearance", "attendance exemption"],
        "fields": [
            {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True},
            {"key": "hearing_date", "label_en": "Hearing Date", "label_gu": "સુનાવણી તારીખ", "type": "date", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR EXEMPTION FROM PERSONAL APPEARANCE

Most Respectfully Sheweth:

1. The above matter is fixed for hearing on {{hearing_date}} before this Hon'ble Court.

2. The applicant is unable to remain personally present on the said date due to {{reason}}.

3. The undersigned advocate is authorized to represent the applicant.

4. It is therefore prayed that this Hon'ble Court may be pleased to grant exemption from personal appearance of the applicant on {{hearing_date}}.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

હાજરી માફીની અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ {{hearing_date}} ના રોજ સુનાવણી માટે નિર્ધારિત છે.

૨. {{reason}} ના કારણે અરજદાર ઉક્ત તારીખે વ્યક્તિગત હાજર રહી શકે તેમ નથી.

૩. નીચે સહી કરનાર વકીલ અરજદારનું પ્રતિનિધિત્વ કરવા અધિકૃત છે.

૪. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય {{hearing_date}} ના રોજ અરજદારને વ્યક્તિગત હાજરીમાંથી મુક્તિ આપવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "cross_close",
        "name_en": "Application to Close Cross-Examination",
        "name_gu": "ઉલટ તપાસનો હક બંધ કરવા બાબત અરજી",
        "category": "General",
        "aliases": ["cross close", "ulat tapas", "ઉલટ તપાસ", "close cross examination"],
        "fields": [
            {"key": "witness_name", "label_en": "Witness Name", "label_gu": "સાક્ષીનું નામ", "type": "text", "required": True},
            {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION TO CLOSE THE RIGHT OF CROSS-EXAMINATION

Most Respectfully Sheweth:

1. The witness {{witness_name}} was to be cross-examined by the opposite party.

2. Despite sufficient opportunities, the opposite party has failed to cross-examine the witness. {{reason}}

3. It is therefore prayed that the right of cross-examination of the said witness be closed in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

ઉલટ તપાસનો હક બંધ કરવા બાબત અરજી

નમ્રપણે વિનંતી છે કે:

૧. સાક્ષી {{witness_name}} ની સામાવાળા પક્ષ દ્વારા ઉલટ તપાસ કરવાની હતી.

૨. પૂરતી તકો આપ્યા છતાં સામાવાળા પક્ષ ઉલટ તપાસ કરવામાં નિષ્ફળ રહેલ છે. {{reason}}

૩. તેથી ન્યાયના હિતમાં ઉક્ત સાક્ષીની ઉલટ તપાસનો હક બંધ કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "evidence_produce",
        "name_en": "Application to Produce Evidence",
        "name_gu": "પુરાવા રજૂ કરવાની અરજી",
        "category": "General",
        "aliases": ["produce evidence", "purava", "પુરાવા"],
        "fields": [
            {"key": "evidence_desc", "label_en": "Evidence Description", "label_gu": "પુરાવાનું વર્ણન", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION TO PRODUCE EVIDENCE

Most Respectfully Sheweth:

1. The applicant wishes to produce the following evidence in support of the case:

{{evidence_desc}}

2. The said evidence is essential for adjudication of the matter.

3. It is therefore prayed that this Hon'ble Court may be pleased to allow the applicant to produce the above evidence on record.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

પુરાવા રજૂ કરવાની અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર કેસના સમર્થનમાં નીચેના પુરાવા રજૂ કરવા ઇચ્છે છે:

{{evidence_desc}}

૨. આ પુરાવા કેસનો નિર્ણય કરવા માટે અતિ આવશ્યક છે.

૩. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય ઉક્ત પુરાવા રેકોર્ડ પર લેવાની પરવાનગી આપશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "document_produce",
        "name_en": "Application to Produce Documents",
        "name_gu": "દસ્તાવેજ રજૂ કરવાની અરજી",
        "category": "General",
        "aliases": ["produce document", "dastavej", "દસ્તાવેજ"],
        "fields": [
            {"key": "document_list", "label_en": "List of Documents", "label_gu": "દસ્તાવેજોની યાદી", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION TO PRODUCE DOCUMENTS

Most Respectfully Sheweth:

1. The applicant wishes to place on record the following documents:

{{document_list}}

2. The said documents are relevant for the just adjudication of the matter.

3. It is therefore prayed that this Hon'ble Court may be pleased to take the said documents on record.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

દસ્તાવેજ રજૂ કરવાની અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર નીચેના દસ્તાવેજો રેકોર્ડ પર મૂકવા ઇચ્છે છે:

{{document_list}}

૨. આ દસ્તાવેજો કેસના યોગ્ય નિર્ણય માટે પ્રસ્તુત છે.

૩. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય ઉક્ત દસ્તાવેજો રેકોર્ડ પર લેવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "time_extension",
        "name_en": "Application for Time Extension",
        "name_gu": "સમય આપવા બાબત અરજી",
        "category": "General",
        "aliases": ["time", "extension", "samay", "સમય"],
        "fields": [
            {"key": "purpose", "label_en": "Purpose", "label_gu": "હેતુ", "type": "textarea", "required": True},
            {"key": "days", "label_en": "Days Required", "label_gu": "જરૂરી દિવસો", "type": "number", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR EXTENSION OF TIME

Most Respectfully Sheweth:

1. The applicant requires additional time of {{days}} days for {{purpose}}.

2. It is therefore prayed that this Hon'ble Court may be pleased to grant {{days}} days' extension in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

સમય આપવા બાબત અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદારને {{purpose}} માટે {{days}} દિવસનો વધારાનો સમય જરૂરી છે.

૨. તેથી ન્યાયના હિતમાં {{days}} દિવસનો સમય આપવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "case_transfer",
        "name_en": "Case Transfer Application",
        "name_gu": "કેસ ટ્રાન્સફર સંબંધિત અરજી",
        "category": "General",
        "aliases": ["transfer", "case transfer", "ટ્રાન્સફર"],
        "fields": [
            {"key": "transfer_to", "label_en": "Transfer To Court", "label_gu": "કોઈ કોર્ટમાં ટ્રાન્સફર", "type": "text", "required": True},
            {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR TRANSFER OF CASE

Most Respectfully Sheweth:

1. The applicant seeks transfer of the above case to {{transfer_to}}.

2. The reason for the transfer is: {{reason}}

3. It is therefore prayed that this Hon'ble Court may be pleased to transfer the above matter to {{transfer_to}}.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

કેસ ટ્રાન્સફર સંબંધિત અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર ઉપરોક્ત કેસને {{transfer_to}} માં ટ્રાન્સફર કરવા વિનંતી કરે છે.

૨. ટ્રાન્સફર માટેનું કારણ: {{reason}}

૩. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય ઉપરોક્ત કેસ {{transfer_to}} માં ટ્રાન્સફર કરવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "recall",
        "name_en": "Recall Application",
        "name_gu": "રિકોલ અરજી",
        "category": "General",
        "aliases": ["recall", "રિકોલ"],
        "fields": [
            {"key": "order_date", "label_en": "Date of Order to Recall", "label_gu": "રિકોલ કરવાનો હુકમ તારીખ", "type": "date", "required": True},
            {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

RECALL APPLICATION

Most Respectfully Sheweth:

1. Order dated {{order_date}} was passed in the above matter.

2. The applicant seeks recall of the said order for the following reasons: {{reason}}

3. It is therefore prayed that the said order dated {{order_date}} be recalled in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

રિકોલ અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસમાં {{order_date}} ના રોજ હુકમ પસાર થયેલ છે.

૨. અરજદાર નીચેના કારણોસર ઉક્ત હુકમને પરત ખેંચવા વિનંતી કરે છે: {{reason}}

૩. તેથી ન્યાયના હિતમાં {{order_date}} નો હુકમ પરત ખેંચવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "warrant_cancel",
        "name_en": "Warrant Cancellation Application",
        "name_gu": "વોરંટ રદ કરવાની અરજી",
        "category": "Criminal",
        "aliases": ["warrant", "warrant cancel", "વોરંટ"],
        "fields": [
            {"key": "warrant_date", "label_en": "Warrant Date", "label_gu": "વોરંટ તારીખ", "type": "date", "required": True},
            {"key": "reason", "label_en": "Reason", "label_gu": "કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR CANCELLATION OF WARRANT

Most Respectfully Sheweth:

1. A warrant dated {{warrant_date}} was issued against the applicant.

2. The applicant could not appear due to {{reason}}.

3. It is therefore prayed that the warrant dated {{warrant_date}} be cancelled in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

વોરંટ રદ કરવાની અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર વિરુદ્ધ {{warrant_date}} ના રોજ વોરંટ ઈસ્યુ થયેલ છે.

૨. {{reason}} ના કારણે અરજદાર હાજર રહી શકેલ ન હતા.

૩. તેથી ન્યાયના હિતમાં {{warrant_date}} નું વોરંટ રદ કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "bail_regular",
        "name_en": "Regular Bail Application",
        "name_gu": "નિયમિત જામીન અરજી",
        "category": "Criminal",
        "aliases": ["bail", "regular bail", "જામીન"],
        "fields": [
            {"key": "fir_number", "label_en": "FIR Number", "label_gu": "FIR નંબર", "type": "text", "required": True},
            {"key": "arrest_date", "label_en": "Arrest Date", "label_gu": "ધરપકડની તારીખ", "type": "date", "required": True},
            {"key": "grounds", "label_en": "Grounds for Bail", "label_gu": "જામીન માટેના કારણો", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}
FIR No. {{fir_number}}

REGULAR BAIL APPLICATION

Most Respectfully Sheweth:

1. The applicant was arrested on {{arrest_date}} in connection with FIR No. {{fir_number}}.

2. Grounds for bail: {{grounds}}

3. The applicant undertakes to abide by all conditions imposed by this Hon'ble Court.

4. It is therefore prayed that this Hon'ble Court may be pleased to release the applicant on regular bail.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}
FIR નં. {{fir_number}}

નિયમિત જામીન અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદારને FIR નં. {{fir_number}} ના સંદર્ભમાં {{arrest_date}} ના રોજ ધરપકડ કરવામાં આવેલ છે.

૨. જામીન માટેના કારણો: {{grounds}}

૩. અરજદાર માનનીય ન્યાયાલય દ્વારા નિર્ધારિત તમામ શરતોનું પાલન કરવા બંધાય છે.

૪. તેથી નમ્રપણે વિનંતી છે કે માનનીય ન્યાયાલય અરજદારને નિયમિત જામીન પર મુક્ત કરવા હુકમ કરશો.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "affidavit",
        "name_en": "General Affidavit",
        "name_gu": "સોગંદનામું",
        "category": "General",
        "aliases": ["affidavit", "sogandnamu", "સોગંદનામું"],
        "fields": [
            {"key": "deponent_name", "label_en": "Deponent Name", "label_gu": "ડિપોનન્ટનું નામ", "type": "text", "required": True},
            {"key": "father_name", "label_en": "Father's Name", "label_gu": "પિતાનું નામ", "type": "text", "required": True},
            {"key": "age", "label_en": "Age", "label_gu": "ઉંમર", "type": "number", "required": True},
            {"key": "address", "label_en": "Address", "label_gu": "સરનામું", "type": "textarea", "required": True},
            {"key": "statement", "label_en": "Statement/Facts", "label_gu": "નિવેદન / હકીકતો", "type": "textarea", "required": True},
        ],
        "content_en": """AFFIDAVIT

I, {{deponent_name}}, s/o {{father_name}}, aged {{age}} years, residing at {{address}}, do hereby solemnly affirm and declare on oath as under:

1. I am the deponent above named and am fully conversant with the facts stated below.

2. {{statement}}

3. Whatever is stated above is true to the best of my knowledge, information and belief.

Place: {{district}}
Date: {{today}}

DEPONENT
{{deponent_name}}

VERIFICATION
Verified at {{district}} on this {{today}} that the contents of the above affidavit are true and correct.

DEPONENT
""",
        "content_gu": """સોગંદનામું

હું, {{deponent_name}}, પિતા {{father_name}}, ઉંમર {{age}} વર્ષ, રહેવાસી {{address}}, સોગંદ પર જાહેર કરું છું કે:

૧. હું ઉપર જણાવેલ ડિપોનન્ટ છું અને નીચે જણાવેલ હકીકતોથી સંપૂર્ણ પરિચિત છું.

૨. {{statement}}

૩. ઉપર જણાવેલી બાબતો મારી જાણ, માહિતી અને માન્યતા મુજબ સાચી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

ડિપોનન્ટ
{{deponent_name}}

પ્રમાણપત્ર
{{district}} ખાતે આજ રોજ {{today}} ના રોજ ઉપરોક્ત સોગંદનામામાં જણાવેલ બાબતો સાચી અને યોગ્ય છે તેમ પ્રમાણિત કરું છું.

ડિપોનન્ટ
""",
    },
]

PLANS = [
    {"id": "single", "name": "Pay Per Template", "price": 9, "credits": 1, "popular": False, "per_template": 9.0},
    {"id": "plan_299", "name": "Starter Pack", "price": 299, "credits": 51, "popular": False, "per_template": 5.86},
    {"id": "plan_499", "name": "Professional Pack", "price": 499, "credits": 251, "popular": True, "per_template": 1.99},
    {"id": "plan_999", "name": "Premium Pack", "price": 999, "credits": 1111, "popular": False, "per_template": 0.90},
]

QUOTES = [
    "Justice begins with preparation.",
    "The best advocate is the best prepared.",
    "Preparation is the mother of success.",
    "Law is the last result of human wisdom.",
    "Where law ends, tyranny begins.",
]
