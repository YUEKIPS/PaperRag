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

---

## D-013 — Web UI：会话右键菜单 + Markdown 回答

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：侧栏会话项支持 `contextmenu`（重命名 / 归档 / 删除），复用既有 PATCH/DELETE API；顶栏归档/删除保留。助手正文用 vendored `marked`（`src/web/static/vendor/marked.umd.js`）经 `markdown.js`  lexer → 安全 DOM（禁 raw HTML / 非 http(s) 链接）；历史加载与打字揭示完成后渲染 `.markdown-body`。`prompts/generate_system.txt` 要求 LLM 输出简洁 GFM。
- **背景**：对齐 RepoAgent 本地 UI 心智（library 右键、markdown-body），仍保持 localhost-only 与无 npm 构建链。
- **后果**：静态资源多 `markdown.js` + vendor；不改变 `src/web/security.py` 或 SSE 范围。

---

## D-014 — 回答语言跟随用户 + 会话删除导航

- **日期**：2026-11-09
- **状态**：已接受
- **决策**：`prompts/generate_system.txt` 要求生成语言与用户问题一致；`rewrite_system.txt` 仅补充「保留原问语言、不擅自翻译」。Web UI 删除/归档当前会话后：刷新列表 → 若有其它会话则切换至首个剩余会话 → **仅**在列表为空时 `POST` 新会话；DELETE/PATCH 失败用 toast 提示。
- **背景**：中文 UI 下英文固定回答体验差；删除当前会话立即新建导致「删不掉」观感。
- **后果**：`app.js` 增 `navigateAfterCurrentSessionRemoved` 与 `showToast`；grade 提示词不变（JSON 判定与语言无关）。

---

## D-015 — Web UI：本地论文库与 PDF 预览

- **日期**：2026-11-09
- **状态**：已接受（MVP）
- **决策**：侧栏增加「对话 / 论文库」切换；`GET /api/papers` 合并 `configs/default.yaml` `arxiv.paper_ids` 与 `data/raw_pdfs/*.pdf`；可选标题来自 `data/raw_pdfs/{id}.meta.json`（`title` 字段），否则 UI 仅展示 arXiv id。`GET /api/papers/{id}/pdf` 以 `application/pdf` 回传本地文件，复用 `_api_allowed()`（localhost + Bearer / `X-Session-Token`）。前端**不用** URL query token：`fetch` 带 Bearer → `Blob` → `URL.createObjectURL` 注入 `<object type="application/pdf">`，避免 iframe 无法带头与 token 泄漏。主区底部内嵌预览 +「插入提问」向 composer 写入 `关于论文 [id]：` 或追加 `[id]`。侧栏 tab 用下划线文字，不用与「新建对话」并列的描边胶囊。
- **背景**：用户需在本地浏览 M1 语料、对照 PDF 提问，不拉 arXiv 元数据、不引入 npm/React。初稿误用已占用的 D-014，更正为本条。
- **后果**：`src/web/papers.py`；`server.py` 增两条 GET；静态 `app.{html,css,js}` 扩展；无网络依赖。底部 `<object>` 预览已由 D-016 取代。

---

## D-016 — Web UI：右侧抽屉 + PDF.js 画布预览

- **日期**：2026-11-09
- **状态**：已接受（MVP）
- **决策**：点选论文库条目时，主区右侧滑出抽屉（可关闭、Esc 关闭），不再把浏览器 PDF 插件嵌在对话下方。PDF 仍由 `GET /api/papers/{id}/pdf` + Bearer 取回字节，交给 vendored PDF.js 4.8.69（`src/web/static/vendor/pdfjs/`，`pdf.min.mjs` + worker）画到 canvas。翻页与缩放用自有工具条，不用系统插件工具条。抽屉只盖住消息区右侧；底栏 composer 保持在抽屉之外，插入提问后可直接输入。关闭抽屉时焦点回到输入框。
- **背景**：底部半屏 `<object type="application/pdf">` 会拉起 Chrome 自带插件（深色工具条），阅读区过矮。
- **后果**：静态多 `pdf-view.js` 与 PDF.js vendor（Apache-2.0）；`.mjs` 以 `text/javascript` 提供给 module worker。不拉 arXiv，不引入 npm 构建。

---

## D-017 — 轻量多轮上下文（非 RepoAgent Session 栈）

- **日期**：2026-11-10
- **状态**：已接受
- **决策**：同一 Web 会话的后续提问，在 `/api/ask` 里读取**已有**问答（只要 question + answer，不拷贝引用），作为 `conversation` 传入 `run_agentic_query`。选择策略：最近 **6** 个完整轮，且 question+answer 的 UTF-8 合计不超过 **24000** 字节。超预算时先整轮丢掉更早的轮次，并计入 `omitted_turns`；只有最新一轮单独仍放不下时，才截断该轮回答（问题能放下就保留问题）。空问题或空回答不算完整轮，也不计入 omitted。本仓没有单独的模型输入预算旋钮，24KB 约按 ~96KB 文本预算的 1/4 取上限，写在 `agent.conversation`（`configs/default.yaml`）。
- **Agent**：`decide` 在第一次检索前把追问收成可独立检索的 `working_query`（无 API 时，stub 把「它 / 第二点 / this」这类指代锚到上一问；`AGENT_GENERATOR=openai` 时用 `prompts/contextualize_system.txt`，失败再回 stub）。原有 `rewrite` 仍是 grade 失败后的检索改写，并看到一段压缩历史，避免把已消解的实体改回代词。`retrieve` 只用 `working_query`，不把往轮引用当本轮证据。`generate` 附上历史块，并写明历史只用于消解指代；结论和引用必须来自本轮 chunk。
- **API / UI**：结果带 `history_included_turns`、`history_omitted_turns`、`history_policy`（以及 `history_truncated_answers`）。回答下方在任一计数非 0 时显示「带入 N 轮 / 省略 M 轮」。
- **明确不移植**：RepoAgent 的 ConversationSession 事件日志、Surface、RequestMeter、摘要服务、tool compaction。
- **后果**：`src/agent/history.py`、`tests/test_history.py`（无索引、无 live DeepSeek）。首问不显示 0/0 那一行。
