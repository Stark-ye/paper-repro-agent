from pathlib import Path

from paper_repro_agent.paths import make_run_context
from paper_repro_agent.stages import run_stage
from paper_repro_agent.state import WorkflowState


def test_run_stage_writes_to_run_dir(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState()

    review = run_stage("literature", state=state, paper="Demo Paper", context=context)

    assert "阶段审查包" in review
    assert (tmp_path / "outputs" / "literature_sources.md").exists()
    assert (tmp_path / "outputs" / "memory.md").exists()
    assert (tmp_path / "outputs" / "stage_notes.md").exists()
    assert (tmp_path / "outputs" / "state.json").exists()
