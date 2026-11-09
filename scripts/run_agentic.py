#!/usr/bin/env python3
"""LangGraph agentic pipeline: decide → retrieve → grade → rewrite → generate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.agent.run import run_agentic_query  # noqa: E402
from src.config import load_config, resolve_path  # noqa: E402
from src.generate.llm import generator_mode  # noqa: E402
from src.retriever.pipeline import _rerank_cfg  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic RAG (LangGraph) smoke run.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    parser.add_argument("--query", type=str, required=True, help="User question")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable cross-encoder rerank for this run (ablation)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable result on stdout",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    index_dir = resolve_path(config, "index")
    manifest = index_dir / "manifest.json"
    if not manifest.exists():
        print(f"Missing index at {index_dir}. Run build_index.py first.", file=sys.stderr)
        return 1

    rerank_cfg = _rerank_cfg(config)
    rerank_default = bool(rerank_cfg.get("enabled", False))
    rerank_enabled = False if args.no_rerank else rerank_default

    print(
        f"Agent generator: {generator_mode(agent=True)}; rerank: {rerank_enabled}",
        file=sys.stderr,
    )

    result = run_agentic_query(
        args.query,
        index_dir,
        config,
        rerank_enabled=rerank_enabled,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "query": result.query,
                    "working_query": result.working_query,
                    "grade_passed": result.grade_passed,
                    "grade_reason": result.grade_reason,
                    "iterations": result.iterations,
                    "generator": result.generator,
                    "num_chunks": result.num_chunks,
                    "citations": result.citations,
                    "answer": result.answer,
                    "trace": result.trace,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("=" * 60)
        print(f"Query: {result.query}")
        print(f"Working query: {result.working_query}")
        print(f"Grade: passed={result.grade_passed} ({result.grade_reason})")
        print(f"Rewrite iterations: {result.iterations}")
        print(f"Chunks: {result.num_chunks}, generator={result.generator}")
        print(result.answer)
        print("Citations:", json.dumps(result.citations, ensure_ascii=False, indent=2))
        print("Trace:", json.dumps(result.trace, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
