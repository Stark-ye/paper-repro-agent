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


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


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
        "--scaffold",
        action="store_true",
        help="Use deterministic scaffolding instead of the default LangChain agent path.",
    )
    run.add_argument(
        "--llm",
        action="store_true",
        help="Deprecated compatibility flag. LangChain is now the default unless --scaffold is set.",
    )

    state = subparsers.add_parser("state", help="Print current workflow state JSON path and content.")
    state.add_argument("--path", default=None, help="Optional state file path.")
    state.add_argument("--run-dir", default=None, help="Read state from a run directory.")

    review = subparsers.add_parser("review", help="Generate a concise reproduction review report.")
    review.add_argument("--run-dir", default=None, help="Run directory to review. Defaults to repo root.")

    subparsers.add_parser("doctor", help="Diagnose local install, model env, and LangChain imports.")

    return parser


def main(argv: list[str] | None = None) -> None:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        env_value = os.getenv("PAPER_REPRO_USE_LLM")
        if args.scaffold:
            use_llm = False
        elif args.llm:
            use_llm = True
        elif env_value is not None:
            use_llm = env_value not in {"0", "false", "False", "no", "NO"}
        else:
            use_llm = True
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

    if args.command == "review":
        from .review_agent import run_review

        context = make_run_context(args.run_dir)
        try:
            result = run_review(context)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        print(result)
        return

    if args.command == "doctor":
        from .doctor import run_doctor

        _safe_print(run_doctor())
        return

    parser.print_help()


def _safe_print(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    sys.stdout.write(safe_text)
    if not safe_text.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
