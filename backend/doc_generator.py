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

# ---- Central document settings (Admin-configurable later) ----
DOC_SETTINGS = {
    "page_size": "A4",
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.5,
    "margin_left_cm": 2.5,
    "margin_right_cm": 2.5,
    "gujarati_font": "LohitGujarati",   # Lohit Gujarati (bundled)
    "english_font": "Times-Roman",       # Times New Roman family
    "english_font_docx": "Times New Roman",
    "gujarati_font_docx": "Lohit Gujarati",
    "body_size": 12,
    "heading_size": 13,
    "line_spacing": 18,
}

_fonts_registered = False


def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    lohit = FONT_DIR / "Lohit-Gujarati.ttf"
    if lohit.exists():
        pdfmetrics.registerFont(TTFont("LohitGujarati", str(lohit)))
        # No separate bold file for Lohit; map bold to the same face so glyphs
        # never fall back to a boxed/placeholder font.
        pdfmetrics.registerFont(TTFont("LohitGujarati-Bold", str(lohit)))
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


def _pdf_align(a: str) -> int:
    return 1 if a == "center" else 0  # 0=left, 1=center


def generate_pdf(blocks: list, language: str = "en") -> str:
    register_fonts()
    buf = io.BytesIO()
    s = DOC_SETTINGS
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=s["margin_top_cm"] * 28.35,
        bottomMargin=s["margin_bottom_cm"] * 28.35,
        leftMargin=s["margin_left_cm"] * 28.35,
        rightMargin=s["margin_right_cm"] * 28.35,
    )
    if language == "gu":
        font_normal = s["gujarati_font"]
        font_bold = "LohitGujarati-Bold"
    else:
        font_normal = "Times-Roman"
        font_bold = "Times-Bold"

    story = []
    for b in blocks:
        if not b["text"]:
            story.append(Spacer(1, 6))
            continue
        safe = b["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        style = ParagraphStyle(
            "p",
            fontName=font_bold if b["bold"] else font_normal,
            fontSize=s["heading_size"] if b["bold"] else s["body_size"],
            leading=s["line_spacing"] + (2 if b["bold"] else 0),
            alignment=_pdf_align(b["align"]),
            spaceAfter=6,
        )
        story.append(Paragraph(safe, style))
    doc.build(story)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_docx(blocks: list, language: str = "en") -> str:
    doc = Document()
    s = DOC_SETTINGS
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
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if b["align"] == "center" else WD_ALIGN_PARAGRAPH.LEFT
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
