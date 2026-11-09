from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

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


def _openai_chat(query: str, context: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    system = (
        "You answer questions about LLM and agent research papers using ONLY the "
        "provided context. Cite sources as [arxiv_id p.N] matching the context tags. "
        "If context is insufficient, say so briefly."
    )
    user = f"Question: {query}\n\nContext:\n{context}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return str(body["choices"][0]["message"]["content"]).strip()


def generate_baseline_answer(
    query: str,
    chunks: list[RetrievedChunk],
) -> BaselineAnswer:
    """
    Default: stable citation-shaped stub. Set BASELINE_GENERATOR=openai and OPENAI_API_KEY
    for LLM answers (OpenAI-compatible chat/completions).
    """
    if not chunks:
        return BaselineAnswer(
            answer="[baseline] No retrieved context. Run ingest and build_index first.",
            citations=[],
            generator="none",
        )

    context, citations = _format_context(chunks)
    mode = os.environ.get("BASELINE_GENERATOR", "stub").strip().lower()

    if mode == "openai":
        try:
            answer = _openai_chat(query, context)
            return BaselineAnswer(answer=answer, citations=citations, generator="openai")
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, RuntimeError) as e:
            answer = _stub_answer(query, context) + f"\n\n[openai fallback: {e}]"
            return BaselineAnswer(answer=answer, citations=citations, generator="stub_fallback")

    answer = _stub_answer(query, context)
    return BaselineAnswer(answer=answer, citations=citations, generator="stub")
