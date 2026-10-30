"""Vector index on disk (D-005: LanceDB). One table per pipeline so layers can be compared side by side."""

import hashlib
from pathlib import Path

import lancedb

INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "index"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ChunkStore:
    def __init__(self, table_name: str, index_dir: Path = INDEX_DIR):
        index_dir.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(index_dir)
        self.table_name = table_name

    def _table(self):
        if self.table_name in self.db.list_tables().tables:
            return self.db.open_table(self.table_name)
        return None

    def drop(self) -> None:
        if self._table() is not None:
            self.db.drop_table(self.table_name)

    def indexed_hashes(self) -> dict[str, str]:
        """doc name -> file hash of the version currently indexed."""
        table = self._table()
        if table is None:
            return {}
        rows = table.search().select(["doc", "doc_hash"]).limit(None).to_list()
        return {row["doc"]: row["doc_hash"] for row in rows}

    def replace_doc(self, doc: str, rows: list[dict]) -> None:
        table = self._table()
        if table is None:
            self.db.create_table(self.table_name, data=rows)
            return
        table.delete(f"doc = '{doc.replace(chr(39), chr(39) * 2)}'")
        table.add(rows)

    def remove_doc(self, doc: str) -> None:
        table = self._table()
        if table is not None:
            table.delete(f"doc = '{doc.replace(chr(39), chr(39) * 2)}'")

    def remove_docs_not_in(self, docs: set[str]) -> list[str]:
        table = self._table()
        removed = sorted(set(self.indexed_hashes()) - docs)
        for doc in removed:
            table.delete(f"doc = '{doc.replace(chr(39), chr(39) * 2)}'")
        return removed

    def build_keyword_index(self) -> None:
        """Full-text index over passage text (stemmed, stop words removed) for keyword search."""
        self._table().create_fts_index("text", replace=True)

    def search(self, vector: list[float], k: int, docs: list[str] | None = None, text: str | None = None) -> list[dict]:
        """Nearest passages; with `docs`, only passages from those files (filtered before ranking).

        With `text`, hybrid search: meaning-based and keyword results fused by rank (reciprocal rank
        fusion). `_distance` is then set to minus the fused score, so lower is still better.
        """
        table = self._table()
        if table is None:
            raise RuntimeError(f"No index yet. Run `indexit index <folder>` first.")
        query = (table.search(query_type="hybrid").vector(vector).text(text) if text else table.search(vector)).metric("cosine")
        if docs:
            names = ", ".join("'" + d.replace("'", "''") + "'" for d in docs)
            query = query.where(f"doc IN ({names})", prefilter=True)
        results = query.limit(k).to_list()
        if text:
            for row in results:
                row["_distance"] = -row["_relevance_score"]
        return results
