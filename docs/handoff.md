# 交接说明

最后更新：2026-11-09

## 仓库状态

- **已完成**：M0 文档与脚手架；**M1 Baseline RAG**（FAISS、`all-MiniLM-L6-v2`、BM25/RRF 原型、baseline stub/可选 LLM）
- **未完成**：LangGraph Agentic、rerank 生产化、`eval_all.py` aggregate 评测

## 本地 / 云端继续 checklist

1. Clone / pull（本 PR 合并后的 `main`）
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. 四步 CLI：`download_pdfs` → `ingest` → `build_index` → `run_baseline`（见 [guides/ingest.md](guides/ingest.md)）
4. 可选 LLM：`BASELINE_GENERATOR=openai` + `OPENAI_API_KEY`
5. M2：LangGraph + rerank；更新 `docs/decisions.md` 与 `docs/reports/`

## 联系人 / 上下文

- 立项说明附件：`PROJECT_BRIEF`（RAG 项目助手，2026-11-09）
- 时区：Asia/Shanghai

## 私有 Origin 仓库

Origin：`yuekips/agentic-paper-rag`（显示名建议 **agentic-paper-rag**）
