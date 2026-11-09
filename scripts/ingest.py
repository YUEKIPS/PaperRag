#!/usr/bin/env python3
"""Parse raw PDFs and write chunked JSONL under data/processed/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config, resolve_path  # noqa: E402
from src.indexer.chunker import chunk_document  # noqa: E402
from src.parser.pdf_parser import parse_pdf  # noqa: E402


def ingest_pdf(
    pdf_path: Path,
    processed_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
) -> int:
    paper_id = pdf_path.stem
    doc = parse_pdf(pdf_path, paper_id=paper_id)
    chunks = chunk_document(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    out_path = processed_dir / f"{paper_id}.chunks.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(
                json.dumps(
                    {
                        "paper_id": ch.paper_id,
                        "page_number": ch.page_number,
                        "chunk_id": ch.chunk_id,
                        "text": ch.text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return len(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest PDFs into chunked JSONL.")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    raw_dir = resolve_path(config, "raw_pdfs")
    processed_dir = resolve_path(config, "processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    ingest_cfg = config.get("ingest", {})
    chunk_size = int(ingest_cfg.get("chunk_size", 512))
    chunk_overlap = int(ingest_cfg.get("chunk_overlap", 64))

    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        print(
            f"No PDFs in {raw_dir}. Run: python scripts/download_pdfs.py",
            file=sys.stderr,
        )
        return 1

    total_chunks = 0
    for pdf in pdfs:
        n = ingest_pdf(pdf, processed_dir, chunk_size, chunk_overlap)
        print(f"{pdf.name}: {n} chunks")
        total_chunks += n

    print(f"Ingest complete. {len(pdfs)} PDFs, {total_chunks} chunks → {processed_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
