from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

# DeepSeek OpenAI-compatible API (see https://api-docs.deepseek.com/)
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_CHAT_MODEL = "deepseek-chat"


def generator_mode(*, agent: bool = False) -> str:
    """
    Resolve generator backend: stub (default) or openai.

    ``openai`` means any OpenAI-compatible HTTP chat/completions endpoint
    (DeepSeek, OpenAI, local vLLM, etc.), not vendor lock-in.
    Agentic path checks AGENT_GENERATOR then BASELINE_GENERATOR.
    """
    if agent:
        mode = os.environ.get("AGENT_GENERATOR", "").strip().lower()
        if mode:
            return mode
    return os.environ.get("BASELINE_GENERATOR", "stub").strip().lower() or "stub"


def resolve_api_key() -> str | None:
    for var in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
        key = os.environ.get(var, "").strip()
        if key:
            return key
    return None


def resolve_base_url(config: dict[str, Any] | None = None) -> str:
    env = os.environ.get("OPENAI_BASE_URL", "").strip()
    if env:
        return env.rstrip("/")
    if config:
        llm = config.get("llm") or {}
        cfg_url = str(llm.get("base_url", "")).strip()
        if cfg_url:
            return cfg_url.rstrip("/")
    return DEFAULT_BASE_URL


def resolve_model(config: dict[str, Any] | None = None) -> str:
    env = os.environ.get("OPENAI_MODEL", "").strip()
    if env:
        return env
    if config:
        llm = config.get("llm") or {}
        cfg_model = str(llm.get("model", "")).strip()
        if cfg_model:
            return cfg_model
    return DEFAULT_CHAT_MODEL


def openai_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    timeout: int = 120,
    config: dict[str, Any] | None = None,
) -> str:
    api_key = resolve_api_key()
    if not api_key:
        raise RuntimeError("No API key: set DEEPSEEK_API_KEY or OPENAI_API_KEY")

    base_url = resolve_base_url(config)
    model = resolve_model(config)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return str(body["choices"][0]["message"]["content"]).strip()


def try_openai_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    config: dict[str, Any] | None = None,
    agent: bool = True,
) -> tuple[str | None, str | None]:
    """
    Return (text, error). On success error is None.
    When mode is stub, returns (None, None) without calling the API.
    """
    mode = generator_mode(agent=agent)
    if mode != "openai":
        return None, None
    try:
        return openai_chat(messages, temperature=temperature, config=config), None
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, RuntimeError) as e:
        return None, str(e)


def llm_endpoint_summary(config: dict[str, Any] | None = None) -> str:
    """Non-secret summary for logs and smoke reports."""
    key = resolve_api_key()
    key_status = "set" if key else "missing"
    return (
        f"mode={generator_mode(agent=True)} "
        f"base_url={resolve_base_url(config)} "
        f"model={resolve_model(config)} "
        f"api_key={key_status}"
    )
