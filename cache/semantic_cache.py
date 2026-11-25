"""
cache/semantic_cache.py — In-memory cosine similarity cache using BGE-small
"""
import numpy as np
from typing import Optional


class SemanticCache:
    def __init__(self, threshold: float = 0.92):
        self.threshold = threshold
        self._store: list[dict] = []  # {embedding, question, response}
        self._model = None

    def _embed(self, text: str) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return self._model.encode(text, normalize_embeddings=True)

    def get(self, question: str) -> Optional[str]:
        if not self._store:
            return None
        emb = self._embed(question)
        for entry in self._store:
            sim = float(np.dot(emb, entry["embedding"]))
            if sim >= self.threshold:
                return entry["response"]
        return None

    def put(self, question: str, response: str) -> None:
        emb = self._embed(question)
        self._store.append({
            "embedding": emb,
            "question": question,
            "response": response,
        })

    def size(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
