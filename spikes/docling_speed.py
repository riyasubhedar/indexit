"""Docling speed spike: seconds per page with OCR on vs off, on the same 10 NVIDIA pages (incl. statements).

  uv run python spikes/docling_speed.py
"""

import time

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

PDF, PAGES = "data/filings/e361e58a-7483-44f5-bc62-a9080ae6ec72.pdf", (49, 58)
for do_ocr in (True, False):
    options = PdfPipelineOptions(do_ocr=do_ocr, do_table_structure=True)
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    converter.convert(PDF, page_range=(49, 49))  # warm up: load models once, not counted
    start = time.monotonic()
    doc = converter.convert(PDF, page_range=PAGES).document
    seconds = time.monotonic() - start
    print(f"OCR {'on ' if do_ocr else 'off'}: {seconds / (PAGES[1] - PAGES[0] + 1):.1f} s/page, {len(doc.tables)} tables")
