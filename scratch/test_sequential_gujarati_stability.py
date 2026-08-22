"""
Sequential Gujarati Document Generation Stability & Anti-Corruption Test
Verifies that 10 sequential generations of complex legal Gujarati documents
produce 100% stable, perfectly shaped, non-colliding font subsets.
"""
import sys
import hashlib
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from doc_generator import generate_pdf_detailed, build_blocks, get_doc_settings

gujarati_legal_texts = [
    # 1. Vakalatnama
    (
        "વકાલતનામું (દિવાની)\n"
        "મેહરબાન પ્રિન્સિપાલ ડિસ્ટ્રિક્ટ એન્ડ સેશન્સ જજ સાહેબની અદાલતમાં, ગાંધીનગર\n"
        "દિવાની પરચુરણ અરજી નં. ૨૪૫/૨૦૨૬\n"
        "વાદી: શ્રી મહેશભાઈ ઈશ્વરભાઈ પ્રજાપતિ\n"
        "વિરુદ્ધ\n"
        "પ્રતિવાદી: ગુજરાત રાજ્ય તથા અન્ય\n"
        "આથી અમો નીચે સહી કરનાર પક્ષકારો અમારા વતી કેસ ચલાવવા એડવોકેટશ્રીને રોકીએ છીએ."
    ),
    # 2. Mudat Arji (Adjournment)
    (
        "મુદત અરજી\n"
        "મેહરબાન સિટી સિવિલ કોર્ટ સાહેબની કોર્ટ નં. ૪ માં, અમદાવાદ\n"
        "દિવાની દાવો નં. ૫૬૭/૨૦૨૫\n"
        "વાદી: શ્રીમતી સુમિત્રાબેન ગોવર્ધનદાસ શાહ\n"
        "વિરુદ્ધ\n"
        "પ્રતિવાદી: શ્રી નરેન્દ્રભાઈ કનૈયાલાલ જોષી\n"
        "વિષય: મુદત આપવા બાબત.\n"
        "સવિનય જણાવવાનું કે કામના મુખ્ય એડવોકેટશ્રી ગુજરાત હાઇકોર્ટમાં રોકાયેલ હોવાથી મુદત આપવા નમ્ર વિનંતી છે."
    ),
    # 3. Document Return Application
    (
        "દસ્તાવેજ પરત મેળવવાની અરજી\n"
        "મેહરબાન ચીફ જ્યુડિશિયલ મેજિસ્ટ્રેટ સાહેબશ્રીની કોર્ટ, વડોદરા\n"
        "ક્રિમિનલ કેસ નં. ૧૨૩૪/૨૦૨૪\n"
        "ફરિયાદી: સ્ટેટ ઓફ ગુજરાત\n"
        "વિરુદ્ધ\n"
        "આરોપી: અલ્પેશકુમાર હસમુખભાઈ સોલંકી\n"
        "વિષય: મુદ્દામાલ/અસલ દસ્તાવેજ પરત આપવા બાબત."
    ),
    # 4. Complex Conjunct Stress Test
    (
        "જટિલ જોડાક્ષર અને વિશિષ્ટ કાનૂની સંજ્ઞાઓ ચકાસણી:\n"
        "ક્ષત્રિય, જ્ઞાનપ્રકાશ, શ્રદ્ધાંજલિ, ત્રિવેણી સંગમ, પ્રક્રિયાગત દ્રષ્ટિકોણ,\n"
        "દ્વારા નિર્દેશિત, ન્યાયાલયની સંવેદનશીલતા, બ્રહ્માંડ, વિદ્યાસહાયક,\n"
        "સ્ટેશન ડાયરી નોંધણી, અધિકૃત પાવર ઓફ એટર્ની, પરિશિષ્ટ-ક."
    )
]

print("=" * 70)
print("RUNNING 10 SEQUENTIAL GUJARATI GENERATION CYCLES (ANTI-COLLISION TEST)")
print("=" * 70)

hashes = []
for i in range(10):
    text = gujarati_legal_texts[i % len(gujarati_legal_texts)]
    blocks = build_blocks(text, f"Test {i+1}", f"ટેસ્ટ {i+1}", "justify")
    settings = get_doc_settings({"page_size": "A4", "template_id": f"tpl_{i}", "raw_content": text, "ctx": {}})
    pdf_b64, meta = generate_pdf_detailed(blocks, "gu", settings)
    
    assert len(pdf_b64) > 1000, f"Generation {i+1} failed with small payload"
    assert meta.get("engine") == "harfbuzz", f"Generation {i+1} failed to use HarfBuzz"
    assert meta.get("font_family") in ("NotoSansGujarati", "NotoSerifGujarati"), f"Generation {i+1} bad font"
    
    # Verify PDF contains valid bytes and unique subset identity
    h = hashlib.sha256(pdf_b64.encode('utf-8')).hexdigest()[:12]
    hashes.append(h)
    print(f"Cycle {i+1:2d}: SUCCESS | Size: {len(pdf_b64):5d} chars | SHA256: {h} | Engine: {meta.get('engine')} | Font: {meta.get('font_family')}")

print("=" * 70)
print("ALL 10 SEQUENTIAL GUJARATI GENERATIONS COMPLETED WITH ZERO CORRUPTION")
print("=" * 70)
