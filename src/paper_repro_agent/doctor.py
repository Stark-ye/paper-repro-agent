from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess
import sys

from .agent import _is_placeholder_key, _read_dotenv
from .paths import REPO_ROOT


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    suggestion: str = ""


def run_doctor() -> str:
    """Return a Chinese diagnostic report for the local runtime."""
    checks = [
        _check_python(),
        _check_cli_install(),
        _check_env_config(),
        _check_import("langchain"),
        _check_import("langchain_openai"),
        _check_langchain_symbols(),
        _check_torch(),
    ]
    return render_doctor_report(checks)


def render_doctor_report(checks: list[CheckResult]) -> str:
    lines = ["# paper-repro 环境诊断", ""]
    for check in checks:
        mark = "OK" if check.ok else "FAIL"
        lines.append(f"## [{mark}] {check.name}")
        lines.append("")
        lines.append(check.detail)
        if check.suggestion:
            lines.append("")
            lines.append(f"建议：{check.suggestion}")
        lines.append("")

    failed = [check for check in checks if not check.ok]
    lines.append("## 结论")
    lines.append("")
    if failed:
        lines.append(f"- 发现 {len(failed)} 个阻塞或风险项，请先按建议修复。")
        lines.append("- 如暂时不配置模型，可使用 `paper-repro run ... --scaffold` 生成离线脚手架。")
    else:
        lines.append("- 当前环境通过基础检查，可以尝试默认 LangChain 工作流。")
    return "\n".join(lines).rstrip() + "\n"


def _check_python() -> CheckResult:
    version = sys.version.split()[0]
    executable = sys.executable
    ok = sys.version_info >= (3, 10)
    return CheckResult(
        name="Python 版本",
        ok=ok,
        detail=f"Python {version}\n解释器：{executable}",
        suggestion="请使用 Python 3.10 或更高版本。" if not ok else "",
    )


def _check_cli_install() -> CheckResult:
    command = shutil.which("paper-repro")
    if command:
        return CheckResult("CLI 安装", True, f"已找到命令：{command}")

    package_importable = _can_import("paper_repro_agent").ok
    if package_importable:
        detail = "当前 Python 可以导入 `paper_repro_agent`，但 PATH 中没有 `paper-repro` 命令。"
    else:
        detail = "当前 Python 不能导入 `paper_repro_agent`，PATH 中也没有 `paper-repro` 命令。"
    return CheckResult(
        name="CLI 安装",
        ok=False,
        detail=detail,
        suggestion="在项目根目录运行 `pip install -e .[pdf,dev,review]`，然后重新打开终端或刷新 PATH。",
    )


def _check_env_config() -> CheckResult:
    env_file_path = REPO_ROOT / ".env"
    env_file = _read_dotenv(env_file_path)
    api_key = os.getenv("PAPER_REPRO_API_KEY") or env_file.get("PAPER_REPRO_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("PAPER_REPRO_BASE_URL") or env_file.get("PAPER_REPRO_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    model = os.getenv("PAPER_REPRO_MODEL") or env_file.get("PAPER_REPRO_MODEL") or "gpt-4.1-mini"
    env_note = "存在" if env_file_path.exists() else "不存在"
    lines = [
        f".env：{env_note}",
        f"模型：{model}",
        f"Base URL：{base_url or '未设置，使用 langchain-openai 默认值'}",
        f"API key：{'已设置' if api_key else '未设置'}",
    ]
    if not api_key or _is_placeholder_key(api_key):
        return CheckResult(
            name="模型环境变量",
            ok=False,
            detail="\n".join(lines),
            suggestion="复制 `.env.example` 为 `.env` 并填写真实 `PAPER_REPRO_API_KEY`，或设置 `OPENAI_API_KEY`；离线测试请使用 `--scaffold`。",
        )
    return CheckResult("模型环境变量", True, "\n".join(lines))


def _check_import(module_name: str) -> CheckResult:
    result = _can_import(module_name)
    if result.ok:
        return CheckResult(f"导入 {module_name}", True, result.detail)
    return CheckResult(
        name=f"导入 {module_name}",
        ok=False,
        detail=result.detail,
        suggestion=_import_suggestion(result.detail),
    )


def _check_langchain_symbols() -> CheckResult:
    errors: list[str] = []
    for label, statement in [
        ("create_agent", "from langchain.agents import create_agent"),
        ("ChatOpenAI", "from langchain_openai import ChatOpenAI"),
    ]:
        completed = _probe_python(statement)
        if completed.returncode != 0:
            errors.append(f"{label}: {_probe_failure(completed)}")
    if errors:
        detail = "\n".join(errors)
        return CheckResult(
            name="LangChain Agent 符号",
            ok=False,
            detail=detail,
            suggestion=_import_suggestion(detail),
        )
    return CheckResult("LangChain Agent 符号", True, "`create_agent` 和 `ChatOpenAI` 均可导入。")


def _check_torch() -> CheckResult:
    result = _can_import("torch")
    if result.ok:
        return CheckResult("torch 可选检查", True, result.detail)

    detail = result.detail
    lowered = detail.lower()
    if "no module named 'torch'" in lowered or "no module named torch" in lowered:
        return CheckResult(
            "torch 可选检查",
            True,
            "未安装 `torch`。本项目的 LangChain/OpenAI-compatible 工作流不需要 PyTorch，因此不构成阻塞。",
        )

    suggestion = (
        "检测到 torch 已安装但不可导入。若错误包含 `torch\\lib\\c10.dll` 或 DLL 初始化失败，"
        "建议卸载损坏的 torch：`pip uninstall -y torch torchvision torchaudio`。"
        "本项目不依赖 torch；如后续复现论文确实需要 PyTorch，请优先在干净虚拟环境中安装 CPU 或 CUDA 版本。"
    )
    return CheckResult("torch 可选检查", False, detail, suggestion)


def _can_import(module_name: str) -> CheckResult:
    code = (
        "import importlib\n"
        f"module = importlib.import_module({module_name!r})\n"
        "version = getattr(module, '__version__', '')\n"
        "location = getattr(module, '__file__', '')\n"
        "print(version)\n"
        "print(location)\n"
    )
    completed = _probe_python(code)
    if completed.returncode != 0:
        detail = _probe_failure(completed)
        return CheckResult(module_name, False, detail)
    output = completed.stdout.splitlines()
    version = output[0].strip() if output else ""
    location = output[1].strip() if len(output) > 1 else ""
    parts = [f"已导入 `{module_name}`"]
    if version:
        parts.append(f"版本：{version}")
    if location:
        parts.append(f"路径：{location}")
    return CheckResult(module_name, True, "\n".join(parts))


def _probe_python(code: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=[sys.executable, "-c", code],
            returncode=124,
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or "",
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or "导入检查超时。",
        )


def _probe_failure(completed: subprocess.CompletedProcess[str]) -> str:
    text = (completed.stderr or completed.stdout or "").strip()
    if not text:
        text = f"子进程退出码：{completed.returncode}"
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) > 8:
        lines = lines[-8:]
    return "\n".join(lines)


def _import_suggestion(detail: str) -> str:
    base = "在项目根目录运行 `pip install -e .[pdf,dev,review]`。"
    lowered = detail.lower()
    if "c10.dll" in lowered or "dll" in lowered or "torch" in lowered:
        return (
            base
            + " 当前错误疑似由 torch DLL 冲突触发；本项目不依赖 torch，可先卸载损坏的 torch，"
            "或使用干净虚拟环境重新安装依赖。"
        )
    return base


def command_available(command: str) -> bool:
    """Small helper kept testable without invoking shell aliases."""
    try:
        completed = subprocess.run(
            [command, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return False
    return completed.returncode == 0
