from __future__ import annotations

from dataclasses import dataclass
import os

from .paths import REPO_ROOT
from .references import load_stage_contract, load_stage_reference, load_system_prompt
from .state import STAGE_LABELS, WorkflowState
from .tools import get_tools


@dataclass(frozen=True)
class ModelConfig:
    model: str
    api_key: str
    base_url: str | None


def build_system_prompt(stage: str) -> str:
    system_prompt = load_system_prompt()
    stage_reference = load_stage_reference(stage)
    stage_contract = load_stage_contract()
    return "\n\n".join(
        [
            system_prompt,
            f"# 当前阶段\n{STAGE_LABELS.get(stage, stage)}",
            "# 当前阶段参考模块",
            stage_reference,
            "# 阶段审查规范",
            stage_contract,
            (
                "必须使用中文输出。阶段完成后只交付本阶段产物和审查包，不要自动进入下一阶段。"
                "复现代码应保持通用结构：方法独立文件、整体比较主程序、必要辅助程序。"
                "不得伪造论文实验结果；没有真实运行数据时要明确标注。"
            ),
        ]
    )


def load_model_config() -> ModelConfig:
    env_file = _read_dotenv(REPO_ROOT / ".env")
    model_name = _env_value("PAPER_REPRO_MODEL", env_file) or "gpt-4.1-mini"
    base_url = _env_value("PAPER_REPRO_BASE_URL", env_file) or _env_value("OPENAI_BASE_URL", env_file)
    api_key = _env_value("PAPER_REPRO_API_KEY", env_file) or _env_value("OPENAI_API_KEY", env_file)
    if not api_key or _is_placeholder_key(api_key):
        raise RuntimeError(
            "Missing model API key. Set PAPER_REPRO_API_KEY or OPENAI_API_KEY, "
            "or copy `.env.example` to `.env` and fill in PAPER_REPRO_API_KEY. "
            "Optional settings: PAPER_REPRO_BASE_URL and PAPER_REPRO_MODEL. "
            "For offline deterministic scaffolding, rerun with `--scaffold`."
        )
    return ModelConfig(model=model_name, api_key=api_key, base_url=base_url)


def _env_value(name: str, env_file: dict[str, str]) -> str | None:
    return os.getenv(name) or env_file.get(name)


def _read_dotenv(path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _is_placeholder_key(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or "your_" in normalized or "api_key_here" in normalized or normalized in {"changeme", "todo"}


def create_repro_agent(stage: str):
    """Create the LangChain agent lazily so tests can run in scaffold mode."""
    try:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
    except Exception as exc:  # pragma: no cover - exercised only without dependencies.
        raise RuntimeError(
            "LangChain dependencies are not installed. Run `pip install -e .` first, "
            "or use `--scaffold` for offline deterministic scaffolding."
        ) from exc

    config = load_model_config()
    model = ChatOpenAI(model=config.model, api_key=config.api_key, base_url=config.base_url)
    return create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=build_system_prompt(stage),
        name="paper_repro_orchestrator",
    )


def invoke_agent(stage: str, state: WorkflowState, user_task: str) -> str:
    agent = create_repro_agent(stage)
    state_summary = {
        "paper_input": state.paper_input,
        "completed_stages": state.completed_stages,
        "artifacts": state.artifacts,
        "risks": state.risks,
    }
    try:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "请执行论文复现工作流的当前阶段。\n"
                            f"当前状态：{state_summary}\n"
                            f"任务要求：{user_task}"
                        ),
                    }
                ]
            }
        )
    except Exception as exc:
        raise RuntimeError(
            "LangChain model invocation failed. Check PAPER_REPRO_MODEL, PAPER_REPRO_BASE_URL "
            "and API key settings, or rerun with `--scaffold`."
        ) from exc
    messages = result.get("messages", [])
    if messages:
        latest = messages[-1]
        return getattr(latest, "content", str(latest))
    return str(result)
