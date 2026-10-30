"""Step 2a ("smart chunking", first layer, D-019): cleaned text, line-aware pieces, and a context line.

Fixes for problems the search eval found in the simple baseline:
- Boilerplate removal: a line that repeats (digits ignored) on at least half of a filing's pages is a
  header/footer, e.g. "Table of Contents", page numbers, or the browser-print date/title/URL lines on
  the AMD PDFs. These made footer-only pieces that crowded search results.
- Pieces are cut at line breaks, and a short leftover is merged into the piece before it, so there
  are no scraps.
- Each piece gets a context line, e.g. "Advanced Micro Devices FY2025 10-K · Item 7. MD&A · p.68", shown
  with search results. It is NOT embedded: an ablation showed that prefixing it hurt ranking with our
  small embedding model (expected page in top 8: 12/23 without the prefix vs 9/23 with it).
"""

import re
from collections import Counter
from pathlib import Path

import pymupdf

from indexit.documents import describe
from indexit.simple_pipeline import Chunk

CHUNK_CHARS = 1500
OVERLAP_CHARS = 200
MIN_TAIL_CHARS = 400  # a leftover shorter than this joins the previous piece
BOILERPLATE_SHARE = 0.5  # a line on at least this share of pages is a header/footer

# "Item 7. Management's…", "ITEM 1A. RISK FACTORS", "Item 8: …". The punctuation after the number is
# required, so a wrapped sentence like "Item 15 of this Annual Report…" isn't mistaken for a heading.
_ITEM_HEADING = re.compile(r"^(?:part\s+[iv]+\s*[,.\-–]?\s*)?item\s+(\d{1,2}[A-C]?)\s*[.:—–]", re.I)
# A short all-capitals line of 2+ words, e.g. "EXECUTIVE OVERVIEW", but not "PART II" or "ITEM 7".
_CAPS_HEADING = re.compile(r"^(?!PART\b|ITEM\b)[A-Z][A-Z&'’\-]+(?: [A-Z&'’\-]+){1,8}$")
_ITEM_TITLES = {
    "1": "Business", "1A": "Risk Factors", "1B": "Unresolved Staff Comments", "1C": "Cybersecurity",
    "2": "Properties", "3": "Legal Proceedings", "4": "Mine Safety Disclosures",
    "5": "Market for Common Equity and Stock Performance", "6": "[Reserved]",
    "7": "Management's Discussion and Analysis (MD&A)", "7A": "Market Risk Disclosures",
    "8": "Financial Statements", "9": "Changes in Accountants", "9A": "Controls and Procedures",
    "9B": "Other Information", "9C": "Foreign Jurisdiction Disclosure", "10": "Directors and Governance",
    "11": "Executive Compensation", "12": "Security Ownership", "13": "Relationships and Director Independence",
    "14": "Accountant Fees", "15": "Exhibits and Financial Statement Schedules", "16": "Form 10-K Summary",
}


def _normalise(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d", "#", line)).strip().lower()


def _page_lines(pdf) -> list[list[str]]:
    pages = [[line.strip() for line in page.get_text().splitlines() if line.strip()] for page in pdf]
    seen_on = Counter(norm for lines in pages for norm in {_normalise(line) for line in lines})
    threshold = max(3, BOILERPLATE_SHARE * len(pages))
    return [[line for line in lines if seen_on[_normalise(line)] < threshold] for lines in pages]


def _section_by_page(pages: list[list[str]]) -> list[str]:
    """Which 10-K Item each page belongs to, carried forward from the last real Item heading.

    A heading near the top of a page labels that page; one further down (e.g. "ITEM 6. [RESERVED]"
    at the bottom of AMD's stock-graph page) only takes effect from the next page. Pages listing many
    Items (tables of contents, cross-reference indexes) are skipped, and an Item heading that jumps
    *backwards* (e.g. "Item 1A" after Item 15) is a cross-reference, not a new section.

    Some filings (JPMorgan) put the annual report after the Items, with no Item headings at all, just
    capitalised headings ("EXECUTIVE OVERVIEW"). A capitalised heading at the top of a page starts a
    section too.
    """
    order = list(_ITEM_TITLES)
    current, current_rank, sections = "", -1, []
    for lines in pages:
        headings = [
            (i, m.group(1).upper()) for i, line in enumerate(lines)
            if (m := _ITEM_HEADING.match(line)) and m.group(1).upper() in _ITEM_TITLES
        ]
        headings = [(i, item) for i, item in headings if order.index(item) >= current_rank] if len(headings) < 4 else []
        caps = next((line for line in lines[:2] if _CAPS_HEADING.match(line)), None)
        if headings and headings[0][0] < 5:
            page_section = f"Item {headings[0][1]}. {_ITEM_TITLES[headings[0][1]]}"
        elif caps:
            page_section = _title(caps)
        else:
            page_section = current
        sections.append(page_section)
        if headings:
            current_rank = order.index(headings[-1][1])
            current = f"Item {headings[-1][1]}. {_ITEM_TITLES[headings[-1][1]]}"
            if caps and headings[-1][0] < 5:
                current = page_section
        elif caps:
            current = page_section
    return sections


def _title(heading: str) -> str:
    """"CONSOLIDATED RESULTS OF OPERATIONS" -> "Consolidated Results of Operations"; keeps "MD&A"."""
    small = {"of", "and", "the", "for", "in", "on", "to", "a", "an", "or"}
    words = heading.split()
    return " ".join(
        w if "&" in w else (w.lower() if i and w.lower() in small else w.capitalize()) for i, w in enumerate(words)
    )


def _size(lines: list[str]) -> int:
    return sum(len(line) + 1 for line in lines)


def _split(lines: list[str]) -> list[str]:
    pieces, current, carried = [], [], 0  # carried = lines at the start of `current` repeated from the last piece
    for line in lines:
        current.append(line)
        if _size(current) >= CHUNK_CHARS:
            pieces.append(" ".join(current))
            overlap = []
            while current and _size(overlap) < OVERLAP_CHARS:  # carry ~200 characters into the next piece
                overlap.insert(0, current.pop())
            current, carried = overlap, len(overlap)
    new_lines = current[carried:]
    if not new_lines:
        return pieces
    if pieces and _size(new_lines) < MIN_TAIL_CHARS:
        pieces[-1] += " " + " ".join(new_lines)
    else:
        pieces.append(" ".join(current))
    return pieces


def chunk_pdf(path: Path) -> list[Chunk]:
    filing = describe(path)
    with pymupdf.open(path) as pdf:
        pages = _page_lines(pdf)
    sections = _section_by_page(pages)
    chunks = []
    for page_index, (lines, section) in enumerate(zip(pages, sections)):
        context = " · ".join(part for part in (filing.label, section, f"p.{page_index + 1}") if part)
        for piece in _split(lines):
            chunks.append(Chunk(doc=path.name, page=page_index + 1, text=piece, context=context))
    return chunks
