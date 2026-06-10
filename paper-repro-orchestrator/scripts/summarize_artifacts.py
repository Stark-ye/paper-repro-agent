#!/usr/bin/env python
"""Summarize paper reproduction artifacts as Markdown."""

from __future__ import annotations

import argparse
from pathlib import Path


def list_files(root: Path, pattern: str) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.glob(pattern) if path.is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize outputs.")
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    lines = ["# 复现产物清单", ""]
    for title, subdir, pattern in [
        ("图片", "figures", "*"),
        ("表格", "tables", "*.csv"),
    ]:
        lines.extend([f"## {title}", ""])
        files = list_files(args.outputs / subdir, pattern)
        if not files:
            lines.append("- 未找到")
        else:
            for path in files:
                size = path.stat().st_size
                lines.append(f"- `{path.as_posix()}` ({size} bytes)")
        lines.append("")

    text = "\n".join(lines)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
