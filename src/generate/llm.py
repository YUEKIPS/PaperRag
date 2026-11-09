from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def generator_mode(*, agent: bool = False) -> str:
    """
    Resolve generator backend: stub (default) or openai.
    Agentic path checks AGENT_GENERATOR then BASELINE_GENERATOR.
    """
    if agent:
        mode = os.environ.get("AGENT_GENERATOR", "").strip().lower()
        if mode:
            return mode
    return os.environ.get("BASELINE_GENERATOR", "stub").strip().lower() or "stub"


def openai_chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    timeout: int = 120,
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

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
) -> tuple[str | None, str | None]:
    """Return (text, error). On success error is None."""
    mode = generator_mode(agent=True)
    if mode != "openai":
        return None, None
    try:
        return openai_chat(messages, temperature=temperature), None
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, RuntimeError) as e:
        return None, str(e)
