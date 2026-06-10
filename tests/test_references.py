from pathlib import Path

from paper_repro_agent.references import STAGE_REFERENCES, load_stage_reference, load_system_prompt


def test_load_stage_reference() -> None:
    text = load_stage_reference("literature")
    assert isinstance(text, str)
    assert len(text) > 20


def test_load_system_prompt() -> None:
    text = load_system_prompt()
    assert isinstance(text, str)
    assert len(text) > 20


def test_reference_files_exist_and_define_artifacts() -> None:
    root = Path("paper-repro-orchestrator")
    assert (root / "SKILL.md").exists()
    for filename in {"system_prompt.md", "stage_contract.md", "templates.md", *STAGE_REFERENCES.values()}:
        path = root / "references" / filename
        text = path.read_text(encoding="utf-8")
        assert len(text) > 20
        assert text.lstrip().startswith("#")
