"""Chroma vector store + local embeddings (sentence-transformers, no API cost)."""
import logging
import threading

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.config import get_settings

log = logging.getLogger(__name__)

COLLECTION = "healthcheck_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

_lock = threading.Lock()
_collection = None


def get_collection():
    """Lazily create the collection once; safe under concurrent first requests."""
    global _collection
    with _lock:
        if _collection is None:
            client = chromadb.PersistentClient(path=str(get_settings().chroma_dir))
            _collection = client.get_or_create_collection(
                COLLECTION, embedding_function=SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL),
                metadata={"hnsw:space": "cosine"})
        return _collection


def reset() -> None:
    global _collection
    with _lock:
        _collection = None


def warm_up() -> None:
    """Load the embedding model and open the index at startup, not on the first user's request."""
    n = get_collection().count()
    get_collection().query(query_texts=["warm up"], n_results=1) if n else None
    log.info("vector store ready: %d chunks", n)


def search(query: str, k: int = 4, category: str | None = None, min_score: float | None = None) -> list[dict]:
    """Top-k passages by cosine similarity, dropping anything below the relevance threshold."""
    threshold = get_settings().min_doc_score if min_score is None else min_score
    where = {"category": category} if category else None
    res = get_collection().query(query_texts=[query], n_results=k, where=where)
    hits = [{"text": doc, "source": m["source"], "title": m["title"], "score": round(1 - d, 3)}
            for doc, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
    kept = [h for h in hits if h["score"] >= threshold]
    log.info("search q=%r kept=%d/%d best=%.2f", query, len(kept), len(hits), hits[0]["score"] if hits else 0)
    return kept
