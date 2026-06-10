from pathlib import Path

from paper_repro_agent.references import load_stage_reference, load_system_prompt


def test_load_stage_reference() -> None:
    text = load_stage_reference("literature")
    assert "文献" in text


def test_load_system_prompt() -> None:
    text = load_system_prompt()
    assert "论文复现" in text
