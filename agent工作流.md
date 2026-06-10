# 轻量化论文复现 Agent 工作流

## 目标

本项目提供一个通用论文复现 CLI Agent。默认架构为 **LangChain 总控 Agent + 阶段化 skills + 工具调用**，不针对某一篇论文硬编码流程。每篇论文使用一个独立运行目录，论文 PDF、复现程序、结果表、报告和审阅产物都保存在该目录下。

离线、测试或无 API key 时，可以使用 `--scaffold` 生成确定性脚手架；脚手架不会伪造论文结果。

## 模型接入

默认使用 LangChain `create_agent` 和 `langchain-openai` 的 OpenAI-compatible Chat API 适配层。

环境变量：

- `PAPER_REPRO_MODEL`
- `PAPER_REPRO_API_KEY`
- `PAPER_REPRO_BASE_URL`
- 兼容 `OPENAI_API_KEY`、`OPENAI_BASE_URL`

OpenAI 示例：

```powershell
set PAPER_REPRO_API_KEY=你的 OpenAI API Key
set PAPER_REPRO_BASE_URL=https://api.openai.com/v1
set PAPER_REPRO_MODEL=gpt-4.1-mini
```

千问/Qwen 示例：

```powershell
set PAPER_REPRO_API_KEY=你的 DashScope API Key
set PAPER_REPRO_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
set PAPER_REPRO_MODEL=qwen-plus
```

## LangChain 主要作用

- 总控 Agent 构建：`src/paper_repro_agent/agent.py` 使用 `create_agent` 组合模型、工具和系统提示。
- 系统提示：`paper-repro-orchestrator/references/system_prompt.md` 定义总控行为、真实性约束和输出约定。
- 阶段 skills：`paper-repro-orchestrator/references/*.md` 规定各阶段目标、产物和审查要求。
- 工具调用：`src/paper_repro_agent/tools.py` 注册 PDF 抽取、文献检索、文件读写、产物检查和汇总工具。
- 审阅增强：安装 `langgraph` 后，`paper-repro review` 使用 LangGraph 子图；否则顺序降级。

## 阶段流程

| 阶段 | 命令 | 主要产物 | 说明 |
| --- | --- | --- | --- |
| 文献与代码源调查 | `paper-repro run --stage literature --run-dir <运行目录>` | `outputs/literature_sources.md` | 自动识别运行目录下唯一 PDF，确认论文身份、官方来源、代码库、数据集和依赖风险。 |
| 论文精读与复现规格 | `paper-repro run --stage reading --run-dir <运行目录>` | `outputs/reproduction_spec.md` | 提取方法、数据、指标、图表目标和真实性约束。 |
| 基线方法实现 | `paper-repro run --stage baseline --run-dir <运行目录>` | `reproduction/main.py`、`reproduction/methods/baseline.py`、`outputs/programs.md` | 生成通用可运行结构，不伪造实验结果。 |
| 核心方法实现 | `paper-repro run --stage core --run-dir <运行目录>` | `reproduction/methods/proposed.py`、`outputs/programs.md` | 为论文核心方法保留独立入口。 |
| 图表与表格整理 | `paper-repro run --stage figures --run-dir <运行目录>` | `outputs/figures/`、`outputs/tables/results.csv` | 只保留必要图表，不硬编码某篇论文数量。 |
| 验证与中文报告 | `paper-repro run --stage validation --run-dir <运行目录>` | `outputs/report.md` | 合成结果对比与复现状态报告。 |
| 总审阅 | `paper-repro review --run-dir <运行目录>` | `outputs/review.md` | 检查程序结构、图表数量、表格数量和数据真实性。 |

离线脚手架模式：

```bash
paper-repro run --stage literature --run-dir runs/demo --scaffold
```

## 代码输出结构

```text
<run-dir>/
  paper.pdf
  outputs/
    literature_sources.md
    reproduction_spec.md
    tables/results.csv
    figures/
    report.md
    programs.md
    review.md
    memory.md
    stage_notes.md
    state.json
  reproduction/
    main.py
    data.py
    metrics.py
    config.json
    methods/
      baseline.py
      proposed.py
```

`reproduction/main.py` 统一调用 `methods/` 下的方法文件，并把结果写入 `outputs/tables/results.csv`。若结果表仍包含 `todo`、`not_run`、`scaffold` 或空复现值，则只能视为未完成状态。

## Skills 与 Prompt 文件

- `paper-repro-orchestrator/SKILL.md`：论文复现总控 skill。
- `references/system_prompt.md`：项目系统提示词。
- `references/stage_contract.md`：阶段审查包规范。
- `references/literature_search.md`：文献与代码源调查 skill。
- `references/reading_spec.md`：论文精读与复现规格 skill。
- `references/code_implementation.md`：代码实现 skill。
- `references/figures_tables.md`：图表表格 skill。
- `references/validation_report.md`：验证报告 skill。
- `references/templates.md`：标准产物模板。

## 记忆功能

- `outputs/memory.md`：长期记忆，记录精炼后的用户偏好、关键决策和变更历史。
- `outputs/stage_notes.md`：阶段笔记，记录每个阶段输入、产物和下一步。
- 使用的记忆更新方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 审阅 Agent

`paper-repro review --run-dir <运行目录>` 输出 `outputs/review.md`，检查：

- 方法程序是否完整且可由主程序调用。
- 图片数量、表格数量和空文件。
- 图表/表格是否能对应 `outputs/reproduction_spec.md`。
- `outputs/tables/results.csv` 是否存在真实运行数据。
- 是否仍有 `todo/not_run/proxy/fake/dummy/scaffold` 风险。

## 示例

```bash
pip install -e .[dev,pdf]

mkdir runs/demo
cp paper.pdf runs/demo/

paper-repro run --stage literature --run-dir runs/demo
paper-repro run --stage reading --run-dir runs/demo
paper-repro run --stage baseline --run-dir runs/demo
paper-repro run --stage core --run-dir runs/demo
paper-repro run --stage validation --run-dir runs/demo
paper-repro review --run-dir runs/demo
```
