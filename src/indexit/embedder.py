"""Local embedding model (D-004): turns text into vectors for meaning-based search.

Free and on-device. Swap MODEL_NAME to try a different model; re-index afterwards,
because vectors from different models aren't comparable.
"""

import threading

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # ~130 MB, 384-dim vectors, strong for its size
# bge models search better when the *question* (not the passages) carries this prefix.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()  # warm_up() may be loading the model while a search waits for it

    def _get_model(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer  # slow import (~5 s); load only when used

                try:  # use the downloaded copy; skips network checks that slow every start
                    self._model = SentenceTransformer(self.model_name, local_files_only=True)
                except OSError:  # first run: download (~130 MB)
                    self._model = SentenceTransformer(self.model_name)
            return self._model

    def warm_up(self) -> None:
        """Load the model in the background so the first search doesn't pay the load time."""
        threading.Thread(target=self._get_model, daemon=True).start()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._get_model().encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32).tolist()

    def embed_query(self, question: str) -> list[float]:
        return self._get_model().encode(QUERY_PREFIX + question, normalize_embeddings=True).tolist()
