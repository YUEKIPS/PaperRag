#!/usr/bin/env python3
"""Run non-agentic baseline: retrieve + stub generate for one query or eval file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config, resolve_path  # noqa: E402
from src.generate.baseline import generate_baseline_answer  # noqa: E402
from src.retriever.baseline import retrieve_baseline  # noqa: E402


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
    args = parser.parse_args()

    config = load_config(args.config)
    index_dir = resolve_path(config, "index")
    index_path = index_dir / "chunks_index.jsonl"
    if not index_path.exists():
        print(f"Missing index at {index_path}. Run build_index.py first.", file=sys.stderr)
        return 1

    top_k = int(config.get("baseline", {}).get("max_context_chunks", 5))

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

    for q in queries:
        chunks = retrieve_baseline(q, index_path, top_k=top_k)
        answer = generate_baseline_answer(q, chunks)
        print("=" * 60)
        print(answer.answer)
        print("Citations:", json.dumps(answer.citations, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
