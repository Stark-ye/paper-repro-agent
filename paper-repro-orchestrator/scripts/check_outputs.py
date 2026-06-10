#!/usr/bin/env python
"""Check figure and table artifacts for a paper reproduction project."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check reproduction outputs.")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--min-figure-bytes", type=int, default=1000)
    args = parser.parse_args()

    figures = args.outputs / "figures"
    tables = args.outputs / "tables"
    problems: list[str] = []

    if not figures.exists():
        problems.append(f"Missing figure directory: {figures}")
    else:
        for path in figures.glob("*"):
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".pdf"}:
                if path.stat().st_size < args.min_figure_bytes:
                    problems.append(f"Figure looks too small: {path}")

    if not tables.exists():
        problems.append(f"Missing table directory: {tables}")
    else:
        for path in tables.glob("*.csv"):
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.reader(handle))
            if len(rows) < 2:
                problems.append(f"CSV has fewer than 2 rows: {path}")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        raise SystemExit(1)

    print("Output check passed.")


if __name__ == "__main__":
    main()
