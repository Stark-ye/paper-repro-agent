from paper_repro_agent.review import StageReview, render_review


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
    assert "等待人工审核" in text or "确认无误" in text
    assert "记忆更新" in text
