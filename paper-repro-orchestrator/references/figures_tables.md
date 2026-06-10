# 图表与表格复现模块

## 目标

复现论文图、表、指标和对照结果，输出到 `outputs/figures/` 和 `outputs/tables/`。

## 流程

1. 从 `outputs/reproduction_spec.md` 读取图表清单。
2. 为每张图和每张表定义输出路径、数据来源和复现标准。
3. 使用可重复脚本生成图表，不手工截图拼接。
4. 图表命名遵循论文编号，例如 `fig1_*.png`、`table2_*.csv`。
5. 随机实验注明随机种子；不能完全复刻时解释差异。

## 输出要求

- 图片写入 `outputs/figures/`。
- 表格写入 `outputs/tables/`。
- 表格尽量同时保留复现值和论文值。
- 图像需要非空、坐标/图例/标题语义清楚。

## 脚本

- `scripts/check_outputs.py`：检查图表目录、文件大小、表格行数和必需文件。
