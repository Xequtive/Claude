#!/usr/bin/env python3
"""Turn downloaded Amex statement PDFs into the s_<key>.txt files the runner reads.
Usage: python3 zoho/amex/amex_ingest.py <folder-with-pdfs>
Accepted names: 'B040 - 24.01 Statement.pdf', 'Amex Platinum - 2024-01 Statement.pdf', '2026-10-21.pdf'."""
import os, re, sys, subprocess
from paths import STMT_DIR
os.makedirs(STMT_DIR, exist_ok=True)
src = sys.argv[1]
for f in sorted(os.listdir(src)):
    if not f.lower().endswith(".pdf"): continue
    m = re.search(r"(\d\d)\.(\d\d) Statement", f) or None
    if m: key = f"{m.group(1)}.{m.group(2)}"
    else:
        m = re.search(r"(20\d\d)-(\d\d)(?:-(\d\d))?", f)
        if not m: print("skip", f); continue
        key = f"{m.group(1)[2:]}.{m.group(2)}" if not m.group(3) or f.startswith("Amex") else f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    out = os.path.join(STMT_DIR, f"s_{key}.txt")
    subprocess.run(["pdftotext", "-layout", os.path.join(src, f), out], check=True)
    print(f, "->", out)
