from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.agent.graph import build_agent_graph
from src.agent.state import AgentState


@dataclass
class AgenticResult:
    query: str
    working_query: str
    answer: str
    citations: list[dict[str, str | int]]
    generator: str
    grade_passed: bool
    grade_reason: str
    iterations: int
    trace: list[dict[str, Any]]
    num_chunks: int


def run_agentic_query(
    query: str,
    index_dir: Path,
    config: dict[str, Any],
    *,
    rerank_enabled: bool | None = None,
) -> AgenticResult:
    agent_cfg = config.get("agent", {})
    max_loops = int(agent_cfg.get("max_grade_rewrite_loops", 2))

    initial: AgentState = {
        "query": query,
        "index_dir": str(index_dir),
        "config": config,
        "max_loops": max_loops,
        "iterations": 0,
        "trace": [],
    }
    if rerank_enabled is not None:
        initial["rerank_enabled"] = rerank_enabled

    app = build_agent_graph()
    final = app.invoke(initial)

    chunks = final.get("chunks") or []
    return AgenticResult(
        query=query,
        working_query=str(final.get("working_query") or query),
        answer=str(final.get("answer") or ""),
        citations=list(final.get("citations") or []),
        generator=str(final.get("generator") or "stub"),
        grade_passed=bool(final.get("grade_passed")),
        grade_reason=str(final.get("grade_reason") or ""),
        iterations=int(final.get("iterations") or 0),
        trace=list(final.get("trace") or []),
        num_chunks=len(chunks),
    )
