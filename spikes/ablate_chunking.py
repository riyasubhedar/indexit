"""Ablation spike: which part of the clean pipeline helps or hurts? Builds small indexes from the
NVIDIA + AMD filings (the ones the golden questions cover) and compares them with eval-search.

  uv run python spikes/ablate_chunking.py
"""

import re
from pathlib import Path

from indexit import clean_pipeline, simple_pipeline
from indexit.embedder import Embedder
from indexit.evaluate import search_eval
from indexit.store import ChunkStore, file_hash

FILES = [p for p in Path("data/filings").glob("*.pdf") if re.search(r"AMD|177440d5|e361e58a", p.name)]


def with_context_embedded(path):
    return [simple_pipeline.Chunk(c.doc, c.page, f"[{c.context}] {c.text}") for c in clean_pipeline.chunk_pdf(path)]


VARIANTS = {"abl_simple": simple_pipeline.chunk_pdf, "abl_clean_ctx": with_context_embedded, "abl_clean_noctx": clean_pipeline.chunk_pdf}

embedder = Embedder()
for table, chunker in VARIANTS.items():
    store = ChunkStore(table)
    if store.indexed_hashes():
        store.build_keyword_index()
        continue
    for pdf in FILES:
        chunks = chunker(pdf)
        vectors = embedder.embed_passages([c.text for c in chunks])
        store.replace_doc(pdf.name, [
            {"id": c.id, "doc": c.doc, "doc_hash": file_hash(pdf), "page": c.page, "text": c.text, "vector": v}
            for c, v in zip(chunks, vectors)
        ])
    store.build_keyword_index()
print(search_eval(tables=[*VARIANTS, "abl_simple+hybrid", "abl_clean_noctx+hybrid"]))
