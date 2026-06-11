from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
from typing import Any

from .paths import REPO_ROOT
from .references import load_stage_contract, load_stage_reference, load_system_prompt
from .state import STAGE_LABELS, WorkflowState
from .tools import get_tools


@dataclass(frozen=True)
class ModelConfig:
    model: str
    api_key: str
    base_url: str | None


@dataclass(frozen=True)
class AgentStageResult:
    artifact_markdown: str
    files_written: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


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
                "# LangChain 结构化返回协议\n"
                "最终只能返回一个 JSON 对象，不要包裹 Markdown 代码块。JSON 必须包含：\n"
                "- artifact_markdown: string，当前阶段主产物 Markdown。\n"
                "- files_written: string[]，仅列出已经真实落盘的补充文件。\n"
                "- risks: string[]，真实性、数据、代码和环境风险。\n"
                "- next_actions: string[]，下一阶段建议。\n\n"
                "文件写入规则：\n"
                "- 如需写入补充文件，必须调用工具写入当前运行目录下的 outputs/ 或 reproduction/。\n"
                "- files_written 只能包含 outputs/ 或 reproduction/ 下的相对路径。\n"
                "- 不要把计划、建议、将来要写的文件放进 files_written。\n"
                "- 当前阶段主产物由系统根据 artifact_markdown 写入，不要在 files_written 中重复声明。\n\n"
                "真实性规则：\n"
                "- 必须使用中文。\n"
                "- 阶段完成后只交付本阶段产物，不要自动进入下一阶段。\n"
                "- 复现代码保持通用结构：方法独立文件、整体比较主程序、必要辅助程序。\n"
                "- 不得伪造论文实验结果；没有真实运行数据时必须明确标注 not_run/todo/scaffold。"
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
            "LangChain dependencies are not installed or cannot be imported. Run `paper-repro doctor` for details, "
            "install with `pip install -e .[pdf,dev,review]`, or use `--scaffold` for offline deterministic scaffolding."
        ) from exc

    config = load_model_config()
    model = ChatOpenAI(model=config.model, api_key=config.api_key, base_url=config.base_url)
    return create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=build_system_prompt(stage),
        name="paper_repro_orchestrator",
    )


def invoke_agent(stage: str, state: WorkflowState, user_task: str) -> AgentStageResult:
    agent = create_repro_agent(stage)
    state_summary = {
        "paper_input": state.paper_input,
        "completed_stages": state.completed_stages,
        "artifacts": state.artifacts,
        "risks": state.risks,
        "run_modes": state.run_modes,
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
                            f"任务要求：{user_task}\n"
                            "最终只能返回符合协议的 JSON 对象。"
                        ),
                    }
                ]
            }
        )
    except Exception as exc:
        raise RuntimeError(
            "LangChain model invocation failed. Check PAPER_REPRO_MODEL, PAPER_REPRO_BASE_URL "
            "and API key settings, run `paper-repro doctor`, or rerun with `--scaffold`."
        ) from exc
    return parse_agent_result(_latest_message_content(result))


def parse_agent_result(content: str) -> AgentStageResult:
    data = _loads_json_object(content)
    artifact = data.get("artifact_markdown")
    if not isinstance(artifact, str) or not artifact.strip():
        raise ValueError(
            "LangChain agent returned an invalid stage result: missing non-empty `artifact_markdown`. "
            "Rerun after checking the model prompt/configuration, or use `--scaffold`."
        )
    return AgentStageResult(
        artifact_markdown=artifact.strip() + "\n",
        files_written=_string_list(data.get("files_written"), "files_written"),
        risks=_string_list(data.get("risks"), "risks"),
        next_actions=_string_list(data.get("next_actions"), "next_actions"),
    )


def _latest_message_content(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages", [])
        if messages:
            latest = messages[-1]
            content = getattr(latest, "content", None)
            if content is None and isinstance(latest, dict):
                content = latest.get("content")
            return _content_to_text(content if content is not None else latest)
    return _content_to_text(result)


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, dict) and isinstance(item.get("content"), str):
                parts.append(item["content"])
        if parts:
            return "\n".join(parts)
    return str(content)


def _loads_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LangChain agent returned an invalid stage result: final message is not valid JSON. "
            "Expected keys: artifact_markdown, files_written, risks, next_actions. "
            "Rerun after checking the model prompt/configuration, or use `--scaffold`."
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("LangChain agent returned an invalid stage result: JSON root must be an object.")
    return data


def _string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"LangChain agent returned an invalid stage result: `{field_name}` must be a string array.")
    return value
