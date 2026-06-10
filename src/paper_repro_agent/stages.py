from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil

from .agent import invoke_agent
from .memory import update_memory
from .paths import RunContext, make_run_context
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
    "baseline": StageConfig("code_implementation.md", "baseline_implementation.md"),
    "core": StageConfig("code_implementation.md", "core_implementation.md"),
    "figures": StageConfig("figures_tables.md", "figures_plan.md"),
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
    elif stage in {"literature", "reading"} and not state.paper_input:
        state.paper_input = _discover_single_pdf(context)
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

    generated_files = [_display_path(artifact)]
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
            "通用复现代码保持方法文件与整体比较主程序分离。",
            "本次运行在阶段结束处停止，等待人工审查后再进入下一阶段。",
        ],
        risks=_stage_risks(stage, use_llm),
        memory_updates=[
            memory_update.summary,
            f"长期记忆：{_display_path(memory_update.memory_path)}",
            f"阶段笔记：{_display_path(memory_update.stage_notes_path)}",
        ],
    )
    review_text = render_review(review)
    state.last_review = "console"
    save_state(state, context.state_path)
    return review_text


def _run_llm_stage(stage: str, state: WorkflowState, context: RunContext) -> tuple[str, list[str]]:
    task = (
        f"为阶段 `{stage}` 生成或更新标准产物。"
        "如需写入补充文件，只能写入 outputs/ 或 reproduction/。"
        "复现代码应采用 `reproduction/main.py`、`reproduction/methods/`、`data.py`、`metrics.py` 的通用结构。"
        "最终回复必须是可保存为阶段产物的 Markdown，且不得伪造实验结果。"
    )
    content = invoke_agent(stage, state, task)
    generated: list[str] = []
    if stage in {"baseline", "core"}:
        generated.extend(_ensure_reproduction_scaffold(context))
        generated.append(_ensure_program_report(context))
    return content, generated


def _run_scaffold_stage(stage: str, state: WorkflowState, context: RunContext) -> tuple[str, list[str]]:
    context.outputs_dir.mkdir(parents=True, exist_ok=True)
    (context.outputs_dir / "figures").mkdir(parents=True, exist_ok=True)
    (context.outputs_dir / "tables").mkdir(parents=True, exist_ok=True)
    reference = load_stage_reference(stage)
    templates = load_templates()

    if stage == "literature":
        return _literature_scaffold(state, reference, templates), []
    if stage == "reading":
        generated = _maybe_extract_pdf_text(state, context)
        return _reading_scaffold(state, reference, context), generated
    if stage == "baseline":
        generated = _ensure_reproduction_scaffold(context)
        generated.append(_ensure_results_template(context))
        generated.append(_ensure_program_report(context))
        return _baseline_scaffold(state, reference, context), generated
    if stage == "core":
        generated = _ensure_reproduction_scaffold(context)
        generated.append(_ensure_program_report(context))
        return _core_scaffold(state, reference, context), generated
    if stage == "figures":
        return _figures_scaffold(state, reference, context), []
    if stage == "validation":
        summary_path = "outputs/artifacts_summary.md"
        try:
            summarize_artifacts(summary_path)
            generated = [_display_path(context.outputs_dir / "artifacts_summary.md")]
        except Exception:
            generated = []
        return _validation_scaffold(state, reference, context), generated
    raise ValueError(f"Unknown stage: {stage}")


def _literature_scaffold(state: WorkflowState, reference: str, templates: str) -> str:
    search_notes = []
    paper = state.paper_input or ""
    if paper and Path(paper).suffix.lower() != ".pdf":
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
| 待补全 | 待联网核对 | 待补全 | 待确认 | 确认论文事实 |

## 代码与数据来源

| 仓库/数据集 | 作者/组织 | 入口 | 依赖 | 数据 | 风险 |
| --- | --- | --- | --- | --- | --- |
| 待补全 | 待确认 | 待确认 | 待确认 | 待确认 | 不能把第三方实现当作论文事实 |

{chr(10).join(search_notes)}

## 结论

- 建议先确认论文身份、官方代码和数据许可，再进入精读规格阶段。
- 若来源缺失，后续代码只能生成通用可运行骨架，不能声称完成论文实验复现。

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

| 方法 | 文件 | 输入 | 输出 | 状态 |
| --- | --- | --- | --- | --- |
| 基线方法 | `reproduction/methods/baseline.py` | 待确认 | 待确认 | 待实现 |
| 论文核心方法 | `reproduction/methods/proposed.py` | 待确认 | 待确认 | 待实现 |

## 数据与指标

- 数据集：待从论文和官方来源确认。
- 评价指标：待从论文表格和实验章节确认。
- 随机种子、训练轮数、硬件环境：待确认。

## 图表目标

- 只复现论文中支撑主要结论的必要图表。
- 每张图表必须能追溯到真实运行数据或明确标注为未完成。

## 真实性约束

- `outputs/tables/results.csv` 中的 `reproduced_value` 只能来自真实程序运行。
- 若方法仍是脚手架，必须保留 `status=not_run` 或 `status=todo`。
- 不允许使用 proxy、fake、dummy 结果冒充复现值。

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
    return f"""# 基线方法实现

## 输入依据

- 论文输入：{state.paper_input}
- 复现规格：`{_display_path(context.outputs_dir / "reproduction_spec.md")}`
- 主程序：`{_display_path(context.reproduction_dir / "main.py")}`
- 基线文件：`{_display_path(context.reproduction_dir / "methods" / "baseline.py")}`

## 已生成的通用代码结构

- `reproduction/main.py`：整体比较入口，统一运行方法并写入 `outputs/tables/results.csv`。
- `reproduction/methods/baseline.py`：基线方法占位实现。
- `reproduction/methods/proposed.py`：论文核心方法占位实现。
- `reproduction/data.py`：数据加载入口。
- `reproduction/metrics.py`：结果表整理入口。
- `reproduction/config.json`：方法、数据和指标配置。

## 运行命令

```bash
python {_display_path(context.reproduction_dir / "main.py")} --outputs {_display_path(context.outputs_dir)}
```

## 约束

- 当前代码只提供可运行骨架，不声称已经实现论文算法。
- 真实数据、指标和方法逻辑应依据 `outputs/reproduction_spec.md` 逐步补齐。

## 本阶段参考

```markdown
{reference}
```
"""


def _core_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    return f"""# 核心方法实现

## 输入依据

- 论文输入：{state.paper_input}
- 复现规格：`{_display_path(context.outputs_dir / "reproduction_spec.md")}`
- 核心方法文件：`{_display_path(context.reproduction_dir / "methods" / "proposed.py")}`
- 整体比较入口：`{_display_path(context.reproduction_dir / "main.py")}`

## 当前实现边界

- `proposed.py` 已作为论文核心方法的独立入口保留。
- 当前默认实现仍是脚手架；需要根据论文公式、算法和实验设置补齐真实逻辑。
- 主程序会统一比较 `baseline` 与 `proposed`，并把真实运行结果写入 `outputs/tables/results.csv`。

## 风险

- 若 `outputs/reproduction_spec.md` 仍未列出方法、数据和指标，应先补齐 reading 阶段。
- 缺少数据或重依赖时，应先写清替代方案，不得输出伪造指标。

## 本阶段参考

```markdown
{reference}
```
"""


def _figures_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    return f"""# 图表与表格整理计划

## 目录

- 图片目录：`{_display_path(context.outputs_dir / "figures")}`
- 表格目录：`{_display_path(context.outputs_dir / "tables")}`
- 默认结果表：`{_display_path(context.outputs_dir / "tables" / "results.csv")}`

## 精简原则

- 只生成论文复现确实需要的图表，不按某篇论文硬编码数量。
- 表格优先合并到 `outputs/tables/results.csv`，除非论文有多个不可合并的核心表格。
- 每张图和每个表都应能追溯到 `reproduction/main.py` 或明确标注为未完成。

## 当前状态

- 已确保输出目录存在。
- 尚未生成真实图表；需要真实运行数据后继续。

## 本阶段参考

```markdown
{reference}
```
"""


def _validation_scaffold(state: WorkflowState, reference: str, context: RunContext) -> str:
    summary_path = context.outputs_dir / "artifacts_summary.md"
    summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else "未生成产物清单。"
    results_path = context.outputs_dir / "tables" / "results.csv"
    results_note = results_path.read_text(encoding="utf-8") if results_path.exists() else "未生成 results.csv。"
    programs_path = context.outputs_dir / "programs.md"
    programs_note = (
        f"复现程序功能说明见 `{_display_path(programs_path)}`。"
        if programs_path.exists()
        else "尚未生成 `outputs/programs.md`；请先运行 baseline 或 core 阶段。"
    )
    figures = sorted((context.outputs_dir / "figures").glob("*"))
    tables = sorted((context.outputs_dir / "tables").glob("*"))
    return f"""# 论文复现报告

## 论文信息

- 输入：{state.paper_input}
- 运行目录：`{_display_path(context.root_dir)}`

## 复现范围

- 代码结构：各方法独立程序 + 一个整体比较主程序。
- 当前主程序：`{_display_path(context.reproduction_dir / "main.py")}`
- 方法目录：`{_display_path(context.reproduction_dir / "methods")}`
- 程序说明：{programs_note}

## 运行命令

```bash
python {_display_path(context.reproduction_dir / "main.py")} --outputs {_display_path(context.outputs_dir)}
paper-repro review --run-dir {_display_path(context.root_dir)}
```

## 结果表

```csv
{results_note}
```

## 图表与表格

- 图片数量：{len([p for p in figures if p.is_file()])}
- 表格数量：{len([p for p in tables if p.is_file()])}

## 产物清单

{summary}

## 差异与风险

- 若结果表中存在 `not_run`、`todo` 或空复现值，说明尚未获得真实复现数据。
- 本报告不把脚手架输出视为论文复现实验结果。
- 需要在补齐数据加载、方法实现和指标计算后重新运行主程序与审阅命令。

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


def _discover_single_pdf(context: RunContext) -> str:
    context.root_dir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(path for path in context.root_dir.glob("*.pdf") if path.is_file())
    if len(pdfs) == 1:
        return _display_path(pdfs[0])
    if not pdfs:
        raise ValueError(
            "No paper PDF was found in the run directory. Put exactly one PDF in "
            f"`{_display_path(context.root_dir)}` or pass `--paper <PDF|URL|title>` explicitly."
        )
    choices = ", ".join(path.name for path in pdfs)
    raise ValueError(
        "Multiple PDF files were found in the run directory. Pass `--paper` explicitly. "
        f"Found: {choices}"
    )


def _ensure_reproduction_scaffold(context: RunContext) -> list[str]:
    context.reproduction_dir.mkdir(parents=True, exist_ok=True)
    methods_dir = context.reproduction_dir / "methods"
    methods_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    files = {
        context.reproduction_dir / "main.py": _main_py(),
        context.reproduction_dir / "data.py": _data_py(),
        context.reproduction_dir / "metrics.py": _metrics_py(),
        context.reproduction_dir / "config.json": json.dumps(
            {
                "data": {"path": None, "note": "Fill with the real dataset path before claiming reproduction."},
                "methods": ["baseline", "proposed"],
                "metrics": [],
                "seed": 7,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        methods_dir / "__init__.py": "",
        methods_dir / "baseline.py": _method_py("baseline", "Baseline method scaffold."),
        methods_dir / "proposed.py": _method_py("proposed", "Proposed paper method scaffold."),
    }
    for path, content in files.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
        paths.append(path)
    if shutil.which("python"):
        pass
    return [_display_path(path) for path in paths]


def _ensure_program_report(context: RunContext) -> str:
    context.outputs_dir.mkdir(parents=True, exist_ok=True)
    methods_dir = context.reproduction_dir / "methods"
    method_files = sorted(path for path in methods_dir.glob("*.py") if path.name != "__init__.py") if methods_dir.exists() else []
    method_rows = "\n".join(
        f"| `{_display_path(path)}` | 复现一个论文方法，需在 `run(dataset)` 中补齐真实逻辑。 | `{_detect_program_status(path)}` |"
        for path in method_files
    )
    if not method_rows:
        method_rows = "| 暂无 | 尚未生成方法文件。 | missing |"
    path = context.outputs_dir / "programs.md"
    path.write_text(
        f"""# 复现程序功能说明

## 总览

本报告说明 `reproduction/` 下各程序的功能、关系和推荐调用顺序。当前默认骨架不会伪造论文结果；若状态仍为 `todo` 或 `scaffold`，说明需要继续实现论文特定逻辑。

## 程序清单

| 文件 | 功能 | 当前状态 |
| --- | --- | --- |
| `{_display_path(context.reproduction_dir / "main.py")}` | 整体比较主程序，统一加载数据、调用方法并写出 `outputs/tables/results.csv`。 | `{_detect_program_status(context.reproduction_dir / "main.py")}` |
| `{_display_path(context.reproduction_dir / "data.py")}` | 数据加载入口，负责把真实数据转换成方法可用的结构。 | `{_detect_program_status(context.reproduction_dir / "data.py")}` |
| `{_display_path(context.reproduction_dir / "metrics.py")}` | 指标汇总入口，把各方法输出转换成统一结果表。 | `{_detect_program_status(context.reproduction_dir / "metrics.py")}` |
| `{_display_path(context.reproduction_dir / "config.json")}` | 记录数据路径、方法列表、指标和随机种子等配置。 | `{_detect_program_status(context.reproduction_dir / "config.json")}` |
{method_rows}

## 调用顺序

1. 在 `outputs/reproduction_spec.md` 中确认数据集、方法、指标和图表目标。
2. 在 `reproduction/data.py` 中补齐真实数据读取逻辑。
3. 分别实现 `reproduction/methods/*.py` 中的 `run(dataset)`。
4. 在 `reproduction/metrics.py` 中补齐论文指标计算和格式化。
5. 运行主程序：

```bash
python {_display_path(context.reproduction_dir / "main.py")} --outputs {_display_path(context.outputs_dir)}
```

6. 运行审阅：

```bash
paper-repro review --run-dir {_display_path(context.root_dir)}
```

## 真实性约束

- `outputs/tables/results.csv` 的复现值必须来自真实程序运行。
- 若程序仍包含 `todo`、`scaffold`、`placeholder` 等标记，最终报告必须说明尚未完成真实复现。
- 不得把 proxy、fake 或 dummy 结果当作论文复现结果。
""",
        encoding="utf-8",
    )
    return _display_path(path)


def _detect_program_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    markers = ("todo", "scaffold", "placeholder", "not_run", "fake", "dummy", "proxy")
    if any(marker in text for marker in markers):
        return "scaffold/todo"
    return "present"


def _ensure_results_template(context: RunContext) -> str:
    tables = context.outputs_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    path = tables / "results.csv"
    if not path.exists():
        path.write_text(
            "method,metric,paper_value,reproduced_value,data_source,status,note\n"
            "baseline,not_run,,,none,todo,Fill after implementing and running the real baseline.\n"
            "proposed,not_run,,,none,todo,Fill after implementing and running the real paper method.\n",
            encoding="utf-8",
        )
    return _display_path(path)


def _main_py() -> str:
    return '''#!/usr/bin/env python
"""Generic comparison runner for a paper reproduction."""

from __future__ import annotations

import argparse
import csv
import importlib
from pathlib import Path
import sys

from data import load_dataset
from metrics import summarize_result


DEFAULT_METHODS = ["baseline", "proposed"]


def run_method(name: str, dataset: dict) -> list[dict]:
    module = importlib.import_module(f"methods.{name}")
    result = module.run(dataset)
    return summarize_result(name, result)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["method", "metric", "paper_value", "reproduced_value", "data_source", "status", "note"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all paper reproduction methods and compare results.")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--data", type=Path, default=None, help="Optional real dataset path.")
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    args = parser.parse_args(argv)

    dataset = load_dataset(args.data)
    rows: list[dict] = []
    for method in args.methods:
        rows.extend(run_method(method, dataset))
    out_path = args.outputs / "tables" / "results.csv"
    write_rows(out_path, rows)
    print(f"Wrote {out_path}")
    if any(row.get("status") not in {"ok", "valid", "complete"} for row in rows):
        print("WARNING: one or more methods are still scaffold/todo outputs.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _data_py() -> str:
    return '''"""Data loading helpers for the reproduction runner."""

from __future__ import annotations

from pathlib import Path


def load_dataset(path: Path | None = None) -> dict:
    if path is None:
        return {
            "source": "none",
            "status": "todo",
            "note": "No real dataset path was provided.",
            "records": [],
        }
    if not path.exists():
        return {
            "source": str(path),
            "status": "missing",
            "note": "Dataset path does not exist.",
            "records": [],
        }
    return {
        "source": str(path),
        "status": "available",
        "note": "Dataset path exists; implement paper-specific parsing here.",
        "records": [],
    }
'''


def _metrics_py() -> str:
    return '''"""Metric formatting helpers for paper reproduction results."""

from __future__ import annotations


def summarize_result(method: str, result: dict) -> list[dict]:
    metrics = result.get("metrics") or {}
    if not metrics:
        return [
            {
                "method": method,
                "metric": "not_run",
                "paper_value": "",
                "reproduced_value": "",
                "data_source": result.get("data_source", "none"),
                "status": result.get("status", "todo"),
                "note": "; ".join(result.get("notes", [])) or "No real metric has been produced.",
            }
        ]
    rows = []
    for metric, value in metrics.items():
        rows.append(
            {
                "method": method,
                "metric": metric,
                "paper_value": result.get("paper_values", {}).get(metric, ""),
                "reproduced_value": value,
                "data_source": result.get("data_source", "unknown"),
                "status": result.get("status", "ok"),
                "note": "; ".join(result.get("notes", [])),
            }
        )
    return rows
'''


def _method_py(name: str, doc: str) -> str:
    return f'''"""{doc}"""

from __future__ import annotations


def run(dataset: dict) -> dict:
    return {{
        "name": "{name}",
        "status": "todo",
        "metrics": {{}},
        "paper_values": {{}},
        "data_source": dataset.get("source", "none"),
        "notes": [
            "This is a scaffold. Replace it with the real paper-specific implementation.",
            "Do not treat this output as a reproduced paper result.",
        ],
    }}
'''


def _stage_risks(stage: str, use_llm: bool) -> list[str]:
    risks = []
    if not use_llm:
        risks.append("本次未启用 LLM，产物为确定性通用脚手架；论文事实需要人工或后续 LLM 阶段补全。")
    if stage == "literature":
        risks.append("联网检索结果可能受网络、API 限流或论文标题歧义影响。")
    if stage == "reading":
        risks.append("PDF 文本抽取可能遗漏公式、表格、图注或多栏顺序。")
    if stage in {"baseline", "core"}:
        risks.append("通用代码骨架不会伪造论文算法，必须依据复现规格继续实现真实方法。")
    if stage == "validation":
        risks.append("若结果表仍包含 todo/not_run，则报告只能视为复现状态摘要。")
    return risks


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()
