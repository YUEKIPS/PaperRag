"""Lightweight multi-turn history for one web session (M6 / D-017).

Selection keeps the most recent complete turns, capped by count and by UTF-8
bytes of question + answer text. Older turns are dropped whole before any
answer is truncated. This is not RepoAgent's session event log.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.generate.llm import generator_mode, try_openai_chat
from src.generate.prompts import load_prompt

DEFAULT_MAX_TURNS = 6
DEFAULT_MAX_HISTORY_BYTES = 24000

_ELLIPSIS = "…"

# Follow-ups that are not searchable on their own. Stub contextualize anchors
# these to the previous question; the LLM path can still rewrite other cases.
_FOLLOWUP_CUES = re.compile(
    r"(?:"
    r"它(?:们|的)?|他们|她们|"
    r"这个|那个|这些|那些|上述|上面|前面|刚才|之前|"
    r"第[0-9一二三四五六七八九十百]+(?:点|条|项)|"
    r"展开|详细讲|再说一下|"
    r"\b(?:it|its|they|them|this|that|these|those)\b|"
    r"\b(?:expand|elaborate)\b"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HistoryTurn:
    question: str
    answer: str


@dataclass(frozen=True)
class HistorySelection:
    turns: tuple[HistoryTurn, ...]
    included_turns: int
    omitted_turns: int
    policy: str
    truncated_answers: int
    history_bytes: int


@dataclass(frozen=True)
class ContextualizeResult:
    working_query: str
    backend: str
    changed: bool
    llm_fallback: str | None = None


def policy_label(max_turns: int, max_history_bytes: int) -> str:
    return f"last_{max_turns}_turns_and_{max_history_bytes}_utf8_bytes"


def conversation_limits(config: Mapping[str, Any] | None) -> tuple[int, int]:
    agent = (config or {}).get("agent") or {}
    conv = agent.get("conversation") or {}
    max_turns = int(conv.get("max_turns", DEFAULT_MAX_TURNS))
    max_bytes = int(conv.get("max_history_bytes", DEFAULT_MAX_HISTORY_BYTES))
    return max(0, max_turns), max(0, max_bytes)


def _turn_bytes(turn: HistoryTurn) -> int:
    return len(turn.question.encode("utf-8")) + len(turn.answer.encode("utf-8"))


def _hard_cut(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8")[:max_bytes]
    while raw:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raw = raw[:-1]
    return ""


def _fit_text(text: str, max_bytes: int) -> str:
    """Shorten text so its UTF-8 size is at most max_bytes, keeping a prefix."""
    if max_bytes <= 0:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    ellipsis_bytes = len(_ELLIPSIS.encode("utf-8"))
    if max_bytes <= ellipsis_bytes:
        return _hard_cut(text, max_bytes)
    keep = encoded[: max_bytes - ellipsis_bytes]
    while keep:
        try:
            return keep.decode("utf-8") + _ELLIPSIS
        except UnicodeDecodeError:
            keep = keep[:-1]
    return _ELLIPSIS


def _truncate_turn(turn: HistoryTurn, budget: int) -> HistoryTurn:
    """Fit one turn into budget. Prefer keeping the question and cutting the answer."""
    if budget <= 0:
        return HistoryTurn("", "")
    if _turn_bytes(turn) <= budget:
        return turn
    question_bytes = len(turn.question.encode("utf-8"))
    if question_bytes < budget:
        answer = _fit_text(turn.answer, budget - question_bytes)
        return HistoryTurn(turn.question, answer)
    return HistoryTurn(_fit_text(turn.question, budget), "")


def coerce_history_turns(conversation: Sequence[Mapping[str, Any]] | None) -> list[HistoryTurn]:
    """Keep complete turns only. Empty question or answer is not a turn and not omitted."""
    turns: list[HistoryTurn] = []
    if not conversation:
        return turns
    for item in conversation:
        if not isinstance(item, Mapping):
            continue
        raw_question = item.get("question")
        if raw_question is None:
            raw_question = item.get("query") or ""
        question = str(raw_question).strip()
        answer = str(item.get("answer") or "").strip()
        if question and answer:
            turns.append(HistoryTurn(question, answer))
    return turns


def select_history(
    conversation: Sequence[Mapping[str, Any]] | None,
    *,
    config: Mapping[str, Any] | None = None,
    max_turns: int | None = None,
    max_history_bytes: int | None = None,
) -> HistorySelection:
    """Select a contiguous suffix of complete turns under the count and byte caps.

    Incomplete items are ignored. Turns outside the last ``max_turns`` count as
    omitted. If the newest remaining turn still exceeds the byte budget, its
    answer is truncated so that one turn fits; older turns are not kept in its
    place.
    """
    cfg_turns, cfg_bytes = conversation_limits(config)
    if max_turns is None:
        max_turns = cfg_turns
    if max_history_bytes is None:
        max_history_bytes = cfg_bytes
    max_turns = max(0, int(max_turns))
    max_history_bytes = max(0, int(max_history_bytes))
    policy = policy_label(max_turns, max_history_bytes)

    complete = coerce_history_turns(conversation)
    if max_turns == 0 or max_history_bytes == 0:
        return HistorySelection(
            turns=(),
            included_turns=0,
            omitted_turns=len(complete),
            policy=policy,
            truncated_answers=0,
            history_bytes=0,
        )

    omitted_by_cap = max(0, len(complete) - max_turns)
    window = complete[-max_turns:]

    chosen: list[HistoryTurn] = []
    for start in range(len(window)):
        suffix = window[start:]
        if sum(_turn_bytes(turn) for turn in suffix) <= max_history_bytes:
            chosen = list(suffix)
            break

    truncated_answers = 0
    if window and not chosen:
        newest = window[-1]
        fitted = _truncate_turn(newest, max_history_bytes)
        chosen = [fitted]
        if fitted.question != newest.question or fitted.answer != newest.answer:
            truncated_answers = 1

    history_bytes = sum(_turn_bytes(turn) for turn in chosen)
    omitted = omitted_by_cap + (len(window) - len(chosen))
    return HistorySelection(
        turns=tuple(chosen),
        included_turns=len(chosen),
        omitted_turns=omitted,
        policy=policy,
        truncated_answers=truncated_answers,
        history_bytes=history_bytes,
    )


def prior_conversation_from_turns(turns: Sequence[Any]) -> list[dict[str, str]]:
    """Map stored session turns to the conversation payload. Citations are not copied."""
    payload: list[dict[str, str]] = []
    for turn in turns:
        if isinstance(turn, Mapping):
            question = str(turn.get("query") or turn.get("question") or "")
            result = turn.get("result") or {}
            if not isinstance(result, Mapping):
                result = {}
            answer = str(result.get("answer") or turn.get("answer") or "")
        else:
            question = str(getattr(turn, "query", "") or "")
            result = getattr(turn, "result", {}) or {}
            answer = str(result.get("answer") or "") if isinstance(result, Mapping) else ""
        payload.append({"question": question, "answer": answer})
    return payload


def history_turns_from_state(state: Mapping[str, Any]) -> list[HistoryTurn]:
    raw = state.get("conversation") or []
    turns: list[HistoryTurn] = []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return turns
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if question or answer:
            turns.append(HistoryTurn(question, answer))
    return turns


def format_history_block(turns: Sequence[HistoryTurn]) -> str:
    if not turns:
        return ""
    lines = ["Prior conversation (resolve references only; NOT evidence; do not cite):"]
    for index, turn in enumerate(turns, start=1):
        lines.append(f"[{index}] User: {turn.question}")
        lines.append(f"Assistant: {turn.answer}")
    return "\n".join(lines)


def looks_like_followup(query: str) -> bool:
    return _FOLLOWUP_CUES.search(query or "") is not None


def stub_contextualize(query: str, turns: Sequence[HistoryTurn]) -> str:
    """Deterministic standalone query. No network. Anchors cues to the latest question."""
    text = (query or "").strip()
    if not text or not turns or not looks_like_followup(text):
        return text
    anchor = turns[-1].question.strip()
    if not anchor or anchor in text:
        return text
    return f"{anchor} — {text}"


def _one_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip().strip('"').strip("'").strip()
        if cleaned:
            return cleaned
    return ""


def _llm_contextualize(
    query: str,
    turns: Sequence[HistoryTurn],
    config: Mapping[str, Any],
) -> tuple[str | None, str | None]:
    system = load_prompt("contextualize_system")
    history = format_history_block(turns)
    user = f"{history}\n\nFollow-up question:\n{query}"
    return try_openai_chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        config=dict(config),
        agent=True,
    )


def contextualize_query(
    query: str,
    turns: Sequence[HistoryTurn],
    *,
    config: Mapping[str, Any] | None = None,
) -> ContextualizeResult:
    """Rewrite a follow-up into a standalone search query.

    No history: return the question unchanged. With history and an OpenAI-compatible
    generator, ask the model; on failure use the stub. Stub mode never calls the network,
    and only rewrites questions that look like follow-ups.
    """
    text = (query or "").strip()
    if not turns:
        return ContextualizeResult(working_query=text, backend="none", changed=False)

    cfg = config or {}
    if generator_mode(agent=True) == "openai":
        llm_query, err = _llm_contextualize(text, turns, cfg)
        if llm_query and not err:
            cleaned = _one_line(llm_query)
            if cleaned:
                return ContextualizeResult(
                    working_query=cleaned,
                    backend="llm",
                    changed=cleaned != text,
                )
        stub_query = stub_contextualize(text, turns)
        return ContextualizeResult(
            working_query=stub_query,
            backend="stub",
            changed=stub_query != text,
            llm_fallback=err or "empty_contextualize",
        )

    stub_query = stub_contextualize(text, turns)
    return ContextualizeResult(
        working_query=stub_query,
        backend="stub",
        changed=stub_query != text,
    )
