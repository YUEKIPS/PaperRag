# AGENTS.md — 云端 / 本地代理协作约定

项目：**Agentic Paper RAG**（`agentic-paper-rag`）

## 项目目标（已定）

- 语料：公开 arXiv LLM / Agent 相关 PDF（M1 清单见 `configs/default.yaml`）
- 检索：混合检索（向量 + BM25 / RRF）+ rerank + **页码级引用**
- 编排：**LangGraph**（decide → retrieve → grade → rewrite → generate）
- 与 RepoAgent 分工：RepoAgent = 代码仓；本项目 = 论文知识库

## 本轮禁止事项

- 不要声称已完成未实现的模块（尤其 Agentic grade/rewrite、rerank 生产化）
- 不要编造评测数字或 dashboard 结果
- 不要提交 `data/raw_pdfs/*.pdf`、向量库产物、`.env`
- 不要在日志中粘贴密钥或完整私有对话

## 开发日志（必须遵守）

习惯对齐 **RepoAgent** `docs/devlog/`：

| 规则 | 说明 |
|------|------|
| 时区 | Asia/Shanghai |
| 结构 | `README.md` 索引 + `daily/YYYY-MM-DD.md` + `monthly/YYYY-MM.md` |
| 结束一轮实质性工作前 | ① 追加当天日报明细 ② 更新当日摘要 ③ 同步月报 ④ 更新索引 |
| 日报章节 | 当日摘要；工作明细（目标 / 讨论与操作 / 结果与验证 / 相关产物 / 待办） |
| 诚实性 | 计划 ≠ 已完成；未验证不写「已通过」 |

完整模板与索引维护说明：[docs/devlog/README.md](docs/devlog/README.md)

## 推荐工作流

1. 读 `docs/plan.md` 当前里程碑与 `docs/decisions.md`
2. 改代码后跑最小烟测：`download_pdfs` → `ingest` → `build_index` → `run_baseline`
3. 更新开发日志与（如有）`docs/handoff.md`
4. Git：小而清晰的提交（`docs:` / `feat:` / `fix:` 前缀均可）

## 关键路径

| 脚本 | 用途 |
|------|------|
| `scripts/download_pdfs.py` | 拉取 M1 PDF |
| `scripts/ingest.py` | 解析 + 分块 |
| `scripts/build_index.py` | 索引（当前为 JSONL 脚手架） |
| `scripts/run_baseline.py` | 非 Agentic 基线烟测 |
| `scripts/run_agentic.py` | **占位**，M2+ |
| `scripts/eval_all.py` | **占位**，M1 检索稳定后 |

## 配置

- 默认：`configs/default.yaml`
- 路径解析：`src/config.py`

## 里程碑速查

- **M0（本轮）**：文档 + git 基线 + 脚手架 — **已完成**
- **M1**：解析 / 分块质量、嵌入索引、真实 baseline 生成（LLM 可选）、引用格式
- **M2**：混合检索 + rerank + LangGraph Agentic 环

细节见 [docs/plan.md](docs/plan.md)。
