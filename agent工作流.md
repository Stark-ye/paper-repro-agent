# 基于 AI Agent 的论文调研与复现自动化工作流构建

## 研究简介

面向 AI 方向论文调研、方法总结与代码复现流程耗时长的问题，本项目搭建基于 LangChain 的轻量化论文复现 Agent 工作流，整合论文检索、PDF 解析、结构化总结、相似文献查询、代码骨架生成、图表检查与中文报告模块，实现科研文献分析与复现准备的自动化。

## 总体设计

第一版采用 **单总控 Agent + 阶段化工具/节点**，不拆分真正自治子 Agent。`paper-repro-orchestrator` 的核心能力是阶段编排、人工审核闸门和标准产物约束；如果过早拆分多个自治 Agent，会增加状态同步、上下文压缩和人工审核控制复杂度。

总控 Agent 负责：

- 读取 `paper-repro-orchestrator/references/system_prompt.md` 作为系统提示词。
- 按阶段加载 `literature_search.md`、`reading_spec.md`、`code_implementation.md`、`figures_tables.md`、`validation_report.md`。
- 调用检索、PDF 抽取、文件写入、脚本执行和产物汇总工具。
- 每个阶段结束后生成审查包并停止，等待用户人工确认后再进入下一阶段。

## 阶段流程

| 阶段 | 命令 | 主要产物 | 说明 |
| --- | --- | --- | --- |
| 文献与代码源调查 | `paper-repro run --paper "<PDF/URL/标题>" --stage literature --run-dir <运行目录>` | `outputs/literature_sources.md` | 确认论文身份、官方来源、代码库、数据集和依赖风险。 |
| 论文精读与复现规格 | `paper-repro run --stage reading --run-dir <运行目录>` | `outputs/reproduction_spec.md` | 提取问题定义、公式、算法、实验设置、图表和复现边界。 |
| 基线方法实现 | `paper-repro run --stage baseline --run-dir <运行目录>` | `outputs/baseline_review.md`、`reproduction/run_reproduction.py` | 生成最小可运行基线入口，不伪造实验结果。 |
| 核心方法实现 | `paper-repro run --stage core --run-dir <运行目录>` | `outputs/core_method_review.md` | 根据复现规格补齐论文核心模块和中间指标。 |
| 图表与表格复现 | `paper-repro run --stage figures --run-dir <运行目录>` | `outputs/figures_tables_review.md`、`outputs/figures/`、`outputs/tables/` | 统一图表目录和命名规范。 |
| 验证与中文报告 | `paper-repro run --stage validation --run-dir <运行目录>` | `outputs/report.md`、`outputs/artifacts_summary.md` | 汇总产物、对照论文结果、说明差异和后续扩展。 |

## 工具模块

- 文献检索工具：arXiv、Semantic Scholar 元信息查询。
- PDF 工具：复用 `paper-repro-orchestrator/scripts/extract_pdf_text.py`。
- 文件工具：安全读取工作区文件，只允许写入 `outputs/` 和 `reproduction/`。
- 检查工具：复用 `check_outputs.py` 检查图表和表格。
- 汇总工具：复用 `summarize_artifacts.py` 生成产物清单。

## 人工审核闸门

每个阶段结束时输出审查包：

```text
本阶段完成：
- ...

生成文件：
- ...

关键结果：
- ...

差异/风险：
- ...

下一阶段：
- ...
```

审查包输出后工作流停止。用户确认后，通过下一条 `paper-repro run --stage ...` 命令继续。

## 记忆功能与指令精炼

为保证多阶段论文复现过程中的上下文连续性，工作流加入轻量化记忆功能。记忆不直接保存完整对话，而是把用户的目标、偏好、约束、阶段性更改和已确认结论整理成可复用的结构化摘要。

记忆分为三类：

- 任务记忆：论文输入、复现目标、当前阶段、已完成阶段、下一步任务。
- 用户偏好记忆：输出语言、是否优先轻量实现、是否允许联网、是否允许安装重依赖、代码风格和报告格式偏好。
- 决策与变更记忆：用户在审查包中确认的修改、范围调整、排除项、替代方案和风险接受情况。

记忆文件建议写入：

- `outputs/state.json`：机器可读状态，记录当前阶段、产物路径、风险摘要和最近审查包。
- `outputs/memory.md`：人工可读长期记忆，记录精炼后的用户指令、偏好、关键决策和变更历史。
- `outputs/stage_notes.md`：阶段运行笔记，记录每个阶段的输入、输出、未完成项和下一阶段提示。

每次运行阶段前，总控 Agent 先读取 `outputs/state.json` 和 `outputs/memory.md`，再把当前用户输入与历史记忆合并为“本阶段有效指令”。如果用户提出新要求，例如“不要安装重依赖”“优先复现表 2”“改用本地 PDF”，Agent 需要自动更新记忆，并在审查包里说明本次记忆发生了什么变化。指定 `--run-dir` 时，记忆文件会写入该运行目录下的 `outputs/`。

采用的记忆更新方法是常见的 **增量摘要记忆（Incremental Summary Memory）+ 反思式压缩（Reflection/Summarization）+ 结构化槽位更新（Slot-based Memory Update）**：

- 增量摘要记忆：每轮只把新增用户指令和阶段结果合并进已有摘要，避免把完整对话全部塞回上下文。
- 反思式压缩：阶段结束时提炼“真正影响后续执行的内容”，删除寒暄、重复描述和已经失效的临时信息。
- 结构化槽位更新：把论文输入、用户偏好、已确认决策、风险接受情况、下一步动作等写入固定字段，后续阶段按字段读取。

推荐的更新规则：

1. 新指令优先级高于旧记忆；如果冲突，保留新指令，并在 `memory.md` 中记录被覆盖的旧约束。
2. 只保存会影响后续阶段的内容，不保存无关对话。
3. 对用户偏好使用稳定字段，例如“默认中文输出”“优先轻量实现”“安装重依赖前先确认”。
4. 对阶段结果使用摘要，不保存大段论文原文、完整日志或长代码。
5. 每个阶段审查包必须包含“记忆更新”小节，说明新增、更新或删除了哪些记忆。

记忆更新示例：

```markdown
## 用户偏好

- 默认使用中文报告和中文审查包。
- 第一版优先轻量可运行，不主动安装重依赖。
- 每个阶段结束后停止，等待人工确认。

## 已确认决策

- 采用单总控 Agent + 阶段化工具，不拆真正自治子 Agent。
- 默认 OpenAI 兼容模型接入。
- CLI 作为第一版运行入口。

## 变更历史

- 2026-06-10：用户要求将 `paper-repro-orchestrator` 的 skill 规则汇入 `agent工作流.md`。
- 2026-06-10：用户要求加入记忆功能，自动精炼用户指令和阶段更改。
```

## 状态与标准产物

- `outputs/state.json`：记录论文输入、当前阶段、已完成阶段、阶段产物路径、风险摘要和最近审查包。
- `outputs/memory.md`：记录精炼后的用户偏好、关键决策、变更历史和后续约束。
- `outputs/stage_notes.md`：记录阶段运行笔记、未完成项和下一阶段提示。
- `outputs/literature_sources.md`：文献、代码库、数据集和相关方法来源。
- `outputs/reproduction_spec.md`：论文精读和复现规格。
- `outputs/figures/`：复现图片。
- `outputs/tables/`：复现表格。
- `outputs/report.md`：中文最终报告。

## 运行方式

安装开发版：

```bash
pip install -e .[dev,pdf]
```

使用确定性脚手架模式，不需要模型密钥：

```bash
paper-repro run --paper "Attention Is All You Need" --stage literature --run-dir runs/attention
paper-repro run --stage reading --run-dir runs/attention
paper-repro run --stage baseline --run-dir runs/attention
paper-repro run --stage core --run-dir runs/attention
paper-repro run --stage figures --run-dir runs/attention
paper-repro run --stage validation --run-dir runs/attention
paper-repro state --run-dir runs/attention
```

使用项目内 AKIT PDF 进行脚手架冒烟测试：

```powershell
$env:PYTHONPATH="src"
python -m paper_repro_agent.cli run --paper "tests/2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf" --stage literature --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage reading --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage baseline --run-dir tests/akit_pdf_smoke
python tests/akit_pdf_smoke/reproduction/run_reproduction.py --stage baseline --outputs tests/akit_pdf_smoke/outputs
python -m paper_repro_agent.cli run --stage figures --run-dir tests/akit_pdf_smoke
python -m paper_repro_agent.cli run --stage validation --run-dir tests/akit_pdf_smoke
```

使用 LangChain + OpenAI 兼容模型：

```bash
set PAPER_REPRO_API_KEY=your_api_key
set PAPER_REPRO_MODEL=gpt-4.1-mini
set PAPER_REPRO_BASE_URL=https://api.openai.com/v1
paper-repro run --paper "Attention Is All You Need" --stage literature --run-dir runs/attention --llm
```

## 后续扩展

- 当单阶段提示过长、工具冲突明显或需要并行执行时，再拆分为 LangGraph 子图或具名子 Agent。
- 若需要强制人工中断和恢复，可将当前 CLI 停止机制升级为 LangGraph interrupt/human-in-the-loop。
- 若需要重依赖、长训练或大型数据集下载，必须先输出风险和替代方案，再等待用户确认。
