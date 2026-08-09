"""Document generation for NyaySetu Pro - PDF via ReportLab, DOCX via python-docx."""

import io
import base64
import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from docx import Document
from docx.shared import Cm, Pt

FONT_DIR = Path(__file__).parent / "fonts"

_fonts_registered = False


def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    reg = FONT_DIR / "NotoSansGujarati-Regular.ttf"
    bold = FONT_DIR / "NotoSansGujarati-Bold.ttf"
    if reg.exists():
        pdfmetrics.registerFont(TTFont("NotoGujarati", str(reg)))
    if bold.exists():
        pdfmetrics.registerFont(TTFont("NotoGujarati-Bold", str(bold)))
    _fonts_registered = True


def generate_pdf(content: str, language: str = "en") -> str:
    """Return base64-encoded PDF."""
    register_fonts()
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
    )

    font_name = "NotoGujarati" if language == "gu" else "Times-Roman"
    font_bold = "NotoGujarati-Bold" if language == "gu" else "Times-Bold"

    body_style = ParagraphStyle(
        "body",
        fontName=font_name,
        fontSize=12,
        leading=18,
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "heading",
        fontName=font_bold,
        fontSize=13,
        leading=20,
        alignment=1,
        spaceAfter=10,
    )

    story = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
            continue
        # Escape XML special chars
        safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Center-align uppercase titles and application headings
        is_heading = (
            safe.isupper() and len(safe) < 100
        ) or "COURT OF" in safe or "માનનીય ન્યાયાલય" in safe or "અરજી" in safe and len(safe) < 60
        style = heading_style if is_heading else body_style
        story.append(Paragraph(safe, style))

    doc.build(story)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_docx(content: str, language: str = "en") -> str:
    """Return base64-encoded DOCX."""
    doc = Document()

    # Configure page margins
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles["Normal"]
    font = style.font
    if language == "gu":
        font.name = "Nirmala UI"
    else:
        font.name = "Times New Roman"
    font.size = Pt(12)

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue
        p = doc.add_paragraph(stripped)
        # Center for headings
        if (stripped.isupper() and len(stripped) < 100) or "COURT OF" in stripped or "માનનીય ન્યાયાલય" in stripped:
            p.alignment = 1
            for run in p.runs:
                run.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def render_template(content_template: str, values: dict) -> str:
    """Replace {{field}} with values."""
    result = content_template
    for k, v in values.items():
        placeholder = "{{" + k + "}}"
        result = result.replace(placeholder, str(v) if v is not None else "")
    # Remove any remaining unfilled placeholders
    import re
    result = re.sub(r"\{\{[^}]+\}\}", "____", result)
    return result
