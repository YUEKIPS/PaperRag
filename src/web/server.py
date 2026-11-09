from __future__ import annotations

import json
import mimetypes
import re
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from src.agent.history import prior_conversation_from_turns
from src.agent.run import run_agentic_query
from src.config import load_config, resolve_path
from src.generate.llm import generator_mode, llm_endpoint_summary, resolve_api_key
from src.web.papers import list_papers, resolve_paper_pdf
from src.web.security import host_allowed, new_session_token, origin_allowed, token_from_request
from src.web.sessions import SessionStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
API_PREFIX = "/api"
_STATIC_MIME = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".wasm": "application/wasm",
}


def _static_content_type(file_path: Path) -> str:
    """JS module workers (PDF.js .mjs) must not be served as octet-stream."""
    override = _STATIC_MIME.get(file_path.suffix.lower())
    if override:
        return override
    ctype, _ = mimetypes.guess_type(str(file_path))
    return ctype or "application/octet-stream"


class PaperRagHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        token: str,
        config: dict[str, Any],
        sessions: SessionStore,
    ) -> None:
        self.session_token = token
        self.config = config
        self.sessions = sessions
        self._ask_lock = threading.Lock()
        super().__init__(server_address, handler_class)


class PaperRagHandler(BaseHTTPRequestHandler):
    server_version = "PaperRagWeb/1.0"

    @property
    def app_server(self) -> PaperRagHTTPServer:
        return self.server  # type: ignore[return-value]

    def log_message(self, format: str, *args: Any) -> None:
        if urlparse(self.path).path.startswith(f"{API_PREFIX}/ask"):
            return
        super().log_message(format, *args)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _api_allowed(self) -> bool:
        if not host_allowed(self):
            return False
        if not origin_allowed(self):
            return False
        return token_from_request(self, self.app_server.session_token)

    def _index_health(self) -> dict[str, Any]:
        index_dir = resolve_path(self.app_server.config, "index")
        manifest = index_dir / "manifest.json"
        faiss = index_dir / "index.faiss"
        index_ok = manifest.is_file() and (faiss.is_file() or (index_dir / "chunks_index.jsonl").is_file())
        cfg = self.app_server.config
        mode = generator_mode(agent=True)
        return {
            "ok": True,
            "index_ok": index_ok,
            "index_dir": str(index_dir),
            "generator_mode": mode,
            "api_key_set": resolve_api_key() is not None,
            "llm_hint": llm_endpoint_summary(cfg) if mode == "openai" else f"mode=stub (set AGENT_GENERATOR=openai for LLM)",
        }

    def _serve_static(self, rel_path: str) -> None:
        rel = rel_path.lstrip("/")
        if rel.startswith("..") or "/.." in rel:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        file_path = (STATIC_DIR / rel).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = _static_content_type(file_path)
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        header_type = f"{ctype}; charset=utf-8" if ctype.startswith("text/") else ctype
        self.send_header("Content-Type", header_type)
        self.send_header("Content-Length", str(len(data)))
        # Localhost-only UI: avoid stale JS/CSS during rapid iteration (HTML already no-store).
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_bytes(self, status: int, data: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_paper_pdf(self, paper_id: str) -> None:
        if not self._api_allowed():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return
        pdf_path = resolve_paper_pdf(self.app_server.config, paper_id)
        if pdf_path is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "pdf_not_found", "id": paper_id})
            return
        data = pdf_path.read_bytes()
        self._send_bytes(HTTPStatus.OK, data, "application/pdf")

    def _serve_index(self) -> None:
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        html = index_path.read_text(encoding="utf-8")
        token = self.app_server.session_token
        inject = f'<meta name="paper-rag-token" content="{token}">'
        if "</head>" in html:
            html = html.replace("</head>", f"  {inject}\n</head>", 1)
        data = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            if not host_allowed(self):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self._serve_index()
            return
        if path.startswith("/static/"):
            if not host_allowed(self):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            self._serve_static(unquote(path[len("/static/") :]))
            return

        if not path.startswith(API_PREFIX):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if path == f"{API_PREFIX}/health":
            if not self._api_allowed():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            self._send_json(HTTPStatus.OK, self._index_health())
            return

        m_sessions = re.fullmatch(rf"{re.escape(API_PREFIX)}/sessions/?", path)
        if m_sessions:
            if not self._api_allowed():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            archived = (urlparse(self.path).query or "").find("archived=1") >= 0
            self._send_json(
                HTTPStatus.OK,
                {"sessions": self.app_server.sessions.list_summaries(include_archived=archived)},
            )
            return

        m_session = re.fullmatch(rf"{re.escape(API_PREFIX)}/sessions/([^/]+)/?", path)
        if m_session:
            if not self._api_allowed():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            sid = m_session.group(1)
            session = self.app_server.sessions.get(sid)
            if session is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            self._send_json(HTTPStatus.OK, session.to_dict())
            return

        if path == f"{API_PREFIX}/papers":
            if not self._api_allowed():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            papers = list_papers(self.app_server.config)
            self._send_json(HTTPStatus.OK, {"papers": papers})
            return

        m_paper_pdf = re.fullmatch(rf"{re.escape(API_PREFIX)}/papers/([^/]+)/pdf/?", path)
        if m_paper_pdf:
            self._serve_paper_pdf(unquote(m_paper_pdf.group(1)))
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith(API_PREFIX):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not self._api_allowed():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        if path == f"{API_PREFIX}/sessions":
            body = self._read_json_body()
            if body is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            title = body.get("title")
            session = self.app_server.sessions.create(title=str(title) if title else None)
            self._send_json(HTTPStatus.CREATED, session.to_dict())
            return

        if path == f"{API_PREFIX}/ask":
            body = self._read_json_body()
            if body is None:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            query = str(body.get("query") or "").strip()
            if not query:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "query_required"})
                return

            session_id = body.get("session_id")
            if session_id:
                session = self.app_server.sessions.get(str(session_id))
                if session is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
                    return
            else:
                session = self.app_server.sessions.create()
                session_id = session.id

            health = self._index_health()
            if not health["index_ok"]:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "index_missing", "message": "Run build_index.py first.", "health": health},
                )
                return

            index_dir = resolve_path(self.app_server.config, "index")
            exercise = bool(body.get("exercise_rewrite"))

            with self.app_server._ask_lock:
                # Re-read inside the lock so a follow-up sees turns just appended.
                session = self.app_server.sessions.get(str(session_id))
                if session is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "session_not_found"})
                    return
                prior = prior_conversation_from_turns(session.turns)
                try:
                    result = run_agentic_query(
                        query,
                        index_dir,
                        self.app_server.config,
                        exercise_strict_grade=exercise,
                        conversation=prior,
                    )
                except Exception as exc:  # noqa: BLE001 — surface to local UI
                    self._send_json(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {"error": "agent_failed", "message": str(exc)},
                    )
                    return
                turn = self.app_server.sessions.append_turn(str(session_id), query, result)
                session = self.app_server.sessions.get(str(session_id))
            self._send_json(
                HTTPStatus.OK,
                {
                    "session_id": session_id,
                    "turn": asdict(turn) if turn else None,
                    "session": session.to_dict() if session else None,
                },
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        m_session = re.fullmatch(rf"{re.escape(API_PREFIX)}/sessions/([^/]+)/?", path)
        if not m_session:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._api_allowed():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        body = self._read_json_body()
        if body is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        sid = m_session.group(1)
        session = self.app_server.sessions.get(sid)
        if session is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        if "archived" in body:
            session.archived = bool(body["archived"])
        if "title" in body:
            title = str(body["title"]).strip()
            if title:
                session.title = title[:120]

        self.app_server.sessions.save(session)
        self._send_json(HTTPStatus.OK, session.to_dict())

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        m_session = re.fullmatch(rf"{re.escape(API_PREFIX)}/sessions/([^/]+)/?", path)
        if not m_session:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._api_allowed():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return
        sid = m_session.group(1)
        if self.app_server.sessions.delete(sid):
            self._send_json(HTTPStatus.OK, {"deleted": True, "id": sid})
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def create_server(
    host: str,
    port: int,
    *,
    config_path: Path | None = None,
    sessions_dir: Path | None = None,
    token: str | None = None,
) -> PaperRagHTTPServer:
    from src.config import REPO_ROOT

    config = load_config(config_path)
    token = token or new_session_token()
    store_dir = sessions_dir or (REPO_ROOT / "data" / "web" / "sessions")
    sessions = SessionStore(store_dir)
    return PaperRagHTTPServer(
        (host, port),
        PaperRagHandler,
        token=token,
        config=config,
        sessions=sessions,
    )
