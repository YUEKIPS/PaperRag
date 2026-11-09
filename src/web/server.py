"""Local stdlib HTTP server for the slim Paper RAG Q&A UI."""

from __future__ import annotations

import json
import mimetypes
import secrets
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.config import DEFAULT_CONFIG_PATH, REPO_ROOT
from src.web.service import WebServiceError, ask_question, health_snapshot

STATIC_DIR = Path(__file__).resolve().parent / "static"
TOKEN_PLACEHOLDER = "__SESSION_TOKEN__"
SESSION_HEADER = "X-Session-Token"


class PaperRagWebHandler(BaseHTTPRequestHandler):
    session_token: str = ""
    config_path: Path = DEFAULT_CONFIG_PATH

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_api_token(self) -> bool:
        token = self.headers.get(SESSION_HEADER, "").strip()
        if token and secrets.compare_digest(token, self.session_token):
            return True
        self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "无效或缺失会话 token"})
        return False

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "请求体必须是 JSON"})
            return None

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._serve_index()
            return
        if path == "/api/health":
            if not self._require_api_token():
                return
            self._send_json(HTTPStatus.OK, health_snapshot(self.config_path))
            return
        if path.startswith("/static/"):
            self._serve_static(path[len("/static/") :])
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/ask":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._require_api_token():
            return
        body = self._read_json_body()
        if body is None:
            return
        query = str(body.get("query", ""))
        try:
            result = ask_question(query, config_path=self.config_path)
            self._send_json(HTTPStatus.OK, {"ok": True, "result": result})
        except WebServiceError as exc:
            self._send_json(exc.status, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001 — surface as 500 without leaking secrets
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": f"内部错误: {type(exc).__name__}"},
            )

    def _serve_index(self) -> None:
        index_path = STATIC_DIR / "index.html"
        try:
            html = index_path.read_text(encoding="utf-8")
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "index.html 缺失")
            return
        html = html.replace(TOKEN_PLACEHOLDER, self.session_token)
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, rel: str) -> None:
        rel = rel.lstrip("/")
        if ".." in Path(rel).parts:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        static_root = STATIC_DIR.resolve()
        file_path = (STATIC_DIR / rel).resolve()
        try:
            file_path.relative_to(static_root)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        content_type = mime or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_handler_class(session_token: str, config_path: Path) -> type[PaperRagWebHandler]:
    class BoundHandler(PaperRagWebHandler):
        pass

    BoundHandler.session_token = session_token
    BoundHandler.config_path = config_path
    return BoundHandler


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    config_path: Path | None = None,
) -> None:
    token = secrets.token_urlsafe(24)
    cfg = config_path or DEFAULT_CONFIG_PATH
    handler = create_handler_class(token, cfg)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"Agentic Paper RAG Web UI: {url}")
    print(f"绑定配置: {cfg.relative_to(REPO_ROOT) if cfg.is_relative_to(REPO_ROOT) else cfg}")
    print("仅本机访问；关闭终端即停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()
