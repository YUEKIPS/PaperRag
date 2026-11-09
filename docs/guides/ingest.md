# Ingest 与索引操作指南（M1）

时区：Asia/Shanghai · 适用里程碑：**M1 Baseline RAG**

## 前置条件

- Python 3.11+
- `pip install -r requirements.txt`（含 `pymupdf`、`sentence-transformers`、`faiss-cpu`、`rank-bm25`）
- 磁盘空间：12 篇 M1 PDF 约数十 MB；FAISS 索引与分块 JSONL 在 `data/` 下（已 gitignore）

## 1. 下载 PDF

```bash
python3 scripts/download_pdfs.py
```

- 论文列表：`configs/default.yaml` → `arxiv.paper_ids`
- 输出：`data/raw_pdfs/<arxiv_id>.pdf`
- 若网络不可用：将任意 PDF 放入 `data/raw_pdfs/`（文件名 stem = arXiv ID），后续步骤相同

## 2. 解析与分块（ingest）

```bash
python3 scripts/ingest.py
```

| 配置项 | 默认 | 说明 |
|--------|------|------|
| `ingest.chunk_size` | 512 | 字符窗口 |
| `ingest.chunk_overlap` | 64 | 相邻块重叠 |

- 解析：PyMuPDF 按页提取纯文本，再按页内滑动窗口分块
- 输出：`data/processed/<arxiv_id>.chunks.jsonl`
- 每条记录字段：`paper_id`、`page_number`（1-based）、`chunk_id`、`text`

**M1 质量说明**：未做多栏 / 公式专项优化；建议 spot check 若干 `chunks.jsonl` 行确认页码与正文连贯。

## 3. 构建索引（build_index）

```bash
python3 scripts/build_index.py
```

| 配置项 | 默认 | 说明 |
|--------|------|------|
| `index.embedding_model` | `sentence-transformers/all-MiniLM-L6-v2` | CPU 友好 |
| `index.hybrid.enabled` | `true` | 写入 BM25 token 侧车 + 检索时 RRF |
| `index.embed_batch_size` | 32 | 嵌入批大小 |

产物（均在 `data/index/`，本地生成）：

- `manifest.json` — 索引类型、chunk 数、模型名
- `faiss.index` — L2 归一化向量的 `IndexFlatIP`
- `chunks_index.jsonl` — 与 FAISS 行序一致的元数据
- `bm25_corpus.json` — hybrid 开启时的分词侧车

## 4. 基线检索与生成

```bash
python3 scripts/run_baseline.py --query "What is retrieval-augmented generation?"
python3 scripts/run_baseline.py --limit 5   # data/eval/questions.json
```

- 检索：`src/retriever/baseline.py`（dense FAISS；`hybrid.enabled` 时 BM25 + RRF）
- 生成（二选一）：
  - **默认 stub**：`BASELINE_GENERATOR=stub`（或未设置）— 拼接摘录 + 引用，无 LLM
  - **可选 LLM**：`BASELINE_GENERATOR=openai` + `OPENAI_API_KEY`；可选 `OPENAI_BASE_URL`、`OPENAI_MODEL`

## 引用格式

回答中的 `citations` 与 stub 正文中的 `[paper_id p.N]` 对应：

```json
{
  "paper_id": "2005.11401",
  "page": 1,
  "chunk_id": "2005.11401_p1_c2"
}
```

## 常见问题

| 现象 | 处理 |
|------|------|
| `No PDFs in data/raw_pdfs` | 先下载或手动放入 PDF |
| `No chunk files` | 先 `ingest.py` |
| `Missing index manifest` | 先 `build_index.py` |
| 首次 build 较慢 | 需下载 HuggingFace 嵌入权重 |
| `hybrid_enabled: false` | 仅 dense FAISS，可在 `default.yaml` 关闭 |

## 相关文档

- [docs/plan.md](../plan.md) — M1/M2 里程碑
- [docs/decisions.md](../decisions.md) — 嵌入模型与索引 ADR
- [docs/reports/smoke_m1_baseline.md](../reports/smoke_m1_baseline.md) — 5 题 smoke（无 aggregate 分数）
