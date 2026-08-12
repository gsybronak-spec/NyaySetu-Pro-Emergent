"""Deterministic DOCX analysis for the Admin Word Template Import feature.

Parses an uploaded .docx with python-docx and extracts page geometry, margins,
fonts, paragraph structure, tables, page breaks, ``{{placeholder}}`` markers and
blank regions, then proposes a NyaySetu Pro template definition (fields, draft
content, settings).

The uploaded Word document is the source of truth: its formatting and wording
are preserved as-is. Detection is explicit and rule-based — no AI, no guessing.
Ambiguous blanks are surfaced as "Unmapped / Review Required" so the admin
decides, never the parser.
"""

import base64
import io
import re
from collections import Counter

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

EMU_PER_CM = 360000.0

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}")
_BLANK_RE = re.compile(r"(?:\[[_\-\. ]{2,}\]|_{3,}|\.{5,})")

# Radio/checkbox glyphs LibreOffice uses in spec forms ("0 ફરીયાદી 0 અરજદાર 0 વાદી").
_RADIO_MARKER_RE = re.compile(r"(?<![\w\u0A80-\u0AFF])(?:0|○|❍|☐|☑)\s+(?=[\u0A80-\u0AFFA-Za-z])")

_DROPDOWN_MARKERS = ("(ડ્રોપ બોક્ષ)", "(ડ્રોપડાઉન)", "(dropdown)", "(drop box)", "(ડ્રોપ બોક્સ)", "dropdown")
_DATE_MARKERS = ("__/__/20", "_/__/20", "dd/mm/yyyy", "dd-mm-yyyy", "તારીખ")

# Placeholder keys that map to the project's catalog-driven selects.
_CATALOG_SELECT_KEYS = {
    "court", "courts", "district", "taluka", "police_station", "case_type",
    "law", "section", "advocate_name", "case_status", "status",
}

_FIELD_TYPES = ("text", "textarea", "number", "mobile", "email", "date", "select", "radio", "checkbox")

_MAX_DOCX_BYTES = 3 * 1024 * 1024  # 3 MB


class DocxImportError(ValueError):
    """Raised for any file that cannot be parsed or is not a Word document."""


# ---------------------------------------------------------------------------
# Low-level extraction helpers
# ---------------------------------------------------------------------------

def _emu_to_cm(value) -> float:
    if value is None:
        return 0.0
    return round(float(value) / EMU_PER_CM, 2)


def _norm_width_height(w_cm: float, h_cm: float):
    """Return (portrait_w, portrait_h) so orientation never confuses detection."""
    return (w_cm, h_cm) if w_cm <= h_cm else (h_cm, w_cm)


def detect_page_size(section) -> str:
    """Detect A4 / Legal / Letter / other from the section page dimensions."""
    if section is None:
        return "A4"
    w, h = _norm_width_height(_emu_to_cm(section.page_width), _emu_to_cm(section.page_height))
    # A4 = 21.0 x 29.7 cm, Legal = 21.59 x 35.56 cm, Letter = 21.59 x 27.94 cm
    if abs(w - 21.0) <= 0.6 and abs(h - 29.7) <= 0.6:
        return "A4"
    if abs(w - 21.59) <= 0.6 and abs(h - 35.56) <= 0.6:
        return "Legal"
    if abs(w - 21.59) <= 0.6 and abs(h - 27.94) <= 0.6:
        return "Letter"
    return "Other"


def _alignment_name(alignment) -> str:
    return {
        WD_ALIGN_PARAGRAPH.LEFT: "left",
        WD_ALIGN_PARAGRAPH.CENTER: "center",
        WD_ALIGN_PARAGRAPH.RIGHT: "right",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    }.get(alignment, "left")


def _run_has_page_break(run) -> bool:
    """True if a run contains an explicit page break or a rendered page break."""
    r_el = run._element
    if r_el.findall(qn("w:br")):
        for br in r_el.findall(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                return True
    if r_el.find(qn("w:lastRenderedPageBreak")) is not None:
        return True
    return False


def _para_has_page_break(p: Paragraph) -> bool:
    for run in p.runs:
        if _run_has_page_break(run):
            return True
    return False


def _iter_body(doc):
    """Yield ('para'|'table', object) for body children in document order."""
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("para", Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("table", Table(child, doc))


def _table_text_lines(table: Table) -> list:
    """Flatten a table into lines (one per row), cells joined with two spaces."""
    lines = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
        if cells:
            lines.append("   ".join(cells))
    return lines


def _run_fonts(p: Paragraph):
    """Collect (latin_font, complex_font, size_pt) from the paragraph's runs."""
    latin = []
    complex_ = []
    sizes = []
    for run in p.runs:
        rPr = run._element.find(qn("w:rPr"))
        if rPr is not None:
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is not None:
                ascii_f = rFonts.get(qn("w:ascii")) or rFonts.get(qn("w:hAnsi"))
                cs_f = rFonts.get(qn("w:cs"))
                if ascii_f:
                    latin.append(ascii_f)
                if cs_f:
                    complex_.append(cs_f)
        sz = run.font.size
        if sz is not None:
            sizes.append(round(float(sz.pt), 1))
    return latin, complex_, sizes


def _collect_fonts(items) -> dict:
    """Determine document fonts from all paragraphs (spec + draft)."""
    latin_all, complex_all, sizes_all = [], [], []
    for kind, obj in items:
        if kind != "para":
            continue
        latin, complex_, sizes = _run_fonts(obj)
        latin_all.extend(latin)
        complex_all.extend(complex_)
        sizes_all.extend(sizes)

    def most_common(lst):
        if not lst:
            return None
        return Counter(lst).most_common(1)[0][0]

    latin_font = most_common(latin_all) or "Times New Roman"
    complex_font = most_common(complex_all) or ""
    gujarati_font = "Lohit Gujarati" if "Lohit" in (complex_font or "") or "Lohit" in (latin_font or "") else "Lohit Gujarati"
    body_size = most_common(sizes_all) or 13.0
    return {
        "latin_font": latin_font,
        "complex_font": complex_font or latin_font,
        "gujarati_font": gujarati_font,
        "body_size": body_size,
    }


def _slugify_latin(text: str) -> str:
    """Slugify the Latin part of a label; '' when there is no Latin text."""
    latin = "".join(ch for ch in text if ch.isascii() and (ch.isalnum() or ch in "_ "))
    latin = re.sub(r"\s+", "_", latin.strip().lower())
    return re.sub(r"[^a-z0-9_]", "", latin)


def _guess_field_type(key: str, label: str, hints: dict) -> str:
    """Deterministic type guess from the key and label. Defaults to text."""
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
    """Split a radio-marker line into options. Returns [] if not a radio line."""
    parts = _RADIO_MARKER_RE.split(line)
    if len(parts) < 3:  # at least two markers -> three segments
        return []
    options = []
    seen = set()
    for part in parts:
        text = part.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        options.append({"value": text, "label_en": text, "label_gu": text})
    return options


def _extract_placeholders(text: str) -> list:
    """Return unique placeholders in order of first appearance."""
    found, seen = [], set()
    for m in _PLACEHOLDER_RE.finditer(text or ""):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            found.append(m.group(1))
    return found


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_docx(data: bytes, file_name: str) -> dict:
    """Analyze an uploaded Word document and propose a template definition.

    Raises DocxImportError for anything that cannot be parsed. The returned
    dict is JSON-serializable and drives the admin "Extracted Fields" review.
    """
    if not file_name or not file_name.lower().endswith(".docx"):
        raise DocxImportError("Unsupported file type. Only .docx Word documents are accepted for import.")
    if not data:
        raise DocxImportError("The uploaded file is empty.")
    if len(data) > _MAX_DOCX_BYTES:
        raise DocxImportError("The uploaded file is too large (max 3 MB).")
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:  # corrupt / not a real docx
        raise DocxImportError("Word file could not be parsed. The file is corrupt or not a valid .docx document.") from exc

    section = doc.sections[0] if doc.sections else None

    # --- Walk the body in document order, splitting spec (page 1) / draft (page 2) ---
    items = []
    draft_start_idx = None
    for kind, obj in _iter_body(doc):
        items.append({"kind": kind, "obj": obj})
        if kind == "para" and draft_start_idx is None and _para_has_page_break(obj):
            draft_start_idx = len(items) - 1

    page_break_detected = draft_start_idx is not None
    spec_items = items[:draft_start_idx] if page_break_detected else []
    draft_items = items[draft_start_idx:] if page_break_detected else items
    if not draft_items:
        draft_items = items  # never leave an empty draft — whole doc is the draft

    # --- Draft lines: preserve source text + alignment per line ---
    draft_lines = []      # text of each line (paragraphs + table rows)
    line_align = []       # matching alignment per non-empty line index
    line_bold = []
    line_underline = []
    for item in draft_items:
        if item["kind"] == "para":
            p = item["obj"]
            text = p.text
            draft_lines.append(text)
            if text.strip():
                line_align.append(_alignment_name(p.alignment))
                line_bold.append(any(r.font.bold for r in p.runs))
                line_underline.append(any(r.underline for r in p.runs))
        else:
            for t in _table_text_lines(item["obj"]):
                draft_lines.append(t)
                line_align.append("left")
                line_bold.append(False)
                line_underline.append(False)

    draft_text = "\n".join(draft_lines)
    placeholders = _extract_placeholders(draft_text)

    # --- Spec page: extract field definitions (conservative, marker-driven) ---
    spec_lines = []
    for item in spec_items:
        if item["kind"] == "para":
            t = item["obj"].text
            if t.strip():
                spec_lines.append(t.strip())
        else:
            spec_lines.extend(_table_text_lines(item["obj"]))

    fields = []
    unmapped = []
    spec_fields = []   # spec-page detected fields (key, label, type hints, line no.)
    seen_spec_labels = set()

    for idx, line in enumerate(spec_lines):
        is_radio = len(_split_radio_options(line)) >= 2
        has_dropdown = any(m in line.lower() for m in _DROPDOWN_MARKERS)
        has_date = any(m in line.lower() for m in _DATE_MARKERS) or "__" in line and "/" in line
        has_blank = bool(_BLANK_RE.search(line))

        # 1) radio groups
        if is_radio:
            options = _split_radio_options(line)
            label = _RADIO_MARKER_RE.sub(" ", line).strip()
            key = _slugify_latin(label) or f"spec_radio_{idx + 1}"
            spec_fields.append({
                "key": key, "label_gu": label, "label_en": label,
                "type": "radio", "required": True, "options": options,
                "source": "spec_page", "source_location": f"Spec Page, line {idx + 1}",
                "referenced_in_draft": False,
            })
            continue

        # 2) dropdown markers -> select
        if has_dropdown:
            label = line
            key = _slugify_latin(label) or f"spec_select_{idx + 1}"
            spec_fields.append({
                "key": key, "label_gu": label, "label_en": label,
                "type": "select", "required": True, "options": [],
                "source": "spec_page", "source_location": f"Spec Page, line {idx + 1}",
                "referenced_in_draft": False,
            })
            continue

        # 3) date-marker lines -> date
        if has_date:
            # Remove any [...] blank token and any standalone underscore runs.
            label = re.sub(r"\[[^\]]*\]", "", line)
            label = re.sub(r"_+", " ", label)
            label = re.sub(r"\s+", " ", label).strip().rstrip(":：")
            if not label:
                label = line
            key = _slugify_latin(label) or f"spec_date_{idx + 1}"
            spec_fields.append({
                "key": key, "label_gu": label, "label_en": label,
                "type": "date", "required": True, "options": [],
                "source": "spec_page", "source_location": f"Spec Page, line {idx + 1}",
                "referenced_in_draft": False,
            })
            continue

        # 4) label + blank marker -> text-ish field
        if has_blank:
            label = _BLANK_RE.sub("", line).strip().rstrip(":：")
            if not label:
                unmapped.append({"text": line, "source_location": f"Spec Page, line {idx + 1}"})
                continue
            if label in seen_spec_labels:
                continue
            seen_spec_labels.add(label)
            key = _slugify_latin(label) or f"spec_field_{idx + 1}"
            spec_fields.append({
                "key": key, "label_gu": label, "label_en": label,
                "type": _guess_field_type(key, label, {"is_radio": False, "has_date": False, "has_dropdown": False}),
                "required": True, "options": [],
                "source": "spec_page", "source_location": f"Spec Page, line {idx + 1}",
                "referenced_in_draft": False,
            })
            continue

        # 5) anything else on the spec page -> review required (never guessed)
        if len(line) <= 160 and not any(m in line for m in ("છે", "રહેશે", "થશે")):
            unmapped.append({"text": line, "source_location": f"Spec Page, line {idx + 1}"})

    # --- Draft placeholders -> definite fields ---
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

    # Merge: placeholder fields first, spec fields added when their key is not taken.
    keys_seen = {f["key"] for f in placeholder_fields}
    for f in spec_fields:
        if f["key"] in keys_seen:
            # Link the spec label to the existing placeholder field (better label).
            for pf in fields or placeholder_fields:
                if pf["key"] == f["key"]:
                    pf["label_gu"] = f["label_gu"]
                    pf["label_en"] = f["label_en"]
                    if f["type"] in ("radio", "select", "date") and f["options"]:
                        pf["type"] = f["type"]
                        pf["options"] = f["options"]
                    break
            continue
        keys_seen.add(f["key"])
        fields.append(f)

    fields = placeholder_fields + fields

    # --- Draft blanks not covered by a placeholder -> review required ---
    blank_unmapped = []
    for i, line in enumerate(draft_lines):
        if not _BLANK_RE.search(line):
            continue
        line_placeholders = set(_extract_placeholders(line))
        if line_placeholders:
            continue  # the line is driven by a real placeholder
        blank_unmapped.append({
            "text": line.strip()[:200] or "(blank line)",
            "source_location": f"Draft, line {i + 1}",
        })
    unmapped = unmapped + blank_unmapped

    # --- Settings from the source document ---
    margins = {
        "top_cm": _emu_to_cm(section.top_margin if section else None),
        "bottom_cm": _emu_to_cm(section.bottom_margin if section else None),
        "left_cm": _emu_to_cm(section.left_margin if section else None),
        "right_cm": _emu_to_cm(section.right_margin if section else None),
    }
    fonts = _collect_fonts(draft_items)

    # Line spacing: from the draft paragraphs (point multiple x body size).
    spacing_pts = None
    for item in draft_items:
        if item["kind"] != "para":
            continue
        ls = item["obj"].paragraph_format.line_spacing
        if isinstance(ls, float) and ls:
            spacing_pts = round(ls * fonts["body_size"], 1)
            break
        if isinstance(ls, (int,)) and ls:
            spacing_pts = round(ls * fonts["body_size"], 1)
            break
    if spacing_pts is None:
        spacing_pts = round(fonts["body_size"] * 1.5, 1)

    # Global alignment reflects the BODY pattern only — centered titles and
    # right-aligned signatures are handled by per-line block_align rules, so
    # they must never flip the document's default alignment.
    body_aligns = [a for a in line_align if a in ("left", "justify")]
    dominant_align = Counter(body_aligns).most_common(1)
    alignment = dominant_align[0][0] if dominant_align else "left"

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

    # Suggested name: first non-empty draft line (usually the title).
    suggested_name_gu = next((l.strip() for l in draft_lines if l.strip()), "")
    suggested_name_en = suggested_name_gu or file_name

    settings = {
        "page_size": detect_page_size(section),
        "margin_top_cm": margins["top_cm"] or 2.0,
        "margin_bottom_cm": margins["bottom_cm"] or 2.0,
        "margin_left_cm": margins["left_cm"] or 2.5,
        "margin_right_cm": margins["right_cm"] or 2.5,
        "gujarati_font": "LohitGujarati",
        "english_font": "Times-Roman",
        "gujarati_font_docx": fonts["gujarati_font"],
        "english_font_docx": fonts["latin_font"] or "Times New Roman",
        "body_size": fonts["body_size"],
        "heading_size": min(fonts["body_size"] + 1, 16.0),
        "line_spacing": spacing_pts,
        "paragraph_spacing": 6,
        "alignment": alignment,
        "block_align": block_align,
    }

    return {
        "file_name": file_name,
        "page_size": settings["page_size"],
        "margins_cm": margins,
        "fonts": fonts,
        "line_spacing_pts": spacing_pts,
        "alignment": alignment,
        "page_break_detected": page_break_detected,
        "spec_line_count": len(spec_lines),
        "draft_line_count": len(draft_lines),
        "fields": fields,
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
    """Decode + size-guard a base64 file payload. Raises DocxImportError."""
    if not content_base64:
        raise DocxImportError("The uploaded file is empty.")
    try:
        data = base64.b64decode(content_base64, validate=False)
    except Exception as exc:
        raise DocxImportError("The uploaded file could not be decoded.") from exc
    if not data:
        raise DocxImportError("The uploaded file is empty.")
    return data
