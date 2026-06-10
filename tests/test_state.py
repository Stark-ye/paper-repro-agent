from pathlib import Path

from paper_repro_agent.state import WorkflowState, load_state, next_stage, save_state


def test_state_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    state = WorkflowState(paper_input="paper.pdf")
    state.mark_completed("literature", tmp_path / "literature_sources.md")

    save_state(state, path)
    loaded = load_state(path)

    assert loaded.paper_input == "paper.pdf"
    assert loaded.completed_stages == ["literature"]
    assert "literature" in loaded.artifacts


def test_next_stage() -> None:
    assert next_stage("literature") == "reading"
    assert next_stage("validation") is None
