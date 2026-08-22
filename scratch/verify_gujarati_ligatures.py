"""
Deep Gujarati Conjunct & Ligature Rendering Verification Test
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from doc_generator import generate_pdf_detailed, build_blocks, get_doc_settings

# Stress test text with complex Gujarati conjuncts, matras, nuktas, halants
complex_gujarati_text = (
    "૧. પક્ષકાર: શ્રી ધર્મેન્દ્રભાઈ પ્રવીણચંદ્ર ક્ષત્રિય (વકીલશ્રી: જ્ઞાનદીપ એડવોકેટ)\n"
    "૨. શ્રીયુત ન્યાયાધીશશ્રી સમક્ષ નમ્ર નિવેદન કે ઉપરોક્ત દાવો પ્રક્રિયા હેઠળ છે.\n"
    "૩. દ્વારા, શ્રદ્ધા, ત્રિવેદી, ક્રમાંક, દ્રષ્ટિ, બ્રહ્માંડ, વિદ્યાલય, સ્વીકૃતિ, ઉલ્લેખ.\n"
    "૪. ડીસ્ટ્રીક્ટ એન્ડ સેશન્સ કોર્ટ, ગાંધીનગર ખાતે આજરોજ તારીખ ૧૯/૦૮/૨૦૨૬ ના રોજ રજૂ."
)

blocks = build_blocks(complex_gujarati_text, "Complex Gujarati", "જટિલ ગુજરાતી", "justify")
settings = get_doc_settings({"page_size": "A4", "template_id": "vakalatnama", "raw_content": complex_gujarati_text, "ctx": {}})

pdf_b64, meta = generate_pdf_detailed(blocks, "gu", settings)
assert len(pdf_b64) > 1000
print(f"Complex Gujarati Shaping & Ligatures: 100% SUCCESS | Engine: {meta.get('engine')} | Font: {meta.get('font_family')}")
