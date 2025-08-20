import io, re
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

INPUT = Path("datasets/sample")
OUTPUT = Path("outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)

# Simple patterns for amounts and percents
CURRENCY = r"(?:\\b(?:USD|US\\$|\\$)\\s*)?([\\d,]+(?:\\.\\d+)?)\\s*(million|billion|thousand|bn|m|k)?"
PERCENT  = r"([0-9]{1,3}(?:\\.[0-9]+)?)\\s*%"

def page_text_or_ocr(doc, page_index, dpi=300):
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

def _first_match(patterns, text, flags=re.I):
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m
    return None

def _fmt_amount(m):
    if not m:
        return "N/A"
    amount = m.group(1)
    unit = (m.group(2) or "").lower()
    unit_map = {"million":"M","m":"M","billion":"B","bn":"B","thousand":"K","k":"K"}
    return f"${amount}{unit_map.get(unit, '')}"

def _fmt_percent(m):
    if not m:
        return "N/A"
    return f"{m.group(1)}%"

def extract_kpis(all_text):
    t = all_text.replace("\u00a0"," ")

    rev_ctx = r"(?:total\\s+revenue|revenue|net\\s+sales)[^\\n\\r]{0,80}" + CURRENCY
    gm_ctx  = r"(?:gross\\s+margin|gross\\s+profit\\s+margin)[^\\n\\r]{0,40}" + PERCENT
    op_ctx  = r"(?:operating\\s+income|income\\s+from\\s+operations|operating\\s+loss)[^\\n\\r]{0,80}" + CURRENCY

    rev = _first_match([rev_ctx], t)
    gm  = _first_match([gm_ctx], t)
    op  = _first_match([op_ctx], t)

    return {
        "revenue": _fmt_amount(rev),
        "gross_margin": _fmt_percent(gm),
        "operating_income": _fmt_amount(op),
    }

def make_brief_md(pdf_name: str, page_files, modes):
    pages = [Path(p).read_text(encoding="utf-8") for p in page_files]
    all_text = "\n\n".join(pages)
    kpis = extract_kpis(all_text)

    lines = []
    lines.append(f"# Executive Brief: {pdf_name}\n")
    lines.append("Auto-generated draft from the local pipeline.\n")
    lines.append("## KPIs")
    lines.append(f"- revenue: {kpis['revenue']}")
    lines.append(f"- gross_margin: {kpis['gross_margin']}")
    lines.append(f"- operating_income: {kpis['operating_income']}")
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
