"""Step 1 baseline ("simple RAG"): plain page text cut into fixed-size pieces.

Deliberately naive so the eval can show what later layers fix:
- tables are flattened into one-value-per-line text (no structure),
- pieces are cut by character count, not by section or table,
- the only metadata is the file name and page (no company / fiscal year).
"""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

CHUNK_CHARS = 1500  # ~375 tokens; a common default for simple RAG
OVERLAP_CHARS = 200  # repeated between neighbouring pieces so a sentence cut in half survives in one


@dataclass
class Chunk:
    doc: str  # PDF file name
    page: int  # 1-based page number as shown in a PDF viewer
    text: str
    context: str = ""  # e.g. "AMD FY2025 10-K · Item 8. Financial Statements · p.74"; shown, not embedded
    embed_text: str = ""  # what gets embedded for search, if different from `text` (e.g. a table's labels)
    kind: str = "text"  # "text" or "table"

    @property
    def id(self) -> str:
        return f"{self.doc}#p{self.page}#{hash(self.text) & 0xFFFFFFFF:08x}"


def chunk_pdf(path: Path) -> list[Chunk]:
    chunks = []
    with pymupdf.open(path) as pdf:
        for page_index, page in enumerate(pdf):
            text = " ".join(page.get_text().split())  # collapse newlines/whitespace
            start = 0
            while start < len(text):
                piece = text[start : start + CHUNK_CHARS]
                if piece.strip():
                    chunks.append(Chunk(doc=path.name, page=page_index + 1, text=piece))
                start += CHUNK_CHARS - OVERLAP_CHARS
    return chunks
