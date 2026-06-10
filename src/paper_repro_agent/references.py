from __future__ import annotations

from pathlib import Path

from .paths import REFERENCES_DIR


STAGE_REFERENCES: dict[str, str] = {
    "literature": "literature_search.md",
    "reading": "reading_spec.md",
    "baseline": "code_implementation.md",
    "core": "code_implementation.md",
    "figures": "figures_tables.md",
    "validation": "validation_report.md",
}

FALLBACK_REFERENCES: dict[str, str] = {
    "system_prompt.md": (
        "# 论文复现总控\n\n"
        "你是一个中文论文复现 Agent。按阶段生成可审阅产物，不伪造实验结果；"
        "缺少数据、代码或依赖时必须明确标注风险和后续步骤。"
    ),
    "stage_contract.md": (
        "# 阶段审查规范\n\n"
        "- 说明本阶段完成了什么。\n"
        "- 列出生成或更新的文件。\n"
        "- 标注风险、缺口和下一阶段建议。\n"
        "- 阶段结束后停止，等待人工确认。"
    ),
    "literature_search.md": (
        "# 文献与代码源调查\n\n"
        "确认论文身份、官方主页、作者代码、数据集、许可证和相关复现来源。"
    ),
    "reading_spec.md": (
        "# 论文精读与复现规格\n\n"
        "提取问题定义、方法拆解、数据集、指标、图表目标和真实性约束。"
    ),
    "code_implementation.md": (
        "# 代码实现\n\n"
        "生成方法独立程序、整体比较主程序、数据加载、指标计算和配置文件；"
        "脚手架不得冒充真实复现结果。"
    ),
    "figures_tables.md": (
        "# 图表与表格\n\n"
        "只复现支撑论文主要结论的必要图表；所有表格和图片应能追溯到真实运行数据。"
    ),
    "validation_report.md": (
        "# 验证与报告\n\n"
        "汇总结果表、图表、程序说明、差异分析和未完成风险，形成简洁中文报告。"
    ),
    "templates.md": (
        "# 产物模板\n\n"
        "- outputs/report.md：结果对比与复现状态。\n"
        "- outputs/programs.md：程序功能说明。\n"
        "- outputs/review.md：审阅 Agent 报告。"
    ),
}


def load_reference(filename: str, references_dir: Path = REFERENCES_DIR) -> str:
    path = references_dir / filename
    if not path.exists():
        try:
            return FALLBACK_REFERENCES[filename]
        except KeyError as exc:
            raise FileNotFoundError(f"Reference file not found: {path}") from exc
    return path.read_text(encoding="utf-8")


def load_system_prompt(references_dir: Path = REFERENCES_DIR) -> str:
    return load_reference("system_prompt.md", references_dir=references_dir)


def load_stage_reference(stage: str, references_dir: Path = REFERENCES_DIR) -> str:
    try:
        filename = STAGE_REFERENCES[stage]
    except KeyError as exc:
        raise ValueError(f"Unknown stage: {stage}") from exc
    return load_reference(filename, references_dir=references_dir)


def load_stage_contract(references_dir: Path = REFERENCES_DIR) -> str:
    return load_reference("stage_contract.md", references_dir=references_dir)


def load_templates(references_dir: Path = REFERENCES_DIR) -> str:
    return load_reference("templates.md", references_dir=references_dir)
