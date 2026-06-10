---
name: paper-repro-orchestrator
description: "中文论文复现总控 skill。Use when the user asks to reproduce an academic paper, implement paper algorithms, reproduce figures/tables, find paper code or data sources, validate results, or generate a Chinese reproduction report."
---

# 论文复现总控

## 核心原则

- 这是论文复现任务的唯一对外入口，不要求用户手动调用子 skill。
- 默认使用 LangChain Agent 读取阶段参考、调用工具并生成产物。
- 每个阶段结束后停止，交付阶段审查包，等待人工确认后再进入下一阶段。
- 所有计划、阶段产物、审查说明和最终报告默认使用中文。
- 不伪造论文结果；没有真实运行数据时必须明确标注 `todo`、`not_run` 或等价风险。
- 安装重依赖、下载大数据、使用第三方代码或长时间训练前，必须说明来源、license 和替代方案。

## 标准流程

1. 文献与代码源调查：确认论文身份、官方主页、代码仓库、数据集和许可风险。
2. 论文精读与复现规格：提取方法、公式、数据、指标、图表目标和真实性约束。
3. 基线方法实现：生成或补齐基线方法文件与整体比较主程序。
4. 核心方法实现：实现论文核心方法，保持方法文件独立。
5. 图表与表格整理：只复现支撑主要结论的必要图表。
6. 验证与中文报告：生成结果对比报告和程序功能说明。
7. 审阅 Agent：生成单文件审阅报告，检查代码结构、图表数量和数据真实性。

## 标准产物

- `outputs/literature_sources.md`
- `outputs/reproduction_spec.md`
- `outputs/tables/results.csv`
- `outputs/figures/`
- `outputs/report.md`
- `outputs/programs.md`
- `outputs/review.md`
- `reproduction/main.py`
- `reproduction/methods/*.py`
- `reproduction/data.py`
- `reproduction/metrics.py`
- `reproduction/config.json`

## 阶段参考

- `references/system_prompt.md`
- `references/stage_contract.md`
- `references/literature_search.md`
- `references/reading_spec.md`
- `references/code_implementation.md`
- `references/figures_tables.md`
- `references/validation_report.md`
- `references/templates.md`
