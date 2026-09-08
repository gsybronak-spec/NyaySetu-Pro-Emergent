import base64
import io
import os
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import pypdfium2 as pdfium
from docx import Document

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from authoritative_catalog_42 import TEMPLATES_42
from doc_generator import (
    build_blocks,
    render_template,
    generate_pdf,
    generate_docx,
    generate_odt,
    rasterize_pdf_pages,
    get_doc_settings,
)

SAMPLE_VALUES = {
    "court_name": "In the Court of Hon'ble Chief Judicial Magistrate, Ahmedabad",
    "case_number": "Criminal Case No. 1234/2026",
    "parties": "State of Gujarat vs. Ronak Sharma",
    "applicant_name": "Ronak Sharma",
    "reason": "advocate is engaged in another Hon'ble Court in urgent trial proceedings",
    "advocate_name": "K. L. Patel",
    "place": "Ahmedabad",
    "date": "08/09/2026",
    "accused_name": "Ronak Sharma",
    "complainant_name": "State of Gujarat",
    "stage": "Evidence",
    "document_title": "Original Sale Deed dated 12/01/2020",
    "relevance_reason": "is of immense importance to establish applicant defense",
    "documents_list": "1. Original Sale Deed\n2. Electricity Bill Receipt",
}

def extract_pdf_text_pypdfium(pdf_bytes: bytes) -> str:
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        full_text = []
        for i in range(len(pdf)):
            page = pdf[i]
            try:
                textpage = page.get_textpage()
                try:
                    full_text.append(textpage.get_text_range())
                finally:
                    textpage.close()
            finally:
                page.close()
        return "\n".join(full_text)
    finally:
        pdf.close()

def verify_mudat_arji_pdf(pdf_bytes: bytes) -> None:
    assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:5] == b"%PDF-", "Not a valid PDF"
    text = extract_pdf_text_pypdfium(pdf_bytes)
    # Forensic Check: Overlap bug caused length to balloon to 11,760 chars.
    # A single-page Mudat Arji with natural spacing has between 400 and 1,500 chars.
    assert len(text) < 2000, f"Forensic Alert: Mudat Arji text length {len(text)} exceeds safe threshold (overlap detected)!"
    assert len(text) > 300, f"Forensic Alert: Mudat Arji text length {len(text)} suspiciously empty!"

def verify_exhibit_doc_pdf(pdf_bytes: bytes) -> None:
    assert len(pdf_bytes) > 1000, f"PDF too small: {len(pdf_bytes)} bytes"
    assert pdf_bytes[:5] == b"%PDF-", "Not a valid PDF"
    text = extract_pdf_text_pypdfium(pdf_bytes)
    # Forensic Check: Inversion bug caused prayer/concluding fragments to precede opening paragraphs.
    idx_most_respectfully = text.find("Most respectfully showeth")
    if idx_most_respectfully == -1:
        idx_most_respectfully = text.find("submit before this Hon'ble Court")
    idx_prayer = text.find("PRAYER")
    if idx_prayer == -1:
        idx_prayer = text.find("prayed that")
    if idx_most_respectfully != -1 and idx_prayer != -1:
        assert idx_most_respectfully < idx_prayer, (
            f"Forensic Alert: Displaced/Inverted text detected! Opening ({idx_most_respectfully}) "
            f"appeared after prayer ({idx_prayer})"
        )

def verify_docx(docx_bytes: bytes) -> None:
    assert len(docx_bytes) > 1000, f"DOCX too small: {len(docx_bytes)} bytes"
    doc = Document(io.BytesIO(docx_bytes))
    assert len(doc.paragraphs) > 0, "DOCX has 0 paragraphs"
    # Ensure line spacing is not collapsed to fractional 1.15pt
    for p in doc.paragraphs:
        if p.paragraph_format.line_spacing is not None:
            assert p.paragraph_format.line_spacing.pt >= 14.0, (
                f"Forensic Alert: DOCX line spacing collapsed: {p.paragraph_format.line_spacing.pt} pt"
            )

def verify_odt(odt_bytes: bytes) -> None:
    assert len(odt_bytes) > 1000, f"ODT too small: {len(odt_bytes)} bytes"
    with zipfile.ZipFile(io.BytesIO(odt_bytes)) as zf:
        assert "content.xml" in zf.namelist(), "ODT missing content.xml"
        content = zf.read("content.xml").decode("utf-8")
        assert "fo:line-height=\"10%\"" not in content, "Forensic Alert: ODT has 10% collapsed line height!"
        assert "fo:line-height" in content, "ODT missing fo:line-height"

def verify_image(img_bytes: bytes) -> None:
    assert len(img_bytes) > 1000, f"Image too small: {len(img_bytes)} bytes"
    assert img_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Image is not a valid PNG"

def run_single_test(iteration: int, template_id: str, fmt: str) -> dict:
    t0 = time.time()
    tpl = next((t for t in TEMPLATES_42 if t["id"] == template_id), None)
    if not tpl:
        raise ValueError(f"Template {template_id} not found")
    
    lang = tpl.get("language", "gu")
    content = tpl.get("content_gu" if lang == "gu" else "content_en") or tpl.get("content", "")
    rendered = render_template(content, SAMPLE_VALUES)
    blocks = build_blocks(rendered, title_en=tpl.get("name_en", ""), title_gu=tpl.get("name_gu", ""))
    settings = get_doc_settings(tpl.get("settings", {}))
    
    if fmt == "pdf":
        raw_b64 = generate_pdf(blocks, language=lang, settings=settings)
        raw = base64.b64decode(raw_b64)
        if template_id in ("mudat_arji", "mudat_arji_gu"):
            verify_mudat_arji_pdf(raw)
        elif template_id in ("document_swikaravani_arji_en", "document_swikaravani_arji_gu", "document_swikaravani_arji"):
            verify_exhibit_doc_pdf(raw)
        else:
            assert len(raw) > 1000 and raw[:5] == b"%PDF-"
    elif fmt == "docx":
        raw_b64 = generate_docx(blocks, language=lang, settings=settings)
        raw = base64.b64decode(raw_b64)
        verify_docx(raw)
    elif fmt == "odt":
        raw_b64 = generate_odt(blocks, language=lang, settings=settings)
        raw = base64.b64decode(raw_b64)
        verify_odt(raw)
    elif fmt == "png":
        raw_b64 = generate_pdf(blocks, language=lang, settings=settings)
        pdf_bytes = base64.b64decode(raw_b64)
        pages = rasterize_pdf_pages(pdf_bytes, scale=1.5)
        assert len(pages) > 0, "No pages rendered to PNG"
        raw = pages[0]
        verify_image(raw)
    else:
        raise ValueError(f"Unknown format: {fmt}")
        
    duration = time.time() - t0
    return {
        "iteration": iteration,
        "template_id": template_id,
        "lang": lang,
        "format": fmt,
        "bytes_len": len(raw),
        "duration_sec": round(duration, 3),
        "status": "PASS",
    }

def main():
    print("=" * 70)
    print("STARTING 100-GENERATION FORENSIC STRESS TEST (PDF, DOCX, ODT, PNG)")
    print("=" * 70)
    
    # 21 pairs = 42 templates. We select a representative diverse sample:
    # 1. mudat_arji (Gujarati HarfBuzz)
    # 2. mudat_arji_en (English ReportLab)
    # 3. document_swikaravani_arji (Exhibit Gujarati)
    # 4. document_swikaravani_arji_en (Exhibit English)
    # 5. jamin_bond_swikarvani_arji (Bail Gujarati)
    # 6. jamin_bond_swikarvani_arji_en (Bail English)
    # 7. warrant_rad_karvani_arji (Warrant Cancellation Gujarati)
    # 8. warrant_rad_karvani_arji_en (Warrant Cancellation English)
    # 9. vakilatnama_civil (Civil Vakalatnama Gujarati)
    # 10. vakilatnama_civil_en (Civil Vakalatnama English)
    
    key_templates = [
        "mudat_arji_gu",
        "mudat_arji_en",
        "document_swikaravani_arji_gu",
        "document_swikaravani_arji_en",
        "jamin_bond_swikarvani_arji_gu",
        "jamin_bond_swikarvani_arji_en",
        "warrant_rad_karvani_arji_gu",
        "warrant_rad_karvani_arji_en",
        "vakilatnama_civil_gu",
        "vakilatnama_civil_en",
    ]
    formats = ["pdf", "docx", "odt", "png"]
    
    tasks = []
    # Build 100 distinct generation tasks
    # 50 sequential, 50 concurrent
    for i in range(100):
        tid = key_templates[i % len(key_templates)]
        fmt = formats[i % len(formats)]
        tasks.append((i + 1, tid, fmt))
        
    print(f"Total test tasks configured: {len(tasks)}")
    
    # Phase 1: 50 Sequential Generations (rigorous isolation check)
    print("\n--- Phase 1: Running 50 Sequential Generations ---")
    seq_results = []
    t_start_seq = time.time()
    for task in tasks[:50]:
        res = run_single_test(*task)
        seq_results.append(res)
        if task[0] % 10 == 0 or task[0] == 50:
            print(f"  [Seq #{task[0]:02d}] {res['template_id']} ({res['format'].upper()}): {res['bytes_len']} bytes in {res['duration_sec']}s - {res['status']}")
    t_seq_total = time.time() - t_start_seq
    print(f"Phase 1 Completed: 50/50 PASSED in {t_seq_total:.2f}s")
    
    # Phase 2: 50 Concurrent Generations (10 parallel worker threads)
    print("\n--- Phase 2: Running 50 Concurrent Generations (10 workers) ---")
    concurrent_results = []
    t_start_conc = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_task = {executor.submit(run_single_test, *t): t for t in tasks[50:]}
        for future in as_completed(future_to_task):
            task_info = future_to_task[future]
            try:
                res = future.result()
                concurrent_results.append(res)
            except Exception as exc:
                print(f"  FAILED Task {task_info}: {exc}")
                raise exc
    t_conc_total = time.time() - t_start_conc
    print(f"Phase 2 Completed: 50/50 PASSED in {t_conc_total:.2f}s")
    
    print("\n--- Phase 3: Exhaustive Sweep of All 42 Templates Across All 4 Formats (168 runs) ---")
    p3_results = []
    t_start_p3 = time.time()
    p3_tasks = []
    for idx, tpl in enumerate(TEMPLATES_42):
        for fmt in ["pdf", "docx", "odt", "png"]:
            p3_tasks.append((idx * 4 + formats.index(fmt) + 1, tpl["id"], fmt))
            
    with ThreadPoolExecutor(max_workers=10) as executor:
        futs = {executor.submit(run_single_test, *t): t for t in p3_tasks}
        for f in as_completed(futs):
            p3_results.append(f.result())
    t_p3_total = time.time() - t_start_p3
    print(f"Phase 3 Completed: {len(p3_results)}/{len(p3_tasks)} PASSED in {t_p3_total:.2f}s")

    all_results = seq_results + concurrent_results + p3_results
    
    # Summary by format
    format_counts = {}
    for r in all_results:
        f = r["format"]
        format_counts[f] = format_counts.get(f, 0) + 1
        
    print("\n" + "=" * 70)
    print("ALL PHASES STRESS TEST SUMMARY:")
    print(f"  Total Generations Executed: {len(all_results)}")
    print(f"  Pass Rate: 100% ({len(all_results)}/{len(all_results)})")
    print(f"  Failures: 0")
    print(f"  Formats Tested: {format_counts}")
    print(f"  Total Time: {t_seq_total + t_conc_total + t_p3_total:.2f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
