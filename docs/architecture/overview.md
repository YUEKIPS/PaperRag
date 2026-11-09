# 架构概览

## 数据流（目标态）

```mermaid
flowchart LR
  PDF[arXiv PDFs] --> Parser
  Parser --> Chunks[Chunk store]
  Chunks --> Indexer[Vector + BM25]
  Indexer --> Store[(Index)]

  Q[User query] --> Orch[LangGraph orchestrator]
  Orch --> Ret[Retriever]
  Ret --> Store
  Ret --> Rerank[Reranker]
  Rerank --> Gen[Generator]
  Gen --> Ans[Answer + citations]
```

## 当前实现（M6）

多轮（D-017）：Web 会话里已完成的问答在下一次 `/api/ask` 进入 `decide`。`decide` 把追问收成 `working_query` 再检索；历史不作为命中证据。`generate` 只把历史用于消解指代，引用仍来自本轮 chunk。上限为最近 6 轮且 question+answer ≤ 24000 UTF-8 字节。

## 当前实现（M2 检索环，仍有效）

- **Parser**：`src/parser/pdf_parser.py`（PyMuPDF，页文本 + 固定字符分块 512/64）
- **Indexer**：`src/indexer/build.py` — sentence-transformers 嵌入 + FAISS；可选 BM25 侧车
- **Retriever**：`retriever/baseline.py` 稠密 + RRF；`retriever/pipeline.py` 统一入口 + 可选 rerank
- **Reranker**：`src/rerank/cross_encoder.py`（CrossEncoder，`retriever.reranker` 配置）
- **Generator / LLM**：`generate/baseline.py` + `generate/llm.py`（stub / OpenAI 兼容；默认 DeepSeek 端点示例）
- **Prompts**：`prompts/*.txt`（contextualize / grade / rewrite / generate）
- **Orchestrator**：`src/agent/graph.py`（LangGraph）；CLI `scripts/run_agentic.py`；多轮选择在 `src/agent/history.py`
- **Eval**：`scripts/eval_all.py` → `data/eval/runs/` + `docs/reports/smoke_m2_agentic.md`

## 配置与入口

- 配置：`configs/default.yaml`
- CLI：`scripts/*.py`
- 库：`src/`

## 部署形态（远期）

单机 / 云端代理均可：无状态 API 可选；索引与 PDF 本地磁盘或对象存储。
