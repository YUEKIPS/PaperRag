# Agentic Paper RAG

面向 LLM / Agent 论文库的 **Agentic RAG**：检索工具化 + grade + rewrite（LangGraph 编排），底层混合检索（向量 + BM25 / RRF）+ rerank + 带页码引用。

与 [RepoAgent](https://github.com/)（代码仓 Agent）互补：RepoAgent 管代码仓库；本项目管 **非代码论文知识库**。

> **当前状态（2026-11-09）**：文档与 Git 基线 + 可运行 **脚手架**（download → ingest → index → baseline 烟测）。完整 Agentic 编排、生产级 rerank、评测报表与 UI **尚未实现**。

## 功能模块（目标）

| 模块 | 说明 |
|------|------|
| `parser` | PDF 解析（PyMuPDF） |
| `indexer` | 分块、向量 / 混合索引 |
| `embed` | 嵌入模型（M1+） |
| `retriever` | 检索 + 融合 |
| `reranker` | 交叉编码器重排（M2+） |
| `orchestrator` | LangGraph：decide → retrieve → grade → rewrite → generate |
| `generate` | 带引用的回答生成 |
| `eval` | 离线评测 |

## 环境要求

- Python 3.11+
- 磁盘：存放 `data/raw_pdfs/`（约 12 篇 M1 论文，数十 MB）

## 安装

```bash
cd agentic-paper-rag   # 仓库根目录
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

配置见 `configs/default.yaml`。敏感信息放 `.env`（已在 `.gitignore` 中忽略）；脚手架阶段不强制 API Key。

## 快速路径：download → ingest → index → baseline

在仓库根目录执行（需先 `pip install -r requirements.txt`）：

```bash
# 1) 下载 M1 arXiv PDF（列表见 configs/default.yaml）
python scripts/download_pdfs.py

# 2) 解析 PDF 并写出分块 JSONL → data/processed/
python scripts/ingest.py

# 3) 构建最小 JSONL 索引 → data/index/
python scripts/build_index.py

# 4) 基线烟测：关键词检索 + 占位生成（非 LLM）
python scripts/run_baseline.py --query "What is retrieval-augmented generation?"

# 或使用 draft 评测题（前 1 道）
python scripts/run_baseline.py --limit 1
```

**说明**：`run_baseline.py` 当前为 **stub 生成器**，用于验证流水线；不输出虚假评测分数。`run_agentic.py` / `eval_all.py` 为占位入口。

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
