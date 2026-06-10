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


def load_reference(filename: str, references_dir: Path = REFERENCES_DIR) -> str:
    path = references_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Reference file not found: {path}")
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
