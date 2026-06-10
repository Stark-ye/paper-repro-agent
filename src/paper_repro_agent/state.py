from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from .paths import OUTPUTS_DIR


STAGES: tuple[str, ...] = (
    "literature",
    "reading",
    "baseline",
    "core",
    "figures",
    "validation",
)

STAGE_LABELS: dict[str, str] = {
    "literature": "文献与代码源调查",
    "reading": "论文精读与复现规格",
    "baseline": "基线方法实现",
    "core": "核心方法实现",
    "figures": "图表与表格复现",
    "validation": "验证与中文报告",
}


@dataclass
class WorkflowState:
    paper_input: str | None = None
    current_stage: str | None = None
    completed_stages: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    last_review: str | None = None

    def mark_completed(self, stage: str, artifact: Path | None = None) -> None:
        if stage not in self.completed_stages:
            self.completed_stages.append(stage)
        self.current_stage = stage
        if artifact is not None:
            self.artifacts[stage] = str(artifact)


def validate_stage(stage: str) -> None:
    if stage not in STAGES:
        allowed = ", ".join(STAGES)
        raise ValueError(f"Unknown stage '{stage}'. Allowed stages: {allowed}")


def load_state(path: Path | None = None) -> WorkflowState:
    state_path = path or OUTPUTS_DIR / "state.json"
    if not state_path.exists():
        return WorkflowState()
    data: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
    return WorkflowState(
        paper_input=data.get("paper_input"),
        current_stage=data.get("current_stage"),
        completed_stages=list(data.get("completed_stages", [])),
        artifacts=dict(data.get("artifacts", {})),
        risks=list(data.get("risks", [])),
        last_review=data.get("last_review"),
    )


def save_state(state: WorkflowState, path: Path | None = None) -> Path:
    state_path = path or OUTPUTS_DIR / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state_path


def next_stage(stage: str) -> str | None:
    validate_stage(stage)
    index = STAGES.index(stage)
    if index + 1 >= len(STAGES):
        return None
    return STAGES[index + 1]
