from __future__ import annotations

import argparse
from pathlib import Path


def extract_pdf_text(pdf: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("pypdf is required. Install with `pip install -e .[pdf]`.") from exc

    reader = PdfReader(str(pdf))
    chunks = []
    for index, page in enumerate(reader.pages, start=1):
        chunks.append(f"\n\n# Page {index}\n\n{page.extract_text() or ''}")
    return "".join(chunks).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text from a PDF.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(extract_pdf_text(args.pdf), encoding="utf-8")


if __name__ == "__main__":
    main()
