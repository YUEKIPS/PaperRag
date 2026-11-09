from __future__ import annotations

from dataclasses import dataclass

from src.retriever.baseline import RetrievedChunk


@dataclass
class BaselineAnswer:
    answer: str
    citations: list[dict[str, str | int]]


def generate_baseline_answer(
    query: str,
    chunks: list[RetrievedChunk],
) -> BaselineAnswer:
    """
    Stub generator: concatenates retrieved excerpts with arXiv-style citations.
    Replace with LLM call in M1+.
    """
    if not chunks:
        return BaselineAnswer(
            answer="[baseline] No retrieved context. Run ingest and build_index first.",
            citations=[],
        )

    parts: list[str] = []
    citations: list[dict[str, str | int]] = []
    for i, ch in enumerate(chunks, start=1):
        excerpt = ch.text[:400].replace("\n", " ")
        parts.append(f"({i}) {excerpt}…")
        citations.append(
            {
                "paper_id": ch.paper_id,
                "page": ch.page_number,
                "chunk_id": ch.chunk_id,
            }
        )

    body = " ".join(parts)
    answer = (
        f"[baseline stub — not an LLM answer]\n"
        f"Query: {query}\n"
        f"Context excerpts:\n{body}"
    )
    return BaselineAnswer(answer=answer, citations=citations)
