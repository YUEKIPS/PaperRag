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
- **状态**：**已由 D-006 取代**（M1）
- **决策**：M0 索引为合并 JSONL + manifest，检索用语义弱的关键词 overlap。
- **背景**：先验证 ingest 链路与引用结构，再换向量索引。
- **后果**：M1 已替换 `build_index` / `retrieve_baseline`；遗留 `scaffold_jsonl` manifest 仍走关键词回退。

---

## D-006 — M1 嵌入与 FAISS 索引

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：Baseline 稠密检索使用 `sentence-transformers/all-MiniLM-L6-v2`（384 维），FAISS `IndexFlatIP` + L2 归一化向量；chunk 元数据与行序对齐的 `chunks_index.jsonl`。
- **背景**：CPU 友好、体量小，适合 12 篇论文 smoke；可在 M2 前再评估更大模型。
- **后果**：`requirements.txt` 启用 `sentence-transformers` / `faiss-cpu`；索引产物仅本地 `data/index/`。

---

## D-007 — M1 混合检索原型

- **日期**：2026-11-09
- **状态**：已接受（原型）
- **决策**：`build_index` 写入 BM25 分词侧车；`retrieve_baseline` 在 `hybrid.enabled` 时对 dense + BM25 做 RRF（k=60）。
- **背景**：验证混合检索接线，非生产级调参。
- **后果**：M2 可替换为独立 `retriever/hybrid.py`、调 pool size 与 rerank。

---

## D-008 — Baseline 生成策略

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：默认 **stub** 生成（摘录 + 页码引用）；可选 `BASELINE_GENERATOR=openai` + `OPENAI_API_KEY` 调用 OpenAI 兼容 `chat/completions`（stdlib `urllib`，无强制 openai 包）。
- **后果**：未配置 API 时 smoke 不依赖外网 LLM；文档须标明当前 generator 模式。

---

## D-005 — 不做虚假 aggregate 评测

- **日期**：2026-11-09
- **状态**：已接受（M2 更新）
- **决策**：`questions.json` 标为 draft；`eval_all.py` 只写定性 smoke 与 per-question 产物，**不输出 Recall@k 等编造总和**。
- **后果**：`data/eval/runs/` gitignore；报告见 `docs/reports/smoke_m2_agentic.md`。

---

## D-009 — M2 Cross-encoder rerank

- **日期**：2026-11-09
- **状态**：已接受（原型）
- **决策**：混合/RRF 召回后对 `candidate_pool`（默认 30）做交叉编码器重排；默认模型 `cross-encoder/ms-marco-MiniLM-L-6-v2`（CPU 友好）。可配置 `retriever.reranker.enabled: false` 或 CLI `--no-rerank`。
- **背景**：比 `BAAI/bge-reranker-base` 更轻，适合云端 smoke；README 文档可换 bge。
- **后果**：`src/rerank/cross_encoder.py`、`src/retriever/pipeline.py`；baseline 与 agentic 共用。

---

## D-010 — M2 LangGraph Agentic 环

- **日期**：2026-11-09
- **状态**：已接受（原型）
- **决策**：`langgraph` 实现 `decide → retrieve → grade → rewrite → generate`；`max_grade_rewrite_loops` 默认 2。Grade/rewrite/generate：默认 **stub**；`AGENT_GENERATOR` 或 `BASELINE_GENERATOR=openai` 时 grade/rewrite 可走 OpenAI 兼容 API（`src/generate/llm.py`）。
- **后果**：`requirements.txt` 启用 `langgraph` / `langchain-core`；decide 节点暂为透传，非学习型路由。

---

## D-011 — M3 生产向 LLM grade/rewrite（DeepSeek 兼容默认）

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：Grade/rewrite/generate 共用 `src/generate/llm.py` 薄 HTTP 客户端（stdlib `urllib`，`/chat/completions`）。API key 优先 `DEEPSEEK_API_KEY`，回退 `OPENAI_API_KEY`；`OPENAI_BASE_URL` 默认示例为 DeepSeek `https://api.deepseek.com/v1`；模型默认 `deepseek-chat`（`configs/default.yaml` `llm` 段可覆盖）。`AGENT_GENERATOR=openai` 表示「OpenAI 兼容 LLM」而非厂商锁定。系统提示词外置至 `prompts/*.txt`。无 key 或请求失败 → stub 回退，并在 trace 中记录 `llm_fallback`。
- **背景**：M2 已有最小 LLM 钩子；M3 对齐 RepoAgent  spirit（兼容端点 + 环境变量），不引入 model-config JSON / pydantic v3 配置体系。
- **后果**：`data/eval/questions.json` 增加弱相关 draft 题；`--exercise-rewrite` / `AGENT_STUB_STRICT_GRADE` 可在无 API 时强制走 rewrite 烟测；LLM 全环 smoke 需用户注入 key。

---

## D-012 — 本地 Web UI（stdlib HTTP）

- **日期**：2026-11-09
- **状态**：已接受（MVP）
- **决策**：在 `src/web/` 提供 **ThreadingHTTPServer + 静态 HTML/CSS/JS** 聊天 UI；仅绑定 `127.0.0.1`；`/api/*` 需 Bearer session token（启动时生成并注入页面）。会话 JSON 持久化于 `data/web/sessions/`（gitignore）。问答仍调用 `run_agentic_query`，不做 SSE 流式（客户端分阶段动效 + 打字式揭示）。
- **背景**：对齐 RepoAgent 本地 UI 心智（侧栏会话、主题、详情 inspector），范围限定论文 Q&A。
- **后果**：`scripts/serve_web.py`；README 增 Web 小节；不引入 React/Vite。
