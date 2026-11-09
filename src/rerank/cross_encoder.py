from __future__ import annotations

from typing import Any

from src.retriever.baseline import RetrievedChunk

_MODEL_CACHE: dict[str, Any] = {}


def load_cross_encoder(model_name: str) -> Any:
    from sentence_transformers import CrossEncoder

    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = CrossEncoder(model_name)
    return _MODEL_CACHE[model_name]


def rerank_chunks(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    model_name: str,
    top_k: int,
) -> list[RetrievedChunk]:
    """Re-score candidates with a cross-encoder; return top_k by rerank score."""
    if not chunks:
        return []
    if len(chunks) <= top_k:
        top_k = len(chunks)

    model = load_cross_encoder(model_name)
    pairs = [(query, ch.text[:2000]) for ch in chunks]
    scores = model.predict(pairs)
    ranked = sorted(
        zip(chunks, scores, strict=True),
        key=lambda x: float(x[1]),
        reverse=True,
    )
    out: list[RetrievedChunk] = []
    for ch, score in ranked[:top_k]:
        out.append(
            RetrievedChunk(
                paper_id=ch.paper_id,
                page_number=ch.page_number,
                chunk_id=ch.chunk_id,
                text=ch.text,
                score=float(score),
            )
        )
    return out
