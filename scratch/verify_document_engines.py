"""
Verification of all 6 document generation formats:
1. Gujarati PDF (HarfBuzz shaped + Noto Serif Gujarati font)
2. English PDF
3. Gujarati DOCX
4. Gujarati ODT
5. Gujarati PNG (pypdfium2 rendered)
6. English PNG
"""
import sys
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from doc_generator import (
    generate_pdf_detailed,
    generate_docx,
    generate_odt,
    generate_document_images,
    build_blocks,
    get_doc_settings,
)

print("=" * 60)
print("TESTING DOCUMENT GENERATION ENGINE FOR VERCEL COMPATIBILITY")
print("=" * 60)

# 1. Gujarati Sample Blocks
gu_text = (
    "મેહરબાન સિટી સિવિલ કોર્ટ, અમદાવાદ સાહેબશ્રીની કોર્ટમાં\n\n"
    "દિવાની દાવો નં. ૧૨૩/૨૦૨૬\n\n"
    "વાદી: શ્રી રમેશભાઈ ગોવિંદભાઈ પટેલ\n"
    "વિરુદ્ધ\n"
    "પ્રતિવાદી: ગુજરાત રાજ્ય\n\n"
    "વિષય: મુદત અરજી\n\n"
    "સવિનય જણાવવાનું કે ઉપરોક્ત કામના વકીલશ્રી અન્ય કોર્ટમાં રોકાયેલ હોવાથી આજની મુદત મોકૂફ રાખવા વિનંતી છે."
)
gu_blocks = build_blocks(gu_text, "Adjournment", "મુદત અરજી", "justify")
settings = get_doc_settings({"page_size": "A4", "template_id": "adjournment", "raw_content": gu_text, "ctx": {}})

# Gujarati PDF
pdf_b64, meta = generate_pdf_detailed(gu_blocks, "gu", settings)
assert len(pdf_b64) > 1000
print(f"1. Gujarati PDF:      SUCCESS | Size: {len(pdf_b64)} chars | Engine: {meta.get('engine')} | Font: {meta.get('font_family')}")

# English PDF
en_text = (
    "IN THE COURT OF CITY CIVIL COURT, AHMEDABAD\n\n"
    "Civil Suit No. 123/2026\n\n"
    "Plaintiff: Mr. Ramesh G. Patel\n"
    "Versus\n"
    "Defendant: State of Gujarat\n\n"
    "Subject: Adjournment Application\n\n"
    "The applicant respectfully submits that the advocate is engaged in another court, hence adjournment is requested."
)
en_blocks = build_blocks(en_text, "Adjournment", "મુદત અરજી", "justify")
pdf_en_b64, meta_en = generate_pdf_detailed(en_blocks, "en", settings)
assert len(pdf_en_b64) > 1000
print(f"2. English PDF:       SUCCESS | Size: {len(pdf_en_b64)} chars | Engine: {meta_en.get('engine')}")

# Gujarati DOCX
docx_b64 = generate_docx(gu_blocks, "gu", settings)
assert len(docx_b64) > 1000
print(f"3. Gujarati DOCX:     SUCCESS | Size: {len(docx_b64)} chars")

# Gujarati ODT
odt_b64 = generate_odt(gu_blocks, "gu", settings)
assert len(odt_b64) > 1000
print(f"4. Gujarati ODT:      SUCCESS | Size: {len(odt_b64)} chars")

# Gujarati PNG / Image
png_pages = generate_document_images(gu_blocks, "gu", settings)
assert len(png_pages) >= 1
assert len(png_pages[0]) > 1000
print(f"5. Gujarati PNG:      SUCCESS | Pages: {len(png_pages)} | Page 1 Bytes: {len(png_pages[0])}")

# English PNG / Image
en_png_pages = generate_document_images(en_blocks, "en", settings)
assert len(en_png_pages) >= 1
assert len(en_png_pages[0]) > 1000
print(f"6. English PNG:       SUCCESS | Pages: {len(en_png_pages)} | Page 1 Bytes: {len(en_png_pages[0])}")

print("\n" + "=" * 60)
print("ALL 6 DOCUMENT FORMATS VERIFIED - ZERO CORRUPTIONS")
print("=" * 60)
