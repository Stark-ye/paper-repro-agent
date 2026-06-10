from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize output artifacts as Markdown.")
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(path for path in args.outputs.rglob("*") if path.is_file() and path.resolve() != args.out.resolve())
    lines = ["# 产物清单", ""]
    if not files:
        lines.append("- 暂无产物。")
    for path in files:
        rel = path.resolve().relative_to(args.outputs.resolve()).as_posix()
        lines.append(f"- `{rel}` ({path.stat().st_size} bytes)")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
