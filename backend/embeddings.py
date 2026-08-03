import os
from pathlib import Path

import numpy as np

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError("sentence-transformers is required for embeddings") from exc
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts):
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings


def save_embeddings(path: Path, embeddings):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, embeddings)


def load_embeddings(path: Path):
    return np.load(path)


def cosine_similarity(matrix, vector):
    return np.dot(matrix, vector)
