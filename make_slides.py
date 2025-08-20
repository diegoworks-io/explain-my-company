from pathlib import Path
import re

brief = Path("outputs/brief.md")
out   = Path("outputs/slides.md")
text  = brief.read_text(encoding="utf-8")

def chunk(h):
    m = re.search(rf"##\s*{re.escape(h)}\s*(.*?)(?=\n##|\Z)", text, re.S)
    return (m.group(1).strip() if m else "").strip()

title = re.search(r"^#\s*(.+)$", text, re.M)
title = title.group(1) if title else "Company Brief"

slides = f"""---
marp: true
paginate: true
theme: default
---

# {title}

Auto-generated from local pipeline.

---

## Numbers in context

{chunk("Numbers in context (KPI-ish)") or "- No numeric snippets detected."}

---

## Detected margins

{chunk("Detected margins") or "- None."}

---

## Notable snippets

{chunk("Notable snippets") or "- None."}

---

## Sources

{chunk("Source pages saved") or "- None."}
"""
out.write_text(slides, encoding="utf-8")
print(f"Wrote {out}")
