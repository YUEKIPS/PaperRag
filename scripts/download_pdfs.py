#!/usr/bin/env python3
"""Download M1 arXiv PDFs listed in configs/default.yaml."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config, resolve_path  # noqa: E402


def download_paper(paper_id: str, dest: Path, url_template: str, delay: float) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return False

    url = url_template.format(paper_id=paper_id)
    headers = {"User-Agent": "agentic-paper-rag/0.1 (research; +https://arxiv.org)"}
    resp = requests.get(url, headers=headers, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    if delay > 0:
        time.sleep(delay)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download arXiv PDFs for M1 corpus.")
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs" / "default.yaml",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if file exists",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    raw_dir = resolve_path(config, "raw_pdfs")
    arxiv = config["arxiv"]
    template = arxiv["pdf_url_template"]
    delay = float(arxiv.get("request_delay_seconds", 1.0))
    ids: list[str] = arxiv["paper_ids"]

    downloaded = skipped = 0
    for paper_id in tqdm(ids, desc="arxiv PDFs"):
        dest = raw_dir / f"{paper_id}.pdf"
        if args.force and dest.exists():
            dest.unlink()
        try:
            if dest.exists() and dest.stat().st_size > 0:
                skipped += 1
                continue
            if download_paper(paper_id, dest, template, delay):
                downloaded += 1
            else:
                skipped += 1
        except requests.RequestException as e:
            print(f"Failed {paper_id}: {e}", file=sys.stderr)
            return 1

    print(f"Done. downloaded={downloaded} skipped={skipped} dir={raw_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
