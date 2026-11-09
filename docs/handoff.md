# 交接说明

最后更新：2026-11-09

## 仓库状态

- **已完成**：M0 + **M1 Baseline** + **M2 Agentic 原型**（LangGraph、cross-encoder rerank、`run_agentic` / `eval_all` 定性 smoke）
- **未完成**：生产级 grade、Recall@k 自动指标、ColBERT / 大 rerank、学习型 decide

## 本地 / 云端继续 checklist

1. Clone / pull（本 PR 合并后的 `main`）
2. `pip install -r requirements.txt`（含 `langgraph`）
3. 四步 CLI：`download_pdfs` → `ingest` → `build_index` → `run_baseline` 或 `run_agentic`（见 [guides/ingest.md](guides/ingest.md)）
4. 可选 LLM：`BASELINE_GENERATOR=openai` 或 `AGENT_GENERATOR=openai` + `OPENAI_API_KEY`
5. 批量定性 eval：`python3 scripts/eval_all.py --limit 5`（产物在 `data/eval/runs/`）
6. Rerank 消融：`--no-rerank` on baseline / agentic / eval_all

## 联系人 / 上下文

- 立项说明附件：`PROJECT_BRIEF`（RAG 项目助手，2026-11-09）
- 时区：Asia/Shanghai

## 私有 Origin 仓库

Origin：`yuekips/agentic-paper-rag`（显示名建议 **agentic-paper-rag**）
