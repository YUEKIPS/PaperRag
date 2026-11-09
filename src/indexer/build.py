from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_index_from_processed(
    processed_dir: Path,
    index_dir: Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Write a minimal JSON-lines index (BM25 / embeddings deferred to M1+).

    Reads ``*.chunks.jsonl`` files produced by ingest.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "type": "scaffold_jsonl",
        "status": "baseline_only",
        "chunk_files": [],
        "embedding_model": None,
        "hybrid_enabled": (config or {}).get("index", {}).get("hybrid", {}).get(
            "enabled", False
        ),
    }

    chunk_paths = sorted(processed_dir.glob("*.chunks.jsonl"))
    records: list[dict[str, Any]] = []
    for cp in chunk_paths:
        manifest["chunk_files"].append(cp.name)
        with cp.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    index_path = index_dir / "chunks_index.jsonl"
    with index_path.open("w", encoding="utf-8") as out:
        for rec in records:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest_path = index_dir / "manifest.json"
    manifest["num_chunks"] = len(records)
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
