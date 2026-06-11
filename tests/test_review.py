from pathlib import Path

from paper_repro_agent.paths import make_run_context
from paper_repro_agent.review import StageReview, render_review
from paper_repro_agent.review_agent import run_review
from paper_repro_agent.state import WorkflowState, save_state


def test_render_review_contains_gate() -> None:
    review = StageReview(
        stage="literature",
        completed=["完成调查"],
        generated_files=["outputs/literature_sources.md"],
        key_results=["生成 Markdown"],
        risks=[],
        memory_updates=["创建长期记忆"],
        workflow_state=WorkflowState(completed_stages=["literature"]),
    )
    text = render_review(review)
    assert "阶段审查包" in text
    assert "显式运行下一阶段命令" in text
    assert "记忆更新" in text
    assert "论文精读与复现规格" in text


def test_review_agent_writes_single_report_and_rejects_todo_results(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    (context.reproduction_dir / "methods").mkdir(parents=True)
    (context.outputs_dir / "tables").mkdir(parents=True)
    (context.outputs_dir / "figures").mkdir(parents=True)
    (context.outputs_dir / "reproduction_spec.md").write_text("# spec\n", encoding="utf-8")
    (context.outputs_dir / "report.md").write_text("# report\n", encoding="utf-8")
    (context.reproduction_dir / "main.py").write_text("print('main')\n", encoding="utf-8")
    (context.reproduction_dir / "data.py").write_text("# data\n", encoding="utf-8")
    (context.reproduction_dir / "metrics.py").write_text("# metrics\n", encoding="utf-8")
    (context.reproduction_dir / "config.json").write_text("{}\n", encoding="utf-8")
    (context.reproduction_dir / "methods" / "baseline.py").write_text("# baseline\n", encoding="utf-8")
    (context.reproduction_dir / "methods" / "proposed.py").write_text("# proposed\n", encoding="utf-8")
    (context.outputs_dir / "tables" / "results.csv").write_text(
        "method,metric,paper_value,reproduced_value,data_source,status,note\n"
        "baseline,not_run,,,none,todo,\n",
        encoding="utf-8",
    )
    save_state(
        WorkflowState(completed_stages=["literature", "reading", "baseline", "core", "figures", "validation"]),
        context.state_path,
    )

    report_path = run_review(context)

    assert report_path.endswith("outputs/review.md")
    text = (context.outputs_dir / "review.md").read_text(encoding="utf-8")
    assert "复现审阅报告" in text
    assert "图表数量" in text
    assert "结论：**不通过**" in text
    assert "结果表仍包含未运行" in text


def test_review_agent_can_pass_real_looking_results(tmp_path: Path) -> None:
    context = make_run_context(tmp_path)
    (context.reproduction_dir / "methods").mkdir(parents=True)
    (context.outputs_dir / "tables").mkdir(parents=True)
    (context.outputs_dir / "figures").mkdir(parents=True)
    (context.outputs_dir / "reproduction_spec.md").write_text("# spec\n", encoding="utf-8")
    (context.outputs_dir / "report.md").write_text("# report\n", encoding="utf-8")
    (context.outputs_dir / "figures" / "figure1.png").write_bytes(b"png")
    (context.reproduction_dir / "main.py").write_text("print('main')\n", encoding="utf-8")
    (context.reproduction_dir / "data.py").write_text("# data\n", encoding="utf-8")
    (context.reproduction_dir / "metrics.py").write_text("# metrics\n", encoding="utf-8")
    (context.reproduction_dir / "config.json").write_text("{}\n", encoding="utf-8")
    (context.reproduction_dir / "methods" / "baseline.py").write_text("# baseline\n", encoding="utf-8")
    (context.reproduction_dir / "methods" / "proposed.py").write_text("# proposed\n", encoding="utf-8")
    (context.outputs_dir / "tables" / "results.csv").write_text(
        "method,metric,paper_value,reproduced_value,data_source,status,note\n"
        "baseline,acc,0.9,0.8,local,ok,real run\n",
        encoding="utf-8",
    )
    save_state(
        WorkflowState(completed_stages=["literature", "reading", "baseline", "core", "figures", "validation"]),
        context.state_path,
    )

    run_review(context)

    text = (context.outputs_dir / "review.md").read_text(encoding="utf-8")
    assert "结论：**通过**" in text
