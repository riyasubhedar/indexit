"""Reranker spike: fetch 30 candidates, re-order with a cross-encoder, keep the top 8. Compare with eval-search metrics.

  uv run python spikes/rerank.py
"""

import statistics
import time

from sentence_transformers import CrossEncoder

from indexit import search
from indexit.documents import list_filings
from indexit.evaluate import expected_pages, key_figures, load_golden

MODELS = ["cross-encoder/ms-marco-MiniLM-L-6-v2", "BAAI/bge-reranker-base"]
filings = {f.file: f for f in list_filings()}
questions = [g for g in load_golden(subset="dev") if expected_pages(g["source"])]


def score(rerank_with=None):
    pages, figures, seconds = 0, [], []
    for g in questions:
        start = time.monotonic()
        results = search.retrieve(g["question"], k=30 if rerank_with else 8)
        if rerank_with:
            scores = rerank_with.predict([(g["question"], r["text"]) for r in results])
            results = [r for _, r in sorted(zip(scores, results), key=lambda pair: -pair[0])][:8]
        seconds.append(time.monotonic() - start)
        got = {(filings[r["doc"]].company, filings[r["doc"]].fiscal_year, r["page"]) for r in results}
        pages += bool(got & set(expected_pages(g["source"])))
        if figs := key_figures(g["expected"]):
            text = " ".join(r["text"] for r in results)
            figures.append(sum(f in text for f in figs) / len(figs))
    return pages, statistics.mean(figures), statistics.median(seconds)


print("| Search | Expected page in top 8 | Key figures in results | Median search time |\n|---|---|---|---|")
p, f, s = score()
print(f"| clean_v2 (no reranker) | {p}/{len(questions)} | {f:.0%} | {s:.2f}s |")
for name in MODELS:
    model = CrossEncoder(name)
    p, f, s = score(model)
    print(f"| + {name} | {p}/{len(questions)} | {f:.0%} | {s:.2f}s |")
