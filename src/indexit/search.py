"""Retrieval shared by every front door (CLI, MCP server, future app)."""

import math
import re

from indexit.documents import companies_in, list_filings, resolve_company
from indexit.embedder import Embedder
from indexit.store import ChunkStore

TABLE = "clean_v2"  # D-019; "simple_v1" is the baseline
HYBRID = False  # keyword + meaning search: tested 2026-10-25, didn't help on raw questions (D-019)
TOP_K = 8  # passages per search
MIN_PER_COMPANY = 3  # when a question names several companies, each gets at least this many passages
PREFER_LATEST = True  # D-011 in search: most passages from the latest filing (+ any year the question names)

_embedder = Embedder()  # loads the model lazily, once per process


def warm_up() -> None:
    _embedder.warm_up()


def retrieve(
    question: str,
    k: int = TOP_K,
    company: str | None = None,
    by_company: bool = True,
    table: str = TABLE,
    hybrid: bool | None = None,
    prefer_latest: bool | None = None,
) -> list[dict]:
    """Passages most relevant to `question`.

    Company-aware ("mentions vs. about"): if `company` is given, or the question names companies, only
    those companies' filings are searched, so a page that merely *mentions* Microsoft in AMD's 10-K
    can't outrank Microsoft's own filing. Several named companies each get an equal share of passages.
    Questions naming no company search everything. `by_company=False` turns this off and `table` picks
    another index version, `hybrid` adds keyword search (all for comparisons).

    Latest filing first (D-011): within a company, most passages come from its latest filing, plus the
    filing for any fiscal year the question names ("Apple's profit in 2024"). A quarter of the slots stay
    open to its other filings, so facts only in an older filing remain reachable.
    """
    vector, store = _embedder.embed_query(question), ChunkStore(table)
    text = question if (HYBRID if hybrid is None else hybrid) else None
    if company:
        resolved = resolve_company(company)
        if resolved is None:
            raise ValueError(f"No filings for company {company!r}.")
        companies = [resolved]
    else:
        companies = companies_in(question) if by_company else []
    if not companies:
        return store.search(vector, k, text=text)
    per_company = max(MIN_PER_COMPANY, math.ceil(k / len(companies)))
    latest_first = PREFER_LATEST if prefer_latest is None else prefer_latest
    hits = []
    for c in companies:
        preferred, others = _split_by_recency(c, question) if latest_first else ([f.file for f in list_filings() if f.company == c], [])
        older_slots = per_company // 4 if others else 0
        hits += store.search(vector, per_company - older_slots, docs=preferred, text=text)
        if older_slots:
            hits += store.search(vector, older_slots, docs=others, text=text)
    return sorted(hits, key=lambda hit: hit["_distance"])


def _split_by_recency(company: str, question: str) -> tuple[list[str], list[str]]:
    """(the company's latest filing + filings for fiscal years named in the question, its other filings)."""
    filings = [f for f in list_filings() if f.company == company]
    named_years = {int(year) for year in re.findall(r"\b(20\d\d)\b", question)}
    latest = max(f.fiscal_year for f in filings)
    preferred = [f.file for f in filings if f.fiscal_year == latest or f.fiscal_year in named_years]
    return preferred, [f.file for f in filings if f.file not in preferred]
