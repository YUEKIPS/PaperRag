# 决策记录

格式：日期 · 状态 · 决策 · 背景 · 后果

---

## D-001 — 技术路线 A+C

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：以自研 Python 管线（A）为主，复用成熟组件做底层（C）：PyMuPDF、FAISS / sentence-transformers、LangGraph（后续）。
- **背景**：需要可控引用与评测；避免重度黑盒 SaaS。
- **后果**：代理可在本仓直接改脚本与 `src/`；LLM API 通过环境变量注入。

---

## D-002 — 与 RepoAgent 互补

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：RepoAgent 专注代码仓库；本项目专注论文 PDF 知识库；开发日志格式对齐 RepoAgent `docs/devlog`。
- **后果**：日志模板与 AGENTS 规则一致，便于同一负责人切换上下文。

---

## D-003 — M1 语料固定清单

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：首批 12 个 arXiv ID 写入 `configs/default.yaml`，`download_pdfs.py` 唯一真理源。
- **后果**：扩展语料只改配置 + 文档，不改下载脚本逻辑。

---

## D-004 — 脚手架索引用 JSONL

- **日期**：2026-11-09
- **状态**：已接受（临时）
- **决策**：M0 索引为合并 JSONL + manifest，检索用语义弱的关键词 overlap。
- **背景**：先验证 ingest 链路与引用结构，再换向量索引。
- **后果**：M1 必须替换 `build_index` / `retrieve_baseline` 实现；manifest 字段预留 `embedding_model`。

---

## D-005 — 不做 M0 虚假评测

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：`questions.json` 标为 draft；`eval_all.py` 保持 stub。
- **后果**：对外分享前需跑真实 eval 并写 `docs/reports/`。
