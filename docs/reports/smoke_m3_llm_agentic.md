# Smoke: M3 Agentic pipeline (LLM-ready grade/rewrite)

- **Run id**: `20261109-212916`
- **Timezone**: Asia/Shanghai
- **Generator mode**: `openai`
- **LLM endpoint**: mode=openai base_url=https://api.deepseek.com/v1 model=deepseek-chat api_key=set
- **Strict stub grade (--exercise-rewrite)**: False
- **Rerank**: enabled
- **Artifacts**: `C:\Users\yueki\Documents\ChatGPT\agentic-paper-rag\data\eval\runs\20261109-212916` (gitignored)

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
- **Grade**: passed=True — llm: The excerpts define RAG as augmenting LLMs with retrieved external knowledge (prepending relevant documents from an external corpus, combining parametric and non-parametric memory) and explain the problem it addresses: LLMs hallucinate because parametric knowledge alone cannot secure accuracy, and RAG complements LLMs by grounding generation in retrieved documents.
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q002

- **Query**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Working query after rewrite**: How do agentic RAG systems differ from a single-shot retrieve-then-generate pipeline?
- **Grade**: passed=True — llm: The excerpts describe SELF-RAG's agentic behavior (adaptive/on-demand retrieval, concurrent passage evaluation, self-critique tokens, tree-decoding) and contrast it with conventional RAG that retrieves indiscriminately in a single pass, providing enough specific detail to answer how agentic RAG differs from single-shot retrieve-then-generate.
- **Rewrite iterations**: 0
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q003

- **Query**: What role does chunking strategy play in PDF-based scientific paper retrieval?
- **Working query after rewrite**: How do document chunking strategies—chunk size, chunk overlap, and semantic versus fixed-length splitting—affect retrieval quality and retrieval-augmented gener
- **Grade**: passed=False — llm: The excerpts discuss RAG frameworks (Self-RAG, CRAG) and retrieval correction, but contain no information about document chunking strategies, chunk size, chunk overlap, semantic vs fixed-length splitting, or empirical findings on optimal chunking for PDF scientific papers.
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q004

- **Query**: Why might hybrid retrieval (dense + sparse) help on technical LLM papers?
- **Working query after rewrite**: Why does hybrid retrieval that combines dense embedding-based search with sparse BM25/keyword search improve retrieval quality and recall for RAG over technical
- **Grade**: passed=False — llm: The excerpts discuss RAG's dense retriever vs BM25 in isolation (noting BM25 wins on entity-centric FEVER) but do not describe hybrid retrieval combining dense and sparse methods, nor provide evidence/rationale for complementary strengths in a hybrid setup. They lack the core facts needed to answer why hybrid retrieval improves quality/recall.
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q005

- **Query**: What should a good answer citation include when answers come from arXiv PDFs?
- **Working query after rewrite**: What should a good answer citation include when answers are generated from arXiv PDFs in retrieval-augmented generation (RAG) systems, specifically covering cit
- **Grade**: passed=False — llm: The excerpts discuss RAG systems, retrieval relevance, and hallucination concerns, but none address citation practices—source document citation, page/section references, chunk-level provenance, or attribution of generated answers to retrieved evidence. They are off-topic for the specific question asked.
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q006

- **Query**: What is Room-Temperature Zettabyte SRAM latency in pre-Unix punch-card folklore?
- **Working query after rewrite**: How do LLM and RAG research papers characterize the latency of room-temperature zettabyte-scale SRAM, and do any discuss pre-Unix punch-card computing folklore 
- **Grade**: passed=False — llm: The excerpts discuss RAG and LLM hallucination/factuality but contain no information about room-temperature zettabyte-scale SRAM latency, nor any mention of pre-Unix punch-card computing folklore or historical computing anecdotes.
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

### q007

- **Query**: List the hyperbolic fungal embedding loss for Victorian-era mimeograph punch-card parsers.
- **Working query after rewrite**: What loss function is used for hyperbolic embeddings of fungal taxonomy data, and how does it compare to embedding methods relevant to historical punch-card or 
- **Grade**: passed=False — llm: The excerpts only contain generic definitions of word embeddings from a single NLP paper; they say nothing about hyperbolic embeddings, fungal taxonomy data, loss functions, or punch-card/mimeograph document parsing methods.
- **Rewrite iterations**: 2
- **Chunks used**: 5
- **Generator**: openai
- **Citations**: 5

## Observations

- LangGraph path `decide → retrieve → grade → rewrite → generate` completed for all items.
- Rewrite loop exercised (iterations > 0 on at least one question): **True**.
- Prompts live under `prompts/*.txt`; HTTP client in `src/generate/llm.py`.
- Inspect per-question JSON under the run directory for `backend`, `llm_fallback`, and trace payloads.
