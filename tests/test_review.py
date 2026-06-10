from pathlib import Path

from paper_repro_agent.paths import make_run_context
from paper_repro_agent.review import StageReview, render_review
from paper_repro_agent.review_agent import run_review


def test_render_review_contains_gate() -> None:
    review = StageReview(
        stage="literature",
        completed=["完成调查"],
        generated_files=["outputs/literature_sources.md"],
        key_results=["生成 Markdown"],
        risks=[],
        memory_updates=["创建长期记忆"],
    )
    text = render_review(review)
    assert "阶段审查包" in text
    assert "显式运行下一阶段命令" in text
    assert "记忆更新" in text


def test_review_agent_writes_single_report(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    (context.reproduction_dir / "methods").mkdir(parents=True)
    (context.outputs_dir / "tables").mkdir(parents=True)
    (context.outputs_dir / "figures").mkdir(parents=True)
    (context.reproduction_dir / "main.py").write_text("print('main')\n", encoding="utf-8")
    (context.reproduction_dir / "data.py").write_text("", encoding="utf-8")
    (context.reproduction_dir / "metrics.py").write_text("", encoding="utf-8")
    (context.reproduction_dir / "config.json").write_text("{}\n", encoding="utf-8")
    (context.reproduction_dir / "methods" / "baseline.py").write_text("", encoding="utf-8")
    (context.reproduction_dir / "methods" / "proposed.py").write_text("", encoding="utf-8")
    (context.outputs_dir / "tables" / "results.csv").write_text(
        "method,metric,paper_value,reproduced_value,data_source,status,note\n"
        "baseline,acc,0.9,0.8,local,ok,\n",
        encoding="utf-8",
    )

    report_path = run_review(context)

    assert report_path.endswith("outputs/review.md")
    text = (context.outputs_dir / "review.md").read_text(encoding="utf-8")
    assert "复现审阅报告" in text
    assert "图表数量" in text
