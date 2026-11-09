#!/usr/bin/env python3
"""Build minimal JSONL index from processed chunks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config, resolve_path  # noqa: E402
from src.indexer.build import build_index_from_processed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build retrieval index (scaffold).")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    processed_dir = resolve_path(config, "processed")
    index_dir = resolve_path(config, "index")

    if not any(processed_dir.glob("*.chunks.jsonl")):
        print(f"No chunk files in {processed_dir}. Run scripts/ingest.py first.", file=sys.stderr)
        return 1

    manifest_path = build_index_from_processed(processed_dir, index_dir, config)
    print(f"Index written. manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
