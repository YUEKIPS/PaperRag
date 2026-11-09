# Smoke: M2 Agentic pipeline

- **Run id**: `20261109-190318`
- **Timezone**: Asia/Shanghai
- **Generator**: `stub` (stub default; set `AGENT_GENERATOR=openai` or `BASELINE_GENERATOR=openai` + `OPENAI_API_KEY` for LLM nodes)
- **Rerank**: enabled
- **Artifacts**: `/agent/repos/agentic-paper-rag/data/eval/runs/20261109-190318` (gitignored)

## Scope

Qualitative smoke over draft `data/eval/questions.json`. **No aggregate Recall@k or accuracy totals.**

## Per-question notes

### q001

- **Query**: What is retrieval-augmented generation (RAG), and what problem does it address for large language models?
- **Working query after rewrite**: What is retrieval-augmented generation (RAG), and what problem does it address for large language models?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=5
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Citations**: 5

### q002

- **Query**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Working query after rewrite**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=5
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Citations**: 5

### q003

- **Query**: What role does chunking strategy play in PDF-based scientific paper retrieval?
- **Working query after rewrite**: What role does chunking strategy play in PDF-based scientific paper retrieval?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Citations**: 5

### q004

- **Query**: Why might hybrid retrieval (dense + sparse) help on technical LLM papers?
- **Working query after rewrite**: Why might hybrid retrieval (dense + sparse) help on technical LLM papers?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Citations**: 5

### q005

- **Query**: What should a good answer citation include when answers come from arXiv PDFs?
- **Working query after rewrite**: What should a good answer citation include when answers come from arXiv PDFs?
- **Grade**: passed=True — stub_overlap_ok matched_chunks=4
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Citations**: 5

## Corpus / index (cloud smoke)

- 12 arXiv PDFs → 2695 chunks (512/64), same M1 manifest (`faiss_dense`, hybrid BM25+RRF enabled).
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` over a pool of 30 hybrid hits → `retriever.top_k` 10, agent `max_context_chunks` 5.

## Ablation (qualitative, not scored)

On `"What is retrieval-augmented generation?"`, top-3 `paper_id` order:

| Rerank | Top-3 papers |
|--------|----------------|
| on | `2310.11511`, `2401.15884`, `2401.15884` |
| off | `2401.15884`, `2310.11511`, `2401.15884` |

Rerank swaps rank-1/2 on this query; no aggregate metric computed. Draft eval items all passed stub grade on first pass (rewrite loop not exercised).

## Observations

- LangGraph path `decide → retrieve → grade → rewrite → generate` completed for all five draft questions on cloud VM.
- Grade/rewrite use deterministic stubs without API; generation follows baseline stub unless `AGENT_GENERATOR=openai` / `BASELINE_GENERATOR=openai` + `OPENAI_API_KEY`.
- Inspect per-question JSON under the run directory for retrieval trace and citation payloads.
- **Deferred**: learned decide router, ColBERT rerank, automated Recall@k, production-grade LLM grading prompts.
