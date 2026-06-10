from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from .paths import make_run_context
from .stages import run_stage
from .state import STAGES, load_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-repro", description="Run staged paper reproduction workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run exactly one workflow stage and stop for review.")
    run.add_argument("--paper", help="Paper PDF path, URL, DOI, arXiv ID, or title.")
    run.add_argument("--stage", required=True, choices=STAGES, help="Workflow stage to run.")
    run.add_argument(
        "--run-dir",
        default=None,
        help="Directory for this run. It will contain outputs/ and reproduction/. Defaults to repo root.",
    )
    run.add_argument(
        "--llm",
        action="store_true",
        help="Use the LangChain agent path. Without this flag, generate deterministic scaffolding.",
    )

    state = subparsers.add_parser("state", help="Print current workflow state JSON path and content.")
    state.add_argument("--path", default=None, help="Optional state file path.")
    state.add_argument("--run-dir", default=None, help="Read state from a run directory.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        use_llm = bool(args.llm or os.getenv("PAPER_REPRO_USE_LLM") == "1")
        context = make_run_context(args.run_dir)
        state = load_state(context.state_path)
        try:
            review = run_stage(args.stage, state=state, paper=args.paper, use_llm=use_llm, context=context)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        print(review)
        return

    if args.command == "state":
        context = make_run_context(args.run_dir)
        state = load_state(Path(args.path) if args.path else context.state_path)
        print(json.dumps(asdict(state), ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
