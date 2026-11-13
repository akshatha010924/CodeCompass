"""Vector store: ChromaDB when available, numpy in-memory fallback (cosine similarity)."""
import numpy as np
from . import config


class MemoryStore:
    backend = "memory"

    def __init__(self):
        self.data = {}

    def index(self, repo_id, chunks, vectors):
        self.data[repo_id] = (np.asarray(vectors), chunks)

    def query(self, repo_id, vector, k):
        if repo_id not in self.data:
            return []
        mat, chunks = self.data[repo_id]
        sims = mat @ np.asarray(vector)
        return [{**chunks[i], "score": float(sims[i])} for i in np.argsort(-sims)[:k]]


class ChromaStore:
    backend = "chroma"

    def __init__(self):
        import chromadb
        self.client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

    def index(self, repo_id, chunks, vectors):
        name = f"repo_{repo_id}"
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        col = self.client.create_collection(name, metadata={"hnsw:space": "cosine"})
        for i in range(0, len(chunks), 200):
            part = chunks[i:i + 200]
            col.add(ids=[c["id"] for c in part], documents=[c["text"] for c in part],
                    embeddings=[list(map(float, v)) for v in vectors[i:i + 200]],
                    metadatas=[{"path": c["path"], "start": c["start"], "end": c["end"],
                                "symbol": c["symbol"], "language": c["language"]} for c in part])

    def query(self, repo_id, vector, k):
        try:
            col = self.client.get_collection(f"repo_{repo_id}")
        except Exception:
            return []
        r = col.query(query_embeddings=[list(map(float, vector))], n_results=k)
        return [{"id": r["ids"][0][i], "text": r["documents"][0][i], **r["metadatas"][0][i],
                 "score": 1 - r["distances"][0][i]} for i in range(len(r["ids"][0]))]


_store = None


def get_store():
    global _store
    if _store is None:
        if config.VECTOR_BACKEND in ("auto", "chroma"):
            try:
                _store = ChromaStore()
            except Exception:
                if config.VECTOR_BACKEND == "chroma":
                    raise
        _store = _store or MemoryStore()
    return _store
