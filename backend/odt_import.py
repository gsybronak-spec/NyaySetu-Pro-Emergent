"""ODT (OpenDocument Text) analysis for the Admin Word/LibreOffice Template Import feature.

Mirrors ``docx_import.analyze_docx`` so the same admin review flow works for
LibreOffice Writer documents: parses an uploaded .odt (a ZIP of XML) and
extracts page geometry, margins, fonts, paragraph structure, alignment, bold,
``{{placeholder}}`` markers and blank regions, then proposes a NyaySetu Pro
template definition (fields, draft content, settings).

ODT is a first-class citizen — LibreOffice Writer compatibility is a product
requirement, not a DOCX rename. Parsing uses only the Python stdlib
(zipfile + xml.etree), so no extra dependency is needed.

The uploaded document is the source of truth: its wording is preserved as-is.
Detection is explicit and rule-based — no AI, no guessing. Ambiguous blanks are
surfaced as "Unmapped / Review Required" so the admin decides.
"""

import base64
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

ODT_MIME = "application/vnd.oasis.opendocument.text"
_MAX_ODT_BYTES = 3 * 1024 * 1024  # 3 MB, same cap as DOCX

_NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
}

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")
_BLANK_RE = re.compile(r"(?:\[[_\-\. ]{2,}\]|_{3,}|\.{5,})")
_RADIO_MARKER_RE = re.compile(r"(?<![\w\u0A80-\u0AFF])(?:0|○|❍|☐|☑)\s+(?=[\u0A80-\u0AFFA-Za-z])")

_DROPDOWN_MARKERS = ("(ડ્રોપ બોક્ષ)", "(ડ્રોપડાઉન)", "(dropdown)", "(drop box)", "(ડ્રોપ બોક્સ)", "dropdown")
_DATE_MARKERS = ("__/__/20", "_/__/20", "dd/mm/yyyy", "dd-mm-yyyy", "તારીખ")

# Same catalog-driven select keys as docx_import.
_CATALOG_SELECT_KEYS = {
    "court", "courts", "district", "taluka", "police_station", "case_type",
    "law", "section", "advocate_name", "case_status", "status",
}

_FIELD_TYPES = ("text", "textarea", "number", "mobile", "email", "date", "select", "radio", "checkbox")


class OdtImportError(ValueError):
    """Raised for any file that cannot be parsed or is not an ODT document."""


def _q(tag: str) -> str:
    return f"{{{_NS['office']}}}{tag}"


def _sq(tag: str) -> str:
    return f"{{{_NS['style']}}}{tag}"


def _tq(tag: str) -> str:
    return f"{{{_NS['text']}}}{tag}"


def _fq(tag: str) -> str:
    return f"{{{_NS['fo']}}}{tag}"


def _cm(value: str) -> float:
    """Parse an ODT length like '2.5cm', '850pt', '3in' to cm. Default 0.0."""
    if not value:
        return 0.0
    m = re.match(r"([\d.]+)\s*(cm|mm|in|pt|pc|px)?", value.strip())
    if not m:
        return 0.0
    num = float(m.group(1))
    unit = (m.group(2) or "cm").lower()
    if unit == "mm":
        return round(num / 10.0, 2)
    if unit == "in":
        return round(num * 2.54, 2)
    if unit == "pt":
        return round(num / 28.35, 2)
    if unit == "pc":
        return round(num / 1.333, 2)
    if unit == "px":
        return round(num / 37.8, 2)
    return round(num, 2)


def _norm_width_height(w_cm: float, h_cm: float):
    return (w_cm, h_cm) if w_cm <= h_cm else (h_cm, w_cm)


def detect_page_size(w_cm: float, h_cm: float) -> str:
    w, h = _norm_width_height(w_cm, h_cm)
    if w <= 0 or h <= 0:
        return "A4"
    if abs(w - 21.0) <= 0.6 and abs(h - 29.7) <= 0.6:
        return "A4"
    if abs(w - 21.59) <= 0.6 and abs(h - 35.56) <= 0.6:
        return "Legal"
    if abs(w - 21.59) <= 0.6 and abs(h - 27.94) <= 0.6:
        return "Letter"
    return "Other"


def _slugify_latin(text: str) -> str:
    latin = "".join(ch for ch in text if ch.isascii() and (ch.isalnum() or ch in "_ "))
    latin = re.sub(r"\s+", "_", latin.strip().lower())
    return re.sub(r"[^a-z0-9_]", "", latin)


def _guess_field_type(key: str, label: str, hints: dict) -> str:
    if hints.get("is_radio"):
        return "radio"
    if hints.get("has_date"):
        return "date"
    if hints.get("has_dropdown") or key in _CATALOG_SELECT_KEYS:
        return "select"
    k = key.lower()
    label_l = label.lower()
    if "mobile" in k or "phone" in k or "mob" in k or "મોબાઈલ" in label_l or "મોબાઇલ" in label_l:
        return "mobile"
    if "email" in k or "mail" in k or "ઈમેલ" in label_l or "ઇમેલ" in label_l:
        return "email"
    if any(w in k for w in ("amount", "total", "qty", "quantity", "count", "age", "year")):
        return "number"
    return "text"


def _humanize_key(key: str) -> str:
    return " ".join(w.capitalize() for w in key.split("_"))


def _split_radio_options(line: str) -> list:
    parts = _RADIO_MARKER_RE.split(line)
    if len(parts) < 3:
        return []
    options, seen = [], set()
    for part in parts:
        text = part.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        options.append({"value": text, "label_en": text, "label_gu": text})
    return options


def _extract_placeholders(text: str) -> list:
    found, seen = [], set()
    for m in _PLACEHOLDER_RE.finditer(text or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            found.append(m.group(1))
    return found


# ---------------------------------------------------------------------------
# ODT parsing helpers
# ---------------------------------------------------------------------------

def _parse_zip(data: bytes):
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception as exc:
        raise OdtImportError(
            "ODT file could not be opened. The file is corrupt or not a valid .odt document."
        ) from exc
    return zf


def _read_xml(zf: zipfile.ZipFile, name: str):
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None
    except Exception as exc:
        raise OdtImportError(
            f"ODT file could not be parsed ({name} is malformed). The file is corrupt or not a valid .odt document."
        ) from exc


def _iter_blocks(root) -> list:
    """Yield ('para', text, align, bold, is_page_break) for office:text children."""
    out = []
    if root is None:
        return out
    office_text = root.find(f".//{_q('text')}")
    if office_text is None:
        return out
    for child in office_text:
        tag = child.tag
        if tag in (_tq("p"), _tq("h")):
            align = "left"
            bold = tag == _tq("h")  # ODT headings are bold by definition
            st_name = child.get(_sq("name"))
            if st_name:
                align, bold = _resolve_para_style(root, st_name, bold)
            text = _para_text(child)
            out.append(("para", text, align, bold, False))
        elif tag == _tq("soft-page-break"):
            out.append(("para", "", "left", False, True))
    return out


def _resolve_para_style(root, style_name: str, default_bold: bool):
    """Look up a paragraph style in automatic-styles / styles; return (align, bold)."""
    align, bold = "left", default_bold
    for styles_parent in [root, root]:
        found = False
        for container in ("office:automatic-styles", "office:styles"):
            elem = root.find(f".//{_sq(container)}")
            # ET path with namespaced container
            cont = None
            for c in root.iter():
                if c.tag == f"{{{_NS['office']}}}{container.split(':')[1]}":
                    cont = c
                    break
            if cont is None:
                continue
            for st in cont:
                if st.tag == _sq("style") and st.get(_sq("name")) == style_name and st.get(_sq("family")) == "paragraph":
                    found = True
                    pprops = st.find(_sq("paragraph-properties"))
                    if pprops is not None:
                        a = pprops.get(_fq("text-align"))
                        if a in ("left", "center", "right", "justify", "start", "end"):
                            align = "justify" if a == "justify" else ("left" if a in ("start",) else a)
                    tprops = st.find(_sq("text-properties"))
                    if tprops is not None:
                        w = tprops.get(_fq("font-weight"))
                        if w == "bold":
                            bold = True
                        elif w == "normal":
                            bold = False
                    break
            if found:
                break
        if found:
            break
    return align, bold


def _para_text(p) -> str:
    """Extract plain text from a text:p element (concatenate spans, expand tabs)."""
    parts = []
    for node in p.iter():
        if node.tag == _tq("s"):
            n = int(node.get(_sq("c")) or "1") or 1
            parts.append(" " * n)
        elif node.tag == _tq("tab"):
            parts.append("\t")
        elif node.tag == _tq("line-break"):
            parts.append("\n")
        elif node.tag == _tq("span") or node.tag == _tq("a") or node.tag is None or isinstance(node.tag, str) and "}" not in node.tag:
            pass
    # Iterating includes text nodes as 'node.tag is None' — collect text content directly.
    text = "".join(p.itertext())
    return text


def _collect_fonts(root) -> dict:
    """Best-effort font extraction from style:text-properties font-name attributes."""
    names = []
    sizes = []
    for elem in root.iter():
        if elem.tag == _sq("text-properties"):
            fn = elem.get(_sq("font-name"))
            if fn:
                names.append(fn)
            sz = elem.get(_fq("font-size"))
            if sz:
                m = re.match(r"([\d.]+)", sz)
                if m:
                    sizes.append(float(m.group(1)))
    latin = next((n for n in names if not re.search(r"[\u0A80-\u0AFF]", n)), "Times New Roman")
    gujarati = next((n for n in names if re.search(r"[\u0A80-\u0AFF]", n) or "Lohit" in n or "Gujarati" in n), "Lohit Gujarati")
    body_size = Counter(sizes).most_common(1)[0][0] if sizes else 13.0
    return {"latin_font": latin, "complex_font": latin, "gujarati_font": gujarati, "body_size": body_size}


def _page_layout(root) -> dict:
    """Extract page size + margins from styles.xml page-layout-properties."""
    info = {"page_width_cm": 0.0, "page_height_cm": 0.0,
            "margin_top_cm": 0.0, "margin_bottom_cm": 0.0,
            "margin_left_cm": 0.0, "margin_right_cm": 0.0}
    for elem in root.iter():
        if elem.tag == _sq("page-layout-properties"):
            w = elem.get(_fq("page-width"))
            h = elem.get(_fq("page-height"))
            if w:
                info["page_width_cm"] = _cm(w)
            if h:
                info["page_height_cm"] = _cm(h)
            info["margin_top_cm"] = _cm(elem.get(_fq("margin-top")))
            info["margin_bottom_cm"] = _cm(elem.get(_fq("margin-bottom")))
            info["margin_left_cm"] = _cm(elem.get(_fq("margin-left")))
            info["margin_right_cm"] = _cm(elem.get(_fq("margin-right")))
            break
    return info


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_odt(data: bytes, file_name: str) -> dict:
    """Analyze an uploaded LibreOffice ODT document and propose a template definition.

    Raises OdtImportError for anything that cannot be parsed. The returned
    dict mirrors ``analyze_docx`` so the admin "Extracted Fields" review flow is
    identical for Word and LibreOffice documents.
    """
    if not file_name or not file_name.lower().endswith(".odt"):
        raise OdtImportError("Unsupported file type. Only .odt LibreOffice documents are accepted for import.")
    if not data:
        raise OdtImportError("The uploaded file is empty.")
    if len(data) > _MAX_ODT_BYTES:
        raise OdtImportError("The uploaded file is too large (max 3 MB).")

    zf = _parse_zip(data)
    # Validate MIME (first file, uncompressed) — cheap real-file check.
    try:
        mimetype = zf.read("mimetype").decode("utf-8", "replace").strip()
        if mimetype != ODT_MIME:
            raise OdtImportError(
                "The file is not a valid ODT document (wrong mimetype). Please upload a real .odt file from LibreOffice Writer."
            )
    except KeyError:
        raise OdtImportError("The file is not a valid ODT document (mimetype missing).")

    content_root = _read_xml(zf, "content.xml")
    styles_root = _read_xml(zf, "styles.xml")
    if content_root is None:
        raise OdtImportError("The ODT document has no content.xml and cannot be parsed.")

    items = _iter_blocks(content_root)
    if not items:
        raise OdtImportError("The ODT document is empty — no paragraphs found.")

    # Body = all paragraphs (ODT documents imported for templates have no
    # spec/draft page split like the Word pipeline; the whole doc is the draft).
    draft_lines = []
    line_align = []
    line_bold = []
    for kind, text, align, bold, is_break in items:
        draft_lines.append(text)
        if text.strip():
            line_align.append(align)
            line_bold.append(bold)

    draft_text = "\n".join(draft_lines)
    placeholders = _extract_placeholders(draft_text)

    # Fields from draft placeholders.
    placeholder_fields = []
    for ph in placeholders:
        placeholder_fields.append({
            "key": ph,
            "label_gu": _humanize_key(ph),
            "label_en": _humanize_key(ph),
            "type": _guess_field_type(ph, ph, {"is_radio": False, "has_date": False, "has_dropdown": False}),
            "required": True,
            "options": [],
            "source": "draft_placeholder",
            "source_location": "Draft document",
            "referenced_in_draft": True,
        })

    # Blank lines not covered by a placeholder -> review required.
    unmapped = []
    for i, line in enumerate(draft_lines):
        if not _BLANK_RE.search(line):
            continue
        if set(_extract_placeholders(line)):
            continue
        unmapped.append({"text": line.strip()[:200] or "(blank line)", "source_location": f"Draft, line {i + 1}"})

    fonts = _collect_fonts(content_root)
    layout = _page_layout(styles_root)
    page_size = detect_page_size(layout["page_width_cm"], layout["page_height_cm"])

    body_aligns = [a for a in line_align if a in ("left", "justify")]
    dominant = Counter(body_aligns).most_common(1)
    alignment = dominant[0][0] if dominant else "left"

    # Per-line alignment rules (position-based, opt-in, source-literal).
    block_align = []
    nonempty = 0
    align_idx = 0
    for line in draft_lines:
        if not line.strip():
            continue
        nonempty += 1
        a = line_align[align_idx] if align_idx < len(line_align) else "left"
        align_idx += 1
        if a != "left":
            block_align.append({"position": nonempty, "align": a, "bold": False})

    suggested_name_gu = next((l.strip() for l in draft_lines if l.strip()), "")
    suggested_name_en = suggested_name_gu or file_name

    settings = {
        "page_size": page_size,
        "margin_top_cm": layout["margin_top_cm"] or 2.0,
        "margin_bottom_cm": layout["margin_bottom_cm"] or 2.0,
        "margin_left_cm": layout["margin_left_cm"] or 2.5,
        "margin_right_cm": layout["margin_right_cm"] or 2.5,
        "gujarati_font": "LohitGujarati",
        "english_font": "Times-Roman",
        "gujarati_font_docx": fonts["gujarati_font"],
        "english_font_docx": fonts["latin_font"] or "Times New Roman",
        "body_size": fonts["body_size"],
        "heading_size": min(fonts["body_size"] + 1, 16.0),
        "line_spacing": round(fonts["body_size"] * 1.5, 1),
        "paragraph_spacing": 6,
        "alignment": alignment,
        "block_align": block_align,
    }

    return {
        "file_name": file_name,
        "page_size": page_size,
        "margins_cm": layout,
        "fonts": fonts,
        "line_spacing_pts": settings["line_spacing"],
        "alignment": alignment,
        "page_break_detected": False,
        "spec_line_count": 0,
        "draft_line_count": len(draft_lines),
        "fields": placeholder_fields,
        "unmapped": unmapped,
        "placeholders": placeholders,
        "draft_content_gu": draft_text,
        "content_en": "",
        "suggested_name_gu": suggested_name_gu,
        "suggested_name_en": suggested_name_en,
        "suggested_category": "General",
        "settings": settings,
    }


def decode_upload(file_name: str, content_base64: str) -> bytes:
    """Decode + size-guard a base64 file payload. Raises OdtImportError."""
    if not content_base64:
        raise OdtImportError("The uploaded file is empty.")
    try:
        data = base64.b64decode(content_base64, validate=False)
    except Exception as exc:
        raise OdtImportError("The uploaded file could not be decoded.") from exc
    if not data:
        raise OdtImportError("The uploaded file is empty.")
    return data
