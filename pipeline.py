import io
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

INPUT = Path("datasets/sample")
OUTPUT = Path("outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)

def page_text_or_ocr(doc, page_index, dpi=300):
    """Try native text; if empty, render page and OCR."""
    page = doc[page_index]
    txt = page.get_text("text").strip()
    if txt:
        return txt, "native"
    # Fallback to OCR
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes(output="png")))
    ocr_txt = pytesseract.image_to_string(img, lang="eng").strip()
    return ocr_txt, "ocr"

def extract_pages_to_txt(pdf_path: Path):
    doc = fitz.open(pdf_path)
    out_files, modes = [], []
    for i in range(len(doc)):
        text, mode = page_text_or_ocr(doc, i)
        out_file = OUTPUT / f"page_{i+1}.txt"
        out_file.write_text(text, encoding="utf-8")
        out_files.append(out_file)
        modes.append(mode)
        print(f"Saved {out_file} ({mode})")
    return out_files, modes

def make_brief_md(pdf_name: str, page_files, modes):
    pages = [Path(p).read_text(encoding="utf-8") for p in page_files]
    kpis = [
        {"metric": "revenue", "value": "TBD", "unit": "USD"},
        {"metric": "gross_margin", "value": "TBD", "unit": "%"},
        {"metric": "operating_income", "value": "TBD", "unit": "USD"},
    ]
    lines = []
    lines.append(f"# Executive Brief: {pdf_name}\n")
    lines.append("Auto-generated draft from the local pipeline. KPIs are placeholders.\n")
    lines.append("## KPIs")
    for k in kpis:
        lines.append(f"- {k['metric']}: {k['value']} {k['unit']}")
    lines.append("\n## Notable snippets")
    snippets = []
    for idx, p in enumerate(pages, start=1):
        s = p.strip().replace("\n", " ")
        if not s:
            continue
        snippets.append((idx, s[:220]))
        if len(snippets) >= 5:
            break
    if not snippets:
        lines.append("- No text detected.")
    else:
        for page_no, snip in snippets:
            mode = modes[page_no-1] if page_no-1 < len(modes) else "unknown"
            lines.append(f"- Page {page_no} ({mode}): {snip}...")
    lines.append("\n## Source pages saved")
    for f in page_files[:10]:
        lines.append(f"- {Path(f).name}")
    (OUTPUT / "brief.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote outputs/brief.md")

if __name__ == "__main__":
    sample_pdfs = list(INPUT.glob("*.pdf"))
    if not sample_pdfs:
        print("Put a PDF inside datasets/sample first!")
    else:
        pdf_path = sample_pdfs[0]
        page_files, modes = extract_pages_to_txt(pdf_path)
        make_brief_md(pdf_path.name, page_files, modes)
