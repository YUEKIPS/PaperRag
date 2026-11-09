from __future__ import annotations

from pathlib import Path
from typing import Any

from src.rerank.cross_encoder import rerank_chunks
from src.retriever.baseline import RetrievedChunk, retrieve_baseline


def _rerank_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config.get("retriever", {}).get("reranker", {}) or {})


def retrieve_with_config(
    query: str,
    index_dir: Path,
    config: dict[str, Any],
    *,
    top_k: int | None = None,
    rerank_override: bool | None = None,
) -> list[RetrievedChunk]:
    """
    Hybrid/dense retrieval from M1, optional cross-encoder rerank (M2).
    When rerank is enabled, fetch `candidate_pool` hits then cut to top_k.
    """
    retr = config.get("retriever", {})
    final_k = top_k if top_k is not None else int(retr.get("top_k", 10))
    r_cfg = _rerank_cfg(config)
    enabled = bool(r_cfg.get("enabled", False))
    if rerank_override is not None:
        enabled = rerank_override

    candidate_k = int(r_cfg.get("candidate_pool", max(final_k * 3, final_k)))
    if enabled:
        hits = retrieve_baseline(query, index_dir, top_k=candidate_k)
        model_name = str(r_cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
        try:
            return rerank_chunks(query, hits, model_name=model_name, top_k=final_k)
        except Exception:
            # Smoke-friendly: fall back to retrieval order if rerank model fails to load
            return hits[:final_k]
    return retrieve_baseline(query, index_dir, top_k=final_k)
