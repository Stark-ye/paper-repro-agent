from pathlib import Path

import pytest

from paper_repro_agent.agent import build_system_prompt, load_model_config, parse_agent_result


def test_load_model_config_requires_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PAPER_REPRO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("paper_repro_agent.agent.REPO_ROOT", tmp_path)

    with pytest.raises(RuntimeError, match=".env.example"):
        load_model_config()


def test_load_model_config_rejects_placeholder_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PAPER_REPRO_API_KEY", "your_dashscope_api_key_here")
    monkeypatch.setattr("paper_repro_agent.agent.REPO_ROOT", tmp_path)

    with pytest.raises(RuntimeError, match="PAPER_REPRO_API_KEY"):
        load_model_config()


def test_load_model_config_supports_openai_compatible_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PAPER_REPRO_API_KEY", "test-key")
    monkeypatch.setenv("PAPER_REPRO_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("PAPER_REPRO_MODEL", "qwen-plus")
    monkeypatch.setattr("paper_repro_agent.agent.REPO_ROOT", tmp_path)

    config = load_model_config()

    assert config.api_key == "test-key"
    assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.model == "qwen-plus"


def test_load_model_config_reads_dotenv(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PAPER_REPRO_API_KEY", raising=False)
    monkeypatch.delenv("PAPER_REPRO_BASE_URL", raising=False)
    monkeypatch.delenv("PAPER_REPRO_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("paper_repro_agent.agent.REPO_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "PAPER_REPRO_API_KEY=dotenv-key\n"
        "PAPER_REPRO_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1\n"
        "PAPER_REPRO_MODEL=qwen-plus\n",
        encoding="utf-8",
    )

    config = load_model_config()

    assert config.api_key == "dotenv-key"
    assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.model == "qwen-plus"


def test_build_system_prompt_contains_stage_contract() -> None:
    prompt = build_system_prompt("literature")
    assert "论文复现" in prompt
    assert "文献与代码源调查" in prompt
    assert "阶段审查规范" in prompt
    assert "artifact_markdown" in prompt
    assert "files_written 只能包含 outputs/ 或 reproduction/ 下的相对路径" in prompt


def test_parse_agent_result_accepts_required_protocol() -> None:
    result = parse_agent_result(
        """
        {
          "artifact_markdown": "# 文献调查\\n\\n- 已完成。",
          "files_written": ["outputs/extra.md"],
          "risks": ["需要人工核对来源"],
          "next_actions": ["进入 reading"]
        }
        """
    )

    assert result.artifact_markdown.startswith("# 文献调查")
    assert result.files_written == ["outputs/extra.md"]
    assert result.risks == ["需要人工核对来源"]
    assert result.next_actions == ["进入 reading"]


def test_parse_agent_result_rejects_non_json() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_agent_result("# 普通 Markdown")


def test_parse_agent_result_rejects_missing_artifact() -> None:
    with pytest.raises(ValueError, match="artifact_markdown"):
        parse_agent_result('{"files_written": [], "risks": [], "next_actions": []}')


def test_parse_agent_result_rejects_bad_list_fields() -> None:
    with pytest.raises(ValueError, match="files_written"):
        parse_agent_result('{"artifact_markdown": "# ok", "files_written": "outputs/a.md"}')
