from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.indexer.build import (
    load_bm25_corpus,
    load_chunk_records,
    load_faiss_index,
    load_index_manifest,
)
from src.indexer.embed import embed_texts, load_embedding_model


@dataclass
class RetrievedChunk:
    paper_id: str
    page_number: int
    chunk_id: str
    text: str
    score: float


_RRF_K = 60


def _record_to_chunk(rec: dict[str, Any], score: float) -> RetrievedChunk:
    return RetrievedChunk(
        paper_id=str(rec["paper_id"]),
        page_number=int(rec["page_number"]),
        chunk_id=str(rec["chunk_id"]),
        text=str(rec.get("text", "")),
        score=float(score),
    )


def _tokenize_query(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 1]


def _retrieve_dense(
    query: str,
    index_dir: Path,
    top_k: int,
    records: list[dict[str, Any]],
) -> list[RetrievedChunk]:
    manifest = load_index_manifest(index_dir)
    model_name = str(manifest["embedding_model"])
    model = load_embedding_model(model_name)
    index = load_faiss_index(index_dir)

    q_vec = embed_texts(model, [query])
    scores, ids = index.search(q_vec, min(top_k, len(records)))
    out: list[RetrievedChunk] = []
    for rank, (idx, score) in enumerate(zip(ids[0], scores[0], strict=True)):
        if idx < 0:
            continue
        out.append(_record_to_chunk(records[int(idx)], float(score)))
    return out


def _retrieve_bm25(
    query: str,
    tokenized_docs: list[list[str]],
    records: list[dict[str, Any]],
    top_k: int,
) -> list[tuple[int, float]]:
    from rank_bm25 import BM25Okapi

    bm25 = BM25Okapi(tokenized_docs)
    q_tokens = _tokenize_query(query)
    if not q_tokens:
        return []
    scores = bm25.get_scores(q_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(i, float(s)) for i, s in ranked[:top_k] if s > 0]


def _rrf_fuse(
    dense_hits: list[RetrievedChunk],
    dense_ids: list[int],
    sparse_hits: list[tuple[int, float]],
    records: list[dict[str, Any]],
    top_k: int,
) -> list[RetrievedChunk]:
    fused: dict[int, float] = {}
    for rank, chunk in enumerate(dense_hits):
        idx = dense_ids[rank]
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)
    for rank, (idx, _score) in enumerate(sparse_hits):
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (_RRF_K + rank + 1)

    ordered = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [_record_to_chunk(records[idx], score) for idx, score in ordered]


def retrieve_baseline(
    query: str,
    index_dir: Path,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Dense FAISS retrieval; optional BM25 + RRF when manifest has hybrid_enabled.
    """
    records = load_chunk_records(index_dir)
    if not records:
        return []

    manifest = load_index_manifest(index_dir)
    idx_type = manifest.get("type", "scaffold_jsonl")

    # Legacy keyword path (pre-M1 manifests)
    if idx_type == "scaffold_jsonl":
        return _retrieve_keyword_legacy(query, index_dir / "chunks_index.jsonl", top_k)

    dense = _retrieve_dense(query, index_dir, top_k, records)
    if not manifest.get("hybrid_enabled"):
        return dense

    tokenized = load_bm25_corpus(index_dir)
    if not tokenized:
        return dense

    pool = max(top_k * 3, top_k)
    model = load_embedding_model(str(manifest["embedding_model"]))
    index = load_faiss_index(index_dir)
    q_vec = embed_texts(model, [query])
    scores, ids = index.search(q_vec, min(pool, len(records)))
    dense_ids = [int(i) for i in ids[0] if i >= 0]
    dense_hits = [
        _record_to_chunk(records[i], float(s))
        for i, s in zip(ids[0], scores[0], strict=True)
        if i >= 0
    ]
    sparse = _retrieve_bm25(query, tokenized, records, pool)
    return _rrf_fuse(dense_hits, dense_ids, sparse, records, top_k)


def _retrieve_keyword_legacy(
    query: str,
    index_path: Path,
    top_k: int,
) -> list[RetrievedChunk]:
    """M0 keyword overlap fallback when only JSONL scaffold index exists."""
    import json

    if not index_path.exists():
        return []

    tokens = {t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 2}
    scored: list[RetrievedChunk] = []

    with index_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            text = rec.get("text", "")
            text_tokens = set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
            overlap = len(tokens & text_tokens)
            if overlap == 0:
                continue
            scored.append(_record_to_chunk(rec, float(overlap)))

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]
