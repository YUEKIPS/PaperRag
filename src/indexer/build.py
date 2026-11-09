from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import faiss

from src.indexer.embed import embed_texts, load_embedding_model


def _load_chunk_records(processed_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for cp in sorted(processed_dir.glob("*.chunks.jsonl")):
        with cp.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def _default_embedding_model(config: dict[str, Any] | None) -> str:
    idx = (config or {}).get("index", {})
    return str(
        idx.get("embedding_model") or "sentence-transformers/all-MiniLM-L6-v2"
    )


def _tokenize_for_bm25(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 1]


def build_index_from_processed(
    processed_dir: Path,
    index_dir: Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Build dense FAISS index (+ optional BM25 sidecar) from chunked JSONL."""
    index_dir.mkdir(parents=True, exist_ok=True)
    records = _load_chunk_records(processed_dir)
    if not records:
        raise ValueError(f"No chunk records under {processed_dir}")

    embedding_model = _default_embedding_model(config)
    hybrid_enabled = bool(
        (config or {}).get("index", {}).get("hybrid", {}).get("enabled", False)
    )
    batch_size = int((config or {}).get("index", {}).get("embed_batch_size", 32))

    model = load_embedding_model(embedding_model)
    texts = [str(r.get("text", "")) for r in records]
    vectors = embed_texts(model, texts, batch_size=batch_size)
    if vectors.shape[0] != len(records):
        raise RuntimeError("Embedding count mismatch with chunk records")

    dim = int(vectors.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    faiss_path = index_dir / "faiss.index"
    faiss.write_index(index, str(faiss_path))

    index_path = index_dir / "chunks_index.jsonl"
    with index_path.open("w", encoding="utf-8") as out:
        for rec in records:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    bm25_path: Path | None = None
    if hybrid_enabled:
        try:
            from rank_bm25 import BM25Okapi

            corpus_tokens = [_tokenize_for_bm25(t) for t in texts]
            bm25 = BM25Okapi(corpus_tokens)
            bm25_path = index_dir / "bm25_corpus.json"
            bm25_path.write_text(
                json.dumps(
                    {
                        "type": "bm25_token_lists",
                        "num_docs": len(corpus_tokens),
                        "tokenized_docs": corpus_tokens,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            _ = bm25  # built at retrieval time from sidecar
        except ImportError:
            hybrid_enabled = False

    chunk_files = [p.name for p in sorted(processed_dir.glob("*.chunks.jsonl"))]
    manifest: dict[str, Any] = {
        "type": "faiss_dense",
        "status": "m1_baseline",
        "chunk_files": chunk_files,
        "num_chunks": len(records),
        "embedding_model": embedding_model,
        "embedding_dim": dim,
        "faiss_index": faiss_path.name,
        "chunks_index": index_path.name,
        "hybrid_enabled": hybrid_enabled,
        "bm25_corpus": bm25_path.name if bm25_path else None,
        "faiss_metric": "inner_product_on_l2_normalized",
    }

    manifest_path = index_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest_path


def load_index_manifest(index_dir: Path) -> dict[str, Any]:
    path = index_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No index manifest at {path}. Run scripts/build_index.py first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_chunk_records(index_dir: Path) -> list[dict[str, Any]]:
    manifest = load_index_manifest(index_dir)
    chunks_name = manifest.get("chunks_index", "chunks_index.jsonl")
    index_path = index_dir / chunks_name
    records: list[dict[str, Any]] = []
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_faiss_index(index_dir: Path) -> faiss.Index:
    manifest = load_index_manifest(index_dir)
    faiss_name = manifest.get("faiss_index", "faiss.index")
    path = index_dir / faiss_name
    if not path.exists():
        raise FileNotFoundError(f"Missing FAISS index at {path}")
    return faiss.read_index(str(path))


def load_bm25_corpus(index_dir: Path) -> list[list[str]] | None:
    manifest = load_index_manifest(index_dir)
    if not manifest.get("hybrid_enabled"):
        return None
    bm25_name = manifest.get("bm25_corpus")
    if not bm25_name:
        return None
    path = index_dir / bm25_name
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("tokenized_docs", [])
