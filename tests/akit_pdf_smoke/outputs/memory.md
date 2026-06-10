# 论文复现 Agent 记忆

## 用户偏好

- 默认使用中文产物、中文审查包和中文报告。
- 第一版优先轻量可运行；需要安装重依赖或长任务前先确认。
- 每个阶段结束后停止，等待人工审核。

## 任务记忆

- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 运行模式：默认脚手架模式；`--llm` 为可选增强路径。

## 已确认决策

- 采用单总控 Agent + 阶段化工具，不拆真正自治子 Agent。
- 支持通过 `--run-dir` 隔离每次运行产物。
## 变更记录：2026-06-10 16:23:15

- 阶段：文献与代码源调查
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature
- 新增/更新产物：tests/akit_pdf_smoke/outputs/literature_sources.md
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 变更记录：2026-06-10 16:23:16

- 阶段：论文精读与复现规格
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature, reading
- 新增/更新产物：tests/akit_pdf_smoke/outputs/reproduction_spec.md, tests/akit_pdf_smoke/outputs/paper_text.txt
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 变更记录：2026-06-10 16:23:16

- 阶段：基线方法实现
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature, reading, baseline
- 新增/更新产物：tests/akit_pdf_smoke/outputs/baseline_review.md, tests/akit_pdf_smoke/reproduction/run_reproduction.py
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 变更记录：2026-06-10 16:23:16

- 阶段：图表与表格复现
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature, reading, baseline, figures
- 新增/更新产物：tests/akit_pdf_smoke/outputs/figures_tables_review.md
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 变更记录：2026-06-10 16:23:16

- 阶段：验证与中文报告
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature, reading, baseline, figures, validation
- 新增/更新产物：tests/akit_pdf_smoke/outputs/report.md, tests/akit_pdf_smoke/outputs/artifacts_summary.md
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。

## 变更记录：2026-06-10 16:23:47

- 阶段：验证与中文报告
- 论文输入：tests\2025 - Nadav Cohen - Adaptive Kalman-Informed Transformer.pdf
- 已完成阶段：literature, reading, baseline, figures, validation
- 新增/更新产物：tests/akit_pdf_smoke/outputs/report.md, tests/akit_pdf_smoke/outputs/artifacts_summary.md
- 记忆方法：增量摘要记忆 + 反思式压缩 + 结构化槽位更新。
