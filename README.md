# paper-repro-agent

一个轻量化论文复现 CLI Agent：把论文 PDF 放进一个运行文件夹，即可按阶段生成复现规格、程序骨架、结果报告和审阅报告。

## Features

- 通用论文复现流程，不针对单篇论文硬编码。
- 支持文件夹式运行：论文、代码、结果和报告都保存在同一个运行目录下。
- 默认使用 LangChain Agent 调用模型和工具完成阶段任务。
- 支持 OpenAI-compatible Chat API，可接入 OpenAI、千问/Qwen 等模型服务。
- 提供 `--scaffold` 离线模式，生成确定性、可运行但不伪造结果的脚手架。
- 可选 LangGraph 审阅子图，生成单文件审阅报告。
- 自动维护 `memory.md` 和 `stage_notes.md`，记录用户偏好、阶段产物和后续约束。

## Installation

本地开发安装：

```bash
pip install -e .[dev,pdf]
```

如需 LangGraph 审阅子图：

```bash
pip install -e .[dev,pdf,review]
```

从 GitHub 安装：

```bash
pip install "paper-repro-agent[pdf] @ git+https://github.com/<user>/<repo>.git"
```

## 环境诊断与修复

默认流程会调用 LangChain 和 OpenAI-compatible 模型。首次运行前建议先执行：

```bash
paper-repro doctor
```

如果还没有把项目安装到当前 Python 环境，请在项目根目录运行：

```bash
pip install -e .[pdf,dev,review]
```

推荐使用干净虚拟环境，避免 base 环境中已有的深度学习依赖影响 LangChain 导入：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .[pdf,dev,review]
paper-repro doctor
```

如果继续使用 Anaconda base 环境，并且 `paper-repro doctor` 报出 `torch\lib\c10.dll` 或 DLL 初始化失败，可尝试重装 CPU 版 torch：

```powershell
pip uninstall -y torch torchvision torchaudio
pip install torch --index-url https://download.pytorch.org/whl/cpu
paper-repro doctor
```

如果暂时不配置 API key，默认 LangChain 模式会报错；可以用 `--scaffold` 运行离线脚手架。

## Quick Start

推荐为每篇论文创建一个独立运行目录。把论文 PDF 放进去后，后续产物都会写在这个目录下。

默认命令会调用 LangChain Agent。请先配置模型；如果只想离线生成脚手架，在每条 `run` 命令后添加 `--scaffold`。

PowerShell：

```powershell
mkdir runs/my-paper
Copy-Item "path\to\paper.pdf" runs/my-paper\

paper-repro run --stage literature --run-dir runs/my-paper
paper-repro run --stage reading --run-dir runs/my-paper
paper-repro run --stage baseline --run-dir runs/my-paper
paper-repro run --stage core --run-dir runs/my-paper
paper-repro run --stage validation --run-dir runs/my-paper
paper-repro review --run-dir runs/my-paper
```

Bash：

```bash
mkdir -p runs/my-paper
cp path/to/paper.pdf runs/my-paper/

paper-repro run --stage literature --run-dir runs/my-paper
paper-repro run --stage reading --run-dir runs/my-paper
paper-repro run --stage baseline --run-dir runs/my-paper
paper-repro run --stage core --run-dir runs/my-paper
paper-repro run --stage validation --run-dir runs/my-paper
paper-repro review --run-dir runs/my-paper
```

如果运行目录下恰好有一个 PDF，`paper-repro run` 会自动识别它。若目录下没有 PDF 或存在多个 PDF，请显式指定：

```bash
paper-repro run --paper "runs/my-paper/paper.pdf" --stage literature --run-dir runs/my-paper
```

查看当前状态：

```bash
paper-repro state --run-dir runs/my-paper
```

未安装包时，可用源码方式运行：

```powershell
$env:PYTHONPATH="src"
python -m paper_repro_agent.cli run --stage literature --run-dir runs/my-paper
```

## Model Configuration

默认使用 LangChain `create_agent` 和 OpenAI-compatible Chat API。OpenAI 示例：

GitHub 仓库只提交 `.env.example`，不会提交真实 `.env`。首次使用时请复制模板：

```bash
cp .env.example .env
```

然后在 `.env` 中填写真实 `PAPER_REPRO_API_KEY`。如果没有配置 API key，默认 LangChain 模式会报错并提示使用 `.env.example` 或 `--scaffold`。

```powershell
set PAPER_REPRO_API_KEY=your_api_key
set PAPER_REPRO_BASE_URL=https://api.openai.com/v1
set PAPER_REPRO_MODEL=gpt-4.1-mini
```

千问/Qwen 示例：

```powershell
set PAPER_REPRO_API_KEY=your_dashscope_api_key
set PAPER_REPRO_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
set PAPER_REPRO_MODEL=qwen-plus
```

也兼容 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。如果未配置 API key，默认 LangChain 模式会提示配置模型或改用 `--scaffold`。

调用示例：

```bash
paper-repro run --stage literature --run-dir runs/my-paper
```

离线脚手架示例：

```bash
paper-repro run --stage literature --run-dir runs/my-paper --scaffold
```

## Project Layout

```text
.
├── README.md
├── agent工作流.md
├── pyproject.toml
├── paper-repro-orchestrator/
│   ├── references/        # 阶段提示词、产物规范和模板
│   └── scripts/           # PDF 抽取、产物检查和产物汇总脚本
├── src/
│   ├── README.md          # 源码模块说明和调用链
│   └── paper_repro_agent/
│       ├── cli.py         # CLI 入口
│       ├── stages.py      # 阶段执行、脚手架生成和报告生成
│       ├── agent.py       # LangChain Agent 构建
│       ├── tools.py       # PDF、检索、读写和汇总工具
│       ├── review_agent.py # 审阅报告生成
│       ├── state.py       # 工作流状态
│       ├── memory.py      # 长期记忆和阶段笔记
│       └── paths.py       # 运行目录解析
└── tests/
    ├── 2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
    └── test_*.py
```

## Run Directory Layout

每篇论文建议对应一个运行目录，例如 `runs/my-paper/`：

```text
runs/my-paper/
├── paper.pdf
├── outputs/
│   ├── literature_sources.md      # 文献、代码源和数据源调查
│   ├── reproduction_spec.md       # 论文精读和复现规格
│   ├── programs.md                # 各复现程序功能说明
│   ├── report.md                  # 结果对比与复现状态报告
│   ├── review.md                  # 审阅 Agent 报告
│   ├── memory.md                  # 长期记忆
│   ├── stage_notes.md             # 阶段笔记
│   ├── state.json                 # 机器可读工作流状态
│   ├── paper_text.txt             # PDF 抽取文本
│   ├── tables/
│   │   └── results.csv            # 默认结果对比表
│   └── figures/                   # 复现图像
└── reproduction/
    ├── main.py                    # 整体比较主程序
    ├── data.py                    # 数据加载入口
    ├── metrics.py                 # 指标整理入口
    ├── config.json                # 数据、方法、指标和随机种子配置
    └── methods/
        ├── baseline.py            # 基线方法
        └── proposed.py            # 论文核心方法
```

## Reports

- `outputs/report.md`：结果对比与复现状态报告，汇总运行命令、结果表、图表数量、产物清单和风险。
- `outputs/programs.md`：复现程序功能说明报告，解释 `reproduction/` 中每个程序的用途、关系和调用顺序。
- `outputs/review.md`：审阅 Agent 报告，检查程序结构、图表/表格数量、空文件、数据真实性和 scaffold/todo 风险。

离线脚手架模式会保留 `todo` 或 `not_run` 标记，不会把占位输出伪装成真实论文结果。

## Review Agent

生成审阅报告：

```bash
paper-repro review --run-dir runs/my-paper
```

审阅内容：

- 方法程序是否完整且可由主程序调用。
- 图片和表格数量、文件是否非空。
- 图表/表格是否能与 `outputs/reproduction_spec.md` 对应。
- `outputs/tables/results.csv` 是否来自真实运行，是否仍存在 scaffold、proxy、todo 或空复现值。
- 最终结论：通过、有条件通过或不通过。

安装 `langgraph` 时优先使用 LangGraph 子图；缺少该依赖时自动降级为顺序审阅函数，输出仍为 `outputs/review.md`。

## Smoke Test

可用任意 PDF 验证文件夹式流程：

```powershell
mkdir runs/readme_smoke
Copy-Item "path\to\paper.pdf" runs/readme_smoke\paper.pdf

$env:PYTHONPATH="src"
python -m paper_repro_agent.cli run --stage literature --run-dir runs/readme_smoke --scaffold
python -m paper_repro_agent.cli run --stage reading --run-dir runs/readme_smoke --scaffold
python -m paper_repro_agent.cli run --stage baseline --run-dir runs/readme_smoke --scaffold
python -m paper_repro_agent.cli run --stage core --run-dir runs/readme_smoke --scaffold
python -m paper_repro_agent.cli run --stage validation --run-dir runs/readme_smoke --scaffold
python -m paper_repro_agent.cli review --run-dir runs/readme_smoke
```

## Tests

```bash
python -m pytest -q
```

## Notes

- 长训练、下载数据或安装重依赖前，应先人工确认数据许可和复现范围。
- 第三方代码和数据不应在未确认 license 的情况下直接提交到仓库。
- 真实复现值必须来自 `reproduction/main.py` 或等价可追溯程序运行。
