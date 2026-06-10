from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import RunContext
from .state import STAGE_LABELS, WorkflowState


@dataclass(frozen=True)
class MemoryUpdate:
    summary: str
    memory_path: Path
    stage_notes_path: Path


def update_memory(stage: str, state: WorkflowState, context: RunContext, generated_files: list[str]) -> MemoryUpdate:
    context.outputs_dir.mkdir(parents=True, exist_ok=True)
    memory_path = context.outputs_dir / "memory.md"
    stage_notes_path = context.outputs_dir / "stage_notes.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stage_label = STAGE_LABELS.get(stage, stage)

    existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    if existing:
        memory_text = existing.rstrip() + "\n\n"
        action = "更新长期记忆：追加当前阶段摘要。"
    else:
        memory_text = _initial_memory(state)
        action = "创建长期记忆：记录论文输入、用户偏好和当前执行约束。"

    memory_text += "\n".join(
        [
            f"## 变更记录：{timestamp}",
            "",
            f"- 阶段：{stage_label}",
            f"- 论文输入：{state.paper_input or '未设置'}",
            f"- 已完成阶段：{', '.join(state.completed_stages) if state.completed_stages else '无'}",
            f"- 新增/更新产物：{', '.join(generated_files) if generated_files else '无'}",
            "- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。",
            "",
        ]
    )
    memory_path.write_text(memory_text, encoding="utf-8")

    notes_text = stage_notes_path.read_text(encoding="utf-8") if stage_notes_path.exists() else "# 阶段运行笔记\n\n"
    notes_text = notes_text.rstrip() + "\n\n" + "\n".join(
        [
            f"## {timestamp} - {stage_label}",
            "",
            f"- 输入论文：{state.paper_input or '未设置'}",
            f"- 产物：{', '.join(generated_files) if generated_files else '无'}",
            "- 下一步：人工审核通过后运行下一阶段命令。",
            "",
        ]
    )
    stage_notes_path.write_text(notes_text, encoding="utf-8")
    return MemoryUpdate(summary=action, memory_path=memory_path, stage_notes_path=stage_notes_path)


def _initial_memory(state: WorkflowState) -> str:
    return "\n".join(
        [
            "# 论文复现 Agent 记忆",
            "",
            "## 用户偏好",
            "",
            "- 默认使用中文产物、中文审查包和中文报告。",
            "- 第一版优先轻量可运行；需要安装重依赖或长任务前先确认。",
            "- 每个阶段结束后停止，等待人工审核。",
            "",
            "## 任务记忆",
            "",
            f"- 论文输入：{state.paper_input or '未设置'}",
            "- 运行模式：默认脚手架模式；`--llm` 为可选增强路径。",
            "",
            "## 已确认决策",
            "",
            "- 采用单总控 Agent + 阶段化工具，不拆真正自治子 Agent。",
            "- 支持通过 `--run-dir` 隔离每次运行产物。",
            "",
        ]
    )
