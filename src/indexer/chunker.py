from __future__ import annotations

from dataclasses import dataclass

from src.parser.pdf_parser import ParsedDocument


@dataclass
class TextChunk:
    paper_id: str
    page_number: int
    chunk_id: str
    text: str


def chunk_document(
    doc: ParsedDocument,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for page in doc.pages:
        text = page.text
        if not text:
            continue
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            segment = text[start:end].strip()
            if segment:
                chunk_id = f"{doc.paper_id}_p{page.page_number}_c{idx}"
                chunks.append(
                    TextChunk(
                        paper_id=doc.paper_id,
                        page_number=page.page_number,
                        chunk_id=chunk_id,
                        text=segment,
                    )
                )
                idx += 1
            if end >= len(text):
                break
            start = max(0, end - chunk_overlap)
    return chunks
