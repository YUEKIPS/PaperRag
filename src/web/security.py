from __future__ import annotations

import secrets
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    pass

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def host_allowed(handler: BaseHTTPRequestHandler) -> bool:
    host = (handler.headers.get("Host") or "").split(":")[0].strip().lower()
    if host in LOCAL_HOSTS:
        return True
    client = handler.client_address[0] if handler.client_address else ""
    return client in LOCAL_HOSTS or client == ""


def origin_allowed(handler: BaseHTTPRequestHandler) -> bool:
    origin = handler.headers.get("Origin")
    if not origin:
        return True
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    return (parsed.hostname or "").lower() in LOCAL_HOSTS


def token_from_request(handler: BaseHTTPRequestHandler, expected: str) -> bool:
    auth = handler.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return secrets.compare_digest(auth[7:].strip(), expected)
    header = handler.headers.get("X-Session-Token") or ""
    if header:
        return secrets.compare_digest(header.strip(), expected)
    return False
