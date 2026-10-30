"""Structured tables from Docling (D-003, D-022), cached on disk because extraction takes ~1.3 s per page.

Each table keeps its real column headers and row labels, and gets a title from the sentence just before
it, e.g. "The following table shows net sales by category for 2025, 2024 and 2023 (dollars in millions)".
Cache: data/parsed/<file hash>.tables.json, so re-indexing never re-runs Docling for an unchanged PDF.
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf

from indexit.documents import PROJECT_DIR
from indexit.store import file_hash

CACHE_DIR = PROJECT_DIR / "data" / "parsed"
BATCH_PAGES = 40  # convert in page batches to keep memory in check on an 8 GB Mac


@dataclass
class Table:
    page: int  # 1-based PDF page
    title: str  # the text just before the table
    markdown: str
    columns: list[str]
    rows: list[str]  # row labels (first column)

    @property
    def compact(self) -> str:
        """The markdown without Docling's cell padding (about half the characters, same cells)."""
        return "\n".join(re.sub(r" {2,}", " ", re.sub(r"-{3,}", "---", line)) for line in self.markdown.splitlines())


def _cache_path(path: Path) -> Path:
    return CACHE_DIR / f"{file_hash(path)[:16]}.tables.json"


def extract_tables(path: Path, progress=None) -> list[Table]:
    cache = _cache_path(path)
    if cache.exists():
        return [Table(**t) for t in json.loads(cache.read_text())]
    from docling.datamodel.base_models import InputFormat  # slow imports; only when extracting
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.types.doc import SectionHeaderItem, TableItem, TextItem

    # OCR off: these are digital PDFs; it only costs time (measured 1.5 vs 1.3 s/page, same tables).
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    with pymupdf.open(path) as pdf:
        pages = len(pdf)
    tables = []
    for first in range(1, pages + 1, BATCH_PAGES):
        last = min(first + BATCH_PAGES - 1, pages)
        doc = converter.convert(path, page_range=(first, last)).document
        text_before, text_before_that = "", ""
        for item, _ in doc.iterate_items():
            if isinstance(item, TableItem) and item.prov:
                frame = item.export_to_dataframe(doc=doc)
                if frame.empty:
                    continue
                tables.append(Table(
                    page=item.prov[0].page_no,
                    title=(item.caption_text(doc) or _title(text_before, text_before_that))[:300],
                    markdown=item.export_to_markdown(doc=doc),
                    columns=[str(c) for c in frame.columns],
                    rows=[str(r) for r in frame.iloc[:, 0] if str(r).strip()],
                ))
            elif isinstance(item, (SectionHeaderItem, TextItem)):
                text_before_that, text_before = text_before, item.text
        if progress:
            progress(last, pages, len(tables))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([asdict(t) for t in tables]))
    return tables


def _title(text_before: str, text_before_that: str) -> str:
    """A units line like "(In millions, except per share amounts)" isn't a title: join it with the line
    above, e.g. "CONSOLIDATED STATEMENTS OF OPERATIONS (In millions, …)"."""
    text_before = text_before.strip()
    if text_before.startswith("(") and text_before_that:
        return f"{text_before_that.strip()} {text_before}"
    return text_before


def page_tables(path: Path, page: int) -> list[Table]:
    """Cached tables on one page ([] if the file hasn't been through Docling yet)."""
    cache = _cache_path(path)
    if not cache.exists():
        return []
    return [Table(**t) for t in json.loads(cache.read_text()) if t["page"] == page]
