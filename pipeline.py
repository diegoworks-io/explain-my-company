import io, re
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

print(">>> PIPELINE VERSION: numbers-in-context v2 (no decimal cutoffs, dedupe, segment penalty)")

# -------- paths --------
INPUT = Path("datasets/sample")
OUTPUT = Path("outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)

# -------- text utils --------
def normalize_text(t: str) -> str:
    # Normalize weird PDF whitespace so regex stays sane
    t = t.replace("\u00a0", " ")          # non-breaking space
    t = re.sub(r"\s+", " ", t).strip()    # collapse all whitespace
    return t

# Money like $47.5 billion, USD 370 million, ($1.2B), $370m
CURRENCY = r"(?:\b(?:USD|US\$|\$)\s*)?\(?([0-9][\d,]*(?:\.\d+)?)\)?\s*(million|billion|thousand|bn|m|k)?"
# Percent like 43%
PERCENT  = r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%"

KW_GOOD = (
    "revenue","total revenue","net sales","operating income",
    "income from operations","operating margin","gross margin",
    "eps","users","dau","mau","arpu","growth","guidance","outlook",
    "capex","capital expenditures","free cash flow","headcount",
)
KW_SEGMENT_BAD = ("family of apps","reality labs","segment","cost of revenue")

def to_amount(m):
    if not m: return None
    g1 = m.group(1)
    try:
        val = float(g1.replace(",", ""))
    except Exception:
        return None
    unit = (m.group(2) or "").lower()
    mult = {"k":1e3,"thousand":1e3,"m":1e6,"million":1e6,"bn":1e9,"billion":1e9}.get(unit,1.0)
    return val * mult

def fmt_percent(m):
    return f"{m.group(1)}%" if m else "N/A"

# -------- PDF -> text (with OCR fallback) --------
def page_text_or_ocr(doc, page_index, dpi=300):
    page = doc[page_index]
    txt = page.get_text("text").strip()
    if txt:
        return txt, "native"
    # Fallback: render and OCR
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes(output="png")))
    ocr = pytesseract.image_to_string(img, lang="eng").strip()
    return ocr, "ocr"

def extract_pages_to_txt(pdf_path: Path):
    doc = fitz.open(pdf_path)
    outs, modes = [], []
    for i in range(len(doc)):
        text, mode = page_text_or_ocr(doc, i)
        out = OUTPUT / f"page_{i+1}.txt"
        out.write_text(text, encoding="utf-8")
        outs.append(out); modes.append(mode)
        print(f"Saved {out} ({mode})")
    return outs, modes

# -------- snippet boundary helpers --------
def _is_decimal_dot(s: str, i: int) -> bool:
    return 0 < i < len(s)-1 and s[i-1].isdigit() and s[i+1].isdigit()

def number_sentence_bounds(s: str, num_match, left=160, right=240):
    """
    Build a snippet around a currency/percent match:
    - Start near previous sentence boundary (ignoring decimal dots)
    - Ensure we include the full numeric phrase + trailing unit/comma
    - End at the next real sentence boundary (ignoring decimal dots)
    """
    n0, n1 = num_match.start(), num_match.end()
    start = max(0, n0 - left)

    # Extend end to include trailing unit/comma words after the number
    tail = s[n1:n1+80]
    m_tail = re.match(r"\s*(?:[A-Za-z-]+)?(?:\s*[A-Za-z-]+)?(?:\s*,)?", tail)
    extra = len(m_tail.group(0)) if m_tail else 0
    end_seed = n1 + min(extra, 80)

    # Walk forward to next punctuation that is not a decimal dot
    end = min(len(s), end_seed + right)
    stop = end
    for i in range(end_seed, min(len(s), end_seed + right)):
        c = s[i]
        if c in ".!?;":
            if c == "." and _is_decimal_dot(s, i):
                continue
            stop = i + 1
            break

    # Snap start to previous sentence boundary (ignoring decimal dots)
    snap = start
    for i in range(n0-1, max(0, n0-300), -1):
        c = s[i]
        if c in ".!?;\n":
            if c == "." and _is_decimal_dot(s, i):
                continue
            snap = i + 1
            break

    return max(0, snap), min(len(s), stop)

# -------- core: collect number-in-context snippets --------
def collect_number_snippets(pages, max_items=10):
    """
    For each page, find currency/percent occurrences and capture a clean sentence/window.
    Score by keywords, magnitude, and downrank segment lines.
    Dedupe by containment to avoid tiny partial repeats.
    """
    results = []
    cur_re = re.compile(CURRENCY, re.I)
    pct_re = re.compile(PERCENT, re.I)

    for idx, raw in enumerate(pages, start=1):
        t = normalize_text(raw)
        # Currency mentions
        for m in cur_re.finditer(t):
            st, en = number_sentence_bounds(t, m)
            snippet = t[st:en].strip()
            if len(snippet) < 40 or len(snippet) > 360:
                continue
            ctx = snippet.lower()
            score = 0.0
            # helpful keywords
            for kw in KW_GOOD:
                if kw in ctx: score += 2.6
            # segments downweight harder
            for bad in KW_SEGMENT_BAD:
                if bad in ctx: score -= 3.0
            # magnitude helps (separate tiny line items from topline)
            amt = to_amount(m)
            if amt is not None:
                score += min(amt/1e9, 10)  # up to +10 for >=10B
            # context candy
            for tag in (" q1 "," q2 "," q3 "," q4 "," 2025 "," 2024 "," yoy "," y/y "," guidance "," outlook "):
                if tag in " " + ctx + " ":
                    score += 0.8
            results.append(("currency", score, idx, snippet))

        # Percent mentions
        for m in pct_re.finditer(t):
            st, en = number_sentence_bounds(t, m)
            snippet = t[st:en].strip()
            if len(snippet) < 40 or len(snippet) > 360:
                continue
            ctx = snippet.lower()
            score = 0.0
            for kw, w in [("operating margin", 3.2), ("gross margin", 3.0),
                          ("margin", 1.6), ("growth", 1.4),
                          ("increase", 1.0), ("decrease", 1.0),
                          ("yoy", 1.2), ("y/y", 1.2)]:
                if kw in ctx: score += w
            for bad in KW_SEGMENT_BAD:
                if bad in ctx: score -= 2.0
            try:
                score += min(float(m.group(1))/10, 5)  # 50% => +5
            except:
                pass
            results.append(("percent", score, idx, snippet))

    # Sort, then dedupe by containment
    results.sort(key=lambda x: x[1], reverse=True)
    deduped = []
    for kind, score, page_no, snip in results:
        snip_l = snip.lower()
        # skip if contained in already kept snippet
        if any(snip_l in kept.lower() for _,_,_,kept in deduped):
            continue
        # skip if it fully contains a long already-kept snippet (avoid near-dup walls of text)
        if any(len(kept) > 60 and kept.lower() in snip_l for _,_,_,kept in deduped):
            continue
        deduped.append((kind, score, page_no, snip))
        if len(deduped) >= max_items:
            break
    return deduped

def try_simple_margin(all_text):
    t = normalize_text(all_text)
    pat = re.compile(r"(?:operating\s+margin)[\s\S]{0,200}"+PERCENT+r"|"+PERCENT+r"\s+(?:operating\s+margin)", re.I)
    m = re.search(pat, t)
    return fmt_percent(re.search(PERCENT, m.group(0), re.I)) if m else "N/A"

# -------- brief writer --------
def make_brief_md(pdf_name: str, page_files, modes):
    pages = [Path(p).read_text(encoding="utf-8") for p in page_files]
    all_text = "\n\n".join(pages)

    # pull top numeric snippets + margin
    top_snips = collect_number_snippets(pages, max_items=10)
    op_margin = try_simple_margin(all_text)

    lines = []
    lines.append(f"# Executive Brief: {pdf_name}\n")
    lines.append("Auto-generated draft from the local pipeline.\n")

    lines.append("## Numbers in context (KPI-ish)")
    if not top_snips:
        lines.append("- No numeric snippets detected.")
    else:
        for kind, score, page_no, snip in top_snips:
            lines.append(f"- Page {page_no}: {snip}")

    lines.append("\n## Detected margins")
    lines.append(f"- operating_margin: {op_margin}")

    lines.append("\n## Notable snippets")
    added = 0
    for idx, p in enumerate(pages, start=1):
        s = p.strip().replace("\n", " ")
        if not s:
            continue
        lines.append(f"- Page {idx} ({modes[idx-1]}): {s[:220]}...")
        added += 1
        if added >= 5:
            break

    lines.append("\n## Source pages saved")
    for f in page_files[:10]:
        lines.append(f"- {Path(f).name}")

    (OUTPUT / "brief.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote outputs/brief.md")

# -------- main --------
if __name__ == "__main__":
    sample_pdfs = list(INPUT.glob("*.pdf"))
    if not sample_pdfs:
        print("Put a PDF inside datasets/sample first!")
    else:
        pdf = sample_pdfs[0]
        pages, modes = extract_pages_to_txt(pdf)
        make_brief_md(pdf.name, pages, modes)
