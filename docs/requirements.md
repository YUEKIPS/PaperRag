# 需求说明

版本：draft · 2026-11-09

## 背景

研究人员需要在对 LLM / Agent 论文提问时，获得 **有页码出处**、可复核的回答；单一向量检索在术语密集论文上易漏召，需要混合检索与 Agentic 纠错循环。

## 功能需求

### F1 语料

- 支持从 arXiv 批量下载 PDF（M1 固定清单 12 篇，可配置扩展）
- 原始 PDF 不纳入 Git

### F2 解析与索引

- PDF → 按页文本 → 可配置分块（size / overlap）
- 索引：向量检索 + BM25（RRF 融合）— **M1 先密集向量 + 脚手架 BM25 接口**
- 持久化索引目录可重建，默认不入库

### F3 检索与重排

- Top-K 检索，支持混合与 rerank — rerank **M2**

### F4 生成与引用

- 回答必须附带 `paper_id` + 页码（+ chunk id）
- Baseline：retrieve → generate；Agentic：grade / rewrite 循环 — **Agentic M2**

### F5 评测

- `data/eval/questions.json` 维护问题集
- 批量评测脚本输出可复现指标 — **无虚假数字；脚手架仅为占位题**

## 非功能需求

- Python 3.11+，依赖锁定于 `requirements.txt`
- 配置集中于 `configs/default.yaml`
- CLI 脚本可独立运行，便于 CI / 代理自动化
- 开发日志 Asia/Shanghai，规则见 `docs/devlog/README.md` 与根 `AGENTS.md`

## 明确不在本轮（2026-11-09 脚手架）

- LangGraph grade / rewrite 完整实现
- 生产级 rerank、Web UI
- 对外公布的评测成绩
