# Source Layout

`src/` 存放 `paper-repro-agent` 的 Python 源码。主包位于 `src/paper_repro_agent/`，由 CLI 入口、阶段执行器、LangChain Agent、工具、状态、记忆和审阅模块组成。

## Module Responsibilities

| 模块 | 作用 |
| --- | --- |
| `paper_repro_agent/cli.py` | 解析 `paper-repro run/state/review` 命令，并把参数交给阶段执行或审阅入口。 |
| `paper_repro_agent/paths.py` | 解析运行目录，统一得到 `root_dir`、`outputs_dir`、`reproduction_dir` 和 `state_path`。 |
| `paper_repro_agent/state.py` | 定义阶段顺序、阶段中文名和 `WorkflowState`，负责状态读写。 |
| `paper_repro_agent/stages.py` | 核心阶段执行器；生成文献调查、复现规格、程序骨架、结果报告和程序说明报告。 |
| `paper_repro_agent/agent.py` | 构建 LangChain `create_agent`，加载系统提示、阶段参考和工具。 |
| `paper_repro_agent/tools.py` | 提供 LangChain 工具：PDF 抽取、arXiv/Semantic Scholar 检索、文件读写、产物检查和汇总。 |
| `paper_repro_agent/memory.py` | 更新 `outputs/memory.md` 和 `outputs/stage_notes.md`。 |
| `paper_repro_agent/review.py` | 渲染阶段审查包，提示用户人工确认后再进入下一阶段。 |
| `paper_repro_agent/review_agent.py` | 生成 `outputs/review.md`；可用 LangGraph 子图执行，也可顺序降级。 |
| `paper_repro_agent/references.py` | 从 `paper-repro-orchestrator/references/` 加载阶段参考文档。 |

## Execution Chain

普通阶段运行链：

```text
CLI
  -> make_run_context(...)
  -> load_state(...)
  -> run_stage(...)
  -> auto-discover PDF when needed
  -> scaffold stage or LangChain agent stage
  -> write outputs/ and reproduction/
  -> update memory and state
  -> print stage review
```

审阅链：

```text
CLI review
  -> make_run_context(...)
  -> run_review(...)
  -> code/artifact/data checks
  -> write outputs/review.md
```

## Stage Flow

| 阶段 | 主要入口 | 主要输出 |
| --- | --- | --- |
| `literature` | `run_stage("literature", ...)` | `outputs/literature_sources.md` |
| `reading` | `run_stage("reading", ...)` | `outputs/reproduction_spec.md`、`outputs/paper_text.txt` |
| `baseline` | `run_stage("baseline", ...)` | `reproduction/main.py`、`methods/baseline.py`、`outputs/programs.md`、`outputs/tables/results.csv` |
| `core` | `run_stage("core", ...)` | `methods/proposed.py`、`outputs/programs.md` |
| `figures` | `run_stage("figures", ...)` | `outputs/figures/`、`outputs/tables/` 规划说明 |
| `validation` | `run_stage("validation", ...)` | `outputs/report.md` |
| `review` | `run_review(...)` | `outputs/review.md` |

## Data Flow

- `--run-dir` 指向单篇论文的运行目录。
- 若 `--paper` 为空，`literature` 和 `reading` 会在运行目录根部查找唯一 PDF。
- 阶段产物写入 `outputs/`。
- 可运行复现程序写入 `reproduction/`。
- 结果表默认写入 `outputs/tables/results.csv`。
- 报告分为三份：
  - `outputs/report.md`：结果对比与复现状态。
  - `outputs/programs.md`：程序功能说明。
  - `outputs/review.md`：审阅 Agent 结论。

## Adding New Behavior

- 新阶段或阶段产物优先扩展 `stages.py`，并保持 `WorkflowState` 可读。
- 新工具优先加入 `tools.py`，再由 `agent.py` 注册给 LangChain。
- 新审阅规则优先加入 `review_agent.py`，保持最终报告仍为单文件 `outputs/review.md`。
- 不要在脚手架阶段伪造论文结果；真实值必须能追溯到可运行程序。
