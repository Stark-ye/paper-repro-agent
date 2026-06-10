from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]
SKILL_ROOT = REPO_ROOT / "paper-repro-orchestrator"
REFERENCES_DIR = SKILL_ROOT / "references"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
OUTPUTS_DIR = REPO_ROOT / "outputs"
REPRODUCTION_DIR = REPO_ROOT / "reproduction"


@dataclass(frozen=True)
class RunContext:
    root_dir: Path
    outputs_dir: Path
    reproduction_dir: Path
    state_path: Path


def make_run_context(run_dir: str | Path | None = None) -> RunContext:
    if run_dir is None:
        root = REPO_ROOT
    else:
        candidate = Path(run_dir)
        root = candidate if candidate.is_absolute() else REPO_ROOT / candidate
        root = root.resolve()

    outputs_dir = root / "outputs"
    reproduction_dir = root / "reproduction"
    return RunContext(
        root_dir=root,
        outputs_dir=outputs_dir,
        reproduction_dir=reproduction_dir,
        state_path=outputs_dir / "state.json",
    )


def run_context_from_env() -> RunContext:
    return make_run_context(os.getenv("PAPER_REPRO_RUN_DIR"))
