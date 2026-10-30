"""Step 2b (D-022): the clean text pipeline + every Docling table as its own passage.

A table passage shows Claude the full table with its headers ("| | 2025 | Change | 2024 |…"), so
numbers can't drift away from their years. What gets *searched* is the table's title + row and column
labels, not the numbers: a grid of numbers has little meaning to embed (see LEARNING.md, "search text
vs content"). Big tables are split into row groups, each repeating the header rows.
"""

from pathlib import Path

from indexit import clean_pipeline
from indexit.documents import describe
from indexit.simple_pipeline import Chunk
from indexit.tables import Table, extract_tables

MAX_TABLE_CHARS = 3000  # larger tables are split into row groups


def _row_groups(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    header, body = lines[:2], lines[2:]  # header row + "|---|" separator
    groups, current = [], []
    for line in body:
        current.append(line)
        if sum(len(l) + 1 for l in header + current) >= MAX_TABLE_CHARS:
            groups.append("\n".join(header + current))
            current = []
    if current or not groups:
        groups.append("\n".join(header + current))
    return groups


def table_chunks(path: Path, tables: list[Table]) -> list[Chunk]:
    label = describe(path).label
    chunks = []
    for table in tables:
        search_text = (
            f"Table: {table.title} Rows: {'; '.join(table.rows[:40])}. "
            f"Columns: {'; '.join(c for c in table.columns if c)}."
        )
        for part in _row_groups(table.markdown):
            chunks.append(Chunk(
                doc=path.name, page=table.page, text=f"Table: {table.title}\n{part}",
                context=f"{label} · Table · p.{table.page}", embed_text=search_text, kind="table",
            ))
    return chunks


def chunk_pdf(path: Path, progress=None) -> list[Chunk]:
    return clean_pipeline.chunk_pdf(path) + table_chunks(path, extract_tables(path, progress))
