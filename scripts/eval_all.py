#!/usr/bin/env python3
"""Batch eval: agentic graph over draft questions; artifacts under data/eval/runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src.eval.harness import run_agentic_eval, write_smoke_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run draft eval set through agentic pipeline.",
        epilog=(
            "M3: questions q006–q007 are weak-relevance drafts to exercise rewrite on stub path. "
            "Use --exercise-rewrite for stricter stub grade. LLM path: AGENT_GENERATOR=openai + API key."
        ),
    )
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    parser.add_argument("--limit", type=int, default=5, help="Max questions from eval JSON")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Disable rerank for this eval run",
    )
    parser.add_argument(
        "--exercise-rewrite",
        action="store_true",
        help="Stricter stub grade for all questions (rewrite-loop smoke)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "smoke_m3_llm_agentic.md",
        help="Markdown smoke report path",
    )
    parser.add_argument(
        "--ablation",
        type=str,
        default="",
        help="Optional qualitative ablation note appended to the report",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    rerank_override = False if args.no_rerank else None

    run_dir, runs, meta = run_agentic_eval(
        config,
        config_path=args.config,
        limit=args.limit,
        rerank_override=rerank_override,
        exercise_strict_grade=args.exercise_rewrite,
    )

    write_smoke_report(
        args.report,
        meta,
        runs,
        run_dir=run_dir,
        ablation_note=args.ablation,
        milestone="M3",
    )

    print(f"Wrote artifacts to {run_dir}", file=sys.stderr)
    print(f"Wrote report to {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
