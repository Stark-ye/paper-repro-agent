from pathlib import Path

from paper_repro_agent.doctor import CheckResult, _check_env_config, render_doctor_report, run_doctor


def test_render_doctor_report_shows_failed_suggestion() -> None:
    report = render_doctor_report(
        [
            CheckResult("示例检查", False, "导入失败", "运行 pip install -e .[pdf,dev,review]"),
        ]
    )

    assert "# paper-repro 环境诊断" in report
    assert "[FAIL] 示例检查" in report
    assert "建议：运行 pip install -e .[pdf,dev,review]" in report
    assert "发现 1 个阻塞或风险项" in report


def test_check_env_config_masks_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PAPER_REPRO_API_KEY", raising=False)
    monkeypatch.delenv("PAPER_REPRO_BASE_URL", raising=False)
    monkeypatch.delenv("PAPER_REPRO_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr("paper_repro_agent.doctor.REPO_ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "PAPER_REPRO_API_KEY=secret-test-key\n"
        "PAPER_REPRO_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1\n"
        "PAPER_REPRO_MODEL=qwen-plus\n",
        encoding="utf-8",
    )

    result = _check_env_config()

    assert result.ok is True
    assert "API key：已设置" in result.detail
    assert "secret-test-key" not in result.detail


def test_check_env_config_rejects_missing_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PAPER_REPRO_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("paper_repro_agent.doctor.REPO_ROOT", tmp_path)

    result = _check_env_config()

    assert result.ok is False
    assert ".env.example" in result.suggestion
    assert "--scaffold" in result.suggestion


def test_run_doctor_returns_report() -> None:
    report = run_doctor()
    assert "# paper-repro 环境诊断" in report
    assert "Python 版本" in report
    assert "LangChain Agent 符号" in report
