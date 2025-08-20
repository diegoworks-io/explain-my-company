# Explain My Company

Turn messy company PDFs (prepared remarks, earnings, filings) into a concise **brief** and a shareable **slide deck**.  
Local-first MVP: simple, reproducible, and no API keys.

![License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)
![OCR](https://img.shields.io/badge/OCR-Tesseract-9cf.svg)
![Slides](https://img.shields.io/badge/Slides-Marp_PDF-6aa84f.svg)

---

## Demo

- Sample brief: [`docs/brief.md`](docs/brief.md)  
- Sample deck (PDF): [`docs/deck.pdf`](docs/deck.pdf)

> Inputs (actual PDFs) are **not** stored in the repo. Use any public investor PDF locally.

---

## What it does

1. **Extract text** from each PDF page with PyMuPDF; if the text layer is missing, **OCR** with Tesseract.
2. **Find numbers in context**: currency and percentages near useful keywords (revenue, operating income, margin, capex, guidance, etc.).
   - Captures a clean sentence window  
   - Handles decimals correctly (no “$20.” truncation)  
   - Dedupe near-duplicates  
   - Downranks obvious segment lines (e.g., “Family of Apps”)
3. **Write a brief** (`outputs/brief.md`) with:
   - Numbers in context (KPI-ish)
   - Detected margins
   - Notable snippets
   - Source pages
4. **Generate slides** (`outputs/slides.md`) and export a **PDF deck** with Marp.

---

## Quickstart

### Requirements
- Python 3.13+
- Tesseract OCR (Windows installer: UB Mannheim build; add `Tesseract-OCR` to PATH)
- Optional for slides: Node LTS and Marp CLI (`npm i -g @marp-team/marp-cli`)

### Setup
```bash
# clone and enter
git clone https://github.com/<your-username>/explain-my-company.git
cd explain-my-company

# Python env
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
