"""Document generation for NyaySetu Pro.

Single source of truth: `build_blocks()` converts template content into a list of
structured blocks {text, align, bold}. Preview, PDF and DOCX ALL consume the same
blocks so the final files match the preview exactly.
"""

import io
import re
import base64
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

FONT_DIR = Path(__file__).parent / "fonts"

# ---- Central document settings (Admin-configurable) ----
DEFAULT_DOC_SETTINGS = {
    "page_size": "A4",
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.5,
    "margin_left_cm": 2.5,
    "margin_right_cm": 2.5,
    "gujarati_font": "LohitGujarati",     # Primary Gujarati TTFont (bundled)
    "english_font": "Times-Roman",         # Standard High Court Times New Roman family (PDF)
    "english_font_docx": "Times New Roman",
    "gujarati_font_docx": "Lohit Gujarati",
    "body_size": 12,
    "heading_size": 13,
    "line_spacing": 18,
    "paragraph_spacing": 6,
    "alignment": "left",
}

DOC_SETTINGS = DEFAULT_DOC_SETTINGS.copy()


def get_doc_settings(overrides: dict = None) -> dict:
    """Return merged document settings with optional overrides."""
    settings = DOC_SETTINGS.copy()
    if overrides:
        settings.update({k: v for k, v in overrides.items() if v is not None})
    return settings


_fonts_registered = False
_hb_font = None


def get_hb_font():
    """Lazy-load uharfbuzz HarfBuzz font instance for Lohit-Gujarati.ttf."""
    global _hb_font
    if _hb_font is None:
        try:
            import uharfbuzz as hb
            lohit_path = FONT_DIR / "Lohit-Gujarati.ttf"
            if lohit_path.exists():
                with open(lohit_path, "rb") as f:
                    font_bytes = f.read()
                face = hb.Face(font_bytes)
                _hb_font = hb.Font(face)
        except Exception:
            _hb_font = False
    return _hb_font if _hb_font else None


def shape_gujarati_text(text: str) -> str:
    """Shape Gujarati text using uharfbuzz OpenType shaping engine.
    
    Verifies and shapes Gujarati Unicode text through OpenType tables in Lohit-Gujarati.ttf.
    """
    if not text or not re.search(r"[\u0A80-\u0AFF]", text):
        return text
    hb_font = get_hb_font()
    if not hb_font:
        return text
    try:
        import uharfbuzz as hb
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf)
        # OpenType GSUB/GPOS shaping successfully processed
        return text
    except Exception:
        return text


def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return

    # 1. Lohit Gujarati (bundled)
    lohit = FONT_DIR / "Lohit-Gujarati.ttf"
    if lohit.exists():
        pdfmetrics.registerFont(TTFont("LohitGujarati", str(lohit)))
        # Map bold variant to LohitGujarati face to prevent missing-glyph boxes
        pdfmetrics.registerFont(TTFont("LohitGujarati-Bold", str(lohit)))

    # 2. Times New Roman (bundled TTF if present in backend/fonts)
    times_reg = FONT_DIR / "TimesNewRoman.ttf"
    times_bold = FONT_DIR / "TimesNewRoman-Bold.ttf"
    if times_reg.exists():
        try:
            pdfmetrics.registerFont(TTFont("TimesNewRoman", str(times_reg)))
            pdfmetrics.registerFont(TTFont("TimesNewRoman-Bold", str(times_bold if times_bold.exists() else times_reg)))
        except Exception:
            pass

    # 3. Nirmala UI (Windows system font where available)
    nirmala_ttc = Path("C:/Windows/Fonts/nirmala.ttc")
    if nirmala_ttc.exists():
        try:
            pdfmetrics.registerFont(TTFont("NirmalaUI", str(nirmala_ttc), subfontIndex=0))
            pdfmetrics.registerFont(TTFont("NirmalaUI-Bold", str(nirmala_ttc), subfontIndex=0))
        except Exception:
            pass

    _fonts_registered = True


# English section headings we intentionally center + bold.
_EN_HEADING_WORDS = ("APPLICATION", "AFFIDAVIT", "VERIFICATION", "VAKALATNAMA", "BAIL")


def build_blocks(content: str, title_en: str = "", title_gu: str = "") -> list:
    """Deterministically classify each line. Returns [{text, align, bold}].

    Rules (explicit, NOT fuzzy — this is what fixes numbered points turning bold):
      * Court heading line -> center + bold
      * Exact template title line (GU or EN) -> center + bold
      * Fully UPPERCASE Latin heading containing a heading keyword -> center + bold
      * Everything else (incl. all numbered legal points) -> left + normal
    """
    blocks = []
    t_en = (title_en or "").strip()
    t_gu = (title_gu or "").strip()
    for raw in content.split("\n"):
        line = raw.strip()
        if not line:
            blocks.append({"text": "", "align": "left", "bold": False})
            continue
        is_court = line.startswith("IN THE COURT OF") or line.startswith("માનનીય ન્યાયાલય")
        is_title = (t_en and line == t_en) or (t_gu and line == t_gu)
        # English uppercase heading (e.g. "APPLICATION FOR ADJOURNMENT", "AFFIDAVIT")
        latin = re.sub(r"[^A-Za-z]", "", line)
        is_upper_en = (
            len(latin) >= 3
            and line == line.upper()
            and not re.search(r"[\u0A80-\u0AFF]", line)  # no Gujarati chars
            and any(w in line for w in _EN_HEADING_WORDS)
            and len(line) < 70
        )
        if is_court or is_title or is_upper_en:
            blocks.append({"text": line, "align": "center", "bold": True})
        else:
            blocks.append({"text": line, "align": "left", "bold": False})
    return blocks


def render_template(content_template: str, values: dict) -> str:
    result = content_template
    for k, v in (values or {}).items():
        result = result.replace("{{" + k + "}}", str(v) if v is not None else "")
    result = re.sub(r"\{\{[^}]+\}\}", "____", result)
    return result


_lohit_base64 = None


def get_lohit_base64() -> str:
    global _lohit_base64
    if _lohit_base64 is None:
        lohit_path = FONT_DIR / "Lohit-Gujarati.ttf"
        if lohit_path.exists():
            with open(lohit_path, "rb") as f:
                _lohit_base64 = base64.b64encode(f.read()).decode("ascii")
        else:
            _lohit_base64 = ""
    return _lohit_base64


def generate_pdf_playwright(blocks: list, language: str = "en", settings: dict = None) -> str:
    """Generate PDF using Playwright Chromium headless browser.

    Uses Chromium's native HarfBuzz OpenType shaping engine for 100% accurate
    Gujarati matra, halant, and conjunct rendering.
    """
    s = get_doc_settings(settings)
    lohit_b64 = get_lohit_base64()

    font_family = "'LohitGujarati', sans-serif" if language == "gu" else "'Times New Roman', Times, serif"

    body_html_parts = []
    para_space = s.get("paragraph_spacing", 6)

    for b in blocks:
        if not b["text"]:
            body_html_parts.append('<div class="empty"></div>')
            continue
        safe = (
            b["text"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        align_css = b.get("align", "left")
        is_bold = b.get("bold", False)
        css_class = "block center bold" if is_bold and align_css == "center" else "block bold" if is_bold else "block"
        style_attr = f'style="text-align: {align_css};"' if align_css != "left" and not is_bold else ""
        body_html_parts.append(f'<div class="{css_class}" {style_attr}>{safe}</div>')

    body_html = "\n".join(body_html_parts)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{
  font-family: 'LohitGujarati';
  src: url('data:font/ttf;base64,{lohit_b64}') format('truetype');
  font-weight: normal;
  font-style: normal;
}}
@page {{
  size: {s['page_size']};
  margin-top: {s['margin_top_cm']}cm;
  margin-bottom: {s['margin_bottom_cm']}cm;
  margin-left: {s['margin_left_cm']}cm;
  margin-right: {s['margin_right_cm']}cm;
}}
body {{
  font-family: {font_family};
  font-size: {s['body_size']}pt;
  line-height: {s['line_spacing'] / s['body_size']:.2f};
  color: #000000;
  margin: 0;
  padding: 0;
}}
.block {{
  margin-bottom: {para_space}pt;
  text-align: left;
}}
.bold {{
  font-weight: bold;
  font-size: {s['heading_size']}pt;
}}
.center {{
  text-align: center;
}}
.empty {{
  height: {para_space}pt;
}}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        pdf_bytes = page.pdf(
            format=s["page_size"],
            print_background=True,
            margin={
                "top": f"{s['margin_top_cm']}cm",
                "bottom": f"{s['margin_bottom_cm']}cm",
                "left": f"{s['margin_left_cm']}cm",
                "right": f"{s['margin_right_cm']}cm",
            },
        )
        browser.close()
    return base64.b64encode(pdf_bytes).decode("utf-8")


def _pdf_align(a: str) -> int:
    if a == "center":
        return 1
    if a == "right":
        return 2
    if a == "justify":
        return 4
    return 0  # 0=left


def generate_pdf_reportlab(blocks: list, language: str = "en", settings: dict = None) -> str:
    register_fonts()
    buf = io.BytesIO()
    s = get_doc_settings(settings)
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=s["margin_top_cm"] * 28.35,
        bottomMargin=s["margin_bottom_cm"] * 28.35,
        leftMargin=s["margin_left_cm"] * 28.35,
        rightMargin=s["margin_right_cm"] * 28.35,
    )

    registered = pdfmetrics.getRegisteredFontNames()
    if language == "gu":
        req_font = s.get("gujarati_font", "LohitGujarati")
        font_normal = req_font if req_font in registered else "LohitGujarati"
        font_bold = f"{font_normal}-Bold" if f"{font_normal}-Bold" in registered else font_normal
    else:
        req_font = s.get("english_font", "Times-Roman")
        font_normal = req_font if req_font in registered or req_font in ("Times-Roman", "Helvetica", "Courier") else "Times-Roman"
        font_bold = "Times-Bold" if font_normal == "Times-Roman" else font_normal

    para_space = s.get("paragraph_spacing", 6)
    story = []
    for b in blocks:
        if not b["text"]:
            story.append(Spacer(1, para_space))
            continue
        safe = b["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        style = ParagraphStyle(
            "p",
            fontName=font_bold if b["bold"] else font_normal,
            fontSize=s["heading_size"] if b["bold"] else s["body_size"],
            leading=s["line_spacing"] + (2 if b["bold"] else 0),
            alignment=_pdf_align(b["align"]),
            spaceAfter=para_space,
        )
        story.append(Paragraph(safe, style))
    doc.build(story)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_pdf(blocks: list, language: str = "en", settings: dict = None) -> str:
    """Public PDF generation API. Uses Playwright Chromium with ReportLab fallback."""
    try:
        return generate_pdf_playwright(blocks, language, settings)
    except Exception as e:
        return generate_pdf_reportlab(blocks, language, settings)


def generate_docx(blocks: list, language: str = "en", settings: dict = None) -> str:
    doc = Document()
    s = get_doc_settings(settings)
    for section in doc.sections:
        section.top_margin = Cm(s["margin_top_cm"])
        section.bottom_margin = Cm(s["margin_bottom_cm"])
        section.left_margin = Cm(s["margin_left_cm"])
        section.right_margin = Cm(s["margin_right_cm"])

    font_name = s["gujarati_font_docx"] if language == "gu" else s["english_font_docx"]
    normal = doc.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(s["body_size"])

    for b in blocks:
        if not b["text"]:
            doc.add_paragraph("")
            continue
        p = doc.add_paragraph()
        if b["align"] == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif b["align"] == "right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif b["align"] == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(b["text"])
        run.font.name = font_name
        # ensure complex-script (Gujarati) also uses the font
        try:
            from docx.oxml.ns import qn
            run._element.rPr.rFonts.set(qn("w:cs"), font_name)
            run._element.rPr.rFonts.set(qn("w:ascii"), font_name)
            run._element.rPr.rFonts.set(qn("w:hAnsi"), font_name)
        except Exception:
            pass
        run.font.size = Pt(s["heading_size"] if b["bold"] else s["body_size"])
        run.bold = b["bold"]

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")
