# 轻量化论文复现 Agent 实施计划

## Summary

- 第一版采用 **单总控 Agent + 阶段化工具/节点**，不拆真正自治子 Agent。
- 使用 Python + LangChain 构建 CLI 版轻量 Agent，默认 OpenAI 兼容模型接入。
- 已将 `paper-repro-orchestrator` 的阶段规则、参考模块和产物规范汇入 `agent工作流.md`。
- 根目录 `IMPLEMENTATION_PLAN.md` 作为后续实现、测试和扩展调用入口。
- 已完成 `--run-dir` 隔离运行、记忆文件写入、AKIT PDF 脚手架测试、README 调用说明和 GitHub 发布准备。

## Key Changes

- 文档层：
  - `agent工作流.md` 保留研究简介，并补充总控 Agent、阶段流程、工具模块、人工审核闸门、标准产物和运行命令。
  - `IMPLEMENTATION_PLAN.md` 记录当前实现计划，后续代码变更按该文件维护。
- 代码层：
  - `src/paper_repro_agent/` 提供 CLI、LangChain agent 构建、阶段状态管理、工具封装、提示词加载和审查包生成。
  - 复用现有脚本：`extract_pdf_text.py`、`check_outputs.py`、`summarize_artifacts.py`。
  - LangChain 依赖懒加载；无模型配置时仍可运行确定性阶段脚手架。
- CLI 接口：
  - `paper-repro run --paper <PDF|URL|标题> --stage literature --run-dir <运行目录>`
  - `paper-repro run --stage reading --run-dir <运行目录>`
  - `paper-repro run --stage baseline --run-dir <运行目录>`
  - `paper-repro run --stage core --run-dir <运行目录>`
  - `paper-repro run --stage figures --run-dir <运行目录>`
  - `paper-repro run --stage validation --run-dir <运行目录>`
  - `paper-repro state --run-dir <运行目录>`
  - `paper-repro run ... --llm` 启用 LangChain agent 路径。
  - `README.md` 记录安装、调用、LLM 配置、AKIT PDF 冒烟测试和产物目录。
- 发布层：
  - `.gitignore` 排除缓存、虚拟环境、本地密钥和默认运行产物。
  - `LICENSE` 使用 MIT License。
  - `.github/workflows/tests.yml` 在 GitHub Actions 中运行 `python -m pytest -q`。
  - 他人可用 `pip install "paper-repro-agent[pdf] @ git+https://github.com/<user>/<repo>.git"` 从 GitHub 安装。

## Agent Design

- 总控 Agent：
  - 读取 `references/system_prompt.md` 作为主系统提示。
  - 根据当前阶段加载对应 reference。
  - 调用工具完成阶段任务，生成阶段产物和审查包。
- 工具封装：
  - 文献检索：arXiv、Semantic Scholar。
  - PDF：调用现有 PDF 抽取脚本。
  - 文件：只允许写入 `outputs/` 和 `reproduction/`。
  - 执行：检查图表与表格，汇总产物。
- 子 Agent 策略：
  - v1 不拆独立子 Agent。
  - 用阶段函数模拟文献分析、论文精读、代码实现、图表复现和验证报告的角色边界。
  - 后续只有在单阶段提示过长、工具冲突明显或需要并行执行时，再拆 LangGraph 子图。

## Test Plan

- 单元测试：
  - 阶段状态读写。
  - reference 文件加载。
  - 审查包 Markdown 生成。
  - CLI 参数解析。
- 集成测试：
  - 使用标题输入跑通 `literature`。
  - 使用已有 state 跑通 `reading`。
  - 使用伪造 `outputs/reproduction_spec.md` 跑通 `baseline -> figures -> validation`。
  - 验证每个阶段完成后不会自动进入下一阶段。
- 手工验收：
  - 输入论文标题或 PDF 后能生成中文结构化产物。
  - 产物路径符合 skill 约定。
  - 缺少依赖、缺少 PDF 抽取工具或联网失败时，能给出清晰风险和替代方案。
  - AKIT PDF 脚手架测试结果保存在 `tests/akit_pdf_smoke/`。

## Assumptions

- 第一版运行形态为 CLI。
- 默认模型接入为 OpenAI 兼容方式，通过环境变量配置 API key、base URL 和 model。
- 使用 LangChain `create_agent` 组合模型、工具和系统提示。
- 人工审核先用 CLI 阶段停止机制实现，必要时再升级为 LangGraph interrupt/human-in-the-loop。
- 确定性脚手架不会伪造论文事实或实验结果。
