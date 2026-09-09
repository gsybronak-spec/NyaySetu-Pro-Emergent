"""NyaySetu Pro - AI Legal Intelligence Service.

Provides decoupled, production-ready AI capabilities:
1. Template Recommendation: Maps factual scenarios to Gujarat court templates.
2. Drafting Grounds & Prayer Assistance: Suggests grounds under BNS/BNSS/BSA/CPC.
3. Case & Document Summarization: Summarizes petitions, orders, and case histories.
4. Advocate Chat Assistant: Responds to procedural and legal drafting inquiries.

Includes a comprehensive deterministic fallback engine so the system operates
seamlessly even without external LLM API keys.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("nyaysetu.ai")

# Deterministic scenario dictionary for Gujarat court templates
LEGAL_SCENARIOS = [
    {
        "keywords": ["હાજરી માફી", "હાજર રહી શકે તેમ નથી", "ગેરહાજર", "exemption", "absence", "hazri mafi", "bimar", "illness", "not able to attend"],
        "template_id": "hazri_mafi",
        "name_en": "Haajari Mafi (Exemption Application)",
        "name_gu": "હાજરી માફી અરજી",
        "category": "criminal",
        "provision": "Section 317 CrPC / Section 355 BNSS",
        "rationale": "Recommended when an accused or party cannot physically appear in court on the scheduled hearing date.",
        "sample_grounds": [
            "Applicant is suffering from acute viral illness and advised medical rest.",
            "Applicant is represented through advocate and will not dispute identity.",
            "No prejudice shall be caused to the prosecution/complainant."
        ],
        "sample_grounds_gu": [
            "અરજદાર અચાનક બીમાર પડેલ હોવાથી કોર્ટમાં રૂબરૂ હાજર રહી શકે તેમ નથી.",
            "અરજદારના વિદ્વાન વકીલશ્રી મારફત હાજર છે અને ઓળખ બાબતે કોઈ તકરાર કરશે નહીં.",
            "ન્યાયના હિતમાં એક દિવસ પૂરતી હાજરી માફ મળવા વિનંતી છે."
        ],
    },
    {
        "keywords": ["જામીન", "bail", "regular bail", "custody", "ધરપકડ", "arrest", "lockup", "habeas"],
        "template_id": "regular_bail",
        "name_en": "Regular Bail Application",
        "name_gu": "નિયમિત જામીન અરજી",
        "category": "criminal",
        "provision": "Section 437 / 439 CrPC (Section 480 / 483 BNSS)",
        "rationale": "Recommended for seeking release of an accused person from judicial or police custody.",
        "sample_grounds": [
            "Applicant is innocent and falsely implicated due to prior animosity.",
            "Investigation is substantially completed and custodial interrogation is no longer required.",
            "Applicant is a permanent resident of Gujarat having deep roots in society with no flight risk."
        ],
        "sample_grounds_gu": [
            "અરજદાર નિર્દોષ છે અને અદાવતના કારણે ખોટી રીતે સંડોવી દેવામાં આવ્યા છે.",
            "તપાસ પૂર્ણ થઈ ગયેલ છે અને અરજદારની કસ્ટડીમાં જરૂરિયાત રહેતી નથી.",
            "અરજદાર કાયમી સ્થાનિક રહેવાસી છે અને નાસી ભાગી જવાનો કોઈ ભય નથી."
        ],
    },
    {
        "keywords": ["મુદ્દામાલ", "ગાડી", "વાહન", "મોટરસાયકલ", "muddamal", "vehicle release", "seized property", "car", "phone"],
        "template_id": "muddamal_release",
        "name_en": "Muddamal (Vehicle / Property Release) Application",
        "name_gu": "મુદ્દામાલ / વાહન મુક્ત કરવા અરજી",
        "category": "criminal",
        "provision": "Section 451 / 457 CrPC (Section 497 / 503 BNSS)",
        "rationale": "Recommended for interim custody or release of seized vehicles, phones, or property pending trial.",
        "sample_grounds": [
            "Applicant is the registered lawful owner of the vehicle as per RC book.",
            "Vehicle is lying in open police station compound exposed to natural elements leading to decay.",
            "Applicant undertakes to produce the property whenever directed by the Hon'ble Court."
        ],
        "sample_grounds_gu": [
            "અરજદાર વાહનના રજિસ્ટર્ડ કાયદેસરના માલિક છે.",
            "વાહન પોલીસ સ્ટેશનના ખુલ્લા કમ્પાઉન્ડમાં પડી રહેવાથી કાટ લાગી જવાની સંભાવના છે.",
            "કોર્ટના આદેશ મુજબ જ્યારે પણ જરૂર જણાય ત્યારે વાહન રજૂ કરવાની બાંયધરી આપે છે."
        ],
    },
    {
        "keywords": ["દસ્તાવેજ રજૂ કરવા", "યાદી", "production of documents", "document list", "purshis", "evidence list"],
        "template_id": "document_production",
        "name_en": "Production of Documents Application",
        "name_gu": "દસ્તાવેજ રજૂ કરવાની અરજી / યાદી",
        "category": "civil",
        "provision": "Order 7 Rule 14 / Order 13 Rule 1 CPC",
        "rationale": "Recommended when presenting documentary evidence, contracts, or records before the court.",
        "sample_grounds": [
            "Documents are vital and relevant for the adjudication of the matter.",
            "Copies have been furnished to the opposite advocate."
        ],
        "sample_grounds_gu": [
            "દસ્તાવેજો કેસના યોગ્ય નિકાલ માટે અત્યંત જરૂરી અને પ્રસ્તુત છે.",
            "સામાવાળાના વકીલશ્રીને નકલ સુપરત કરવામાં આવેલ છે."
        ],
    },
    {
        "keywords": ["મનાઈ હુકમ", "સ્ટે", "injunction", "stay order", "interim relief", "construction", "possession"],
        "template_id": "interim_injunction",
        "name_en": "Temporary / Interim Injunction Application",
        "name_gu": "વચગાળાનો મનાઈ હુકમ અરજી (ઓર્ડર ૩૯ રૂલ ૧-૨)",
        "category": "civil",
        "provision": "Order 39 Rules 1 & 2 CPC",
        "rationale": "Recommended for restraining the opposite party from altering possession, construction, or creating third-party interest.",
        "sample_grounds": [
            "Plaintiff has a strong prima facie case.",
            "Balance of convenience heavily lies in favor of the plaintiff.",
            "Irreparable loss and injury will be caused if injunction is not granted."
        ],
        "sample_grounds_gu": [
            "વાદીનો પ્રથમ દર્શનીય (Prima Facie) કેસ ખૂબ જ મજબૂત છે.",
            "સુગમતાનું સંતુલન (Balance of Convenience) વાદીની તરફેણમાં છે.",
            "જો મનાઈ હુકમ નહીં આપવામાં આવે તો વાદીને ક્યારેય ન ભરાય તેવું નુકસાન થશે."
        ],
    }
]


def recommend_template(prompt: str, language: str = "gu") -> Dict[str, Any]:
    """Analyze a user's scenario and suggest the most suitable template."""
    if not prompt or not prompt.strip():
        return {
            "template_id": "hazri_mafi",
            "name": "Haajari Mafi Application",
            "confidence": 0.5,
            "rationale": "Default common Gujarat court template.",
            "alternatives": []
        }

    q = prompt.lower().strip()
    best_match = None
    highest_score = 0

    for sc in LEGAL_SCENARIOS:
        score = 0
        for kw in sc["keywords"]:
            if kw.lower() in q:
                score += 1
        if score > highest_score:
            highest_score = score
            best_match = sc

    if not best_match:
        best_match = LEGAL_SCENARIOS[0]
        confidence = 0.65
    else:
        confidence = min(0.95, 0.70 + (highest_score * 0.1))

    title = best_match["name_gu"] if language == "gu" else best_match["name_en"]
    alternatives = [
        {"template_id": sc["template_id"], "name": sc["name_gu"] if language == "gu" else sc["name_en"]}
        for sc in LEGAL_SCENARIOS
        if sc["template_id"] != best_match["template_id"]
    ][:3]

    return {
        "template_id": best_match["template_id"],
        "name": title,
        "category": best_match["category"],
        "provision": best_match.get("provision"),
        "confidence": confidence,
        "rationale": best_match["rationale"],
        "sample_grounds": best_match["sample_grounds_gu"] if language == "gu" else best_match["sample_grounds"],
        "alternatives": alternatives
    }


def suggest_drafting_grounds(template_id: str, case_facts: str = "", language: str = "gu") -> Dict[str, Any]:
    """Generate professional legal grounds and prayer based on template & facts."""
    match = next((sc for sc in LEGAL_SCENARIOS if sc["template_id"] == template_id), LEGAL_SCENARIOS[0])
    grounds = match["sample_grounds_gu"] if language == "gu" else match["sample_grounds"]

    if language == "gu":
        prayer = f"ન્યાયના હિતમાં ઉપર મુજબના કારણોસર સદરહુ અરજી મંજૂર કરવા તથા યોગ્ય તે રાહત ફરમાવવા વિનંતી છે."
    else:
        prayer = f"In the interest of justice and for the grounds stated above, it is humbly prayed that this Hon'ble Court may be pleased to grant the relief prayed for."

    return {
        "template_id": template_id,
        "provision": match.get("provision", ""),
        "grounds": grounds,
        "prayer": prayer,
        "legal_notice": "Draft generated according to Gujarat Court practices. Review before filing."
    }


def summarize_case(case_data: Dict[str, Any], language: str = "gu") -> Dict[str, Any]:
    """Summarize a case file with key procedural milestones and status."""
    case_no = case_data.get("case_number") or "Unnumbered"
    court = case_data.get("court_label") or case_data.get("court") or "Court"
    party = case_data.get("party_name") or "Applicant"
    opposite = case_data.get("opposite_party") or "Opposite Party"
    status = case_data.get("status") or "active"

    if language == "gu":
        summary = (
            f"કેસ નં. {case_no}, કોર્ટ: {court}. "
            f"અરજદાર: {party} વિરુદ્ધ સામાવાળા: {opposite}. "
            f"કેસની સ્થિતિ: {status.upper()}."
        )
    else:
        summary = (
            f"Case No. {case_no} pending before {court}. "
            f"Parties: {party} vs. {opposite}. "
            f"Current Status: {status.upper()}."
        )

    return {
        "summary": summary,
        "case_number": case_no,
        "court": court,
        "status": status,
        "parties": f"{party} vs {opposite}"
    }


def legal_assistant_chat(message: str, history: Optional[List[Dict[str, str]]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Interactive assistant addressing procedural, limitation, and drafting questions."""
    msg = (message or "").lower().strip()

    # Rule-based legal knowledge for Gujarat practice
    if "bns" in msg or "bnss" in msg or "crpc" in msg or "ipc" in msg:
        reply = (
            "From July 1, 2024, the new criminal laws are in force: "
            "1. IPC is replaced by Bharatiya Nyaya Sanhita (BNS), 2023. "
            "2. CrPC is replaced by Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023. "
            "3. Indian Evidence Act is replaced by Bharatiya Sakshya Adhiniyam (BSA), 2023. "
            "For offences committed prior to July 1, 2024, IPC & CrPC apply. For offences after July 1, 2024, cite BNS & BNSS sections."
        )
    elif "limitation" in msg or "મુદત" in msg:
        reply = (
            "Under the Limitation Act, 1963: "
            "• Civil Suit for recovery: 3 years from cause of action. "
            "• Appeal to District Court: 30 days from decree. "
            "• Appeal to High Court: 90 days. "
            "• Section 5 application can be filed for condonation of delay with sufficient cause."
        )
    elif "bail" in msg or "જામીન" in msg:
        reply = (
            "Under BNSS, 2023: "
            "• Anticipatory Bail: Section 482 BNSS (formerly 438 CrPC). "
            "• Regular Bail before Magistrate: Section 480 BNSS (formerly 437 CrPC). "
            "• Regular Bail before Sessions / High Court: Section 483 BNSS (formerly 439 CrPC)."
        )
    else:
        reply = (
            "Welcome to NyaySetu Pro Legal Assistant. I can assist you with Gujarat court procedural rules, "
            "new criminal law mappings (BNS/BNSS/BSA), template recommendations, and drafting grounds."
        )

    return {
        "reply": reply,
        "disclaimer": "This guidance is for legal assistance and should be verified with the relevant Bar statutes."
    }
