from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from src.agent.history import (
    contextualize_query,
    format_history_block,
    history_turns_from_state,
)
from src.agent.state import AgentState
from src.generate.baseline import generate_baseline_answer
from src.generate.llm import generator_mode, try_openai_chat
from src.generate.prompts import load_prompt
from src.retriever.pipeline import retrieve_with_config


def _append_trace(state: AgentState, event: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    trace = list(state.get("trace") or [])
    trace.append({"event": event, **detail})
    return trace


def decide_node(state: AgentState) -> dict[str, Any]:
    """Set the search query. Follow-ups are rewritten into a standalone working_query.

    Routing stays a passthrough. History is used only for coreference; it is not
    retrieved as evidence. The grade-failure rewrite node still runs later.
    """
    query = state["query"]
    turns = history_turns_from_state(state)
    resolved = contextualize_query(query, turns, config=state.get("config") or {})
    return {
        "working_query": resolved.working_query,
        "iterations": int(state.get("iterations") or 0),
        "trace": _append_trace(
            state,
            "decide",
            {
                "working_query": resolved.working_query,
                "contextualized": resolved.changed,
                "contextualize_backend": resolved.backend,
                "llm_fallback": resolved.llm_fallback,
                "history_included_turns": int(state.get("history_included_turns") or 0),
                "history_omitted_turns": int(state.get("history_omitted_turns") or 0),
                "history_policy": state.get("history_policy") or "",
            },
        ),
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Retrieve from the working query only. Prior answers and citations are not hits."""
    config = state["config"]
    index_dir = Path(state["index_dir"])
    q = state.get("working_query") or state["query"]
    rerank_override = state.get("rerank_enabled")
    chunks = retrieve_with_config(
        q,
        index_dir,
        config,
        rerank_override=rerank_override if rerank_override is not None else None,
    )
    agent_cfg = config.get("agent", {})
    max_ctx = int(agent_cfg.get("max_context_chunks", config.get("retriever", {}).get("top_k", 10)))
    chunks = chunks[:max_ctx]
    return {
        "chunks": chunks,
        "trace": _append_trace(
            state,
            "retrieve",
            {
                "working_query": q,
                "num_chunks": len(chunks),
                "top_paper_ids": [c.paper_id for c in chunks[:3]],
            },
        ),
    }


def _query_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(t) > 2}


def _stub_grade_strict(state: AgentState) -> bool:
    if state.get("exercise_strict_grade"):
        return True
    env = os.environ.get("AGENT_STUB_STRICT_GRADE", "").strip().lower()
    return env in ("1", "true", "yes")


def _stub_grade(query: str, chunks: list[Any], *, strict: bool = False) -> tuple[bool, str]:
    if not chunks:
        return False, "no_chunks"
    q_tokens = _query_tokens(query)
    if not q_tokens:
        return True, "empty_query_tokens"

    chunk_union: set[str] = set()
    for ch in chunks[:5]:
        chunk_union |= _query_tokens(ch.text)
    coverage = len(q_tokens & chunk_union) / max(len(q_tokens), 1)
    min_coverage = 0.55 if strict else 0.35
    if coverage < min_coverage:
        reason = f"stub_token_coverage_low coverage={coverage:.2f}"
        if strict:
            reason += " (strict mode)"
        return False, reason

    matched = 0
    min_overlap = 3 if strict else 2
    need_matched = 3 if strict else 1
    for ch in chunks[:5]:
        overlap = len(q_tokens & _query_tokens(ch.text))
        if overlap >= min_overlap:
            matched += 1
    if matched >= need_matched:
        label = "stub_overlap_ok"
        if strict:
            label += "_strict"
        return True, f"{label} matched_chunks={matched} coverage={coverage:.2f}"
    reason = "stub_overlap_low"
    if strict:
        reason += " (strict mode)"
    return False, reason


def _parse_grade_json(text: str) -> tuple[bool, str]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    data = json.loads(cleaned.strip())
    return bool(data.get("passed")), str(data.get("reason", ""))


def _llm_grade(
    query: str,
    chunks: list[Any],
    config: dict[str, Any],
) -> tuple[bool | None, str | None, str | None]:
    """Returns (passed, reason, error)."""
    excerpts = []
    for i, ch in enumerate(chunks[:5], start=1):
        excerpts.append(
            f"({i}) [{ch.paper_id} p.{ch.page_number}] {ch.text[:600].replace(chr(10), ' ')}"
        )
    context = "\n".join(excerpts) or "(no context)"
    system = load_prompt("grade_system")
    user = f"Question: {query}\n\nExcerpts:\n{context}"
    text, err = try_openai_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        config=config,
        agent=True,
    )
    if err:
        return None, None, err
    if text is None:
        return None, None, None
    try:
        passed, reason = _parse_grade_json(text)
        return passed, reason, None
    except json.JSONDecodeError:
        return None, None, "grade_json_parse_error"


def grade_node(state: AgentState) -> dict[str, Any]:
    query = state.get("working_query") or state["query"]
    chunks = state.get("chunks") or []
    config = state.get("config") or {}
    strict = _stub_grade_strict(state)
    passed, reason = _stub_grade(query, chunks, strict=strict)
    grade_backend = "stub"
    llm_fallback: str | None = None

    if generator_mode(agent=True) == "openai":
        llm_pass, llm_reason, llm_err = _llm_grade(query, chunks, config)
        if llm_pass is not None:
            passed, reason = llm_pass, f"llm: {llm_reason}"
            grade_backend = "llm"
        elif llm_err:
            llm_fallback = llm_err
            reason = f"stub ({reason}); llm_fallback: {llm_err}"

    return {
        "grade_passed": passed,
        "grade_reason": reason,
        "trace": _append_trace(
            state,
            "grade",
            {
                "passed": passed,
                "reason": reason,
                "num_chunks": len(chunks),
                "backend": grade_backend,
                "strict_stub": strict,
                "llm_fallback": llm_fallback,
            },
        ),
    }


def _stub_rewrite(query: str, reason: str) -> str:
    extra = "retrieval augmented generation LLM agents"
    if "overlap" in reason or "no_chunks" in reason:
        return f"{query} ({extra})"
    return f"{query} — explain with definitions from the cited papers"


def _llm_rewrite(
    query: str,
    reason: str,
    config: dict[str, Any],
    history_block: str | None = None,
) -> tuple[str | None, str | None]:
    system = load_prompt("rewrite_system")
    parts: list[str] = []
    if history_block:
        parts.append(history_block)
        parts.append(
            "Use the conversation only to keep entities that are already resolved. "
            "Do not treat it as evidence and do not answer."
        )
    parts.append(f"Current query: {query}")
    parts.append(f"Grade feedback: {reason}")
    user = "\n\n".join(parts)
    return try_openai_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        config=config,
        agent=True,
    )


def rewrite_node(state: AgentState) -> dict[str, Any]:
    query = state.get("working_query") or state["query"]
    reason = state.get("grade_reason") or ""
    config = state.get("config") or {}
    history_block = format_history_block(history_turns_from_state(state))
    new_q = _stub_rewrite(query, reason)
    rewrite_backend = "stub"
    llm_fallback: str | None = None

    if generator_mode(agent=True) == "openai":
        llm_q, err = _llm_rewrite(query, reason, config, history_block or None)
        if llm_q and not err:
            new_q = llm_q.strip()
            rewrite_backend = "llm"
        elif err:
            llm_fallback = err

    iterations = int(state.get("iterations") or 0) + 1
    return {
        "working_query": new_q,
        "iterations": iterations,
        "trace": _append_trace(
            state,
            "rewrite",
            {
                "from": query,
                "to": new_q,
                "iteration": iterations,
                "backend": rewrite_backend,
                "llm_fallback": llm_fallback,
            },
        ),
    }


def generate_node(state: AgentState) -> dict[str, Any]:
    query = state["query"]
    chunks = state.get("chunks") or []
    config = state.get("config") or {}
    history_block = format_history_block(history_turns_from_state(state))
    result = generate_baseline_answer(
        query,
        chunks,
        config=config,
        from_agent=True,
        history_block=history_block or None,
    )

    return {
        "answer": result.answer,
        "citations": result.citations,
        "generator": result.generator,
        "trace": _append_trace(
            state,
            "generate",
            {"generator": result.generator, "citations": len(result.citations)},
        ),
    }
