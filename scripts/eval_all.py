#!/usr/bin/env python3
"""Placeholder for batch eval — no reported metrics in scaffold round."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "eval_all.py is a stub. "
        "Batch evaluation and metrics will land after M1 retrieval quality baseline.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
