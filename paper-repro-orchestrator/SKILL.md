---
name: paper-repro-orchestrator
description: "中文论文复现总控 skill，是用户唯一需要调用的论文复现入口。Use when the user asks to reproduce an academic paper, implement paper algorithms, reproduce figures/tables, find paper code repositories, generate runnable reproduction code, validate results, or create a Chinese reproduction report with staged human review. Internally handles literature search, paper reading, implementation, figures/tables, validation, and reporting without requiring users to call sub-skills."
---

# 论文复现总控

## 核心原则

- 这是唯一对用户暴露的论文复现 skill；不要要求用户再调用其他 `paper-repro-*` skill。
- 根据任务进度自行读取内部参考模块：`references/literature_search.md`、`references/reading_spec.md`、`references/code_implementation.md`、`references/figures_tables.md`、`references/validation_report.md`。
- 先规划，再执行；先检索和精读论文，再写代码。
- 联网查找论文主页、作者代码库、数据集、第三方复现和相关方法，优先引用官方来源。
- 每个子目标完成后必须停止，交付审查包，等待用户明确说“继续执行”。
- 所有计划、审查说明、报告默认使用中文。
- 需要安装依赖、下载大仓库或引入重框架时，先说明风险和替代方案。

## 启动流程

1. 确认论文输入：本地 PDF、arXiv/DOI/URL、论文标题或附件。
2. 检查工作目录、已有文件、可用 Python/Node/LaTeX/PDF 工具和关键依赖。
3. 读取 `references/literature_search.md`，完成文献、代码库、数据集和相关方法调查。
4. 读取 `references/reading_spec.md`，精读论文并生成 `outputs/reproduction_spec.md`。
5. 产出分阶段复现计划，并等待用户审核。

## 默认阶段

1. 文献与代码源调查。
2. 论文精读与复现规格。
3. 基线方法实现。
4. 核心方法实现。
5. 图表与表格复现。
6. 验证与中文报告。

## 内部模块选择

- 文献检索：读取 `references/literature_search.md`。
- 论文精读规格：读取 `references/reading_spec.md`；需要抽取 PDF 文本时使用 `scripts/extract_pdf_text.py`。
- 代码实现：读取 `references/code_implementation.md`。
- 图表复现：读取 `references/figures_tables.md`；需要检查图表时使用 `scripts/check_outputs.py`。
- 验证报告：读取 `references/validation_report.md`；需要汇总产物时使用 `scripts/summarize_artifacts.py`。
- 模板：需要标准文档结构时读取 `references/templates.md`。

## 人工审核闸门

每个阶段结束时输出：

- 本阶段做了什么。
- 生成或更新了哪些文件。
- 关键结果和命令输出摘要。
- 已知差异、风险和未完成项。
- 下一阶段准备做什么。

输出后停止，不要继续下一阶段，除非用户说“继续执行”。

## 标准产物

- `outputs/literature_sources.md`
- `outputs/reproduction_spec.md`
- `outputs/figures/`
- `outputs/tables/`
- `outputs/report.md`

## 参考文件

- 总控系统提示词：`references/system_prompt.md`
- 阶段产物和审查包规范：`references/stage_contract.md`
- 文献检索模块：`references/literature_search.md`
- 论文精读模块：`references/reading_spec.md`
- 代码实现模块：`references/code_implementation.md`
- 图表复现模块：`references/figures_tables.md`
- 验证报告模块：`references/validation_report.md`
- 模板集合：`references/templates.md`
