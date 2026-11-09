from __future__ import annotations

import argparse
from pathlib import Path

from src.config import REPO_ROOT
from src.web.env import load_dotenv
from src.web.server import run_server


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="本地 Paper RAG 问答 Web UI（127.0.0.1）")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认仅本机）")
    parser.add_argument("--port", type=int, default=8765, help="端口")
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs" / "default.yaml",
        help="配置文件路径",
    )
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("为安全起见仅允许绑定 127.0.0.1 / localhost / ::1")
    run_server(host=args.host, port=args.port, config_path=args.config)


if __name__ == "__main__":
    main()
