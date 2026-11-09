#!/usr/bin/env python3
"""Start the local slim Q&A web UI (stdlib HTTP + static page)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.web.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
