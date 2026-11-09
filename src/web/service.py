"""Web Q&A service: health checks and agentic queries (no HTTP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agent.run import AgenticResult, run_agentic_query
from src.config import load_config, resolve_path
from src.generate.llm import generator_mode, resolve_api_key


class WebServiceError(Exception):
    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _index_ready(index_dir: Path) -> bool:
    return (index_dir / "manifest.json").is_file()


def health_snapshot(config_path: Path | None = None) -> dict[str, Any]:
    config = load_config(config_path)
    index_dir = resolve_path(config, "index")
    mode = generator_mode(agent=True)
    has_key = resolve_api_key() is not None
    llm_ready = mode != "openai" or has_key
    return {
        "ok": True,
        "index_present": _index_ready(index_dir),
        "index_dir": str(index_dir),
        "generator_mode": mode,
        "llm_configured": llm_ready,
        "llm_mode_hint": (
            "stub（无 API 或 AGENT_GENERATOR 未设 openai）"
            if mode != "openai"
            else ("openai 兼容端点（已检测到 API key）" if has_key else "openai 模式但未配置 API key，将回退 stub")
        ),
    }


def agentic_result_to_dict(result: AgenticResult) -> dict[str, Any]:
    return {
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
    }


def ask_question(
    query: str,
    *,
    config_path: Path | None = None,
    rerank_enabled: bool | None = None,
) -> dict[str, Any]:
    text = (query or "").strip()
    if not text:
        raise WebServiceError("query 不能为空", status=400)

    config = load_config(config_path)
    index_dir = resolve_path(config, "index")
    if not _index_ready(index_dir):
        raise WebServiceError(
            f"索引未就绪（缺少 {index_dir / 'manifest.json'}）。请先运行 scripts/build_index.py。",
            status=503,
        )

    result = run_agentic_query(
        text,
        index_dir,
        config,
        rerank_enabled=rerank_enabled,
    )
    return agentic_result_to_dict(result)
