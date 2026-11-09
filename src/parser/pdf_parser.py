from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    page_number: int  # 1-based
    text: str


@dataclass
class ParsedDocument:
    paper_id: str
    source_path: Path
    pages: list[ParsedPage] = field(default_factory=list)


def parse_pdf(pdf_path: Path, paper_id: str | None = None) -> ParsedDocument:
    """
    Extract text per page from a PDF.

    M1: uses PyMuPDF when available. Scaffold returns empty pages if import fails.
    """
    pid = paper_id or pdf_path.stem.replace(".pdf", "")
    doc = ParsedDocument(paper_id=pid, source_path=pdf_path)

    try:
        import fitz  # PyMuPDF
    except ImportError:
        return doc

    with fitz.open(pdf_path) as pdf:
        for i, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            doc.pages.append(ParsedPage(page_number=i, text=text.strip()))
    return doc
