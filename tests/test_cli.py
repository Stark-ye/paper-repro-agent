from paper_repro_agent.cli import build_parser


def test_cli_parses_run_stage() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--paper", "demo.pdf", "--stage", "literature", "--run-dir", "tests/smoke"])
    assert args.command == "run"
    assert args.paper == "demo.pdf"
    assert args.stage == "literature"
    assert args.run_dir == "tests/smoke"
