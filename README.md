# PaperRag

**Agentic Paper RAG**（`agentic-paper-rag`）是一个本地论文问答项目。语料是公开 arXiv 上的 LLM / Agent 论文 PDF。你提问后，它检索相关片段，再给出带页码出处的回答。

公开仓库是 [PaperRag](https://github.com/YUEKIPS/PaperRag)。配置里的项目名，以及一些已有的本地目录，仍叫 `agentic-paper-rag`。

编排使用 LangGraph，顺序是 **decide → retrieve → grade → rewrite → generate**：先把问题整理成可以检索的问法，再检索、检查片段是否够用、必要时改写问题，最后生成回答。检索是混合的：向量与 BM25 用 RRF 融合，然后做 cross-encoder 重排。

## 功能

- 按配置中的 arXiv 编号下载 PDF，解析文本并建立索引
- 向量检索（FAISS）与 BM25 混合，再用 cross-encoder 重排
- 回答附带论文编号、页码和片段编号
- 本机网页：多会话聊天、论文库、PDF 预览、Markdown 回答
- 同一会话的后续问题会带上最近的完整问答（最多 **6** 轮，这些问题和回答的 UTF-8 合计不超过 **24000** 字节）。这些内容用来理解「它」「上面」这类指代。检索针对整理后的当前问题，引用对应该轮检索到的片段。带入或省略的轮数会显示在回答下方

## 环境

- Python 3.11 及以上
- 默认清单约 12 篇 PDF，占几十 MB。第一次建索引会下载嵌入模型，第一次检索重排会下载重排模型

## 安装

```bash
git clone https://github.com/YUEKIPS/PaperRag.git
cd PaperRag
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

本地文件夹如果仍叫 `agentic-paper-rag`，进入那个目录后执行同样的命令。下面的命令都在仓库根目录运行。

## 配置

常用项在 `configs/default.yaml`：

| 配置 | 作用 |
|------|------|
| `arxiv.paper_ids` | 要下载的论文编号。默认 12 篇 |
| `ingest.chunk_size` / `ingest.chunk_overlap` | 分块大小与重叠，默认 512 / 64 个字符 |
| `index.embedding_model` | 嵌入模型，默认 `sentence-transformers/all-MiniLM-L6-v2` |
| `index.hybrid.enabled` | 是否启用 BM25，并在检索时与向量结果做 RRF |
| `retriever.reranker` | 重排开关与模型，默认 `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `agent.conversation` | 同一会话带入的轮数和字节上限（6 轮、24000 字节） |
| `llm.base_url` / `llm.model` | 对话接口，默认 `https://api.deepseek.com/v1` 与 `deepseek-chat` |

密钥放在环境变量或仓库根目录的 `.env`（已被 Git 忽略）。可以从 `.env.example` 复制：

```bash
export AGENT_GENERATOR=openai
export DEEPSEEK_API_KEY=你的密钥
```

也可以使用 `OPENAI_API_KEY`。换其它兼容端点时设置 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

`AGENT_GENERATOR=openai` 表示使用 OpenAI 兼容的 `chat/completions` 接口，默认示例是 DeepSeek。网页和 `run_agentic.py` 使用 `AGENT_GENERATOR`。`run_baseline.py` 使用 `BASELINE_GENERATOR`。

未配置密钥时，回答由检索到的原文摘录和页码引用组成。配置密钥后，由模型写回答，语言与提问一致。

## 准备语料并提问

```bash
python3 scripts/download_pdfs.py
python3 scripts/ingest.py
python3 scripts/build_index.py

python3 scripts/run_agentic.py --query "How do agentic RAG systems differ from single-shot RAG?"
```

基线路径是检索后直接生成：

```bash
python3 scripts/run_baseline.py --query "What is retrieval-augmented generation?"
```

PDF、分块和索引写在 `data/` 下，默认不提交到 Git。换论文清单后，重新执行上面的下载、解析和建索引。

更细的步骤、引用字段和常见报错见 [docs/guides/ingest.md](docs/guides/ingest.md)。

## 网页

索引建好后启动本机页面：

```bash
python3 scripts/serve_web.py
```

浏览器打开 <http://127.0.0.1:8765/>。服务只接受本机访问。

- **对话**：新建会话并提问。会话保存在本机，可以重命名、归档或删除
- **论文库**：列出配置中的论文和本地 PDF。点开后在右侧预览，并用「插入提问」把该论文编号写入输入框
- 回答以 Markdown 显示。可以展开查看片段是否通过检查、问题如何被改写，以及引用
- 主题有 Ink、Slate、Sand
- 若这一轮用到了更早的问答，回答下方会显示「带入 N 轮 / 省略 M 轮」

## 许可证

尚未选定。
