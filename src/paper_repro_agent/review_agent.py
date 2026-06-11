from __future__ import annotations

import csv
from pathlib import Path
from typing import TypedDict

from .paths import RunContext
from .state import STAGES, load_state


class ReviewState(TypedDict):
    context: RunContext
    findings: list[str]
    conclusion: str


def run_review(context: RunContext) -> str:
    context.outputs_dir.mkdir(parents=True, exist_ok=True)
    initial: ReviewState = {"context": context, "findings": [], "conclusion": "不通过"}
    try:
        state = _run_langgraph(initial)
    except Exception:
        state = _run_sequential(initial)
    report = _render_report(state)
    path = context.outputs_dir / "review.md"
    path.write_text(report, encoding="utf-8")
    return _display_path(path)


def _run_langgraph(state: ReviewState) -> ReviewState:
    from langgraph.graph import END, StateGraph
    from langgraph.checkpoint.memory import MemorySaver

    graph = StateGraph(ReviewState)
    graph.add_node("code_reviewer", _code_reviewer)
    graph.add_node("artifact_reviewer", _artifact_reviewer)
    graph.add_node("data_reviewer", _data_reviewer)
    graph.add_node("final_gatekeeper", _final_gatekeeper)
    graph.set_entry_point("code_reviewer")
    graph.add_edge("code_reviewer", "artifact_reviewer")
    graph.add_edge("artifact_reviewer", "data_reviewer")
    graph.add_edge("data_reviewer", "final_gatekeeper")
    graph.add_edge("final_gatekeeper", END)
    app = graph.compile(checkpointer=MemorySaver())
    return app.invoke(state, config={"configurable": {"thread_id": "generic-review"}})


def _run_sequential(state: ReviewState) -> ReviewState:
    for node in (_code_reviewer, _artifact_reviewer, _data_reviewer, _final_gatekeeper):
        state = node(state)
    return state


def _code_reviewer(state: ReviewState) -> ReviewState:
    context = state["context"]
    findings = list(state["findings"])
    main = context.reproduction_dir / "main.py"
    methods_dir = context.reproduction_dir / "methods"
    methods = sorted(path for path in methods_dir.glob("*.py") if path.name != "__init__.py") if methods_dir.exists() else []
    findings.append(f"代码结构：检测到 {len(methods)} 个方法文件。")
    if not main.exists():
        findings.append("BLOCKER: 缺少 `reproduction/main.py`，无法统一运行和比较方法。")
    if not methods:
        findings.append("BLOCKER: 缺少 `reproduction/methods/*.py` 方法文件。")
    for required in ["data.py", "metrics.py", "config.json"]:
        if not (context.reproduction_dir / required).exists():
            findings.append(f"BLOCKER: 缺少必要辅助文件 `reproduction/{required}`。")
    empty_code = [
        path
        for path in [main, context.reproduction_dir / "data.py", context.reproduction_dir / "metrics.py", *methods]
        if path.exists() and path.is_file() and path.stat().st_size == 0 and path.name != "__init__.py"
    ]
    if empty_code:
        findings.append("BLOCKER: 存在空代码文件：" + ", ".join(_display_path(path) for path in empty_code))
    state["findings"] = findings
    return state


def _artifact_reviewer(state: ReviewState) -> ReviewState:
    context = state["context"]
    findings = list(state["findings"])
    figures = sorted((context.outputs_dir / "figures").glob("*")) if (context.outputs_dir / "figures").exists() else []
    tables = sorted((context.outputs_dir / "tables").glob("*")) if (context.outputs_dir / "tables").exists() else []
    figure_files = [path for path in figures if path.is_file()]
    table_files = [path for path in tables if path.is_file()]
    real_figures = [path for path in figure_files if path.name.lower() != "readme.md"]
    findings.append(f"图表数量：图片 {len(real_figures)} 个，表格 {len(table_files)} 个。")
    empty = [path for path in figure_files + table_files if path.stat().st_size == 0]
    if empty:
        findings.append("BLOCKER: 存在空图表文件：" + ", ".join(_display_path(path) for path in empty))

    workflow_state = load_state(context.state_path)
    missing_stages = [stage for stage in STAGES if stage not in workflow_state.completed_stages]
    if missing_stages:
        findings.append("BLOCKER: 工作流阶段未全部完成：" + ", ".join(missing_stages))
    if "figures" not in workflow_state.completed_stages:
        findings.append("BLOCKER: 图表阶段未完成，不能判定图表与论文目标匹配。")
    if not (context.outputs_dir / "reproduction_spec.md").exists():
        findings.append("BLOCKER: 缺少 `outputs/reproduction_spec.md`，无法核对图表是否匹配论文目标。")
    if not (context.outputs_dir / "report.md").exists():
        findings.append("BLOCKER: 缺少 `outputs/report.md`。")
    state["findings"] = findings
    return state


def _data_reviewer(state: ReviewState) -> ReviewState:
    context = state["context"]
    findings = list(state["findings"])
    results = context.outputs_dir / "tables" / "results.csv"
    if not results.exists():
        findings.append("BLOCKER: 缺少 `outputs/tables/results.csv`，无法判断数据是否真实有效。")
        state["findings"] = findings
        return state

    rows = _read_csv(results)
    findings.append(f"结果表：检测到 {len(rows)} 行。")
    bad_tokens = ("todo", "not_run", "proxy", "fake", "dummy", "scaffold")
    risky_rows = []
    for index, row in enumerate(rows, start=2):
        text = " ".join(str(value).lower() for value in row.values())
        if any(token in text for token in bad_tokens) or not row.get("reproduced_value"):
            risky_rows.append(index)
    if risky_rows:
        findings.append(
            "BLOCKER: 结果表仍包含未运行、脚手架或空复现值，不能视为真实有效数据；问题行："
            + ", ".join(str(i) for i in risky_rows)
        )
    else:
        findings.append("数据真实性：结果表未发现明显 scaffold/proxy/todo 标记，仍需人工核对数据来源。")
    state["findings"] = findings
    return state


def _final_gatekeeper(state: ReviewState) -> ReviewState:
    findings = state["findings"]
    if any(item.startswith("BLOCKER") or "BLOCKER:" in item for item in findings):
        conclusion = "不通过"
    else:
        conclusion = "通过"
    state["conclusion"] = conclusion
    return state


def _render_report(state: ReviewState) -> str:
    context = state["context"]
    return "\n".join(
        [
            "# 复现审阅报告",
            "",
            f"- 运行目录：`{_display_path(context.root_dir)}`",
            f"- 结论：**{state['conclusion']}**",
            "",
            "## 审阅结果",
            "",
            *[f"- {finding}" for finding in state["findings"]],
            "",
            "## 审阅范围",
            "",
            "- 方法程序是否完整且可由主程序调用。",
            "- 图片和表格数量、文件是否非空。",
            "- 图表/表格是否能与复现规格中的目标对应。",
            "- 结果数据是否来自真实运行，是否仍存在 scaffold/proxy/todo 风险。",
            "",
            "## 建议",
            "",
            "- 若结论不是“通过”，请先补齐阻塞项，再重新运行 `paper-repro review --run-dir <运行目录>`。",
            "- 真实论文结果必须来自 `reproduction/main.py` 或等价可追溯程序运行。",
            "",
        ]
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()
