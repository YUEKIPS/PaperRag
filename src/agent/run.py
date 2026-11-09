from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.agent.graph import build_agent_graph
from src.agent.history import select_history
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
    history_included_turns: int
    history_omitted_turns: int
    history_policy: str
    history_truncated_answers: int


def run_agentic_query(
    query: str,
    index_dir: Path,
    config: dict[str, Any],
    *,
    rerank_enabled: bool | None = None,
    exercise_strict_grade: bool = False,
    conversation: list[dict[str, Any]] | None = None,
) -> AgenticResult:
    agent_cfg = config.get("agent", {})
    max_loops = int(agent_cfg.get("max_grade_rewrite_loops", 2))
    history = select_history(conversation, config=config)

    initial: AgentState = {
        "query": query,
        "index_dir": str(index_dir),
        "config": config,
        "max_loops": max_loops,
        "iterations": 0,
        "trace": [],
        "conversation": [
            {"question": turn.question, "answer": turn.answer} for turn in history.turns
        ],
        "history_included_turns": history.included_turns,
        "history_omitted_turns": history.omitted_turns,
        "history_policy": history.policy,
        "history_truncated_answers": history.truncated_answers,
    }
    if rerank_enabled is not None:
        initial["rerank_enabled"] = rerank_enabled
    if exercise_strict_grade:
        initial["exercise_strict_grade"] = True

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
        history_included_turns=int(final.get("history_included_turns") or 0),
        history_omitted_turns=int(final.get("history_omitted_turns") or 0),
        history_policy=str(final.get("history_policy") or ""),
        history_truncated_answers=int(final.get("history_truncated_answers") or 0),
    )
