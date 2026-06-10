from __future__ import annotations

from dataclasses import dataclass, field

from .state import STAGE_LABELS, next_stage


@dataclass
class StageReview:
    stage: str
    completed: list[str] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)
    key_results: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    memory_updates: list[str] = field(default_factory=list)


def render_review(review: StageReview) -> str:
    upcoming = next_stage(review.stage)
    upcoming_text = STAGE_LABELS[upcoming] if upcoming else "全部阶段已完成，可运行 `paper-repro review` 生成总审阅报告。"
    lines = [
        f"# 阶段审查包：{STAGE_LABELS.get(review.stage, review.stage)}",
        "",
        "本阶段完成：",
        *_as_bullets(review.completed),
        "",
        "生成或更新文件：",
        *_as_bullets(review.generated_files),
        "",
        "关键结果：",
        *_as_bullets(review.key_results),
        "",
        "差异/风险：",
        *_as_bullets(review.risks or ["暂无新增风险；仍需人工核对论文事实和实验结果。"]),
        "",
        "记忆更新：",
        *_as_bullets(review.memory_updates or ["本阶段没有新的长期记忆变化。"]),
        "",
        "下一步：",
        f"- {upcoming_text}",
        "",
        "审查提示：本工具会在每个阶段结束后停止。确认无误后，请显式运行下一阶段命令。",
    ]
    return "\n".join(lines)


def _as_bullets(items: list[str]) -> list[str]:
    if not items:
        return ["- 无"]
    return [f"- {item}" for item in items]
