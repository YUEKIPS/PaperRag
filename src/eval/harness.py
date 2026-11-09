from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.agent.run import AgenticResult, run_agentic_query
from src.config import resolve_eval_runs_dir, resolve_path
from src.generate.llm import llm_endpoint_summary


@dataclass
class EvalRunMeta:
    run_id: str
    timezone: str
    generator_mode: str
    rerank_enabled: bool
    num_questions: int
    config_path: str
    llm_endpoint: str
    exercise_strict_grade: bool


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
    exercise_strict_grade: bool = False,
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
        llm_endpoint=llm_endpoint_summary(config),
        exercise_strict_grade=exercise_strict_grade,
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
            exercise_strict_grade=exercise_strict_grade,
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
        "questions": [
            {
                "id": r.question_id,
                "grade_passed": r.result.get("grade_passed"),
                "iterations": r.result.get("iterations"),
            }
            for r in runs
        ],
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
    milestone: str = "M3",
) -> None:
    rewrite_counts = [int(r.result.get("iterations") or 0) for r in runs]
    any_rewrite = any(n > 0 for n in rewrite_counts)

    lines = [
        f"# Smoke: {milestone} Agentic pipeline (LLM-ready grade/rewrite)",
        "",
        f"- **Run id**: `{meta.run_id}`",
        f"- **Timezone**: {meta.timezone}",
        f"- **Generator mode**: `{meta.generator_mode}`",
        f"- **LLM endpoint**: {meta.llm_endpoint}",
        f"- **Strict stub grade (--exercise-rewrite)**: {meta.exercise_strict_grade}",
        f"- **Rerank**: {'enabled' if meta.rerank_enabled else 'disabled'}",
        f"- **Artifacts**: `{run_dir}` (gitignored)",
        "",
        "## LLM env (DeepSeek-compatible default)",
        "",
        "```bash",
        "export AGENT_GENERATOR=openai",
        "export DEEPSEEK_API_KEY=...",
        "# optional: OPENAI_API_KEY, OPENAI_BASE_URL=https://api.deepseek.com/v1, OPENAI_MODEL=deepseek-chat",
        "```",
        "",
        "Without a key, grade/rewrite/generate use **stub** paths; trace entries may include `llm_fallback` when mode is openai but the key or request fails.",
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
                f"- **Generator**: {res.get('generator')}",
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
            f"- Rewrite loop exercised (iterations > 0 on at least one question): **{any_rewrite}**.",
            "- Prompts live under `prompts/*.txt`; HTTP client in `src/generate/llm.py`.",
            "- Inspect per-question JSON under the run directory for `backend`, `llm_fallback`, and trace payloads.",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
