# Agentic Paper RAG

面向 LLM / Agent 论文库的 **Agentic RAG**：检索工具化 + grade + rewrite（LangGraph 编排），底层混合检索（向量 + BM25 / RRF）+ rerank + 带页码引用。

与 [RepoAgent](https://github.com/)（代码仓 Agent）互补：RepoAgent 管代码仓库；本项目管 **非代码论文知识库**。

> **当前状态（2026-11-09）**：**M4** — 在 M3 LLM 钩子之上增加 **本地 Web 问答 UI**（`run_web.py` / `127.0.0.1`）。无 Recall@k aggregate；decide 路由学习与 ColBERT 级 rerank **未** 做。

## 功能模块（目标）

| 模块 | 说明 |
|------|------|
| `parser` | PDF 解析（PyMuPDF） |
| `indexer` | 分块、FAISS 向量 / BM25 侧车 |
| `embed` | `src/indexer/embed.py` — sentence-transformers |
| `retriever` | 稠密 + RRF（`pipeline.py`） |
| `rerank` | Cross-encoder 重排（可 `--no-rerank`） |
| `agent` | LangGraph：decide → retrieve → grade → rewrite → generate |
| `generate` | 带引用的回答生成 |
| `eval` | 离线评测 |
| `web` | 本地 stdlib HTTP + 静态页问答 UI |

## 环境要求

- Python 3.11+
- 磁盘：存放 `data/raw_pdfs/`（约 12 篇 M1 论文，数十 MB）；首次 `build_index` 会下载嵌入模型权重

## 安装

```bash
cd agentic-paper-rag   # 仓库根目录
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

配置见 `configs/default.yaml`。敏感信息放 `.env` 或环境变量（已在 `.gitignore` 中忽略 `.env`）。

### 可选：LLM（OpenAI-compatible，默认示例 DeepSeek）

```bash
# Agentic grade + rewrite + generate（推荐）
export AGENT_GENERATOR=openai
export DEEPSEEK_API_KEY=...

# Baseline-only generation（不设 AGENT_GENERATOR 时）
export BASELINE_GENERATOR=openai

# 也可用 OPENAI_API_KEY；其它兼容端点：
# export OPENAI_BASE_URL=https://api.deepseek.com/v1   # default in configs/default.yaml
# export OPENAI_MODEL=deepseek-chat                    # or gpt-4o-mini, etc.
```

未设置 key 时节点回退 **stub**（摘录 + 引用）；trace 会记录 `llm_fallback`。适合无 API 烟测。

`AGENT_GENERATOR=openai` 表示「兼容 chat/completions LLM」，不是 OpenAI 厂商锁定。Agentic 节点优先读 `AGENT_GENERATOR`，否则回退 `BASELINE_GENERATOR`。

Rewrite 环烟测（无 API）：`run_agentic.py --exercise-rewrite` 或 eval 题 `q006`/`q007`。

## 快速路径：download → ingest → index → baseline / agentic

在仓库根目录执行：

```bash
# 1) 下载 M1 arXiv PDF（列表见 configs/default.yaml）
python3 scripts/download_pdfs.py

# 2) 解析 PDF 并写出分块 JSONL → data/processed/
python3 scripts/ingest.py

# 3) 构建 FAISS 索引（+ 可选 BM25 侧车）→ data/index/
python3 scripts/build_index.py

# 4) 基线：稠密/混合检索 + rerank + 生成
python3 scripts/run_baseline.py --query "What is retrieval-augmented generation?"

# 5) Agentic LangGraph
python3 scripts/run_agentic.py --query "How do agentic RAG systems differ from single-shot RAG?"

# 5 题定性 eval
python3 scripts/eval_all.py --limit 5
```

### 本地 Web UI（论文问答）

构建索引后可在本机浏览器使用多会话聊天界面（stdlib HTTP + 静态资源，**仅绑定 127.0.0.1**）：

```bash
python3 scripts/serve_web.py
# 默认 http://127.0.0.1:8765/
```

功能：左侧 **对话 / 论文库** 切换（论文列表、点选后右侧抽屉用 vendored **PDF.js** 画布预览、**插入提问** 写入 `[arXiv id]`）；会话列表（持久化在 `data/web/sessions/`，已 gitignore；**右键**重命名 / 归档 / 删除）、Ink/Slate/Sand 主题、composer 进度与分阶段展示、助手回答 **Markdown 渲染**（vendored `marked` + 安全 DOM）、回答详情（grade / rewrite / trace / citations）。API 需页面内注入的 session token；PDF 仍由前端 `fetch` + Bearer 取字节（无 URL token），不使用浏览器 PDF 插件；后端调用 `run_agentic_query`；generate 提示词要求模型输出简洁 Markdown。

详细步骤与引用格式：[docs/guides/ingest.md](docs/guides/ingest.md)。  
Smoke 记录：[docs/reports/smoke_m1_baseline.md](docs/reports/smoke_m1_baseline.md)、[docs/reports/smoke_m2_agentic.md](docs/reports/smoke_m2_agentic.md)、[docs/reports/smoke_m3_llm_agentic.md](docs/reports/smoke_m3_llm_agentic.md)。

## 仓库布局

```
agentic-paper-rag/
  AGENTS.md
  configs/default.yaml
  data/raw_pdfs/ data/processed/ data/index/ data/eval/
  docs/          # 需求、计划、架构、开发日志
  scripts/       # CLI 入口
  src/           # 库代码
```

详细文档索引见 [docs/README.md](docs/README.md)。

## 文档与协作

- 代理 / 自动化协作规范：[AGENTS.md](AGENTS.md)
- 开发日志（Asia/Shanghai）：[docs/devlog/README.md](docs/devlog/README.md)

## 许可证

待定（M1 前补充）。
