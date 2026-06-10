from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check figure and table outputs.")
    parser.add_argument("--outputs", type=Path, required=True)
    args = parser.parse_args()

    figures = [p for p in (args.outputs / "figures").glob("*") if p.is_file()] if (args.outputs / "figures").exists() else []
    tables = [p for p in (args.outputs / "tables").glob("*") if p.is_file()] if (args.outputs / "tables").exists() else []
    empty = [p for p in figures + tables if p.stat().st_size == 0]
    print(f"Figures: {len(figures)}")
    print(f"Tables: {len(tables)}")
    print(f"Empty files: {len(empty)}")
    for path in empty:
        print(f"EMPTY: {path}")
    if empty:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
