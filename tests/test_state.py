from pathlib import Path

import pytest

from paper_repro_agent.state import (
    WorkflowState,
    load_state,
    next_incomplete_stage,
    next_stage,
    save_state,
    validate_stage_prerequisites,
)


def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = WorkflowState(paper_input="paper.pdf")
    state.mark_completed("literature", tmp_path / "literature_sources.md", mode="scaffold")

    save_state(state, path)
    loaded = load_state(path)

    assert loaded.paper_input == "paper.pdf"
    assert loaded.completed_stages == ["literature"]
    assert "literature" in loaded.artifacts
    assert loaded.run_modes == {"literature": "scaffold"}


def test_load_state_keeps_backward_compatibility(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text(
        '{"paper_input": "paper.pdf", "completed_stages": ["literature"], "artifacts": {}, "risks": []}',
        encoding="utf-8",
    )

    loaded = load_state(path)

    assert loaded.paper_input == "paper.pdf"
    assert loaded.run_modes == {}


def test_next_stage() -> None:
    assert next_stage("literature") == "reading"
    assert next_stage("validation") is None


def test_next_incomplete_stage() -> None:
    assert next_incomplete_stage(WorkflowState(completed_stages=["literature", "reading"])) == "baseline"
    assert next_incomplete_stage(WorkflowState(completed_stages=list(("literature", "reading", "baseline", "core", "figures", "validation")))) is None


def test_validate_stage_prerequisites() -> None:
    validate_stage_prerequisites("literature", WorkflowState())
    validate_stage_prerequisites("reading", WorkflowState(completed_stages=["literature"]))
    with pytest.raises(RuntimeError, match="requires completed prerequisite"):
        validate_stage_prerequisites("validation", WorkflowState(completed_stages=["literature", "reading", "baseline", "core"]))
