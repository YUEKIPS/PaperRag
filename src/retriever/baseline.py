from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RetrievedChunk:
    paper_id: str
    page_number: int
    chunk_id: str
    text: str
    score: float


def retrieve_baseline(
    query: str,
    index_path: Path,
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Keyword overlap retriever for pipeline smoke tests (not production quality).
    """
    if not index_path.exists():
        return []

    tokens = {t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 2}
    scored: list[RetrievedChunk] = []

    with index_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            text = rec.get("text", "")
            text_tokens = set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
            overlap = len(tokens & text_tokens)
            if overlap == 0:
                continue
            scored.append(
                RetrievedChunk(
                    paper_id=rec["paper_id"],
                    page_number=rec["page_number"],
                    chunk_id=rec["chunk_id"],
                    text=text,
                    score=float(overlap),
                )
            )

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]
