"""Parsing spike: run Docling on a page range of one PDF and print its tables."""
import sys
import time

from docling.document_converter import DocumentConverter

path, first, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
start = time.time()
doc = DocumentConverter().convert(path, page_range=(first, last)).document
print(f"converted pages {first}-{last} in {time.time() - start:.0f}s")
for table in doc.tables:
    print(f"--- table on page {table.prov[0].page_no} ---")
    print(table.export_to_markdown(doc=doc))
