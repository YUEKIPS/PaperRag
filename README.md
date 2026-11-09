# Agentic Paper RAG

面向 LLM / Agent 论文库的 **Agentic RAG**：检索工具化 + grade + rewrite（LangGraph 编排），底层混合检索（向量 + BM25 / RRF）+ rerank + 带页码引用。

与 [RepoAgent](https://github.com/)（代码仓 Agent）互补：RepoAgent 管代码仓库；本项目管 **非代码论文知识库**。

> **当前状态（2026-11-09）**：**M2 Agentic 原型** 已落地 — M1 索引链 + **cross-encoder rerank** + **LangGraph**（grade/rewrite 环）+ `run_agentic` / `eval_all` 定性 smoke。无 Recall@k aggregate；decide 路由与 ColBERT 级 rerank **未** 做。

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

### 可选：LLM 生成

```bash
export BASELINE_GENERATOR=openai
export OPENAI_API_KEY=sk-...
# 可选：OPENAI_BASE_URL、OPENAI_MODEL（默认 gpt-4o-mini）
```

未设置时 baseline / agentic 使用 **stub**（摘录 + 引用），适合无 API 烟测。

Agentic 节点优先读 `AGENT_GENERATOR`，否则回退 `BASELINE_GENERATOR`。

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

详细步骤与引用格式：[docs/guides/ingest.md](docs/guides/ingest.md)。  
Smoke 记录：[docs/reports/smoke_m1_baseline.md](docs/reports/smoke_m1_baseline.md)、[docs/reports/smoke_m2_agentic.md](docs/reports/smoke_m2_agentic.md)。

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
