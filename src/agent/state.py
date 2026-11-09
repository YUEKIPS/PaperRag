from __future__ import annotations

from typing import Any, TypedDict

from src.retriever.baseline import RetrievedChunk


class AgentState(TypedDict, total=False):
    query: str
    working_query: str
    index_dir: str
    config: dict[str, Any]
    chunks: list[RetrievedChunk]
    grade_passed: bool
    grade_reason: str
    answer: str
    citations: list[dict[str, str | int]]
    generator: str
    iterations: int
    max_loops: int
    trace: list[dict[str, Any]]
    rerank_enabled: bool
    # When true, stub grade uses stricter token overlap (rewrite-loop smoke without API).
    exercise_strict_grade: bool
    # Selected prior turns only ({question, answer}). Not evidence for this turn.
    conversation: list[dict[str, str]]
    history_included_turns: int
    history_omitted_turns: int
    history_policy: str
    history_truncated_answers: int
