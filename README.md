Explain My Company

Turn messy company PDFs (prepared remarks, earnings, filings) into a concise brief and a shareable slide deck.
Local-first MVP: simple, reproducible, and no API keys.








Demo

Sample brief: docs/brief.md

Sample deck (PDF): docs/deck.pdf

Inputs (actual PDFs) are not stored in the repo. Use any public investor PDF locally.

What it does

Extract text from each PDF page with PyMuPDF; if the text layer is missing, OCR with Tesseract.

Find numbers in context: currency and percentages near useful keywords (revenue, operating income, margin, capex, guidance, etc.).

Captures a clean sentence window

Handles decimals correctly (no “$20.” truncation)

Dedupe near-duplicates

Downranks obvious segment lines (e.g., “Family of Apps”)

Write a brief (outputs/brief.md) with:

Numbers in context (KPI-ish)

Detected margins

Notable snippets

Source pages

Generate slides (outputs/slides.md) and export a PDF deck with Marp.

Quickstart
Requirements

Python 3.13+

Tesseract OCR (Windows installer: UB Mannheim build; add Tesseract-OCR to PATH)

Optional for slides: Node LTS and Marp CLI (npm i -g @marp-team/marp-cli)

Setup
# clone and enter
git clone https://github.com/<you>/explain-my-company.git
cd explain-my-company

# Python env
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt

Run
# put a public PDF here
mkdir -p datasets/sample
# copy your PDF into datasets/sample

# parse → brief
python pipeline.py

# make slides (markdown → PDF)
python make_slides.py
marp outputs/slides.md --pdf --output outputs/deck.pdf


Outputs:

outputs/brief.md

outputs/slides.md

outputs/deck.pdf (if Marp is installed)

Folder structure
.
├─ datasets/
│  └─ sample/           # your local PDFs (not committed)
├─ outputs/             # generated brief/slides (gitignored)
├─ docs/                # demo artifacts committed for viewers
├─ pipeline.py          # PDF → text → numbers-in-context → brief
├─ make_slides.py       # brief → slides.md (Marp-friendly)
├─ requirements.txt
├─ .gitignore
└─ LICENSE

Tech notes

Extraction: PyMuPDF for native text, Tesseract OCR fallback at 300 DPI.

Normalization: squash weird whitespace and non-breaking spaces.

Scoring: keyword boosts (revenue, operating income, margin, capex…), magnitude bias for likely consolidated figures, penalties for segment jargon.

Boundaries: sentence windows that ignore decimal dots, include units (“billion/million”), and trim duplicates.

Limitations

Heuristics can still surface some segment lines; that’s intentional for completeness.

No LLM in the loop yet; this is deterministic and fast.

PDFs vary wildly; OCR accuracy depends on source quality.

Roadmap

Simple web UI (upload → brief → deck download)

“Segment vs consolidated” tags per snippet

Optional LLM pass for clean KPI table + narrative

Auto 60-sec video (script + TTS + captions)

Tests and small sample corpus

Dockerfile for one-command run

Contributing

PRs welcome. Please keep inputs public and free of secrets. Run ruff/black if you introduce Python styling (future).

License

MIT. See LICENSE.

Privacy

This tool is local-first. Your PDFs stay on your machine unless you decide to share outputs. The repo intentionally ignores outputs/ and any *.pdf.

If you want, add a repo description and topics on GitHub: ai, ocr, nlp, pdf, marp, summarization, data-extraction. Then push.