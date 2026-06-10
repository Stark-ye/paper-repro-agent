from __future__ import annotations

import os

from .references import load_stage_contract, load_stage_reference, load_system_prompt
from .state import STAGE_LABELS, WorkflowState
from .tools import get_tools


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
            "必须使用中文输出。阶段完成后只交付本阶段产物和审查包，不要自动进入下一阶段。",
        ]
    )


def create_repro_agent(stage: str):
    """Create the LangChain agent lazily so tests work without LangChain installed."""
    try:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
    except Exception as exc:  # pragma: no cover - exercised only without dependencies.
        raise RuntimeError(
            "LangChain dependencies are not installed. Run `pip install -e .` first, "
            "or run without `--llm` to use deterministic scaffolding."
        ) from exc

    model_name = os.getenv("PAPER_REPRO_MODEL", "gpt-4.1-mini")
    base_url = os.getenv("PAPER_REPRO_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("PAPER_REPRO_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)
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
    messages = result.get("messages", [])
    if messages:
        latest = messages[-1]
        return getattr(latest, "content", str(latest))
    return str(result)
