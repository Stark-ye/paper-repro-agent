#!/usr/bin/env python
"""Extract text from a PDF for paper reproduction workflows."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_pdftotext(pdf: Path) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    result = subprocess.run(
        [exe, "-layout", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def run_python_extractors(pdf: Path) -> str:
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(str(pdf))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        pass

    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(str(pdf))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise RuntimeError(
            "No usable PDF extractor found. Install pypdf/PyPDF2 or make pdftotext available."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF text.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    text = run_pdftotext(args.pdf) or run_python_extractors(args.pdf)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
