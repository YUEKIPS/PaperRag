from __future__ import annotations

from typing import Any

import numpy as np

_MODEL_CACHE: dict[str, Any] = {}


def load_embedding_model(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def embed_texts(model: Any, texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Return float32 matrix (n, dim) with L2-normalized rows for cosine / inner product."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 64,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(vectors, dtype=np.float32)
