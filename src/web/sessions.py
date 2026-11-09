from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.run import AgenticResult


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_title(first_query: str, max_len: int = 48) -> str:
    q = " ".join(first_query.split())
    if len(q) <= max_len:
        return q or "新对话"
    return q[: max_len - 1].rstrip() + "…"


@dataclass
class TurnRecord:
    id: str
    query: str
    created_at: str
    result: dict[str, Any]

    @classmethod
    def from_agentic(cls, query: str, result: AgenticResult) -> TurnRecord:
        return cls(
            id=str(uuid.uuid4()),
            query=query,
            created_at=_now_iso(),
            result={
                "query": result.query,
                "working_query": result.working_query,
                "answer": result.answer,
                "citations": result.citations,
                "generator": result.generator,
                "grade_passed": result.grade_passed,
                "grade_reason": result.grade_reason,
                "iterations": result.iterations,
                "trace": result.trace,
                "num_chunks": result.num_chunks,
            },
        )


@dataclass
class ChatSession:
    id: str
    title: str
    created_at: str
    updated_at: str
    archived: bool = False
    turns: list[TurnRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "turns": [asdict(t) for t in self.turns],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession:
        turns = [
            TurnRecord(
                id=str(t["id"]),
                query=str(t["query"]),
                created_at=str(t["created_at"]),
                result=dict(t["result"]),
            )
            for t in data.get("turns") or []
        ]
        return cls(
            id=str(data["id"]),
            title=str(data.get("title") or "新对话"),
            created_at=str(data.get("created_at") or _now_iso()),
            updated_at=str(data.get("updated_at") or _now_iso()),
            archived=bool(data.get("archived")),
            turns=turns,
        )


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        safe = session_id.replace("/", "").replace("..", "")
        return self.root / f"{safe}.json"

    def list_summaries(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("archived") and not include_archived:
                continue
            items.append(
                {
                    "id": data.get("id"),
                    "title": data.get("title") or "新对话",
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "archived": bool(data.get("archived")),
                    "turn_count": len(data.get("turns") or []),
                }
            )
        return items

    def get(self, session_id: str) -> ChatSession | None:
        path = self._path(session_id)
        if not path.is_file():
            return None
        return ChatSession.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, session: ChatSession) -> None:
        session.updated_at = _now_iso()
        path = self._path(session.id)
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self, title: str | None = None) -> ChatSession:
        now = _now_iso()
        session = ChatSession(
            id=str(uuid.uuid4()),
            title=title or "新对话",
            created_at=now,
            updated_at=now,
        )
        self.save(session)
        return session

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        if path.is_file():
            path.unlink()
            return True
        return False

    def append_turn(self, session_id: str, query: str, result: AgenticResult) -> TurnRecord | None:
        session = self.get(session_id)
        if session is None:
            return None
        turn = TurnRecord.from_agentic(query, result)
        session.turns.append(turn)
        if session.title == "新对话" or not session.title.strip():
            session.title = _session_title(query)
        elif len(session.turns) == 1:
            session.title = _session_title(query)
        self.save(session)
        return turn
