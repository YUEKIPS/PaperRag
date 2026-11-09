from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.agent.run import AgenticResult, run_agentic_query
from src.config import resolve_eval_runs_dir, resolve_path


@dataclass
class EvalRunMeta:
    run_id: str
    timezone: str
    generator_mode: str
    rerank_enabled: bool
    num_questions: int
    config_path: str


@dataclass
class QuestionRun:
    question_id: str
    text: str
    result: dict[str, Any] = field(default_factory=dict)


def _shanghai_now() -> datetime:
    return datetime.now(tz=ZoneInfo("Asia/Shanghai"))


def run_agentic_eval(
    config: dict[str, Any],
    *,
    config_path: Path,
    limit: int | None = None,
    rerank_override: bool | None = None,
) -> tuple[Path, list[QuestionRun], EvalRunMeta]:
    from src.generate.llm import generator_mode
    from src.retriever.pipeline import _rerank_cfg

    eval_path = resolve_path(config, "eval_questions")
    data = json.loads(eval_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    if limit is not None:
        questions = questions[:limit]

    index_dir = resolve_path(config, "index")
    out_root = resolve_eval_runs_dir(config)

    run_id = _shanghai_now().strftime("%Y%m%d-%H%M%S")
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    r_cfg = _rerank_cfg(config)
    rerank_on = bool(r_cfg.get("enabled", False))
    if rerank_override is not None:
        rerank_on = rerank_override

    meta = EvalRunMeta(
        run_id=run_id,
        timezone="Asia/Shanghai",
        generator_mode=generator_mode(agent=True),
        rerank_enabled=rerank_on,
        num_questions=len(questions),
        config_path=str(config_path),
    )
    (run_dir / "meta.json").write_text(
        json.dumps(asdict(meta), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    runs: list[QuestionRun] = []
    for q in questions:
        qid = str(q.get("id", "unknown"))
        text = str(q.get("text", ""))
        ar: AgenticResult = run_agentic_query(
            text,
            index_dir,
            config,
            rerank_enabled=rerank_override,
        )
        payload = {
            "query": ar.query,
            "working_query": ar.working_query,
            "grade_passed": ar.grade_passed,
            "grade_reason": ar.grade_reason,
            "iterations": ar.iterations,
            "generator": ar.generator,
            "num_chunks": ar.num_chunks,
            "citations": ar.citations,
            "answer_preview": ar.answer[:2000],
            "trace": ar.trace,
        }
        (run_dir / f"{qid}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        runs.append(QuestionRun(question_id=qid, text=text, result=payload))

    summary = {
        "meta": asdict(meta),
        "questions": [{"id": r.question_id, "grade_passed": r.result.get("grade_passed")} for r in runs],
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return run_dir, runs, meta


def write_smoke_report(
    report_path: Path,
    meta: EvalRunMeta,
    runs: list[QuestionRun],
    *,
    run_dir: Path,
    ablation_note: str = "",
) -> None:
    lines = [
        "# Smoke: M2 Agentic pipeline",
        "",
        f"- **Run id**: `{meta.run_id}`",
        f"- **Timezone**: {meta.timezone}",
        f"- **Generator**: `{meta.generator_mode}` (stub default; set `AGENT_GENERATOR=openai` or `BASELINE_GENERATOR=openai` + `OPENAI_API_KEY` for LLM nodes)",
        f"- **Rerank**: {'enabled' if meta.rerank_enabled else 'disabled'}",
        f"- **Artifacts**: `{run_dir}` (gitignored)",
        "",
        "## Scope",
        "",
        "Qualitative smoke over draft `data/eval/questions.json`. **No aggregate Recall@k or accuracy totals.**",
        "",
        "## Per-question notes",
        "",
    ]
    for r in runs:
        res = r.result
        lines.extend(
            [
                f"### {r.question_id}",
                "",
                f"- **Query**: {r.text[:200]}{'…' if len(r.text) > 200 else ''}",
                f"- **Working query after rewrite**: {res.get('working_query', '')[:160]}",
                f"- **Grade**: passed={res.get('grade_passed')} — {res.get('grade_reason')}",
                f"- **Rewrite iterations**: {res.get('iterations')}",
                f"- **Chunks used**: {res.get('num_chunks')}",
                f"- **Citations**: {len(res.get('citations') or [])}",
                "",
            ]
        )

    if ablation_note:
        lines.extend(["## Ablation (qualitative)", "", ablation_note, ""])

    lines.extend(
        [
            "## Observations",
            "",
            "- LangGraph path `decide → retrieve → grade → rewrite → generate` completed for all items.",
            "- Grade/rewrite use deterministic stubs without API; generation follows baseline stub unless OpenAI env is set.",
            "- Inspect per-question JSON under the run directory for retrieval trace and citation payloads.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
