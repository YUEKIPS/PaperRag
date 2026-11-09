from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from src.generate.llm import generator_mode, try_openai_chat
from src.generate.prompts import load_prompt
from src.retriever.baseline import RetrievedChunk


@dataclass
class BaselineAnswer:
    answer: str
    citations: list[dict[str, str | int]]
    generator: str


def _format_context(chunks: list[RetrievedChunk]) -> tuple[str, list[dict[str, str | int]]]:
    parts: list[str] = []
    citations: list[dict[str, str | int]] = []
    for i, ch in enumerate(chunks, start=1):
        excerpt = ch.text[:1200].replace("\n", " ")
        cite_tag = f"[{ch.paper_id} p.{ch.page_number}]"
        parts.append(f"({i}) {cite_tag} {excerpt}")
        citations.append(
            {
                "paper_id": ch.paper_id,
                "page": ch.page_number,
                "chunk_id": ch.chunk_id,
            }
        )
    return "\n\n".join(parts), citations


def _stub_answer(query: str, context: str) -> str:
    return (
        f"[baseline stub — not an LLM answer]\n"
        f"Query: {query}\n"
        f"Context excerpts:\n{context}"
    )


def _use_llm(*, from_agent: bool) -> bool:
    if from_agent:
        from src.generate.llm import generator_mode

        return generator_mode(agent=True) == "openai"
    return os.environ.get("BASELINE_GENERATOR", "stub").strip().lower() == "openai"


def generate_baseline_answer(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    config: dict[str, Any] | None = None,
    from_agent: bool = False,
) -> BaselineAnswer:
    """
    Default: stable citation-shaped stub.

    Set BASELINE_GENERATOR=openai (or AGENT_GENERATOR for agentic generate path)
    and DEEPSEEK_API_KEY or OPENAI_API_KEY for OpenAI-compatible chat/completions.
    """
    if not chunks:
        return BaselineAnswer(
            answer="[baseline] No retrieved context. Run ingest and build_index first.",
            citations=[],
            generator="none",
        )

    context, citations = _format_context(chunks)

    if _use_llm(from_agent=from_agent):
        system = load_prompt("generate_system")
        user = f"Question: {query}\n\nContext:\n{context}"
        text, err = try_openai_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            config=config,
            agent=from_agent,
        )
        if text and not err:
            return BaselineAnswer(answer=text, citations=citations, generator="openai")
        reason = err or "llm_disabled_or_empty"
        answer = _stub_answer(query, context) + f"\n\n[openai fallback: {reason}]"
        return BaselineAnswer(answer=answer, citations=citations, generator="stub_fallback")

    answer = _stub_answer(query, context)
    return BaselineAnswer(answer=answer, citations=citations, generator="stub")
