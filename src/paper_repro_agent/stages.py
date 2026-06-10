from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from .agent import invoke_agent
from .memory import update_memory
from .paths import OUTPUTS_DIR, REPRODUCTION_DIR, RunContext, make_run_context
from .references import load_stage_reference, load_templates
from .review import StageReview, render_review
from .state import STAGE_LABELS, WorkflowState, save_state, validate_stage
from .tools import search_arxiv, search_semantic_scholar, summarize_artifacts


@dataclass(frozen=True)
class StageConfig:
    reference_name: str
    artifact_name: str


STAGE_CONFIG: dict[str, StageConfig] = {
    "literature": StageConfig("literature_search.md", "literature_sources.md"),
    "reading": StageConfig("reading_spec.md", "reproduction_spec.md"),
    "baseline": StageConfig("code_implementation.md", "baseline_review.md"),
    "core": StageConfig("code_implementation.md", "core_method_review.md"),
    "figures": StageConfig("figures_tables.md", "figures_tables_review.md"),
    "validation": StageConfig("validation_report.md", "report.md"),
}


def run_stage(
    stage: str,
    state: WorkflowState,
    paper: str | None = None,
    use_llm: bool = False,
    context: RunContext | None = None,
) -> str:
    context = context or make_run_context()
    validate_stage(stage)
    if paper:
        state.paper_input = paper
    if stage in {"literature", "reading"} and not state.paper_input:
        raise ValueError(f"Stage '{stage}' requires --paper or an existing outputs/state.json paper_input.")

    previous_run_dir = os.getenv("PAPER_REPRO_RUN_DIR")
    os.environ["PAPER_REPRO_RUN_DIR"] = _display_path(context.root_dir)
    try:
        if use_llm:
            content, generated = _run_llm_stage(stage, state, context)
        else:
            content, generated = _run_scaffold_stage(stage, state, context)
    finally:
        if previous_run_dir is None:
            os.environ.pop("PAPER_REPRO_RUN_DIR", None)
        else:
            os.environ["PAPER_REPRO_RUN_DIR"] = previous_run_dir

    artifact = context.outputs_dir / STAGE_CONFIG[stage].artifact_name
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(content, encoding="utf-8")

    generated_files = [artifact.relative_to(Path.cwd()).as_posix() if artifact.is_relative_to(Path.cwd()) else str(artifact)]
    generated_files.extend(generated)
    state.mark_completed(stage, artifact)
    memory_update = update_memory(stage, state, context, generated_files)
    generated_files.extend(
        [
            _display_path(memory_update.memory_path),
            _display_path(memory_update.stage_notes_path),
        ]
    )
    review = StageReview(
        stage=stage,
        completed=[
            f"已按 `{STAGE_CONFIG[stage].reference_name}` 执行 {STAGE_LABELS[stage]} 阶段。",
            "已生成阶段产物并更新工作流状态。",
        ],
        generated_files=generated_files,
        key_results=[
            "阶段产物采用中文 Markdown。",
            "本次运行在阶段结束处停止，等待人工审核后再进入下一阶段。",
        ],
        risks=_stage_risks(stage, use_llm),
        memory_updates=[
            memory_update.summary,
            f"长期记忆：{_display_path(memory_update.memory_path)}",
            f"阶段笔记：{_display_path(memory_update.stage_notes_path)}",
        ],
    )
    review_text = render_review(review)
    review_path = context.outputs_dir / f"{stage}_review.md"
    review_path.write_text(review_text, encoding="utf-8")

    state.last_review = _display_path(review_path)
    save_state(state, context.state_path)
    return review_text


def _run_llm_stage(stage: str, state: WorkflowState, context: RunContext) -> tuple[str, list[str]]:
    task = (
        f"为阶段 `{stage}` 生成或更新标准产物。"
        "如需写入补充文件，只能写入 outputs/ 或 reproduction/。"
        "最终回复必须是可保存为阶段产物的 Markdown。"
    )
    content = invoke_agent(stage, state, task)
    return content, []


def _run_scaffold_stage(stage: str, state: WorkflowState, context: RunContext) -> tuple[str, list[str]]:
    context.outputs_dir.mkdir(parents=True, exist_ok=True)
    (context.outputs_dir / "figures").mkdir(parents=True, exist_ok=True)
    (context.outputs_dir / "tables").mkdir(parents=True, exist_ok=True)
    reference = load_stage_reference(stage)
    templates = load_templates()

    if stage == "literature":
        return _literature_scaffold(state, reference, templates), []
    if stage == "reading":
        return _reading_scaffold(state, reference, context), _maybe_extract_pdf_text(state, context)
    if stage == "baseline":
        return _baseline_scaffold(state, reference, context), [_ensure_reproduction_runner(context)]
    if stage == "core":
        return _core_scaffold(state, reference), []
    if stage == "figures":
        return _figures_scaffold(state, reference), []
    if stage == "validation":
        summary_path = "outputs/artifacts_summary.md"
        summarize_artifacts(summary_path)
        return _validation_scaffold(state, reference, context), [_display_path(context.outputs_dir / "artifacts_summary.md")]
    raise ValueError(f"Unknown stage: {stage}")


def _literature_scaffold(state: WorkflowState, reference: str, templates: str) -> str:
    search_notes = []
    paper = state.paper_input or ""
    if paper and not Path(paper).suffix.lower() == ".pdf":
        for name, tool_func in [("arXiv", search_arxiv), ("Semantic Scholar", search_semantic_scholar)]:
            try:
                result = tool_func(paper, 3)
                search_notes.append(f"## {name} 检索结果\n\n```json\n{result[:3000]}\n```")
            except Exception as exc:
                search_notes.append(f"## {name} 检索结果\n\n- 检索失败：{exc}")
    return f"""# 文献与代码源调查

## 论文身份

- 输入：{paper}
- 状态：待人工核对标题、作者、年份、arXiv/DOI 和官方主页。

## 官方来源

| 类型 | 名称 | 链接 | 可用性 | 复现作用 |
| --- | --- | --- | --- | --- |
| 待补充 | 待联网核对 | 待补充 | 待确认 | 确认论文事实 |

## 代码库

| 仓库 | 作者/组织 | 入口 | 依赖 | 数据 | 风险 |
| --- | --- | --- | --- | --- | --- |
| 待补充 | 待确认 | 待确认 | 待确认 | 待确认 | 不能把第三方实现当作论文事实 |

{chr(10).join(search_notes)}

## 结论

- 推荐实现路线：先完成论文身份和官方代码核对，再进入精读规格。
- 依赖风险：作者代码、数据集、预训练权重可能缺失或需要登录。
- 数据风险：实际数据许可和下载方式需单独确认。

## 本阶段参考

```markdown
{reference}
```

## 模板依据

```markdown
{templates}
```
"""


def _reading_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    text_note = "未检测到已抽取的 PDF 文本。"
    text_path = context.outputs_dir / "paper_text.txt"
    if text_path.exists():
        text = text_path.read_text(encoding="utf-8", errors="replace")
        text_note = text[:5000]
    return f"""# 论文复现规格

## 论文概览

- 输入：{state.paper_input}
- 当前状态：需要人工或 LLM 精读补全问题定义、方法和实验设置。

## 方法拆解

- 核心任务：待从论文正文确认。
- 输入输出：待从论文正文确认。
- 算法步骤：待从公式、伪代码和方法章节提取。

## 实验设置

- 数据集：待确认。
- 评价指标：待确认。
- 随机种子与训练参数：待确认。

## 图表目标

- 待列出论文中需要复现的图和表。

## 实现计划

- 先实现最小可运行基线。
- 再实现论文核心方法。
- 每一步输出中间指标和阶段审查包。

## 风险和差异

- 该文件目前是轻量脚手架，不代表已完成论文事实核验。
- 若使用 PDF，需检查抽取文本是否丢失公式、表格和图注。

## PDF 抽取文本预览

```text
{text_note}
```

## 本阶段参考

```markdown
{reference}
```
"""


def _baseline_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    return f"""# 基线方法实现审查

## 输入依据

- 论文输入：{state.paper_input}
- 复现规格：`{_display_path(context.outputs_dir / "reproduction_spec.md")}`
- 运行入口：`{_display_path(context.reproduction_dir / "run_reproduction.py")}`

## 已生成基线骨架

- 提供 `python {_display_path(context.reproduction_dir / "run_reproduction.py")} --stage baseline --outputs {_display_path(context.outputs_dir)}`。
- 默认创建 `outputs/tables/baseline_metrics.csv`，用于记录后续真实基线指标。
- 默认不伪造论文结果，所有指标需在实现具体方法后补齐。

## 后续实现契约

- 从 `outputs/reproduction_spec.md` 补齐数据加载、模型、指标和随机种子。
- 长训练、下载数据或安装重依赖前必须人工确认。

## 本阶段参考

```markdown
{reference}
```
"""


def _core_scaffold(state: WorkflowState, reference: str) -> str:
    return f"""# 核心方法实现审查

## 输入依据

- 论文输入：{state.paper_input}
- 复现规格：`outputs/reproduction_spec.md`
- 基线入口：`reproduction/run_reproduction.py`

## 核心方法任务

- 根据复现规格补齐论文核心模块、损失函数、训练/推理流程。
- 保留基线实现，避免核心方法改动破坏可对照结果。
- 输出中间指标和日志，便于解释差异。

## 风险

- 当前阶段需要论文公式、算法和实验参数支撑；若 `outputs/reproduction_spec.md` 仍为空，应先回到 reading 阶段。
- 缺失重依赖时先实现可运行替代层，并在最终报告中标注。

## 本阶段参考

```markdown
{reference}
```
"""


def _figures_scaffold(state: WorkflowState, reference: str) -> str:
    return f"""# 图表与表格复现审查

## 目录

- 图片目录：`outputs/figures/`
- 表格目录：`outputs/tables/`

## 图表计划

- 从 `outputs/reproduction_spec.md` 读取图表清单。
- 每张图按论文编号命名，例如 `fig1_*.png`。
- 每张表尽量同时保留论文值和复现值。

## 当前状态

- 已确保输出目录存在。
- 尚未生成真实图表；需要基线和核心方法产出数据后继续。

## 本阶段参考

```markdown
{reference}
```
"""


def _validation_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    summary_path = context.outputs_dir / "artifacts_summary.md"
    summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else "未生成产物清单。"
    return f"""# 论文复现报告

## 论文信息

- 输入：{state.paper_input}

## 复现范围

- 当前为轻量化工作流生成的阶段性报告。
- 实际复现范围以 `outputs/reproduction_spec.md` 和代码实现为准。

## 环境和依赖

- Python CLI：`paper-repro`
- LangChain：可选增强路径；无模型配置时使用确定性脚手架。

## 运行命令

```bash
paper-repro run --paper "<PDF|URL|标题>" --stage literature
paper-repro run --stage reading
paper-repro run --stage baseline
paper-repro run --stage core
paper-repro run --stage figures
paper-repro run --stage validation
```

## 图表产物

{summary}

## 结果对照

- 待填入论文原始结果和当前复现结果。

## 差异分析

- 当前报告不伪造实验结论；差异需在真实运行后补充。

## 后续扩展建议

- 接入 LLM 后重新运行 literature 和 reading 阶段，补全论文事实。
- 根据复现规格补齐 `reproduction/run_reproduction.py`。

## 本阶段参考

```markdown
{reference}
```
"""


def _maybe_extract_pdf_text(state: WorkflowState, context: RunContext) -> list[str]:
    paper = state.paper_input
    if not paper:
        return []
    path = Path(paper)
    if path.suffix.lower() != ".pdf":
        return []
    source = path if path.is_absolute() else Path.cwd() / path
    if not source.exists():
        return []
    try:
        from .tools import extract_pdf_text

        extract_pdf_text(str(source), "outputs/paper_text.txt")
        return [_display_path(context.outputs_dir / "paper_text.txt")]
    except Exception:
        return []


def _ensure_reproduction_runner(context: RunContext) -> str:
    context.reproduction_dir.mkdir(parents=True, exist_ok=True)
    runner = context.reproduction_dir / "run_reproduction.py"
    if not runner.exists():
        runner.write_text(
            '''#!/usr/bin/env python
"""Minimal reproduction runner scaffold generated by paper-repro-agent."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def run_baseline(outputs: Path) -> None:
    tables = outputs / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    path = tables / "baseline_metrics.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "paper_value", "reproduced_value", "note"])
        writer.writerow(["todo", "", "", "Fill after implementing the paper-specific baseline."])
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paper reproduction stages.")
    parser.add_argument("--stage", choices=["baseline", "core", "all"], default="baseline")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    if args.stage in {"baseline", "all"}:
        run_baseline(args.outputs)
    if args.stage in {"core", "all"}:
        print("Core method is paper-specific. Implement it after completing outputs/reproduction_spec.md.")


if __name__ == "__main__":
    main()
''',
            encoding="utf-8",
        )
    if shutil.which("python"):
        pass
    return _display_path(runner)


def _stage_risks(stage: str, use_llm: bool) -> list[str]:
    risks = []
    if not use_llm:
        risks.append("本次未启用 LLM，产物为可运行脚手架，论文事实需要人工或后续 LLM 阶段补全。")
    if stage == "literature":
        risks.append("联网检索结果可能受网络、API 限流或论文标题歧义影响。")
    if stage == "reading":
        risks.append("PDF 文本抽取可能遗漏公式、表格、图注或多栏顺序。")
    if stage in {"baseline", "core"}:
        risks.append("通用代码骨架不会伪造论文算法，需要依据复现规格继续实现。")
    return risks


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)
