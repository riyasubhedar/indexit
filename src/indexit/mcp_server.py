"""IndexIt MCP server (D-013): exposes search over the filings as tools for Claude Code / Desktop.

Run by the AI client over stdio:  .venv/bin/python -m indexit.mcp_server
"""

import pymupdf
from mcp.server.mcpserver import MCPServer

from indexit.documents import FILINGS_DIR, format_filings, list_filings as _list_filings
from indexit.prompts import ANSWER_FORMAT, ROLE
from indexit.search import retrieve, warm_up
from indexit.tables import page_tables

TABLE_BUDGET_CHARS = 16_000  # ≈4k tokens of tables per search; a page's tables are ~1.3k chars (median)

server = MCPServer(
    name="indexit",
    instructions="Search and read a folder of company 10-K filings. Call list_filings first.",
)


def _labels() -> dict[str, str]:
    return {f.file: f.label for f in _list_filings()}


def _section(passage: dict) -> str:
    """"Advanced Micro Devices FY2025 10-K · Item 8. Financial Statements · p.74" -> "Item 8. Financial Statements"."""
    parts = passage.get("context", "").split(" · ")
    return parts[1] if len(parts) == 3 else ""


@server.tool()
def list_filings() -> str:
    """List the 10-K filings available: company, fiscal year, fiscal period end date, page count, file name."""
    return format_filings()


@server.tool()
def search_filings(query: str, company: str | None = None, k: int = 8) -> str:
    """Find the passages most relevant to `query` (meaning-based search).

    Searches only the filings of companies named in `query` (so pages that merely mention a company in
    another company's 10-K don't crowd out its own filing). Set `company` (e.g. "Microsoft", "AMD") to
    restrict the search to one company explicitly, e.g. when the query names other companies too.
    Returns about `k` passages (max 15), each with document label, file name and page number.
    Write specific queries, e.g. "NVIDIA fiscal 2026 data center revenue".
    """
    labels = _labels()
    try:
        passages = retrieve(query, min(max(k, 1), 15), company=company)
    except ValueError as error:
        companies = sorted({f.company for f in _list_filings()})
        return f"{error} Companies with filings: {', '.join(companies)}."
    return "\n\n".join(
        f'<passage document="{labels.get(p["doc"], p["doc"])}" section="{_section(p)}" '
        f'file="{p["doc"]}" page="{p["page"]}">\n'
        f'{p["text"]}\n</passage>'
        for p in passages
    ) + _result_page_tables(passages, labels)


def _result_page_tables(passages: list[dict], labels: dict[str, str]) -> str:
    """Small-to-big (D-022): search finds pages through text passages; Claude then gets each result
    page's Docling tables with their column headers, so numbers can't drift from their years. Pages in
    rank order, each once, within TABLE_BUDGET_CHARS; read_page shows the rest."""
    blocks, used, seen = [], 0, set()
    for p in passages:
        key = (p["doc"], p["page"])
        if key in seen:
            continue
        seen.add(key)
        for t in page_tables(FILINGS_DIR / p["doc"], p["page"]):
            block = (f'<table document="{labels.get(p["doc"], p["doc"])}" file="{p["doc"]}" '
                     f'page="{p["page"]}" title="{t.title}">\n{t.compact}\n</table>')
            if used + len(block) > TABLE_BUDGET_CHARS:
                continue
            blocks.append(block)
            used += len(block)
    if not blocks:
        return ""
    return ("\n\nStructured tables from the pages above (column headers kept; prefer these for numbers "
            "and years):\n\n" + "\n\n".join(blocks))


@server.tool()
def read_page(file: str, page: int) -> str:
    """Return the full text of one page (1-based page number) of a filing, e.g. to see a whole table.

    `file` must be a file name exactly as shown by list_filings.
    """
    filings = {f.file: f for f in _list_filings()}
    if file not in filings:  # only files in the filings folder, never arbitrary paths
        return f"Unknown file {file!r}. Use a file name from list_filings."
    filing = filings[file]
    if not 1 <= page <= filing.pages:
        return f"{filing.label} has pages 1-{filing.pages}."
    with pymupdf.open(FILINGS_DIR / file) as pdf:
        text = pdf[page - 1].get_text()
    tables = page_tables(FILINGS_DIR / file, page)
    structured = "".join(
        f'\n<table title="{t.title}">\n{t.compact}\n</table>' for t in tables
    )
    note = "\nStructured versions of this page's tables (column headers kept; prefer these for numbers):" if tables else ""
    return f'<page document="{filing.label}" page="{page}">\n{text}{note}{structured}\n</page>'


@server.prompt()
def indexit_answer(question: str) -> str:
    """Answer a question about the filings in IndexIt's two-part format."""
    return f"{ROLE} Use the IndexIt tools to research this question.\n\n{ANSWER_FORMAT}\n\nQuestion: {question}"


if __name__ == "__main__":
    warm_up()  # load the embedding model while Claude is still planning its first search
    server.run()
