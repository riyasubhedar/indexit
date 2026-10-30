"""Spike helper: print page numbers and snippets where a regex matches, across all filings.

  uv run python spikes/find.py "<regex>" [snippet width] [company filter regex]
"""

import re
import sys

import pymupdf

from indexit.documents import FILINGS_DIR, list_filings

pattern = re.compile(sys.argv[1], re.I)
width = int(sys.argv[2]) if len(sys.argv) > 2 else 200
only = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else None
for filing in list_filings():
    if only and not only.search(filing.label):
        continue
    for i, page in enumerate(pymupdf.open(FILINGS_DIR / filing.file)):
        text = " ".join(page.get_text().split())
        for m in list(pattern.finditer(text))[:2]:
            print(f"{filing.label} p{i + 1}: …{text[max(0, m.start() - 60):m.start() + width]}…")
