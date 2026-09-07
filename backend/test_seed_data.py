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
    {"id": "amreli", "en": "Amreli", "gu": "અમરેલી"},
    {"id": "aravalli", "en": "Aravalli", "gu": "અરવલ્લી"},
    {"id": "banaskantha", "en": "Banaskantha", "gu": "બનાસકાંઠા"},
    {"id": "bharuch", "en": "Bharuch", "gu": "ભરૂચ"},
    {"id": "botad", "en": "Botad", "gu": "બોટાદ"},
    {"id": "chhota_udaipur", "en": "Chhota Udaipur", "gu": "છોટાઉદેપુર"},
    {"id": "dahod", "en": "Dahod", "gu": "દાહોદ"},
    {"id": "dang", "en": "Dang", "gu": "ડાંગ"},
    {"id": "devbhoomi_dwarka", "en": "Devbhoomi Dwarka", "gu": "દેવભૂમિ દ્વારકા"},
    {"id": "gir_somnath", "en": "Gir Somnath", "gu": "ગીર સોમનાથ"},
    {"id": "kheda", "en": "Kheda", "gu": "ખેડા"},
    {"id": "mahisagar", "en": "Mahisagar", "gu": "મહીસાગર"},
    {"id": "morbi", "en": "Morbi", "gu": "મોરબી"},
    {"id": "narmada", "en": "Narmada", "gu": "નર્મદા"},
    {"id": "navsari", "en": "Navsari", "gu": "નવસારી"},
    {"id": "panchmahal", "en": "Panchmahal", "gu": "પંચમહાલ"},
    {"id": "porbandar", "en": "Porbandar", "gu": "પોરબંદર"},
    {"id": "sabarkantha", "en": "Sabarkantha", "gu": "સાબરકાંઠા"},
    {"id": "surendranagar", "en": "Surendranagar", "gu": "સુરેન્દ્રનગર"},
    {"id": "tapi", "en": "Tapi", "gu": "તાપી"},
    {"id": "valsad", "en": "Valsad", "gu": "વલસાડ"},
    {"id": "vav_tharad", "en": "Vav-Tharad", "gu": "વાવ-થરાદ"},
]

# Talukas under each district (authoritative: Gujarati Wikipedia district table, 2024/2025 revision).
# District -> taluka dependency used by forms, autofill and validation.
TALUKAS = [
    {"id": "ahmedabad_city_east", "district_id": "ahmedabad", "en": "Ahmedabad City (East)", "gu": "અમદાવાદ સીટી (પૂર્વ)"},
    {"id": "ahmedabad_city_west", "district_id": "ahmedabad", "en": "Ahmedabad City (West)", "gu": "અમદાવાદ સીટી (પશ્ચિમ)"},
    {"id": "bavla", "district_id": "ahmedabad", "en": "Bavla", "gu": "બાવળા"},
    {"id": "daskroi", "district_id": "ahmedabad", "en": "Daskroi", "gu": "દસ્ક્રોઇ"},
    {"id": "detroj_rampura", "district_id": "ahmedabad", "en": "Detroj-Rampura", "gu": "દેત્રોજ-રામપુરા"},
    {"id": "dhandhuka", "district_id": "ahmedabad", "en": "Dhandhuka", "gu": "ધંધુકા"},
    {"id": "dholera", "district_id": "ahmedabad", "en": "Dholera", "gu": "ધોલેરા"},
    {"id": "dholka", "district_id": "ahmedabad", "en": "Dholka", "gu": "ધોળકા"},
    {"id": "mandal", "district_id": "ahmedabad", "en": "Mandal", "gu": "માંડલ"},
    {"id": "sanand", "district_id": "ahmedabad", "en": "Sanand", "gu": "સાણંદ"},
    {"id": "viramgam", "district_id": "ahmedabad", "en": "Viramgam", "gu": "વિરમગામ"},
    {"id": "amreli", "district_id": "amreli", "en": "Amreli", "gu": "અમરેલી"},
    {"id": "babra", "district_id": "amreli", "en": "Babra", "gu": "બાબરા"},
    {"id": "bagasara", "district_id": "amreli", "en": "Bagasara", "gu": "બગસરા"},
    {"id": "dhari", "district_id": "amreli", "en": "Dhari", "gu": "ધારી"},
    {"id": "jafrabad", "district_id": "amreli", "en": "Jafrabad", "gu": "જાફરાબાદ"},
    {"id": "kunkavav", "district_id": "amreli", "en": "Kunkavav", "gu": "કુંકાવાવ"},
    {"id": "lathi", "district_id": "amreli", "en": "Lathi", "gu": "લાઠી"},
    {"id": "rajula", "district_id": "amreli", "en": "Rajula", "gu": "રાજુલા"},
    {"id": "savarkundla", "district_id": "amreli", "en": "Savarkundla", "gu": "સાવરકુંડલા"},
    {"id": "lilia", "district_id": "amreli", "en": "Lilia", "gu": "લીલીયા"},
    {"id": "khambha", "district_id": "amreli", "en": "Khambha", "gu": "ખાંભા"},
    {"id": "anand", "district_id": "anand", "en": "Anand", "gu": "આણંદ"},
    {"id": "anklav", "district_id": "anand", "en": "Anklav", "gu": "આંકલાવ"},
    {"id": "borsad", "district_id": "anand", "en": "Borsad", "gu": "બોરસદ"},
    {"id": "khambhat", "district_id": "anand", "en": "Khambhat", "gu": "ખંભાત"},
    {"id": "petlad", "district_id": "anand", "en": "Petlad", "gu": "પેટલાદ"},
    {"id": "sojitra", "district_id": "anand", "en": "Sojitra", "gu": "સોજિત્રા"},
    {"id": "tarapur", "district_id": "anand", "en": "Tarapur", "gu": "તારાપુર"},
    {"id": "umreth", "district_id": "anand", "en": "Umreth", "gu": "ઉમરેઠ"},
    {"id": "modasa", "district_id": "aravalli", "en": "Modasa", "gu": "મોડાસા"},
    {"id": "bayad", "district_id": "aravalli", "en": "Bayad", "gu": "બાયડ"},
    {"id": "bhiloda", "district_id": "aravalli", "en": "Bhiloda", "gu": "ભિલોડા"},
    {"id": "dhansura", "district_id": "aravalli", "en": "Dhansura", "gu": "ધનસુરા"},
    {"id": "malpur", "district_id": "aravalli", "en": "Malpur", "gu": "માલપુર"},
    {"id": "meghraj", "district_id": "aravalli", "en": "Meghraj", "gu": "મેઘરજ"},
    {"id": "palanpur", "district_id": "banaskantha", "en": "Palanpur", "gu": "પાલનપુર"},
    {"id": "amirgadh", "district_id": "banaskantha", "en": "Amirgadh", "gu": "અમીરગઢ"},
    {"id": "danta", "district_id": "banaskantha", "en": "Danta", "gu": "દાંતા"},
    {"id": "dantiwada", "district_id": "banaskantha", "en": "Dantiwada", "gu": "દાંતીવાડા"},
    {"id": "deesa", "district_id": "banaskantha", "en": "Deesa", "gu": "ડીસા"},
    {"id": "vadgam", "district_id": "banaskantha", "en": "Vadgam", "gu": "વડગામ"},
    {"id": "dhanera", "district_id": "banaskantha", "en": "Dhanera", "gu": "ધાનેરા"},
    {"id": "kankrej", "district_id": "banaskantha", "en": "Kankrej", "gu": "કાંકરેજ"},
    {"id": "hadad", "district_id": "banaskantha", "en": "Hadad", "gu": "હડાદ"},
    {"id": "ogad", "district_id": "banaskantha", "en": "Ogad", "gu": "ઓગડ"},
    {"id": "bharuch", "district_id": "bharuch", "en": "Bharuch", "gu": "ભરૂચ"},
    {"id": "amod", "district_id": "bharuch", "en": "Amod", "gu": "આમોદ"},
    {"id": "ankleshwar", "district_id": "bharuch", "en": "Ankleshwar", "gu": "અંકલેશ્વર"},
    {"id": "hansot", "district_id": "bharuch", "en": "Hansot", "gu": "હાંસોટ"},
    {"id": "jambusar", "district_id": "bharuch", "en": "Jambusar", "gu": "જંબુસર"},
    {"id": "jhagadia", "district_id": "bharuch", "en": "Jhagadia", "gu": "ઝઘડિયા"},
    {"id": "vagra", "district_id": "bharuch", "en": "Vagra", "gu": "વાગરા"},
    {"id": "valia", "district_id": "bharuch", "en": "Valia", "gu": "વાલિયા"},
    {"id": "netrang", "district_id": "bharuch", "en": "Netrang", "gu": "નેત્રંગ"},
    {"id": "bhavnagar", "district_id": "bhavnagar", "en": "Bhavnagar", "gu": "ભાવનગર"},
    {"id": "gariadhar", "district_id": "bhavnagar", "en": "Gariadhar", "gu": "ગારીયાધાર"},
    {"id": "vallabhipur", "district_id": "bhavnagar", "en": "Vallabhipur", "gu": "વલ્લભીપુર"},
    {"id": "mahuva", "district_id": "bhavnagar", "en": "Mahuva", "gu": "મહુવા"},
    {"id": "ghogha", "district_id": "bhavnagar", "en": "Ghogha", "gu": "ઘોઘા"},
    {"id": "jesar", "district_id": "bhavnagar", "en": "Jesar", "gu": "જેસર"},
    {"id": "palitana", "district_id": "bhavnagar", "en": "Palitana", "gu": "પાલીતાણા"},
    {"id": "sihor", "district_id": "bhavnagar", "en": "Sihor", "gu": "સિહોર"},
    {"id": "talaja", "district_id": "bhavnagar", "en": "Talaja", "gu": "તળાજા"},
    {"id": "umrala", "district_id": "bhavnagar", "en": "Umrala", "gu": "ઉમરાળા"},
    {"id": "botad", "district_id": "botad", "en": "Botad", "gu": "બોટાદ"},
    {"id": "barwala", "district_id": "botad", "en": "Barwala", "gu": "બરવાળા"},
    {"id": "gadhada", "district_id": "botad", "en": "Gadhada", "gu": "ગઢડા"},
    {"id": "ranpur", "district_id": "botad", "en": "Ranpur", "gu": "રાણપુર"},
    {"id": "chhota_udaipur", "district_id": "chhota_udaipur", "en": "Chhota Udaipur", "gu": "છોટાઉદેપુર"},
    {"id": "bodeli", "district_id": "chhota_udaipur", "en": "Bodeli", "gu": "બોડેલી"},
    {"id": "pavi_jetpur", "district_id": "chhota_udaipur", "en": "Pavi Jetpur", "gu": "પાવી જેતપુર"},
    {"id": "kavant", "district_id": "chhota_udaipur", "en": "Kavant", "gu": "ક્વાંટ"},
    {"id": "nasvadi", "district_id": "chhota_udaipur", "en": "Nasvadi", "gu": "નસવાડી"},
    {"id": "sankheda", "district_id": "chhota_udaipur", "en": "Sankheda", "gu": "સંખેડા"},
    {"id": "dahod", "district_id": "dahod", "en": "Dahod", "gu": "દાહોદ"},
    {"id": "devgadbaria", "district_id": "dahod", "en": "Devgadbaria", "gu": "દેવગઢબારિયા"},
    {"id": "dhanpur", "district_id": "dahod", "en": "Dhanpur", "gu": "ધાનપુર"},
    {"id": "fatepura", "district_id": "dahod", "en": "Fatepura", "gu": "ફતેપુરા"},
    {"id": "garbada", "district_id": "dahod", "en": "Garbada", "gu": "ગરબાડા"},
    {"id": "limkheda", "district_id": "dahod", "en": "Limkheda", "gu": "લીમખેડા"},
    {"id": "jhalod", "district_id": "dahod", "en": "Jhalod", "gu": "ઝાલોદ"},
    {"id": "sanjeli", "district_id": "dahod", "en": "Sanjeli", "gu": "સંજેલી"},
    {"id": "singvad", "district_id": "dahod", "en": "Singvad", "gu": "સીંગવડ"},
    {"id": "ahwa", "district_id": "dang", "en": "Ahwa", "gu": "આહવા"},
    {"id": "subir", "district_id": "dang", "en": "Subir", "gu": "સુબિર"},
    {"id": "waghai", "district_id": "dang", "en": "Waghai", "gu": "વઘઇ"},
    {"id": "khambhalia", "district_id": "devbhoomi_dwarka", "en": "Khambhalia", "gu": "ખંભાળિયા"},
    {"id": "dwarka", "district_id": "devbhoomi_dwarka", "en": "Dwarka", "gu": "દ્વારકા"},
    {"id": "bhanvad", "district_id": "devbhoomi_dwarka", "en": "Bhanvad", "gu": "ભાણવડ"},
    {"id": "kalyanpur", "district_id": "devbhoomi_dwarka", "en": "Kalyanpur", "gu": "કલ્યાણપુર"},
    {"id": "gandhinagar", "district_id": "gandhinagar", "en": "Gandhinagar", "gu": "ગાંધીનગર"},
    {"id": "dehgam", "district_id": "gandhinagar", "en": "Dehgam", "gu": "દહેગામ"},
    {"id": "kalol", "district_id": "gandhinagar", "en": "Kalol", "gu": "કલોલ"},
    {"id": "mansa", "district_id": "gandhinagar", "en": "Mansa", "gu": "માણસા"},
    {"id": "patan_veraval", "district_id": "gir_somnath", "en": "Patan-Veraval", "gu": "પાટણ-વેરાવળ"},
    {"id": "gir_gadhada", "district_id": "gir_somnath", "en": "Gir Gadhada", "gu": "ગીર ગઢડા"},
    {"id": "kodinar", "district_id": "gir_somnath", "en": "Kodinar", "gu": "કોડીનાર"},
    {"id": "sutrapada", "district_id": "gir_somnath", "en": "Sutrapada", "gu": "સુત્રાપાડા"},
    {"id": "talala", "district_id": "gir_somnath", "en": "Talala", "gu": "તાલાલા"},
    {"id": "una", "district_id": "gir_somnath", "en": "Una", "gu": "ઉના"},
    {"id": "jamnagar", "district_id": "jamnagar", "en": "Jamnagar", "gu": "જામનગર"},
    {"id": "dhrol", "district_id": "jamnagar", "en": "Dhrol", "gu": "ધ્રોળ"},
    {"id": "jamjodhpur", "district_id": "jamnagar", "en": "Jamjodhpur", "gu": "જામજોધપુર"},
    {"id": "jodiya", "district_id": "jamnagar", "en": "Jodiya", "gu": "જોડિયા"},
    {"id": "kalavad", "district_id": "jamnagar", "en": "Kalavad", "gu": "કાલાવડ"},
    {"id": "lalpur", "district_id": "jamnagar", "en": "Lalpur", "gu": "લાલપુર"},
    {"id": "junagadh_city", "district_id": "junagadh", "en": "Junagadh City", "gu": "જુનાગઢ શહેર"},
    {"id": "junagadh_rural", "district_id": "junagadh", "en": "Junagadh Rural", "gu": "જુનાગઢ ગ્રામ્ય"},
    {"id": "bhesan", "district_id": "junagadh", "en": "Bhesan", "gu": "ભેંસાણ"},
    {"id": "keshod", "district_id": "junagadh", "en": "Keshod", "gu": "કેશોદ"},
    {"id": "maliya", "district_id": "junagadh", "en": "Maliya", "gu": "માળિયા"},
    {"id": "manavadar", "district_id": "junagadh", "en": "Manavadar", "gu": "માણાવદર"},
    {"id": "mangrol", "district_id": "junagadh", "en": "Mangrol", "gu": "માંગરોળ"},
    {"id": "mendarda", "district_id": "junagadh", "en": "Mendarda", "gu": "મેંદરડા"},
    {"id": "vanthali", "district_id": "junagadh", "en": "Vanthali", "gu": "વંથલી"},
    {"id": "visavadar", "district_id": "junagadh", "en": "Visavadar", "gu": "વિસાવદર"},
    {"id": "bhuj", "district_id": "kutch", "en": "Bhuj", "gu": "ભુજ"},
    {"id": "abdasa", "district_id": "kutch", "en": "Abdasa", "gu": "અબડાસા"},
    {"id": "bhachau", "district_id": "kutch", "en": "Bhachau", "gu": "ભચાઉ"},
    {"id": "gandhidham", "district_id": "kutch", "en": "Gandhidham", "gu": "ગાંધીધામ"},
    {"id": "mundra", "district_id": "kutch", "en": "Mundra", "gu": "મુન્દ્રા"},
    {"id": "nakhatrana", "district_id": "kutch", "en": "Nakhatrana", "gu": "નખત્રાણા"},
    {"id": "anjar", "district_id": "kutch", "en": "Anjar", "gu": "અંજાર"},
    {"id": "lakhpat", "district_id": "kutch", "en": "Lakhpat", "gu": "લખપત"},
    {"id": "mandvi", "district_id": "kutch", "en": "Mandvi", "gu": "માંડવી"},
    {"id": "rapar", "district_id": "kutch", "en": "Rapar", "gu": "રાપર"},
    {"id": "kheda", "district_id": "kheda", "en": "Kheda", "gu": "ખેડા"},
    {"id": "nadiad", "district_id": "kheda", "en": "Nadiad", "gu": "નડીઆદ"},
    {"id": "galteshwar", "district_id": "kheda", "en": "Galteshwar", "gu": "ગળતેશ્વર"},
    {"id": "kapadvanj", "district_id": "kheda", "en": "Kapadvanj", "gu": "કપડવંજ"},
    {"id": "kathlal", "district_id": "kheda", "en": "Kathlal", "gu": "કઠલાલ"},
    {"id": "mahudha", "district_id": "kheda", "en": "Mahudha", "gu": "મહુધા"},
    {"id": "matar", "district_id": "kheda", "en": "Matar", "gu": "માતર"},
    {"id": "mehmedabad", "district_id": "kheda", "en": "Mehmedabad", "gu": "મહેમદાવાદ"},
    {"id": "thasra", "district_id": "kheda", "en": "Thasra", "gu": "ઠાસરા"},
    {"id": "vaso", "district_id": "kheda", "en": "Vaso", "gu": "વસો"},
    {"id": "lunawada", "district_id": "mahisagar", "en": "Lunawada", "gu": "લુણાવાડા"},
    {"id": "balasinor", "district_id": "mahisagar", "en": "Balasinor", "gu": "બાલાસિનોર"},
    {"id": "kadana", "district_id": "mahisagar", "en": "Kadana", "gu": "કડાણા"},
    {"id": "khanpur", "district_id": "mahisagar", "en": "Khanpur", "gu": "ખાનપુર"},
    {"id": "santrampur", "district_id": "mahisagar", "en": "Santrampur", "gu": "સંતરામપુર"},
    {"id": "virpur", "district_id": "mahisagar", "en": "Virpur", "gu": "વિરપુર"},
    {"id": "mehsana", "district_id": "mehsana", "en": "Mehsana", "gu": "મહેસાણા"},
    {"id": "becharaji", "district_id": "mehsana", "en": "Becharaji", "gu": "બેચરાજી"},
    {"id": "vadnagar", "district_id": "mehsana", "en": "Vadnagar", "gu": "વડનગર"},
    {"id": "vijapur", "district_id": "mehsana", "en": "Vijapur", "gu": "વિજાપુર"},
    {"id": "jotana", "district_id": "mehsana", "en": "Jotana", "gu": "જોટાણા"},
    {"id": "kadi", "district_id": "mehsana", "en": "Kadi", "gu": "કડી"},
    {"id": "kheralu", "district_id": "mehsana", "en": "Kheralu", "gu": "ખેરાલુ"},
    {"id": "satlasana", "district_id": "mehsana", "en": "Satlasana", "gu": "સતલાસણા"},
    {"id": "unjha", "district_id": "mehsana", "en": "Unjha", "gu": "ઊંઝા"},
    {"id": "visnagar", "district_id": "mehsana", "en": "Visnagar", "gu": "વિસનગર"},
    {"id": "morbi", "district_id": "morbi", "en": "Morbi", "gu": "મોરબી"},
    {"id": "halvad", "district_id": "morbi", "en": "Halvad", "gu": "હળવદ"},
    {"id": "maliya_miyana", "district_id": "morbi", "en": "Maliya (Miyana)", "gu": "માળિયા (મિયાણા)"},
    {"id": "tankara", "district_id": "morbi", "en": "Tankara", "gu": "ટંકારા"},
    {"id": "wankaner", "district_id": "morbi", "en": "Wankaner", "gu": "વાંકાનેર"},
    {"id": "dediapada", "district_id": "narmada", "en": "Dediapada", "gu": "ડેડિયાપાડા"},
    {"id": "garudeshwar", "district_id": "narmada", "en": "Garudeshwar", "gu": "ગરૂડેશ્વર"},
    {"id": "nandod", "district_id": "narmada", "en": "Nandod", "gu": "નાંદોદ"},
    {"id": "sagbara", "district_id": "narmada", "en": "Sagbara", "gu": "સાગબારા"},
    {"id": "tilakvada", "district_id": "narmada", "en": "Tilakvada", "gu": "તિલકવાડા"},
    {"id": "navsari", "district_id": "navsari", "en": "Navsari", "gu": "નવસારી"},
    {"id": "vansda", "district_id": "navsari", "en": "Vansda", "gu": "વાંસદા"},
    {"id": "chikhli", "district_id": "navsari", "en": "Chikhli", "gu": "ચિખલી"},
    {"id": "gandevi", "district_id": "navsari", "en": "Gandevi", "gu": "ગણદેવી"},
    {"id": "jalalpore", "district_id": "navsari", "en": "Jalalpore", "gu": "જલાલપોર"},
    {"id": "khergam", "district_id": "navsari", "en": "Khergam", "gu": "ખેરગામ"},
    {"id": "godhra", "district_id": "panchmahal", "en": "Godhra", "gu": "ગોધરા"},
    {"id": "ghoghamba", "district_id": "panchmahal", "en": "Ghoghamba", "gu": "ઘોઘંબા"},
    {"id": "halol", "district_id": "panchmahal", "en": "Halol", "gu": "હાલોલ"},
    {"id": "jambughoda", "district_id": "panchmahal", "en": "Jambughoda", "gu": "જાંબુઘોડા"},
    {"id": "kalol_panchmahal", "district_id": "panchmahal", "en": "Kalol", "gu": "કાલોલ"},
    {"id": "morva_hadaf", "district_id": "panchmahal", "en": "Morva Hadaf", "gu": "મોરવા હડફ"},
    {"id": "shehera", "district_id": "panchmahal", "en": "Shehera", "gu": "શહેરા"},
    {"id": "patan", "district_id": "patan", "en": "Patan", "gu": "પાટણ"},
    {"id": "chanasma", "district_id": "patan", "en": "Chanasma", "gu": "ચાણસ્મા"},
    {"id": "harij", "district_id": "patan", "en": "Harij", "gu": "હારીજ"},
    {"id": "radhanpur", "district_id": "patan", "en": "Radhanpur", "gu": "રાધનપુર"},
    {"id": "sami", "district_id": "patan", "en": "Sami", "gu": "સમી"},
    {"id": "shankheshwar", "district_id": "patan", "en": "Shankheshwar", "gu": "શંખેશ્વર"},
    {"id": "santalpur", "district_id": "patan", "en": "Santalpur", "gu": "સાંતલપુર"},
    {"id": "saraswati", "district_id": "patan", "en": "Saraswati", "gu": "સરસ્વતી"},
    {"id": "siddhpur", "district_id": "patan", "en": "Siddhpur", "gu": "સિદ્ધપુર"},
    {"id": "porbandar", "district_id": "porbandar", "en": "Porbandar", "gu": "પોરબંદર"},
    {"id": "kutiyana", "district_id": "porbandar", "en": "Kutiyana", "gu": "કુતિયાણા"},
    {"id": "ranavav", "district_id": "porbandar", "en": "Ranavav", "gu": "રાણાવાવ"},
    {"id": "rajkot", "district_id": "rajkot", "en": "Rajkot", "gu": "રાજકોટ"},
    {"id": "dhoraji", "district_id": "rajkot", "en": "Dhoraji", "gu": "ધોરાજી"},
    {"id": "gondal", "district_id": "rajkot", "en": "Gondal", "gu": "ગોંડલ"},
    {"id": "jamkandorna", "district_id": "rajkot", "en": "Jamkandorna", "gu": "જામકંડોરણા"},
    {"id": "jasdan", "district_id": "rajkot", "en": "Jasdan", "gu": "જસદણ"},
    {"id": "jetpur", "district_id": "rajkot", "en": "Jetpur", "gu": "જેતપુર"},
    {"id": "kotda_sangani", "district_id": "rajkot", "en": "Kotda Sangani", "gu": "કોટડા-સાંગાણી"},
    {"id": "lodhika", "district_id": "rajkot", "en": "Lodhika", "gu": "લોધિકા"},
    {"id": "paddhari", "district_id": "rajkot", "en": "Paddhari", "gu": "પડધરી"},
    {"id": "upleta", "district_id": "rajkot", "en": "Upleta", "gu": "ઉપલેટા"},
    {"id": "vichhiya", "district_id": "rajkot", "en": "Vichhiya", "gu": "વીંછીયા"},
    {"id": "himmatnagar", "district_id": "sabarkantha", "en": "Himmatnagar", "gu": "હિંમતનગર"},
    {"id": "idar", "district_id": "sabarkantha", "en": "Idar", "gu": "ઇડર"},
    {"id": "khedbrahma", "district_id": "sabarkantha", "en": "Khedbrahma", "gu": "ખેડબ્રહ્મા"},
    {"id": "prantij", "district_id": "sabarkantha", "en": "Prantij", "gu": "પ્રાંતિજ"},
    {"id": "talod", "district_id": "sabarkantha", "en": "Talod", "gu": "તલોદ"},
    {"id": "vadali", "district_id": "sabarkantha", "en": "Vadali", "gu": "વડાલી"},
    {"id": "vijaynagar", "district_id": "sabarkantha", "en": "Vijaynagar", "gu": "વિજયનગર"},
    {"id": "poshina", "district_id": "sabarkantha", "en": "Poshina", "gu": "પોશિના"},
    {"id": "bardoli", "district_id": "surat", "en": "Bardoli", "gu": "બારડોલી"},
    {"id": "kamrej", "district_id": "surat", "en": "Kamrej", "gu": "કામરેજ"},
    {"id": "choryasi", "district_id": "surat", "en": "Choryasi", "gu": "ચોર્યાસી"},
    {"id": "mahuva_surat", "district_id": "surat", "en": "Mahuva", "gu": "મહુવા"},
    {"id": "mandvi_surat", "district_id": "surat", "en": "Mandvi", "gu": "માંડવી"},
    {"id": "mangrol_surat", "district_id": "surat", "en": "Mangrol", "gu": "માંગરોળ"},
    {"id": "olpad", "district_id": "surat", "en": "Olpad", "gu": "ઓલપાડ"},
    {"id": "palsana", "district_id": "surat", "en": "Palsana", "gu": "પલસાણા"},
    {"id": "umarpada", "district_id": "surat", "en": "Umarpada", "gu": "ઉમરપાડા"},
    {"id": "chotila", "district_id": "surendranagar", "en": "Chotila", "gu": "ચોટીલા"},
    {"id": "chuda", "district_id": "surendranagar", "en": "Chuda", "gu": "ચુડા"},
    {"id": "dasada", "district_id": "surendranagar", "en": "Dasada", "gu": "દસાડા"},
    {"id": "dhrangadhra", "district_id": "surendranagar", "en": "Dhrangadhra", "gu": "ધ્રાંગધ્રા"},
    {"id": "lakhtar", "district_id": "surendranagar", "en": "Lakhtar", "gu": "લખતર"},
    {"id": "limbdi", "district_id": "surendranagar", "en": "Limbdi", "gu": "લીંબડી"},
    {"id": "muli", "district_id": "surendranagar", "en": "Muli", "gu": "મુળી"},
    {"id": "sayla", "district_id": "surendranagar", "en": "Sayla", "gu": "સાયલા"},
    {"id": "thangadh", "district_id": "surendranagar", "en": "Thangadh", "gu": "થાનગઢ"},
    {"id": "wadhwan", "district_id": "surendranagar", "en": "Wadhwan", "gu": "વઢવાણ"},
    {"id": "vyara", "district_id": "tapi", "en": "Vyara", "gu": "વ્યારા"},
    {"id": "nizar", "district_id": "tapi", "en": "Nizar", "gu": "નિઝર"},
    {"id": "songadh", "district_id": "tapi", "en": "Songadh", "gu": "સોનગઢ"},
    {"id": "uchchhal", "district_id": "tapi", "en": "Uchchhal", "gu": "ઉચ્છલ"},
    {"id": "valod", "district_id": "tapi", "en": "Valod", "gu": "વાલોડ"},
    {"id": "dolvan", "district_id": "tapi", "en": "Dolvan", "gu": "ડોલવણ"},
    {"id": "kukarmunda", "district_id": "tapi", "en": "Kukarmunda", "gu": "કુકરમુંડા"},
    {"id": "vadodara", "district_id": "vadodara", "en": "Vadodara", "gu": "વડોદરા"},
    {"id": "dabhoi", "district_id": "vadodara", "en": "Dabhoi", "gu": "ડભોઇ"},
    {"id": "desar", "district_id": "vadodara", "en": "Desar", "gu": "ડેસર"},
    {"id": "karjan", "district_id": "vadodara", "en": "Karjan", "gu": "કરજણ"},
    {"id": "padra", "district_id": "vadodara", "en": "Padra", "gu": "પાદરા"},
    {"id": "savli", "district_id": "vadodara", "en": "Savli", "gu": "સાવલી"},
    {"id": "shinor", "district_id": "vadodara", "en": "Shinor", "gu": "શિનોર"},
    {"id": "waghodia", "district_id": "vadodara", "en": "Waghodia", "gu": "વાઘોડિયા"},
    {"id": "valsad", "district_id": "valsad", "en": "Valsad", "gu": "વલસાડ"},
    {"id": "dharampur", "district_id": "valsad", "en": "Dharampur", "gu": "ધરમપુર"},
    {"id": "kaprada", "district_id": "valsad", "en": "Kaprada", "gu": "કપરાડા"},
    {"id": "pardi", "district_id": "valsad", "en": "Pardi", "gu": "પારડી"},
    {"id": "umargam", "district_id": "valsad", "en": "Umargam", "gu": "ઉમરગામ"},
    {"id": "vapi", "district_id": "valsad", "en": "Vapi", "gu": "વાપી"},
    {"id": "vav", "district_id": "vav_tharad", "en": "Vav", "gu": "વાવ"},
    {"id": "tharad", "district_id": "vav_tharad", "en": "Tharad", "gu": "થરાદ"},
    {"id": "suigam", "district_id": "vav_tharad", "en": "Suigam", "gu": "સુઇગામ"},
    {"id": "lakhani", "district_id": "vav_tharad", "en": "Lakhani", "gu": "લાખણી"},
    {"id": "deodar", "district_id": "vav_tharad", "en": "Deodar", "gu": "દિયોદર"},
    {"id": "bhabhar", "district_id": "vav_tharad", "en": "Bhabhar", "gu": "ભાભર"},
    {"id": "rah", "district_id": "vav_tharad", "en": "Rah", "gu": "રાહ"},
    {"id": "dharanidhar", "district_id": "vav_tharad", "en": "Dharanidhar", "gu": "ધરણીધર"},
]


# Courts scoped by district_id. "generic" courts appear for every district.
# Every Gujarat district has a District & Sessions Court at its headquarters
# (Gujarat High Court / District Judiciary structure) — one entry per district,
# scoped by district_id so lawyer forms only show courts of the selected district.
# (district_id, en, gu, legacy_id_or_None). Legacy IDs are preserved so existing
# cases/templates that reference the old court ids keep resolving.
COURTS = [
    {
        "id": "principal_district_and_sessions_judge_d12c22",
        "en": "PRINCIPAL DISTRICT AND SESSIONS JUDGE",
        "gu": "પ્રિન્સીપાલ ડીસ્ટ્રીક્ટ એન્ડ સેસન્સ જજ",
        "district_id": "generic"
    },
    {
        "id": "2nd_additional_district_judge_522bbb",
        "en": "2nd ADDITIONAL DISTRICT JUDGE",
        "gu": "બીજા એડિશનલ ડીસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "3rd_additional_district_judge_dbec67",
        "en": "3rd ADDITIONAL DISTRICT JUDGE",
        "gu": "ત્રીજા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "4th_additional_district_judge_2673de",
        "en": "4th ADDITIONAL DISTRICT JUDGE",
        "gu": "ચોથા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "5th_additional_district_judge_19adda",
        "en": "5th ADDITIONAL DISTRICT JUDGE",
        "gu": "પાંચમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "6th_additional_district_judge_fbb72d",
        "en": "6th ADDITIONAL DISTRICT JUDGE",
        "gu": "છઠ્ઠા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "7th_additional_district_judge_398fee",
        "en": "7th ADDITIONAL DISTRICT JUDGE",
        "gu": "સાતમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "8th_additional_district_judge_c68ab1",
        "en": "8th ADDITIONAL DISTRICT JUDGE",
        "gu": "આઠમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "9th_additional_district_judge_e53af1",
        "en": "9th ADDITIONAL DISTRICT JUDGE",
        "gu": "નવમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "10th_additional_district_judge_aa08cd",
        "en": "10th ADDITIONAL DISTRICT JUDGE",
        "gu": "દસમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "11th_additional_district_judge_d978d2",
        "en": "11th ADDITIONAL DISTRICT JUDGE",
        "gu": "અગ્યારમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "12th_additional_district_judge_0dbcb2",
        "en": "12th ADDITIONAL DISTRICT JUDGE",
        "gu": "બારમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "13th_additional_district_judge_e5a99c",
        "en": "13th ADDITIONAL DISTRICT JUDGE",
        "gu": "તેરમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "14th_additional_district_judge_949d31",
        "en": "14th ADDITIONAL DISTRICT JUDGE",
        "gu": "ચૌદમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "15th_additional_district_judge_1ca00f",
        "en": "15th ADDITIONAL DISTRICT JUDGE",
        "gu": "પંદરમા એડિશનલ ડિસ્ટ્રીક્ટ જજ",
        "district_id": "generic"
    },
    {
        "id": "chief_judicial_magistrate_0abfd0",
        "en": "CHIEF JUDICIAL MAGISTRATE",
        "gu": "ચીફ જ્યુડિશિયલ મેજીસ્ટ્રેટ",
        "district_id": "generic"
    },
    {
        "id": "principal_senior_civil_judge_623c03",
        "en": "PRINCIPAL SENIOR CIVIL JUDGE",
        "gu": "પ્રિન્સિપાલ સિનિયર સિવિલ જજ",
        "district_id": "generic"
    },
    {
        "id": "additional_senior_civil_judge___acjm_546aa7",
        "en": "ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "2nd_additional_senior_civil_judge___acjm_321a9b",
        "en": "2nd ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "બીજા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "3rd_additional_senior_civil_judge___acjm_7782ed",
        "en": "3rd ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "ત્રીજા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "4th_additional_senior_civil_judge___jmfc_0ef8e3",
        "en": "4th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "ચોથા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "5th_additional_senior_civil_judge___acjm_fec557",
        "en": "5th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "પાંચમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "6th_additional_senior_civil_judge___acjm_7438c8",
        "en": "6th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "છઠ્ઠા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "7th_additional_senior_civil_judge___acjm_15d43c",
        "en": "7th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "સાતમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "8th_additional_senior_civil_judge___acjm_471d11",
        "en": "8th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "આઠમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "9th_additional_senior_civil_judge___acjm_b10c35",
        "en": "9th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "નવમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "10th_additional_senior_civil_judge___acj_79f5ff",
        "en": "10th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "દસમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "11th_additional_senior_civil_judge___acj_68da3e",
        "en": "11th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "અગ્યારમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "12th_additional_senior_civil_judge___acj_fa4696",
        "en": "12th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "બારમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "13th_additional_senior_civil_judge___acj_e1660e",
        "en": "13th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "તેરમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "14th_additional_senior_civil_judge___acj_16dc8f",
        "en": "14th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "ચૌદમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "15th_additional_senior_civil_judge___acj_5aa729",
        "en": "15th ADDITIONAL SENIOR CIVIL JUDGE & ACJM",
        "gu": "પંદરમા એડિશનલ સિનિયર સિવિલ જજ & એડી. ચીફ જ્યુડી. મેજી.",
        "district_id": "generic"
    },
    {
        "id": "additional_civil_judge___jmfc_613fc1",
        "en": "ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "2nd_additional_civil_judge___jmfc_d41bf9",
        "en": "2nd ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "બીજા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "3rd_additional_civil_judge___jmfc_b38461",
        "en": "3rd ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "ત્રીજા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "4th_additional_civil_judge___jmfc_6a64db",
        "en": "4th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "ચોથા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "5th_additional_civil_judge___jmfc_08e089",
        "en": "5th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "પાંચમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "6th_additional_civil_judge___jmfc_d46629",
        "en": "6th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "છઠ્ઠા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "7th_additional_civil_judge___jmfc_ce626f",
        "en": "7th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "સાતમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "8th_additional_civil_judge___jmfc_8123a9",
        "en": "8th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "આઠમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "9th_additional_civil_judge___jmfc_942060",
        "en": "9th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "નવમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "10th_additional_civil_judge___jmfc_fb7f64",
        "en": "10th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "દસમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "11th_additional_civil_judge___jmfc_5c5515",
        "en": "11th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "અગ્યારમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "12th_additional_civil_judge___jmfc_966c26",
        "en": "12th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "બારમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "13th_additional_civil_judge___jmfc_75df11",
        "en": "13th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "તેરમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "14th_additional_civil_judge___jmfc_6bf30d",
        "en": "14th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "ચૌદમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    },
    {
        "id": "15th_additional_civil_judge___jmfc_487d3a",
        "en": "15th ADDITIONAL CIVIL JUDGE & JMFC",
        "gu": "પંદરમા એડિશનલ સિવિલ જજ & જ્યુડી. મેજી. ફ. ક.",
        "district_id": "generic"
    }
]

# Legacy court definitions preserved so existing cases and tests continue to resolve.
_DISTRICT_COURTS = [
    ("ahmedabad", "District & Sessions Court, Ahmedabad", "જિલ્લા અને સેશન્સ કોર્ટ, અમદાવાદ", "dst_ahmedabad"),
    ("gandhinagar", "District & Sessions Court, Gandhinagar", "જિલ્લા અને સેશન્સ કોર્ટ, ગાંધીનગર", "dst_gandhinagar"),
    ("surat", "District & Sessions Court, Surat", "જિલ્લા અને સેશન્સ કોર્ટ, સુરત", "surat_district"),
    ("vadodara", "District & Sessions Court, Vadodara", "જિલ્લા અને સેશન્સ કોર્ટ, વડોદરા", "vad_district"),
    ("rajkot", "District & Sessions Court, Rajkot", "જિલ્લા અને સેશન્સ કોર્ટ, રાજકોટ", "rajkot_district"),
    ("bhavnagar", "District & Sessions Court, Bhavnagar", "જિલ્લા અને સેશન્સ કોર્ટ, ભાવનગર", None),
    ("jamnagar", "District & Sessions Court, Jamnagar", "જિલ્લા અને સેશન્સ કોર્ટ, જામનગર", None),
    ("junagadh", "District & Sessions Court, Junagadh", "જિલ્લા અને સેશન્સ કોર્ટ, જૂનાગઢ", None),
    ("anand", "District & Sessions Court, Anand", "જિલ્લા અને સેશન્સ કોર્ટ, આણંદ", None),
    ("kutch", "District & Sessions Court, Bhuj", "જિલ્લા અને સેશન્સ કોર્ટ, ભુજ", None),
    ("mehsana", "District & Sessions Court, Mehsana", "જિલ્લા અને સેશન્સ કોર્ટ, મહેસાણા", None),
    ("patan", "District & Sessions Court, Patan", "જિલ્લા અને સેશન્સ કોર્ટ, પાટણ", None),
    ("amreli", "District & Sessions Court, Amreli", "જિલ્લા અને સેશન્સ કોર્ટ, અમરેલી", None),
    ("aravalli", "District & Sessions Court, Modasa", "જિલ્લા અને સેશન્સ કોર્ટ, મોડાસા", None),
    ("banaskantha", "District & Sessions Court, Palanpur", "જિલ્લા અને સેશન્સ કોર્ટ, પાલનપુર", None),
    ("bharuch", "District & Sessions Court, Bharuch", "જિલ્લા અને સેશન્સ કોર્ટ, ભરૂચ", None),
    ("botad", "District & Sessions Court, Botad", "જિલ્લા અને સેશન્સ કોર્ટ, બોટાદ", None),
    ("chhota_udaipur", "District & Sessions Court, Chhota Udaipur", "જિલ્લા અને સેશન્સ કોર્ટ, છોટાઉદેપુર", None),
    ("dahod", "District & Sessions Court, Dahod", "જિલ્લા અને સેશન્સ કોર્ટ, દાહોદ", None),
    ("dang", "District & Sessions Court, Ahwa", "જિલ્લા અને સેશન્સ કોર્ટ, આહવા", None),
    ("devbhoomi_dwarka", "District & Sessions Court, Khambhalia", "જિલ્લા અને સેશન્સ કોર્ટ, ખંભાળિયા", None),
    ("gir_somnath", "District & Sessions Court, Veraval", "જિલ્લા અને સેશન્સ કોર્ટ, વેરાવળ", None),
    ("kheda", "District & Sessions Court, Nadiad", "જિલ્લા અને સેશન્સ કોર્ટ, નડીઆદ", None),
    ("mahisagar", "District & Sessions Court, Lunawada", "જિલ્લા અને સેશન્સ કોર્ટ, લુણાવાડા", None),
    ("morbi", "District & Sessions Court, Morbi", "જિલ્લા અને સેશન્સ કોર્ટ, મોરબી", None),
    ("narmada", "District & Sessions Court, Rajpipla", "જિલ્લા અને સેશન્સ કોર્ટ, રાજપીપળા", None),
    ("navsari", "District & Sessions Court, Navsari", "જિલ્લા અને સેશન્સ કોર્ટ, નવસારી", None),
    ("panchmahal", "District & Sessions Court, Godhra", "જિલ્લા અને સેશન્સ કોર્ટ, ગોધરા", None),
    ("porbandar", "District & Sessions Court, Porbandar", "જિલ્લા અને સેશન્સ કોર્ટ, પોરબંદર", None),
    ("sabarkantha", "District & Sessions Court, Himmatnagar", "જિલ્લા અને સેશન્સ કોર્ટ, હિંમતનગર", None),
    ("surendranagar", "District & Sessions Court, Surendranagar", "જિલ્લા અને સેશન્સ કોર્ટ, સુરેન્દ્રનગર", None),
    ("tapi", "District & Sessions Court, Vyara", "જિલ્લા અને સેશન્સ કોર્ટ, વ્યારા", None),
    ("valsad", "District & Sessions Court, Valsad", "જિલ્લા અને સેશન્સ કોર્ટ, વલસાડ", None),
    ("vav_tharad", "District & Sessions Court, Tharad", "જિલ્લા અને સેશન્સ કોર્ટ, થરાદ", None),
]

LEGACY_COURTS = [
    {"id": "gen_district", "district_id": "generic", "en": "District Court", "gu": "જિલ્લા ન્યાયાલય"},
    {"id": "gen_sessions", "district_id": "generic", "en": "Sessions Court", "gu": "સેશન્સ ન્યાયાલય"},
    {"id": "gen_jmfc", "district_id": "generic", "en": "Court of JMFC", "gu": "જે.એમ.એફ.સી. ન્યાયાલય"},
    {"id": "gen_civil_senior", "district_id": "generic", "en": "Principal Senior Civil Judge", "gu": "મુખ્ય વરિષ્ઠ સિવિલ જજ"},
    {"id": "gen_civil_junior", "district_id": "generic", "en": "Civil Judge (Junior Division)", "gu": "સિવિલ જજ (જુનિયર ડિવિઝન)"},
    {"id": "gen_family", "district_id": "generic", "en": "Family Court", "gu": "ફેમિલી કોર્ટ"},
    {"id": "ahd_metro", "district_id": "ahmedabad", "en": "Metropolitan Magistrate Court, Ahmedabad", "gu": "મેટ્રોપોલિટન મેજિસ્ટ્રેટ કોર્ટ, અમદાવાદ"},
    {"id": "ahd_city_civil", "district_id": "ahmedabad", "en": "City Civil Court, Ahmedabad", "gu": "સિટી સિવિલ કોર્ટ, અમદાવાદ"},
] + [
    {"id": legacy_id or f"dst_{d_id}", "district_id": d_id, "en": en, "gu": gu}
    for d_id, en, gu, legacy_id in _DISTRICT_COURTS
]

# Police stations scoped by district_id.
POLICE_STATIONS = [
    {"id": "ahd_naranpura", "district_id": "ahmedabad", "en": "Naranpura P.S.", "gu": "નારણપુરા પોલીસ સ્ટેશન"},
    {"id": "ahd_navrangpura", "district_id": "ahmedabad", "en": "Navrangpura P.S.", "gu": "નવરંગપુરા પોલીસ સ્ટેશન"},
    {"id": "ahd_satellite", "district_id": "ahmedabad", "en": "Satellite P.S.", "gu": "સેટેલાઇટ પોલીસ સ્ટેશન"},
    {"id": "ahd_vastrapur", "district_id": "ahmedabad", "en": "Vastrapur P.S.", "gu": "વસ્ત્રાપુર પોલીસ સ્ટેશન"},
    {"id": "surat_adajan", "district_id": "surat", "en": "Adajan P.S.", "gu": "અડાજણ પોલીસ સ્ટેશન"},
    {"id": "surat_varachha", "district_id": "surat", "en": "Varachha P.S.", "gu": "વરાછા પોલીસ સ્ટેશન"},
    {"id": "vad_gotri", "district_id": "vadodara", "en": "Gotri P.S.", "gu": "ગોત્રી પોલીસ સ્ટેશન"},
    {"id": "rajkot_gandhigram", "district_id": "rajkot", "en": "Gandhigram P.S.", "gu": "ગાંધીગ્રામ પોલીસ સ્ટેશન"},
    {"id": "gnr_sector21", "district_id": "gandhinagar", "en": "Sector 21 P.S.", "gu": "સેક્ટર ૨૧ પોલીસ સ્ટેશન"},
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
            {"key": "order_date", "label_en": "Order Date (optional)", "label_gu": "હુકમની તારીખ (વૈકલ્પિક)", "type": "date", "required": False},
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
    {
        "id": "restoration",
        "name_en": "Restoration Application",
        "name_gu": "કેસ પુનઃસ્થાપન અરજી",
        "category": "General",
        "aliases": ["restoration", "restore", "punah sthapan", "પુનઃસ્થાપન", "restore case"],
        "fields": [
            {"key": "dismiss_date", "label_en": "Date of Dismissal", "label_gu": "કેસ કાઢી નાખ્યાની તારીખ", "type": "date", "required": True},
            {"key": "reason", "label_en": "Reason for Absence", "label_gu": "ગેરહાજરીનું કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR RESTORATION

Most Respectfully Sheweth:

1. The above matter was dismissed for default on {{dismiss_date}}.

2. The applicant could not remain present due to {{reason}}.

3. It is therefore prayed that this Hon'ble Court may be pleased to restore the above matter to its original file in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

કેસ પુનઃસ્થાપન અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ {{dismiss_date}} ના રોજ ગેરહાજરીના કારણે કાઢી નાખવામાં આવેલ છે.

૨. {{reason}} ના કારણે અરજદાર હાજર રહી શકેલ ન હતા.

૩. તેથી ન્યાયના હિતમાં ઉપરોક્ત કેસ મૂળ ફાઈલ પર પુનઃસ્થાપિત કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "condonation_delay",
        "name_en": "Condonation of Delay Application",
        "name_gu": "વિલંબ માફી અરજી",
        "category": "General",
        "aliases": ["condonation", "delay", "vilamb", "વિલંબ", "condone delay"],
        "fields": [
            {"key": "days_delay", "label_en": "Days of Delay", "label_gu": "વિલંબના દિવસો", "type": "number", "required": True},
            {"key": "reason", "label_en": "Reason for Delay", "label_gu": "વિલંબનું કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR CONDONATION OF DELAY

Most Respectfully Sheweth:

1. There has been a delay of {{days_delay}} days in filing the above matter/application.

2. The said delay occurred due to {{reason}} and was neither intentional nor deliberate.

3. It is therefore prayed that the delay of {{days_delay}} days be condoned in the interest of justice.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

વિલંબ માફી અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ / અરજી દાખલ કરવામાં {{days_delay}} દિવસનો વિલંબ થયેલ છે.

૨. આ વિલંબ {{reason}} ના કારણે થયેલ છે અને તે ઈરાદાપૂર્વકનો ન હતો.

૩. તેથી ન્યાયના હિતમાં {{days_delay}} દિવસનો વિલંબ માફ કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "interim_injunction",
        "name_en": "Interim Injunction Application",
        "name_gu": "વચગાળાનો મનાઈહુકમ અરજી",
        "category": "Civil",
        "aliases": ["injunction", "interim injunction", "manai hukam", "મનાઈહુકમ", "stay"],
        "fields": [
            {"key": "relief", "label_en": "Injunction Sought", "label_gu": "માંગેલ મનાઈહુકમ", "type": "textarea", "required": True},
            {"key": "grounds", "label_en": "Grounds", "label_gu": "કારણો", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR INTERIM INJUNCTION

Most Respectfully Sheweth:

1. The applicant seeks the following interim relief: {{relief}}

2. Grounds: {{grounds}}

3. The applicant has a prima facie case and the balance of convenience lies in favour of the applicant. Irreparable loss will be caused if injunction is not granted.

4. It is therefore prayed that this Hon'ble Court may be pleased to grant the above interim injunction pending final disposal.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

વચગાળાનો મનાઈહુકમ અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર નીચે મુજબનો વચગાળાનો રાહત માંગે છે: {{relief}}

૨. કારણો: {{grounds}}

૩. અરજદારનો પ્રથમદર્શી કેસ છે અને સગવડનું સંતુલન અરજદારની તરફેણમાં છે. મનાઈહુકમ ન આપવામાં આવે તો ન ભરપાઈ થાય તેવું નુકસાન થશે.

૪. તેથી કેસના આખરી નિકાલ સુધી ઉપરોક્ત વચગાળાનો મનાઈહુકમ આપવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "vakalatnama",
        "name_en": "Vakalatnama",
        "name_gu": "વકાલતનામું",
        "category": "General",
        "aliases": ["vakalatnama", "vakalat", "વકાલતનામું", "power of attorney", "appointment of advocate"],
        "fields": [
            {"key": "client_name", "label_en": "Client Name", "label_gu": "અસીલનું નામ", "type": "text", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

VAKALATNAMA

I, {{client_name}}, do hereby appoint and retain {{advocate_name}}, Advocate, to appear, act and plead on my behalf in the above matter.

I authorise the said Advocate to file and receive documents, to make statements, to compromise, and to do all acts necessary for the conduct of the case.

Place: {{district}}
Date: {{today}}

Signature of Client
{{client_name}}

Accepted
{{advocate_name}}, Advocate
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

વકાલતનામું

હું, {{client_name}}, આથી {{advocate_name}}, વકીલ ને ઉપરોક્ત કેસમાં મારા વતી હાજર રહેવા, કાર્યવાહી કરવા અને દલીલ કરવા નિમણૂક કરું છું.

હું ઉક્ત વકીલને દસ્તાવેજો દાખલ કરવા અને મેળવવા, નિવેદન કરવા, સમાધાન કરવા અને કેસ ચલાવવા માટે જરૂરી તમામ કાર્ય કરવા અધિકૃત કરું છું.

સ્થળ: {{district}}
તારીખ: {{today}}

અસીલની સહી
{{client_name}}

સ્વીકૃત
{{advocate_name}}, વકીલ
""",
    },
    {
        "id": "return_documents",
        "name_en": "Application for Return of Documents",
        "name_gu": "દસ્તાવેજ પરત મેળવવા અરજી",
        "category": "General",
        "aliases": ["return document", "return of documents", "dastavej pariat", "દસ્તાવેજ પરત"],
        "fields": [
            {"key": "document_list", "label_en": "Documents to Return", "label_gu": "પરત મેળવવાના દસ્તાવેજો", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR RETURN OF DOCUMENTS

Most Respectfully Sheweth:

1. The following original documents were produced on record: {{document_list}}

2. The said documents are now required by the applicant.

3. It is therefore prayed that this Hon'ble Court may be pleased to return the said original documents after retaining certified copies on record.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

દસ્તાવેજ પરત મેળવવા અરજી

નમ્રપણે વિનંતી છે કે:

૧. નીચેના મૂળ દસ્તાવેજો રેકોર્ડ પર રજૂ કરવામાં આવેલ છે: {{document_list}}

૨. આ દસ્તાવેજો હવે અરજદારને જરૂરી છે.

૩. તેથી પ્રમાણિત નકલ રેકોર્ડ પર રાખીને ઉક્ત મૂળ દસ્તાવેજો પરત આપવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "inspection",
        "name_en": "Application for Inspection of Records",
        "name_gu": "રેકોર્ડ તપાસ અરજી",
        "category": "General",
        "aliases": ["inspection", "record inspection", "record tapas", "રેકોર્ડ તપાસ"],
        "fields": [
            {"key": "record_desc", "label_en": "Records to Inspect", "label_gu": "તપાસવાના રેકોર્ડ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR INSPECTION OF RECORDS

Most Respectfully Sheweth:

1. The applicant seeks inspection of the following records: {{record_desc}}

2. Such inspection is necessary for the proper conduct of the case.

3. It is therefore prayed that this Hon'ble Court may be pleased to grant inspection of the said records.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

રેકોર્ડ તપાસ અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર નીચેના રેકોર્ડની તપાસ કરવા વિનંતી કરે છે: {{record_desc}}

૨. કેસના યોગ્ય સંચાલન માટે આ તપાસ જરૂરી છે.

૩. તેથી ઉક્ત રેકોર્ડની તપાસ કરવાની પરવાનગી આપવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "compromise",
        "name_en": "Compromise / Settlement Application",
        "name_gu": "સમાધાન અરજી",
        "category": "General",
        "aliases": ["compromise", "settlement", "samadhan", "સમાધાન", "consent"],
        "fields": [
            {"key": "terms", "label_en": "Terms of Compromise", "label_gu": "સમાધાનની શરતો", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

COMPROMISE / SETTLEMENT APPLICATION

Most Respectfully Sheweth:

1. The parties have amicably settled the dispute on the following terms: {{terms}}

2. The parties pray that the above matter be disposed of in terms of the said compromise.

3. It is therefore prayed that this Hon'ble Court may be pleased to record the compromise and dispose of the matter accordingly.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

સમાધાન અરજી

નમ્રપણે વિનંતી છે કે:

૧. પક્ષકારોએ નીચેની શરતો પર સૌહાર્દપૂર્ણ સમાધાન કરેલ છે: {{terms}}

૨. પક્ષકારો ઉપરોક્ત કેસ ઉક્ત સમાધાનની શરતો મુજબ નિકાલ કરવા વિનંતી કરે છે.

૩. તેથી સમાધાન નોંધીને કેસનો તદનુસાર નિકાલ કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "withdrawal",
        "name_en": "Withdrawal of Case Application",
        "name_gu": "કેસ પાછો ખેંચવા અરજી",
        "category": "General",
        "aliases": ["withdrawal", "withdraw case", "kes pacho", "કેસ પાછો"],
        "fields": [
            {"key": "reason", "label_en": "Reason for Withdrawal", "label_gu": "પાછો ખેંચવાનું કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR WITHDRAWAL OF CASE

Most Respectfully Sheweth:

1. The applicant does not wish to prosecute the above matter further for the following reason: {{reason}}

2. It is therefore prayed that this Hon'ble Court may be pleased to permit the applicant to withdraw the above matter.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

કેસ પાછો ખેંચવા અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર નીચેના કારણોસર ઉપરોક્ત કેસ આગળ ચલાવવા ઇચ્છતા નથી: {{reason}}

૨. તેથી અરજદારને ઉપરોક્ત કેસ પાછો ખેંચવાની પરવાનગી આપવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "amendment",
        "name_en": "Amendment Application",
        "name_gu": "સુધારા અરજી",
        "category": "General",
        "aliases": ["amendment", "amend", "sudhara", "સુધારા"],
        "fields": [
            {"key": "amendment_desc", "label_en": "Proposed Amendment", "label_gu": "સૂચિત સુધારો", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

AMENDMENT APPLICATION

Most Respectfully Sheweth:

1. The applicant seeks to amend the pleadings as under: {{amendment_desc}}

2. The proposed amendment is necessary for determining the real questions in controversy and will not prejudice the opposite party.

3. It is therefore prayed that this Hon'ble Court may be pleased to allow the above amendment.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

સુધારા અરજી

નમ્રપણે વિનંતી છે કે:

૧. અરજદાર નીચે મુજબ પ્લીડિંગમાં સુધારો કરવા ઇચ્છે છે: {{amendment_desc}}

૨. વિવાદના ખરા પ્રશ્નો નક્કી કરવા આ સુધારો જરૂરી છે અને તેથી સામાવાળા પક્ષને કોઈ નુકસાન થશે નહીં.

૩. તેથી ઉપરોક્ત સુધારો મંજૂર કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "surety",
        "name_en": "Surety / Bail Bond Application",
        "name_gu": "જામીનખત અરજી",
        "category": "Criminal",
        "aliases": ["surety", "bail bond", "jaminkhat", "જામીનખત"],
        "fields": [
            {"key": "surety_name", "label_en": "Surety Name", "label_gu": "જામીનદારનું નામ", "type": "text", "required": True},
            {"key": "amount", "label_en": "Bond Amount", "label_gu": "જામીનની રકમ", "type": "text", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

SURETY / BAIL BOND APPLICATION

Most Respectfully Sheweth:

1. {{surety_name}} offers to stand as surety for the accused for an amount of Rs. {{amount}}.

2. The surety is solvent and willing to abide by the conditions imposed by this Hon'ble Court.

3. It is therefore prayed that the surety be accepted and the accused be released accordingly.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

જામીનખત અરજી

નમ્રપણે વિનંતી છે કે:

૧. {{surety_name}} આરોપી માટે રૂ. {{amount}} ની રકમના જામીનદાર તરીકે ઊભા રહેવા તૈયાર છે.

૨. જામીનદાર સધ્ધર છે અને માનનીય ન્યાયાલયની શરતોનું પાલન કરવા તૈયાર છે.

૩. તેથી જામીન સ્વીકારીને આરોપીને તદનુસાર મુક્ત કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "early_hearing",
        "name_en": "Application for Early Hearing",
        "name_gu": "વહેલી સુનાવણી અરજી",
        "category": "General",
        "aliases": ["early hearing", "urgent hearing", "vaheli sunavani", "વહેલી સુનાવણી", "expedite"],
        "fields": [
            {"key": "reason", "label_en": "Reason for Urgency", "label_gu": "તાકીદનું કારણ", "type": "textarea", "required": True},
        ],
        "content_en": """IN THE COURT OF {{court}}, {{district}}

{{case_type}} No. {{case_number}}

APPLICATION FOR EARLY HEARING

Most Respectfully Sheweth:

1. The above matter is pending before this Hon'ble Court.

2. Early hearing is required for the following urgent reason: {{reason}}

3. It is therefore prayed that this Hon'ble Court may be pleased to grant an early hearing of the above matter.

Place: {{district}}
Date: {{today}}

Advocate for the Applicant
{{advocate_name}}
""",
        "content_gu": """માનનીય ન્યાયાલય {{court}}, {{district}}

{{case_type}} નં. {{case_number}}

વહેલી સુનાવણી અરજી

નમ્રપણે વિનંતી છે કે:

૧. ઉપરોક્ત કેસ આ માનનીય ન્યાયાલય સમક્ષ ચાલુ છે.

૨. નીચેના તાકીદના કારણોસર વહેલી સુનાવણી જરૂરી છે: {{reason}}

૩. તેથી ઉપરોક્ત કેસની વહેલી સુનાવણી કરવા વિનંતી છે.

સ્થળ: {{district}}
તારીખ: {{today}}

અરજદારના વકીલ
{{advocate_name}}
""",
    },
    {
        "id": "document_return_application",
        "name_en": "Application for Return of Document",
        "name_gu": "દસ્તાવેજ પરત મેળવવાની અરજી",
        "category": "Civil",
        "aliases": ["document return", "return of document", "dastavej parat", "parat levani arji", "parat magavani arji", "દસ્તાવેજ પરત", "દસ્તાવેજ પરત મેળવવાની અરજી"],
        "fields": [
            {
                "key": "court", "label_en": "Court Name", "label_gu": "કોર્ટનું નામ", "type": "select", "required": True,
                "options": [
                    {"value": "gen_district", "label_en": "District Court", "label_gu": "જિલ્લા ન્યાયાલય"},
                    {"value": "gen_sessions", "label_en": "Sessions Court", "label_gu": "સેશન્સ ન્યાયાલય"},
                    {"value": "gen_jmfc", "label_en": "Court of JMFC", "label_gu": "જે.એમ.એફ.સી. ન્યાયાલય"},
                    {"value": "gen_civil_senior", "label_en": "Principal Senior Civil Judge", "label_gu": "મુખ્ય વરિષ્ઠ સિવિલ જજ"},
                    {"value": "gen_civil_junior", "label_en": "Civil Judge (Junior Division)", "label_gu": "સિવિલ જજ (જુનિયર ડિવિઝન)"},
                    {"value": "gen_family", "label_en": "Family Court", "label_gu": "ફેમિલી કોર્ટ"},
                    {"value": "ahd_metro", "label_en": "Metropolitan Magistrate Court, Ahmedabad", "label_gu": "મેટ્રોપોલિટન મેજિસ્ટ્રેટ કોર્ટ, અમદાવાદ"},
                    {"value": "ahd_city_civil", "label_en": "City Civil Court, Ahmedabad", "label_gu": "સિટી સિવિલ કોર્ટ, અમદાવાદ"},
                    {"value": "surat_district", "label_en": "District & Sessions Court, Surat", "label_gu": "જિલ્લા અને સેશન્સ કોર્ટ, સુરત"},
                    {"value": "vad_district", "label_en": "District & Sessions Court, Vadodara", "label_gu": "જિલ્લા અને સેશન્સ કોર્ટ, વડોદરા"},
                    {"value": "rajkot_district", "label_en": "District & Sessions Court, Rajkot", "label_gu": "જિલ્લા અને સેશન્સ કોર્ટ, રાજકોટ"},
                ],
            },
            {
                "key": "district", "label_en": "District", "label_gu": "જિલ્લો", "type": "select", "required": True,
                "options": [
                    {"value": "ahmedabad", "label_en": "Ahmedabad", "label_gu": "અમદાવાદ"},
                    {"value": "gandhinagar", "label_en": "Gandhinagar", "label_gu": "ગાંધીનગર"},
                    {"value": "surat", "label_en": "Surat", "label_gu": "સુરત"},
                    {"value": "vadodara", "label_en": "Vadodara", "label_gu": "વડોદરા"},
                    {"value": "rajkot", "label_en": "Rajkot", "label_gu": "રાજકોટ"},
                    {"value": "bhavnagar", "label_en": "Bhavnagar", "label_gu": "ભાવનગર"},
                    {"value": "jamnagar", "label_en": "Jamnagar", "label_gu": "જામનગર"},
                    {"value": "junagadh", "label_en": "Junagadh", "label_gu": "જૂનાગઢ"},
                    {"value": "anand", "label_en": "Anand", "label_gu": "આણંદ"},
                    {"value": "kutch", "label_en": "Kutch", "label_gu": "કચ્છ"},
                    {"value": "mehsana", "label_en": "Mehsana", "label_gu": "મહેસાણા"},
                    {"value": "patan", "label_en": "Patan", "label_gu": "પાટણ"},
                ],
            },
            {
                "key": "taluka", "label_en": "Taluka (Optional)", "label_gu": "તાલુકો", "type": "select", "required": False,
                "options": [
                    {"value": "અમદાવાદ શહેર", "label_en": "Ahmedabad City", "label_gu": "અમદાવાદ શહેર", "district_id": "ahmedabad"},
                    {"value": "બાવળા", "label_en": "Bavla", "label_gu": "બાવળા", "district_id": "ahmedabad"},
                    {"value": "દાસક્રોઈ", "label_en": "Daskroi", "label_gu": "દાસક્રોઈ", "district_id": "ahmedabad"},
                    {"value": "ધંધુકા", "label_en": "Dhandhuka", "label_gu": "ધંધુકા", "district_id": "ahmedabad"},
                    {"value": "ધોળકા", "label_en": "Dholka", "label_gu": "ધોળકા", "district_id": "ahmedabad"},
                    {"value": "સાણંદ", "label_en": "Sanand", "label_gu": "સાણંદ", "district_id": "ahmedabad"},
                    {"value": "વિરમગામ", "label_en": "Viramgam", "label_gu": "વિરમગામ", "district_id": "ahmedabad"},
                    {"value": "માંડલ", "label_en": "Mandal", "label_gu": "માંડલ", "district_id": "ahmedabad"},
                    {"value": "ગાંધીનગર", "label_en": "Gandhinagar", "label_gu": "ગાંધીનગર", "district_id": "gandhinagar"},
                    {"value": "કલોલ", "label_en": "Kalol", "label_gu": "કલોલ", "district_id": "gandhinagar"},
                    {"value": "માણસા", "label_en": "Mansa", "label_gu": "માણસા", "district_id": "gandhinagar"},
                    {"value": "દહેગામ", "label_en": "Dehgam", "label_gu": "દહેગામ", "district_id": "gandhinagar"},
                    {"value": "સુરત શહેર", "label_en": "Surat City", "label_gu": "સુરત શહેર", "district_id": "surat"},
                    {"value": "બારડોલી", "label_en": "Bardoli", "label_gu": "બારડોલી", "district_id": "surat"},
                    {"value": "ચોર્યાસી", "label_en": "Choryasi", "label_gu": "ચોર્યાસી", "district_id": "surat"},
                    {"value": "કામરેજ", "label_en": "Kamrej", "label_gu": "કામરેજ", "district_id": "surat"},
                    {"value": "ઓલપાડ", "label_en": "Olpad", "label_gu": "ઓલપાડ", "district_id": "surat"},
                    {"value": "પલસાણા", "label_en": "Palsana", "label_gu": "પલસાણા", "district_id": "surat"},
                    {"value": "વડોદરા શહેર", "label_en": "Vadodara City", "label_gu": "વડોદરા શહેર", "district_id": "vadodara"},
                    {"value": "પાદરા", "label_en": "Padra", "label_gu": "પાદરા", "district_id": "vadodara"},
                    {"value": "સાવલી", "label_en": "Savli", "label_gu": "સાવલી", "district_id": "vadodara"},
                    {"value": "વાઘોડિયા", "label_en": "Waghodia", "label_gu": "વાઘોડિયા", "district_id": "vadodara"},
                    {"value": "કરજણ", "label_en": "Karjan", "label_gu": "કરજણ", "district_id": "vadodara"},
                    {"value": "ડભોઈ", "label_en": "Dabhoi", "label_gu": "ડભોઈ", "district_id": "vadodara"},
                    {"value": "રાજકોટ શહેર", "label_en": "Rajkot City", "label_gu": "રાજકોટ શહેર", "district_id": "rajkot"},
                    {"value": "ગોંડલ", "label_en": "Gondal", "label_gu": "ગોંડલ", "district_id": "rajkot"},
                    {"value": "જસદણ", "label_en": "Jasdan", "label_gu": "જસદણ", "district_id": "rajkot"},
                    {"value": "જેતપુર", "label_en": "Jetpur", "label_gu": "જેતપુર", "district_id": "rajkot"},
                    {"value": "ધોરાજી", "label_en": "Dhoraji", "label_gu": "ધોરાજી", "district_id": "rajkot"},
                    {"value": "વાંકાનેર", "label_en": "Wankaner", "label_gu": "વાંકાનેર", "district_id": "rajkot"},
                    {"value": "ભાવનગર શહેર", "label_en": "Bhavnagar City", "label_gu": "ભાવનગર શહેર", "district_id": "bhavnagar"},
                    {"value": "સિહોર", "label_en": "Sihor", "label_gu": "સિહોર", "district_id": "bhavnagar"},
                    {"value": "પાલીતાણા", "label_en": "Palitana", "label_gu": "પાલીતાણા", "district_id": "bhavnagar"},
                    {"value": "તળાજા", "label_en": "Talaja", "label_gu": "તળાજા", "district_id": "bhavnagar"},
                    {"value": "ગારીયાધાર", "label_en": "Gariadhar", "label_gu": "ગારીયાધાર", "district_id": "bhavnagar"},
                    {"value": "જામનગર શહેર", "label_en": "Jamnagar City", "label_gu": "જામનગર શહેર", "district_id": "jamnagar"},
                    {"value": "કાલાવડ", "label_en": "Kalavad", "label_gu": "કાલાવડ", "district_id": "jamnagar"},
                    {"value": "ધ્રોલ", "label_en": "Dhrol", "label_gu": "ધ્રોલ", "district_id": "jamnagar"},
                    {"value": "જામજોધપુર", "label_en": "Jamjodhpur", "label_gu": "જામજોધપુર", "district_id": "jamnagar"},
                    {"value": "ખંભાળિયા", "label_en": "Khambhalia", "label_gu": "ખંભાળિયા", "district_id": "jamnagar"},
                    {"value": "જૂનાગઢ શહેર", "label_en": "Junagadh City", "label_gu": "જૂનાગઢ શહેર", "district_id": "junagadh"},
                    {"value": "કેશોદ", "label_en": "Keshod", "label_gu": "કેશોદ", "district_id": "junagadh"},
                    {"value": "માણાવદર", "label_en": "Manavadar", "label_gu": "માણાવદર", "district_id": "junagadh"},
                    {"value": "વંથલી", "label_en": "Vanthali", "label_gu": "વંથલી", "district_id": "junagadh"},
                    {"value": "ભેસાણ", "label_en": "Bhesan", "label_gu": "ભેસાણ", "district_id": "junagadh"},
                    {"value": "આણંદ", "label_en": "Anand", "label_gu": "આણંદ", "district_id": "anand"},
                    {"value": "બોરસદ", "label_en": "Borsad", "label_gu": "બોરસદ", "district_id": "anand"},
                    {"value": "ખંભાત", "label_en": "Khambhat", "label_gu": "ખંભાત", "district_id": "anand"},
                    {"value": "પેટલાદ", "label_en": "Petlad", "label_gu": "પેટલાદ", "district_id": "anand"},
                    {"value": "ઉમરેઠ", "label_en": "Umreth", "label_gu": "ઉમરેઠ", "district_id": "anand"},
                    {"value": "ભુજ", "label_en": "Bhuj", "label_gu": "ભુજ", "district_id": "kutch"},
                    {"value": "અંજાર", "label_en": "Anjar", "label_gu": "અંજાર", "district_id": "kutch"},
                    {"value": "ભચાઉ", "label_en": "Bhachau", "label_gu": "ભચાઉ", "district_id": "kutch"},
                    {"value": "ગાંધીધામ", "label_en": "Gandhidham", "label_gu": "ગાંધીધામ", "district_id": "kutch"},
                    {"value": "મુંદ્રા", "label_en": "Mundra", "label_gu": "મુંદ્રા", "district_id": "kutch"},
                    {"value": "રાપર", "label_en": "Rapar", "label_gu": "રાપર", "district_id": "kutch"},
                    {"value": "મહેસાણા", "label_en": "Mehsana", "label_gu": "મહેસાણા", "district_id": "mehsana"},
                    {"value": "વિસનગર", "label_en": "Visnagar", "label_gu": "વિસનગર", "district_id": "mehsana"},
                    {"value": "કાડી", "label_en": "Kadi", "label_gu": "કાડી", "district_id": "mehsana"},
                    {"value": "વિજાપુર", "label_en": "Vijapur", "label_gu": "વિજાપુર", "district_id": "mehsana"},
                    {"value": "વડનગર", "label_en": "Vadnagar", "label_gu": "વડનગર", "district_id": "mehsana"},
                    {"value": "ઉંઝા", "label_en": "Unjha", "label_gu": "ઉંઝા", "district_id": "mehsana"},
                    {"value": "પાટણ", "label_en": "Patan", "label_gu": "પાટણ", "district_id": "patan"},
                    {"value": "સિદ્ધપુર", "label_en": "Sidhpur", "label_gu": "સિદ્ધપુર", "district_id": "patan"},
                    {"value": "ચાણસ્મા", "label_en": "Chanasma", "label_gu": "ચાણસ્મા", "district_id": "patan"},
                    {"value": "રાધનપુર", "label_en": "Radhanpur", "label_gu": "રાધનપુર", "district_id": "patan"},
                    {"value": "હરિજ", "label_en": "Harij", "label_gu": "હરિજ", "district_id": "patan"},
                ],
            },
            {
                "key": "case_type", "label_en": "Case Type", "label_gu": "કેસ પ્રકાર", "type": "select", "required": True,
                "options": [
                    {"value": "civil_suit", "label_en": "Civil Suit", "label_gu": "સિવિલ સૂટ"},
                    {"value": "regular_civil_suit", "label_en": "Regular Civil Suit", "label_gu": "રેગ્યુલર સિવિલ સૂટ"},
                    {"value": "special_civil_suit", "label_en": "Special Civil Suit", "label_gu": "સ્પેશિયલ સિવિલ સૂટ"},
                    {"value": "commercial_suit", "label_en": "Commercial Suit", "label_gu": "કોમર્શિયલ સૂટ"},
                    {"value": "civil_appeal", "label_en": "Civil Appeal", "label_gu": "સિવિલ અપીલ"},
                    {"value": "civil_revision", "label_en": "Civil Revision", "label_gu": "સિવિલ રિવિઝન"},
                    {"value": "execution", "label_en": "Execution", "label_gu": "એક્ઝિક્યુશન"},
                    {"value": "misc_civil_app", "label_en": "Miscellaneous Civil Application", "label_gu": "મિસલેનિયસ સિવિલ અરજી"},
                    {"value": "interim_app", "label_en": "Interim Application", "label_gu": "ઇન્ટરિમ અરજી"},
                    {"value": "other_civil", "label_en": "Other Civil Matter", "label_gu": "અન્ય સિવિલ બાબત"},
                    {"value": "criminal_case", "label_en": "Criminal Case", "label_gu": "ક્રિમિનલ કેસ"},
                    {"value": "criminal_complaint", "label_en": "Criminal Complaint", "label_gu": "ક્રિમિનલ ફરિયાદ"},
                    {"value": "criminal_appeal", "label_en": "Criminal Appeal", "label_gu": "ક્રિમિનલ અપીલ"},
                    {"value": "criminal_revision", "label_en": "Criminal Revision", "label_gu": "ક્રિમિનલ રિવિઝન"},
                    {"value": "criminal_misc_app", "label_en": "Criminal Miscellaneous Application", "label_gu": "ક્રિમિનલ મિસ. અરજી"},
                    {"value": "bail_application", "label_en": "Bail Application", "label_gu": "જામીન અરજી"},
                    {"value": "regular_bail", "label_en": "Regular Bail", "label_gu": "રેગ્યુલર બેલ"},
                    {"value": "anticipatory_bail", "label_en": "Anticipatory Bail", "label_gu": "એન્ટિસિપેટરી બેલ"},
                    {"value": "sessions_case", "label_en": "Sessions Case", "label_gu": "સેશન્સ કેસ"},
                    {"value": "summons_case", "label_en": "Summons Case", "label_gu": "સમન્સ કેસ"},
                    {"value": "warrant_case", "label_en": "Warrant Case", "label_gu": "વોરંટ કેસ"},
                    {"value": "other_criminal", "label_en": "Other Criminal Matter", "label_gu": "અન્ય ક્રિમિનલ બાબત"},
                    {"value": "other", "label_en": "Other", "label_gu": "અન્ય"},
                ],
            },
            {"key": "case_number", "label_en": "Case Number", "label_gu": "કેસ નંબર", "type": "text", "required": True},
            {
                "key": "applicant_role", "label_en": "Applicant-side Role", "label_gu": "ફરીયાદી / અરજદાર / વાદી", "type": "radio", "required": True,
                "options": [
                    {"value": "ફરીયાદી", "label_en": "Farayadi (Complainant)", "label_gu": "ફરીયાદી"},
                    {"value": "અરજદાર", "label_en": "Arjadaar (Applicant)", "label_gu": "અરજદાર"},
                    {"value": "વાદી", "label_en": "Vaadi (Plaintiff)", "label_gu": "વાદી"},
                ],
            },
            {"key": "party_name", "label_en": "Name", "label_gu": "નામ", "type": "text", "required": True},
            {
                "key": "opposite_party_role", "label_en": "Opposite-party Role", "label_gu": "આરોપી / સામાવાળા / પ્રતિવાદી", "type": "radio", "required": True,
                "options": [
                    {"value": "આરોપી", "label_en": "Aaropi (Accused)", "label_gu": "આરોપી"},
                    {"value": "સામાવાળા", "label_en": "Saamavaala (Opponent)", "label_gu": "સામાવાળા"},
                    {"value": "પ્રતિવાદી", "label_en": "Prativaadi (Defendant)", "label_gu": "પ્રતિવાદી"},
                ],
            },
            {"key": "opposite_party", "label_en": "Name", "label_gu": "નામ", "type": "text", "required": True},
            {"key": "advocate_name", "label_en": "Advocate For", "label_gu": "કોના તરફે એડવોકેટ", "type": "select", "required": True, "options": []},
            {
                "key": "case_status", "label_en": "Case Status", "label_gu": "કેસ ચાલુ છે કે ડિસ્પોસ્ડ થયેલ છે", "type": "select", "required": True,
                "options": [
                    {"value": "ચાલુ", "label_en": "Ongoing", "label_gu": "ચાલુ"},
                    {"value": "ડિસ્પોસ્ડ", "label_en": "Disposed", "label_gu": "ડિસ્પોસ્ડ"},
                ],
            },
            {"key": "document_name", "label_en": "Document Name / Description", "label_gu": "દસ્તાવેજનું નામ / વિગત", "type": "textarea", "required": True, "placeholder": "દા.ત. આંક ૧૯ મુજબનો મકાનનો દસ્તાવેજ / પાસપોર્ટ જમા થયેલ હોય તો પાસપોર્ટ"},
            {"key": "date", "label_en": "Date", "label_gu": "તારીખ", "type": "date", "required": True},
            {"key": "place", "label_en": "Place", "label_gu": "સ્થળ", "type": "text", "required": True},
        ],
        "settings": {
            # Page geometry reproduces the source document: A4, 2cm top/bottom,
            # 4cm left/right margins, 13pt Gujarati at 150% line height.
            "page_size": "A4",
            "margin_top_cm": 2,
            "margin_bottom_cm": 2,
            "margin_left_cm": 4,
            "margin_right_cm": 4,
            "body_size": 13,
            "heading_size": 13,
            "line_spacing": 19.5,
            # Per-line layout from the source: centered header block (court line,
            # place line, case line, parties, title), justified body, right-aligned
            # signature. First matching rule wins.
            "block_align": [
                {"contains": "સાહેબશ્રીની કોર્ટમાં", "align": "center"},
                {"position": 2, "align": "center"},
                {"contains": " નં. ", "align": "center"},
                {"contains": "વિરુદ્ધ", "align": "center"},
                {"contains": "દસ્તાવેજ પરત મેળવવાની અરજી", "align": "center", "bold": False},
                {"contains": "સદર કામમા અમો", "align": "justify"},
                {"contains": "સદર કેસ આપ નામદાર", "align": "justify"},
                {"contains": "સદર દસ્તાવેજની હવે", "align": "justify"},
                {"contains": "તારીખ :", "align": "left"},
                {"contains": "સ્થળ :", "align": "left"},
                {"contains": "ના એડવોકેટ", "align": "right"},
            ],
        },
        "content_en": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,

{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{applicant_role}} {{party_name}}
વિરુદ્ધ
{{opposite_party_role}} {{opposite_party}}

દસ્તાવેજ પરત મેળવવાની અરજી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ {{case_status_clause}}. સદર કેસમાં {{document_name}} કામમા રજૂ કરવામાં આવેલ {{tense}}. સદર દસ્તાવેજની હવે કેસના હેતુ માટે જરૂરિયાત ન હોવાથી તથા દસ્તાવેજ પરત મેળવવો ન્યાયના હિતમાં હોય, જેથી સદર દસ્તાવેજ પરત અપાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{place}}

{{selected_party_role}}ના એડવોકેટ
""",
        "content_gu": """મહેરબાન {{court}} સાહેબશ્રીની કોર્ટમાં,

{{taluka_place}}

{{case_type}} નં. {{case_number}}

{{applicant_role}} {{party_name}}
વિરુદ્ધ
{{opposite_party_role}} {{opposite_party}}

દસ્તાવેજ પરત મેળવવાની અરજી

સદર કામમા અમો {{selected_party_role}} ના એડવોકેટની આપ નામદાર કોર્ટને નમ્ર અરજ છે કે.....

સદર કેસ આપ નામદાર કોર્ટ સમક્ષ {{case_status_clause}}. સદર કેસમાં {{document_name}} કામમા રજૂ કરવામાં આવેલ {{tense}}. સદર દસ્તાવેજની હવે કેસના હેતુ માટે જરૂરિયાત ન હોવાથી તથા દસ્તાવેજ પરત મેળવવો ન્યાયના હિતમાં હોય, જેથી સદર દસ્તાવેજ પરત અપાવવા યોગ્ય તે હુકમ કરવા મહેરબાની કરશોજી.

તારીખ : {{date_display}}
સ્થળ : {{place}}

{{selected_party_role}}ના એડવોકેટ
""",
    },
]

# Template-level page-size defaults (admin-controlled via template settings).
# Affidavit / સોગંદનામું-type documents are drafted on Legal-size paper; all
# other templates default to A4. Admins can change any template's page size in
# the Template Editor (Page & Typography Settings).
_TEMPLATE_PAGE_SIZES = {
    "affidavit": "Legal",
}
for _seed_t in TEMPLATES:
    _seed_t.setdefault("settings", {})
    _seed_t["settings"].setdefault(
        "page_size",
        _TEMPLATE_PAGE_SIZES.get(_seed_t.get("id"), "A4"),
    )

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
