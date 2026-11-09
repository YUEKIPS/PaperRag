# 项目计划

更新：2026-11-09（Asia/Shanghai）

## 里程碑

### M0 — 文档 + Git 基线 + 脚手架 ✅（本轮交付）

- [x] 仓库结构、`README` / `AGENTS.md` / `docs/*`
- [x] `docs/devlog` 与 2026-11-09 日报、2026-11 月报初稿
- [x] `.gitignore`、`requirements.txt`、`configs/default.yaml`
- [x] `download_pdfs` / `ingest` / `build_index` / `run_baseline` 最小可运行链
- [x] `data/eval/questions.json` draft 占位题
- [ ] **未做**：Agentic、混合检索生产化、真实 LLM 生成、评测报表

### M1 — 可演示的 Baseline RAG

- [x] PyMuPDF 解析：12 篇 ingest 烟测（2695 chunks）；公式 / 多栏未做专项抽检
- [x] 嵌入模型 `all-MiniLM-L6-v2` + FAISS 向量索引（`data/index/`，gitignore）
- [x] BM25 侧车 + 检索时 RRF 原型（`index.hybrid.enabled: true`）
- [x] `run_baseline`：dense/hybrid 检索 + stub 默认；`BASELINE_GENERATOR=openai` 可选 LLM
- [x] 引用格式 + 5 题 smoke（见 `docs/reports/smoke_m1_baseline.md`，无 aggregate 分数）
- [x] `docs/guides/ingest.md` 操作说明

### M2 — Agentic + 混合检索强化

- [x] LangGraph 编排（decide → retrieve → grade → rewrite → generate），`src/agent/graph.py`
- [x] Cross-encoder rerank（`retriever.reranker`，`--no-rerank` 消融）
- [x] `run_agentic.py`、`eval_all.py` 实装；产物 `data/eval/runs/`（gitignore）
- [x] 烟测报告 `docs/reports/smoke_m2_agentic.md`（定性，无 aggregate Recall@k）
- [ ] **未做**：ColBERT、自动召回指标、decide 路由学习

### M3 — LLM grade/rewrite（DeepSeek 兼容）✅（本轮交付）

- [x] `prompts/*.txt` + `src/generate/llm.py`（`DEEPSEEK_API_KEY` / `OPENAI_BASE_URL` 默认 DeepSeek）
- [x] Grade JSON `{passed, reason}`、rewrite 单线输出；失败回退 stub + trace
- [x] `--exercise-rewrite`、弱相关 eval 题 q006–q007；报告 `docs/reports/smoke_m3_llm_agentic.md`
- [ ] **未在本环境验证**：有 API key 时的全 LLM 环与 rewrite 次数（依赖用户注入 key）

### M4 — 本地 Web 问答 UI ✅（本轮交付）

- [x] `src/web/`：`ThreadingHTTPServer` 仅 `127.0.0.1`、会话 token + `/api/health` `/api/ask`
- [x] 静态页：回答、引用（paper_id / page / chunk_id）、grade / rewrite / trace 折叠面板
- [x] `scripts/run_web.py`、`python -m src.web`；可选根目录 `.env` 加载
- [ ] **未在本环境验证**：有索引时的浏览器端到端（云端快照无 `data/index/`）；本地 `build_index` 后手动打开 UI

## 本轮之后建议的下一步（M5+）

1. 公式/多栏 PDF spot check；必要时调 chunk 策略
2. 在 `eval_all` 上追加人工标注 gold chunk，再讨论是否做 Recall@k（仍不编造数字）
3. 评估更大 rerank（如 `BAAI/bge-reranker-base`）与嵌入模型升级
4. 学习型 decide 路由

## 风险

| 风险 | 缓解 |
|------|------|
| PDF 解析噪声 | 页级元数据 + 人工 spot check |
| arXiv 限速 | `request_delay_seconds` + 本地缓存 |
| Agent 幻觉引用 | grade 节点校验 chunk 是否支撑陈述（M2） |
