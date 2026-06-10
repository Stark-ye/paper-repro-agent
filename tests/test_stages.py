from pathlib import Path

import pytest

from paper_repro_agent.paths import make_run_context
from paper_repro_agent.stages import run_stage
from paper_repro_agent.state import WorkflowState


def test_run_stage_writes_to_run_dir(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState()

    review = run_stage("literature", state=state, paper="Demo Paper", use_llm=False, context=context)

    assert "阶段审查包" in review
    assert (tmp_path / "outputs" / "literature_sources.md").exists()
    assert (tmp_path / "outputs" / "memory.md").exists()
    assert (tmp_path / "outputs" / "stage_notes.md").exists()
    assert (tmp_path / "outputs" / "state.json").exists()


def test_run_stage_discovers_single_pdf_in_run_dir(tmp_path: Path) -> None:
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-1.4\n")
    context = make_run_context(tmp_path)
    state = WorkflowState()

    run_stage("literature", state=state, use_llm=False, context=context)

    assert state.paper_input is not None
    assert state.paper_input.endswith("paper.pdf")
    assert (tmp_path / "outputs" / "literature_sources.md").exists()


def test_run_stage_requires_pdf_or_paper_input(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)

    with pytest.raises(ValueError, match="No paper PDF"):
        run_stage("literature", state=WorkflowState(), use_llm=False, context=context)


def test_run_stage_rejects_multiple_auto_discovered_pdfs(tmp_path: Path) -> None:
    (tmp_path / "one.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "two.pdf").write_bytes(b"%PDF-1.4\n")
    context = make_run_context(tmp_path)

    with pytest.raises(ValueError, match="Multiple PDF"):
        run_stage("literature", state=WorkflowState(), use_llm=False, context=context)


def test_baseline_stage_generates_generic_reproduction_scaffold(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")

    run_stage("baseline", state=state, use_llm=False, context=context)

    assert (tmp_path / "reproduction" / "main.py").exists()
    assert (tmp_path / "reproduction" / "data.py").exists()
    assert (tmp_path / "reproduction" / "metrics.py").exists()
    assert (tmp_path / "reproduction" / "config.json").exists()
    assert (tmp_path / "reproduction" / "methods" / "baseline.py").exists()
    assert (tmp_path / "reproduction" / "methods" / "proposed.py").exists()
    assert (tmp_path / "outputs" / "tables" / "results.csv").exists()
    assert (tmp_path / "outputs" / "programs.md").exists()


def test_core_stage_updates_program_report(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")

    run_stage("core", state=state, use_llm=False, context=context)

    text = (tmp_path / "outputs" / "programs.md").read_text(encoding="utf-8")
    assert "复现程序功能说明" in text
    assert "reproduction/methods/proposed.py" in text
