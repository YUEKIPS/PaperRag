# M1 Baseline Smoke（诚实记录）

日期：2026-11-09（Asia/Shanghai）  
环境：云端代理 · `generator=stub`（未配置 `OPENAI_API_KEY`）  
语料：12 篇 M1 PDF · **2695** chunks · FAISS + hybrid RRF 原型  

**不含**人工标注准确率、Recall@k、nDCG 等 aggregate 指标（刻意避免占位数字）。

## 执行命令

```bash
python3 scripts/download_pdfs.py
python3 scripts/ingest.py
python3 scripts/build_index.py
python3 scripts/run_baseline.py --limit 5
```

## 观察摘要（5 道 draft 题）

| ID | 检索 hit 数 | 主要命中 paper_id | 主观相关性（粗粒度） |
|----|-------------|-------------------|----------------------|
| q001 RAG 定义 | 5 | 2005.11401, 2401.15884 | **高** — 首条为原始 RAG 论文 |
| q002 Agentic vs single-shot | 5 | 2005.11401, 2310.11511 | **中** — 部分命中泛 RAG，非全 agentic |
| q003 Chunking | 5 | 2005.11401, 2401.15884 | **低–中** — 语料少直接谈固定窗口分块 |
| q004 Hybrid 检索 | 5 | 2401.15884, 2005.11401 | **中** — 有 sparse/dense 讨论片段 |
| q005 引用字段 | 5 | 2005.11401, 2310.11511 | **中** — 命中 citation / factuality 段落 |

所有运行均返回 **5/5** `top_k=5` 非空命中；stub 输出均带 `paper_id` + `page` + `chunk_id` 引用列表。

## 局限（交 M2）

- 生成仍为 stub，不能评估答案质量
- 无 rerank；RRF 为原型级融合
- 未做公式 / 多栏解析专项评测
- q002–q005 显示语义检索对「概念型」问法仍会偏题

## 复现

本地重跑后完整终端输出可保存为 `data/eval/runs/smoke_m1_YYYY-MM-DD.log`（`*.log` 已 gitignore）。
