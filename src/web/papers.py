from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.config import resolve_path

# arXiv IDs used in M1 corpus filenames (`{id}.pdf`).
_ARXIV_ID = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$", re.IGNORECASE)


def _safe_paper_id(paper_id: str) -> bool:
    if not paper_id or len(paper_id) > 64:
        return False
    if "/" in paper_id or "\\" in paper_id or ".." in paper_id:
        return False
    return bool(_ARXIV_ID.match(paper_id))


def _title_from_sidecar(raw_dir: Path, paper_id: str) -> str | None:
    for name in (f"{paper_id}.meta.json", f"{paper_id}.json"):
        path = raw_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            title = data.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()[:500]
    return None


def list_papers(config: dict[str, Any]) -> list[dict[str, Any]]:
    """List configured corpus IDs plus any PDF stems under raw_pdfs."""
    raw_dir = resolve_path(config, "raw_pdfs")
    configured: list[str] = list(config.get("arxiv", {}).get("paper_ids") or [])
    ids: set[str] = {str(x) for x in configured if _safe_paper_id(str(x))}

    if raw_dir.is_dir():
        for pdf in raw_dir.glob("*.pdf"):
            stem = pdf.stem
            if _safe_paper_id(stem):
                ids.add(stem)

    papers: list[dict[str, Any]] = []
    for pid in sorted(ids):
        pdf_path = raw_dir / f"{pid}.pdf"
        has_pdf = pdf_path.is_file() and pdf_path.stat().st_size > 0
        title = _title_from_sidecar(raw_dir, pid)
        papers.append(
            {
                "id": pid,
                "title": title,
                "filename": f"{pid}.pdf",
                "has_pdf": has_pdf,
            }
        )
    return papers


def resolve_paper_pdf(config: dict[str, Any], paper_id: str) -> Path | None:
    if not _safe_paper_id(paper_id):
        return None
    raw_dir = resolve_path(config, "raw_pdfs")
    path = (raw_dir / f"{paper_id}.pdf").resolve()
    if not str(path).startswith(str(raw_dir.resolve())):
        return None
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None
