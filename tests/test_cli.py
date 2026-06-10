from paper_repro_agent.cli import build_parser


def test_cli_parses_run_stage() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--paper", "demo.pdf", "--stage", "literature", "--run-dir", "tests/smoke"])
    assert args.command == "run"
    assert args.paper == "demo.pdf"
    assert args.stage == "literature"
    assert args.run_dir == "tests/smoke"
    assert args.scaffold is False


def test_cli_parses_scaffold_mode() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--stage", "literature", "--run-dir", "runs/demo", "--scaffold"])
    assert args.command == "run"
    assert args.scaffold is True


def test_cli_parses_review() -> None:
    parser = build_parser()
    args = parser.parse_args(["review", "--run-dir", "runs/demo"])
    assert args.command == "review"
    assert args.run_dir == "runs/demo"


def test_cli_has_no_akit_command() -> None:
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "akit" not in choices
