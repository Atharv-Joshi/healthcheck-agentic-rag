"""Chroma vector store + local embeddings (sentence-transformers, no API cost)."""
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_DIR = Path(os.getenv("CHROMA_DIR", Path(__file__).resolve().parents[2] / "chroma_db"))
COLLECTION = "healthcheck_docs"
EMBED_MODEL = "all-MiniLM-L6-v2"

_collection = None


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            COLLECTION, embedding_function=SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL),
            metadata={"hnsw:space": "cosine"})
    return _collection


def search(query: str, k: int = 4, category: str | None = None) -> list[dict]:
    where = {"category": category} if category else None
    res = get_collection().query(query_texts=[query], n_results=k, where=where)
    return [{"text": doc, "source": m["source"], "title": m["title"], "score": round(1 - d, 3)}
            for doc, m, d in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
