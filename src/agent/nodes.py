from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.agent.state import AgentState
from src.generate.baseline import generate_baseline_answer
from src.generate.llm import generator_mode, try_openai_chat
from src.retriever.pipeline import retrieve_with_config


def _append_trace(state: AgentState, event: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    trace = list(state.get("trace") or [])
    trace.append({"event": event, **detail})
    return trace


def decide_node(state: AgentState) -> dict[str, Any]:
    """Passthrough decide: use original query; agentic routing hooks reserved for later."""
    query = state["query"]
    return {
        "working_query": query,
        "iterations": int(state.get("iterations") or 0),
        "trace": _append_trace(state, "decide", {"working_query": query}),
    }


def retrieve_node(state: AgentState) -> dict[str, Any]:
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


def _stub_grade(query: str, chunks: list[Any]) -> tuple[bool, str]:
    if not chunks:
        return False, "no_chunks"
    q_tokens = _query_tokens(query)
    if not q_tokens:
        return True, "empty_query_tokens"
    matched = 0
    for ch in chunks[:5]:
        overlap = len(q_tokens & _query_tokens(ch.text))
        if overlap >= 2:
            matched += 1
    if matched >= 1:
        return True, f"stub_overlap_ok matched_chunks={matched}"
    return False, "stub_overlap_low"


def _llm_grade(query: str, chunks: list[Any]) -> tuple[bool | None, str | None]:
    excerpts = []
    for i, ch in enumerate(chunks[:5], start=1):
        excerpts.append(
            f"({i}) [{ch.paper_id} p.{ch.page_number}] {ch.text[:600].replace(chr(10), ' ')}"
        )
    context = "\n".join(excerpts) or "(no context)"
    system = (
        "You judge whether the excerpts can support a factual answer to the question. "
        'Reply with JSON only: {"passed": true/false, "reason": "..."}'
    )
    user = f"Question: {query}\n\nExcerpts:\n{context}"
    text, err = try_openai_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )
    if err:
        return None, err
    if text is None:
        return None, None
    try:
        # tolerate markdown fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned)
        return bool(data.get("passed")), str(data.get("reason", ""))
    except json.JSONDecodeError:
        return None, "grade_json_parse_error"


def grade_node(state: AgentState) -> dict[str, Any]:
    query = state.get("working_query") or state["query"]
    chunks = state.get("chunks") or []
    passed, reason = _stub_grade(query, chunks)

    if generator_mode(agent=True) == "openai":
        llm_pass, llm_reason = _llm_grade(query, chunks)
        if llm_pass is not None:
            passed, reason = llm_pass, f"llm: {llm_reason}"

    return {
        "grade_passed": passed,
        "grade_reason": reason,
        "trace": _append_trace(
            state,
            "grade",
            {"passed": passed, "reason": reason, "num_chunks": len(chunks)},
        ),
    }


def _stub_rewrite(query: str, reason: str) -> str:
    extra = "retrieval augmented generation LLM agents"
    if "overlap" in reason:
        return f"{query} ({extra})"
    return f"{query} — explain with definitions from the cited papers"


def _llm_rewrite(query: str, reason: str) -> tuple[str | None, str | None]:
    system = (
        "Rewrite the user question to improve retrieval over LLM/agent research PDFs. "
        "Output one line of text only, no quotes."
    )
    user = f"Original: {query}\nGrade feedback: {reason}"
    text, err = try_openai_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return text, err


def rewrite_node(state: AgentState) -> dict[str, Any]:
    query = state.get("working_query") or state["query"]
    reason = state.get("grade_reason") or ""
    new_q = _stub_rewrite(query, reason)

    if generator_mode(agent=True) == "openai":
        llm_q, err = _llm_rewrite(query, reason)
        if llm_q and not err:
            new_q = llm_q.strip()

    iterations = int(state.get("iterations") or 0) + 1
    return {
        "working_query": new_q,
        "iterations": iterations,
        "trace": _append_trace(
            state,
            "rewrite",
            {"from": query, "to": new_q, "iteration": iterations},
        ),
    }


def generate_node(state: AgentState) -> dict[str, Any]:
    query = state["query"]
    chunks = state.get("chunks") or []
    result = generate_baseline_answer(query, chunks)
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
