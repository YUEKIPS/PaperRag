#!/usr/bin/env python3
"""Serve the local Paper RAG chat UI on 127.0.0.1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.web.env import load_dotenv  # noqa: E402
from src.web.server import create_server  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Paper RAG local web UI (stdlib HTTP).")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "configs" / "default.yaml")
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("Refusing to bind outside localhost.", file=sys.stderr)
        return 2

    load_dotenv()
    httpd = create_server(args.host, args.port, config_path=args.config)
    url = f"http://{args.host if args.host != '::1' else '127.0.0.1'}:{args.port}/"
    print(f"Paper RAG UI at {url}", file=sys.stderr)
    print("Session API token is injected into the page (local use only).", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
