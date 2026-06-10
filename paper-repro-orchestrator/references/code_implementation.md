# 代码实现 Skill

目标：生成和维护通用复现程序。

## 目录约定

- `reproduction/main.py`：整体比较主程序。
- `reproduction/methods/baseline.py`：基线方法。
- `reproduction/methods/proposed.py`：论文核心方法。
- `reproduction/data.py`：数据加载。
- `reproduction/metrics.py`：指标整理。
- `reproduction/config.json`：数据、方法、指标和随机种子配置。

## 必做

- 每个方法保持独立 `run(dataset)` 入口。
- 主程序统一调用所有方法并写出 `outputs/tables/results.csv`。
- 程序说明写入 `outputs/programs.md`。
- 未实现真实算法时保留 `todo` 或 `not_run`，不得伪造结果。
