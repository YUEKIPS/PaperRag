# 交接说明

最后更新：2026-11-09

## 仓库状态

- **已完成**：M0 文档、Git 基线、download → ingest → index → baseline 脚手架
- **未完成**：Agentic LangGraph、向量/FAISS 索引、rerank、`eval_all` 指标

## 本地继续 M1  checklist

1. Clone / pull 当前 `main`
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. 跑通四步 CLI（见根 `README.md`）
4. 实现向量索引并更新 `docs/decisions.md`（嵌入模型选型）
5. 日报写入 `docs/devlog/daily/YYYY-MM-DD.md`

## 联系人 / 上下文

- 立项说明附件：`PROJECT_BRIEF`（RAG 项目助手，2026-11-09）
- 时区：Asia/Shanghai

## 私有 Origin 仓库

建议在 Origin 将显示名设为 **agentic-paper-rag**（若当前为临时仓库名，可在控制台重命名后更新 remote URL）。
