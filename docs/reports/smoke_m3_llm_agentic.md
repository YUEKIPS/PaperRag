# Smoke: M3 Agentic pipeline (LLM-ready grade/rewrite)

- **Run id**: `20261109-204908`
- **Timezone**: Asia/Shanghai
- **Generator mode**: `stub`
- **LLM endpoint**: mode=stub base_url=https://api.deepseek.com/v1 model=deepseek-chat api_key=missing
- **Strict stub grade (--exercise-rewrite)**: False
- **Rerank**: enabled
- **Artifacts**: `/agent/repos/agentic-paper-rag/data/eval/runs/20261109-204908` (gitignored)

## LLM env (DeepSeek-compatible default)

```bash
export AGENT_GENERATOR=openai
export DEEPSEEK_API_KEY=...
# optional: OPENAI_API_KEY, OPENAI_BASE_URL=https://api.deepseek.com/v1, OPENAI_MODEL=deepseek-chat
```

Without a key, grade/rewrite/generate use **stub** paths; trace entries may include `llm_fallback` when mode is openai but the key or request fails.

## Scope

Qualitative smoke over draft `data/eval/questions.json`. **No aggregate Recall@k or accuracy totals.**

## Per-question notes

### q001

- **Query**: What is retrieval-augmented generation (RAG), and what problem does it address for large language models?
- **Working query after rewrite**: What is retrieval-augmented generation (RAG), and what problem does it address for large language models?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=5 coverage=0.69
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q002

- **Query**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Working query after rewrite**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=5 coverage=0.50
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q003

- **Query**: What role does chunking strategy play in PDF-based scientific paper retrieval?
- **Working query after rewrite**: What role does chunking strategy play in PDF-based scientific paper retrieval?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4 coverage=0.45
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q004

- **Query**: Why might hybrid retrieval (dense + sparse) help on technical LLM papers?
- **Working query after rewrite**: Why might hybrid retrieval (dense + sparse) help on technical LLM papers?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4 coverage=0.40
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q005

- **Query**: What should a good answer citation include when answers come from arXiv PDFs?
- **Working query after rewrite**: What should a good answer citation include when answers come from arXiv PDFs?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4 coverage=0.50
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q006

- **Query**: What is Room-Temperature Zettabyte SRAM latency in pre-Unix punch-card folklore?
- **Working query after rewrite**: What is Room-Temperature Zettabyte SRAM latency in pre-Unix punch-card folklore? — explain with definitions from the cited papers
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4 coverage=0.39
- **Rewrite iterations**: 1
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

### q007

- **Query**: List the hyperbolic fungal embedding loss for Victorian-era mimeograph punch-card parsers.
- **Working query after rewrite**: List the hyperbolic fungal embedding loss for Victorian-era mimeograph punch-card parsers. — explain with definitions from the cited papers — explain with defin
- **Grade**: passed=False — stub_token_coverage_low coverage=0.32
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: stub
- **Citations**: 5

## Observations

- LangGraph path `decide → retrieve → grade → rewrite → generate` completed for all items.
- Rewrite loop exercised (iterations > 0 on at least one question): **True** (q006: 1, q007: 2 on stub grade).
- **LLM path**: not run in this cloud VM (`api_key=missing`). With `AGENT_GENERATOR=openai` and no key, grade stays on stub and trace records `llm_fallback: No API key: set DEEPSEEK_API_KEY or OPENAI_API_KEY`.
- Prompts live under `prompts/*.txt`; HTTP client in `src/generate/llm.py`.
- Inspect per-question JSON under the run directory for `backend`, `llm_fallback`, and trace payloads.
