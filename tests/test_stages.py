from pathlib import Path

import pytest

from paper_repro_agent.agent import AgentStageResult
from paper_repro_agent.paths import make_run_context
from paper_repro_agent.stages import run_stage
from paper_repro_agent.state import WorkflowState, load_state


def _completed_state(*stages: str) -> WorkflowState:
    state = WorkflowState(paper_input="Demo Paper")
    for stage in stages:
        state.mark_completed(stage)
    return state


def test_run_stage_writes_to_run_dir(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState()

    review = run_stage("literature", state=state, paper="Demo Paper", use_llm=False, context=context)

    assert "阶段审查包" in review
    assert "运行模式：scaffold" in review
    assert "已通过阶段产物闭环校验" in review
    assert (tmp_path / "outputs" / "literature_sources.md").exists()
    assert (tmp_path / "outputs" / "memory.md").exists()
    assert (tmp_path / "outputs" / "stage_notes.md").exists()
    assert (tmp_path / "outputs" / "state.json").exists()
    assert load_state(tmp_path / "outputs" / "state.json").run_modes["literature"] == "scaffold"


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


def test_stage_prerequisites_are_enforced(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)

    with pytest.raises(RuntimeError, match="requires completed prerequisite"):
        run_stage("validation", state=_completed_state("literature", "reading", "baseline", "core"), use_llm=False, context=context)


def test_baseline_stage_generates_generic_reproduction_scaffold(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = _completed_state("literature", "reading")

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
    state = _completed_state("literature", "reading", "baseline")

    run_stage("core", state=state, use_llm=False, context=context)

    text = (tmp_path / "outputs" / "programs.md").read_text(encoding="utf-8")
    assert "复现程序功能说明" in text
    assert "reproduction/methods/proposed.py" in text


def test_llm_stage_uses_structured_agent_result(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")
    extra = tmp_path / "outputs" / "extra.md"
    extra.parent.mkdir(parents=True)
    extra.write_text("extra\n", encoding="utf-8")

    def fake_invoke(stage, state, task):
        return AgentStageResult(
            artifact_markdown="# LLM 文献调查\n\n- 已按协议返回。",
            files_written=["outputs/extra.md"],
            risks=["需要人工核对来源"],
            next_actions=["继续 reading"],
        )

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    review = run_stage("literature", state=state, use_llm=True, context=context)

    assert "运行模式：langchain" in review
    assert "下一步建议：继续 reading" in review
    assert (tmp_path / "outputs" / "literature_sources.md").read_text(encoding="utf-8").startswith("# LLM 文献调查")
    loaded = load_state(tmp_path / "outputs" / "state.json")
    assert loaded.run_modes["literature"] == "langchain"
    assert "需要人工核对来源" in loaded.risks


def test_llm_declared_generated_file_must_exist(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")

    def fake_invoke(stage, state, task):
        return AgentStageResult(
            artifact_markdown="# LLM 文献调查",
            files_written=["outputs/missing_notes.md"],
        )

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    with pytest.raises(RuntimeError, match="declared generated file does not exist"):
        run_stage("literature", state=state, use_llm=True, context=context)
    assert not (tmp_path / "outputs" / "state.json").exists()


def test_llm_declared_generated_file_cannot_escape_run_dir(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    outside = tmp_path.parent / "outside_notes.md"
    outside.write_text("outside\n", encoding="utf-8")
    state = WorkflowState(paper_input="Demo Paper")

    def fake_invoke(stage, state, task):
        return AgentStageResult(
            artifact_markdown="# LLM 文献调查",
            files_written=[str(outside)],
        )

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    with pytest.raises(RuntimeError, match="relative paths"):
        run_stage("literature", state=state, use_llm=True, context=context)


def test_llm_declared_generated_file_must_use_allowed_roots(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")

    def fake_invoke(stage, state, task):
        return AgentStageResult(
            artifact_markdown="# LLM 文献调查",
            files_written=["notes/outside.md"],
        )

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    with pytest.raises(RuntimeError, match="outputs/ or reproduction"):
        run_stage("literature", state=state, use_llm=True, context=context)


def test_llm_baseline_creates_results_template(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = _completed_state("literature", "reading")

    def fake_invoke(stage, state, task):
        return AgentStageResult(artifact_markdown="# 基线实现\n\n- 仍为脚手架。")

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    run_stage("baseline", state=state, use_llm=True, context=context)

    results = (tmp_path / "outputs" / "tables" / "results.csv").read_text(encoding="utf-8")
    assert "todo" in results
    assert "not_run" in results


def test_validation_report_must_disclose_unfinished_results(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = _completed_state("literature", "reading", "baseline", "core", "figures")
    (context.outputs_dir / "tables").mkdir(parents=True)
    (context.outputs_dir / "tables" / "results.csv").write_text(
        "method,metric,paper_value,reproduced_value,data_source,status,note\n"
        "baseline,not_run,,,none,todo,\n",
        encoding="utf-8",
    )

    def fake_invoke(stage, state, task):
        return AgentStageResult(artifact_markdown="# 完成报告\n\n结果很好。")

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    with pytest.raises(RuntimeError, match="does not disclose"):
        run_stage("validation", state=state, use_llm=True, context=context)


def test_invalid_llm_stage_result_does_not_write_state(monkeypatch, tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    state = WorkflowState(paper_input="Demo Paper")

    def fake_invoke(stage, state, task):
        raise ValueError("LangChain agent returned an invalid stage result")

    monkeypatch.setattr("paper_repro_agent.stages.invoke_agent", fake_invoke)

    with pytest.raises(ValueError, match="invalid stage result"):
        run_stage("literature", state=state, use_llm=True, context=context)

    assert not (tmp_path / "outputs" / "state.json").exists()
    assert not (tmp_path / "outputs" / "literature_sources.md").exists()
