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

- [ ] PyMuPDF 解析质量抽检（公式 / 多栏 — 按论文抽样）
- [ ] 嵌入模型 + FAISS（或等价）向量索引
- [ ] 可选：BM25 并行索引与 RRF 原型
- [ ] `run_baseline` 接 LLM（环境变量配置）或稳定本地 stub 策略
- [ ] 引用格式文档化 + 5 题 smoke eval（**记录过程，不编造 aggregate 分数**）
- [ ] `docs/guides/ingest.md` 操作说明

### M2 — Agentic + 混合检索强化

- [ ] LangGraph 编排（decide → retrieve → grade → rewrite → generate）
- [ ] Reranker 接入
- [ ] `run_agentic.py`、`eval_all.py` 实装
- [ ] 对比实验报告入 `docs/reports/`

## 本轮之后建议的下一步（本地 / 云端 M1）

1. `pip install -r requirements.txt` 并执行完整四步流水线
2. 在 `src/indexer/build.py` 接入 `sentence-transformers` + FAISS
3. 扩展 `retriever/baseline.py` 或新增 `retriever/hybrid.py`
4. 更新日报与 `docs/decisions.md`（嵌入模型选型）

## 风险

| 风险 | 缓解 |
|------|------|
| PDF 解析噪声 | 页级元数据 + 人工 spot check |
| arXiv 限速 | `request_delay_seconds` + 本地缓存 |
| Agent 幻觉引用 | grade 节点校验 chunk 是否支撑陈述（M2） |
