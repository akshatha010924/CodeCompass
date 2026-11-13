"""Embeddings: Sentence Transformers when available, hashing fallback otherwise."""
import hashlib, re
import numpy as np
from . import config


class HashEmbedder:
    """Deterministic bag-of-tokens embedding. Lexical only - a dependency-free fallback."""
    name, dim = "hashing-fallback", 384

    def encode(self, texts):
        out = np.zeros((len(texts), self.dim), dtype="float32")
        for i, t in enumerate(texts):
            for tok in re.findall(r"[A-Za-z]+|\d+", re.sub(r"([a-z])([A-Z])", r"\1 \2", t).lower()):
                out[i, int(hashlib.md5(tok.encode()).hexdigest(), 16) % self.dim] += 1.0
            out[i] /= np.linalg.norm(out[i]) or 1.0
        return out


class STEmbedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model, self.name = SentenceTransformer(config.EMBED_MODEL), config.EMBED_MODEL

    def encode(self, texts):
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        if config.EMBED_BACKEND in ("auto", "sentence-transformers"):
            try:
                _embedder = STEmbedder()
            except Exception:
                if config.EMBED_BACKEND != "auto":
                    raise
        _embedder = _embedder or HashEmbedder()
    return _embedder
