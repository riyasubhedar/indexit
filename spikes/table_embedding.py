"""Spike: what should a table passage be searched by? Copies docling_v3 into docling_v3b with the table
rows re-embedded from title + full table text (instead of title + row/column labels), then compares.

  uv run python spikes/table_embedding.py
"""

from indexit.embedder import Embedder
from indexit.evaluate import load_golden, search_eval
from indexit.search import retrieve
from indexit.store import ChunkStore

source, target = ChunkStore("docling_v3")._table(), ChunkStore("docling_v3b")
target.drop()
rows = source.search().limit(None).to_list()
tables = [r for r in rows if r["kind"] == "table"]
vectors = Embedder().embed_passages([r["text"] for r in tables])  # text = "Table: <title>\n<markdown>"
for r, v in zip(tables, vectors):
    r["vector"] = v
for r in rows:
    r.pop("_distance", None)
target.db.create_table("docling_v3b", data=rows)
print(search_eval(tables=["docling_v3", "docling_v3b"]))
qs = load_golden(subset="dev")
for table in ("docling_v3", "docling_v3b"):
    n = sum(r.get("kind") == "table" for g in qs for r in retrieve(g["question"], table=table))
    print(f"{table}: table passages in top-8 across {len(qs)} dev questions: {n}")
