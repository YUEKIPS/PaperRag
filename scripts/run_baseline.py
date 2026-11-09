#!/usr/bin/env python3
"""Run non-agentic baseline: retrieve + stub generate for one query or eval file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config, resolve_path  # noqa: E402
from src.generate.baseline import generate_baseline_answer  # noqa: E402
from src.retriever.pipeline import _rerank_cfg, retrieve_with_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Baseline RAG smoke test.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    parser.add_argument("--query", type=str, help="Single query string")
    parser.add_argument(
        "--eval-file",
        type=Path,
        help="Run first N questions from eval JSON (default: config paths.eval_questions)",
    )
    parser.add_argument("--limit", type=int, default=1, help="Max questions when using --eval-file")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable cross-encoder rerank (ablation)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    index_dir = resolve_path(config, "index")
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"Missing index manifest at {manifest_path}. Run build_index.py first.", file=sys.stderr)
        return 1

    top_k = int(
        config.get("baseline", {}).get(
            "max_context_chunks", config.get("retriever", {}).get("top_k", 5)
        )
    )

    queries: list[str] = []
    if args.query:
        queries = [args.query]
    else:
        eval_path = args.eval_file or resolve_path(config, "eval_questions")
        data = json.loads(eval_path.read_text(encoding="utf-8"))
        for q in data.get("questions", [])[: args.limit]:
            queries.append(q["text"])

    if not queries:
        print("Provide --query or a valid eval file.", file=sys.stderr)
        return 1

    gen_mode = os.environ.get("BASELINE_GENERATOR", "stub")
    print(f"Generator mode: {gen_mode}", file=sys.stderr)

    rerank_default = bool(_rerank_cfg(config).get("enabled", False))
    rerank_enabled = False if args.no_rerank else rerank_default

    for q in queries:
        chunks = retrieve_with_config(q, index_dir, config, top_k=top_k, rerank_override=rerank_enabled)
        answer = generate_baseline_answer(q, chunks)
        print("=" * 60)
        print(f"Query: {q}")
        print(
            f"Retriever: top_k={top_k}, rerank={rerank_enabled}, "
            f"hits={len(chunks)}, generator={answer.generator}"
        )
        print(answer.answer)
        print("Citations:", json.dumps(answer.citations, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
