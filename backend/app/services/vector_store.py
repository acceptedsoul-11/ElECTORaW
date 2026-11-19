from __future__ import annotations

from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import HashingVectorizer


class LocalHashEmbeddingFunction:
    """Deterministic local embedding function for ChromaDB.

    It produces fixed-size dense vectors without an external model download.
    ChromaDB persists and searches the vectors; there is deliberately no
    second retrieval backend in the runtime.
    """

    def __init__(self, n_features: int = 384) -> None:
        self.n_features = n_features
        self.vectorizer = HashingVectorizer(n_features=n_features, alternate_sign=False, norm="l2", ngram_range=(1, 2), lowercase=True)

    def __call__(self, input: list[str]) -> list[list[float]]:
        matrix = self.vectorizer.transform(input)
        return matrix.toarray().tolist()

    # ChromaDB 1.x calls these explicit methods for document and query
    # embeddings. Keep __call__ above for compatibility with older clients.
    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_query(self, input: str | list[str]) -> list[float] | list[list[float]]:
        values = [input] if isinstance(input, str) else input
        embeddings = self(values)
        return embeddings[0] if isinstance(input, str) else embeddings

    @staticmethod
    def name() -> str:
        return "local_hash_v1"

    def get_config(self) -> dict[str, Any]:
        return {"n_features": self.n_features}

    def is_legacy(self) -> bool:
        return False

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "LocalHashEmbeddingFunction":
        return LocalHashEmbeddingFunction(int(config.get("n_features", 384)))


class LocalVectorStore:
    def __init__(self, path: Path, collection_name: str = "electoraw_corpus") -> None:
        self.path = path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.error: str | None = None
        try:
            import chromadb
            self.path.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.path))
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "embedding_model": "local_hash_v1"},
                embedding_function=LocalHashEmbeddingFunction(),
            )
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            raise RuntimeError(
                "ChromaDB is required for ELECTORaW RAG and could not be opened: "
                f"{self.error}"
            ) from exc

    @property
    def available(self) -> bool:
        return True

    @property
    def count(self) -> int:
        return int(self.collection.count())

    def upsert(self, chunks: list[Any]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[{"title": chunk.title, "locator": chunk.locator, "source_type": chunk.source_type, "year": chunk.year if chunk.year is not None else -1} for chunk in chunks],
        )

    def query(self, question: str, chunks_by_id: dict[str, Any], year: int | None = None, top_k: int = 5) -> list[tuple[Any, float]]:
        result = self.collection.query(
            query_texts=[question],
            n_results=min(max(top_k * 3, top_k), max(self.count, 1)),
            include=["distances", "metadatas"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        matches: list[tuple[Any, float]] = []
        for index, chunk_id in enumerate(ids):
            chunk = chunks_by_id.get(chunk_id)
            metadata = metadatas[index] if index < len(metadatas) else {}
            chunk_year = metadata.get("year", -1) if metadata else -1
            if chunk is None or (year is not None and chunk_year not in (year, -1)):
                continue
            distance = float(distances[index]) if index < len(distances) else 1.0
            matches.append((chunk, max(0.0, 1.0 - distance)))
        return matches[:top_k]
