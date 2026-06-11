from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .paths import REPO_ROOT, SCRIPTS_DIR, run_context_from_env
from .references import load_reference


def _safe_workspace_path(path: str, allowed_roots: tuple[str, ...] = ("outputs", "reproduction")) -> Path:
    context = run_context_from_env()
    raw = Path(path)
    candidate = raw.resolve() if raw.is_absolute() else (context.root_dir / raw).resolve()
    root = context.root_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path escapes run directory: {path}")
    rel = candidate.relative_to(root)
    if not rel.parts or rel.parts[0] not in allowed_roots:
        allowed = ", ".join(allowed_roots)
        raise ValueError(f"Writable paths must be under: {allowed}")
    return candidate


def load_reference_tool(filename: str) -> str:
    """Load a paper reproduction reference markdown file by filename."""
    return load_reference(filename)


def read_workspace_file(path: str) -> str:
    """Read a UTF-8 file from the current run directory."""
    context = run_context_from_env()
    raw = Path(path)
    candidate = raw.resolve() if raw.is_absolute() else (context.root_dir / raw).resolve()
    root = context.root_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"Path escapes run directory: {path}")
    return candidate.read_text(encoding="utf-8")


def write_workspace_file(path: str, content: str) -> str:
    """Write a UTF-8 file under outputs/ or reproduction/ in the current run directory."""
    candidate = _safe_workspace_path(path)
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(content, encoding="utf-8")
    return f"Wrote {_display_path(candidate)}"


def extract_pdf_text(pdf_path: str, out_path: str = "outputs/paper_text.txt") -> str:
    """Extract PDF text with the bundled extraction script."""
    script = SCRIPTS_DIR / "extract_pdf_text.py"
    context = run_context_from_env()
    output = _safe_workspace_path(out_path, allowed_roots=("outputs",))
    raw_pdf = Path(pdf_path)
    if raw_pdf.is_absolute():
        source = raw_pdf.resolve()
    else:
        candidates = [(REPO_ROOT / raw_pdf).resolve(), (context.root_dir / raw_pdf).resolve()]
        source = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    if script.exists():
        cmd = [sys.executable, str(script), str(source), "--out", str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return f"Extracted PDF text to {_display_path(output)}"
    _extract_pdf_text_fallback(source, output)
    return f"Extracted PDF text to {_display_path(output)}"


def check_outputs(outputs: str = "outputs") -> str:
    """Check figure and table outputs with the bundled output checker."""
    script = SCRIPTS_DIR / "check_outputs.py"
    context = run_context_from_env()
    raw_outputs = Path(outputs)
    outputs_path = raw_outputs.resolve() if raw_outputs.is_absolute() else (context.root_dir / raw_outputs).resolve()
    if not script.exists():
        return _check_outputs_fallback(outputs_path)
    cmd = [sys.executable, str(script), "--outputs", str(outputs_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(text)
    return text


def summarize_artifacts(out_path: str = "outputs/artifacts_summary.md") -> str:
    """Summarize generated reproduction artifacts as Markdown."""
    script = SCRIPTS_DIR / "summarize_artifacts.py"
    context = run_context_from_env()
    output = _safe_workspace_path(out_path, allowed_roots=("outputs",))
    if not script.exists():
        _summarize_artifacts_fallback(context.outputs_dir, output)
        return f"Wrote {_display_path(output)}"
    cmd = [
        sys.executable,
        str(script),
        "--outputs",
        str(context.outputs_dir),
        "--out",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stdout + "\n" + result.stderr).strip())
    return f"Wrote {_display_path(output)}"


def search_arxiv(query: str, max_results: int = 5) -> str:
    """Search arXiv for paper metadata and return compact JSON."""
    encoded = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max(1, min(max_results, 10)),
        }
    )
    url = f"https://export.arxiv.org/api/query?{encoded}"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            raw = response.read()
    except Exception as exc:
        return json.dumps(
            [{"source": "arXiv", "query": query, "status": "error", "error": str(exc)}],
            ensure_ascii=False,
            indent=2,
        )
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        results.append(
            {
                "title": (entry.findtext("atom:title", default="", namespaces=ns) or "").strip(),
                "id": (entry.findtext("atom:id", default="", namespaces=ns) or "").strip(),
                "published": (entry.findtext("atom:published", default="", namespaces=ns) or "").strip(),
                "summary": (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()[:500],
            }
        )
    return json.dumps(results, ensure_ascii=False, indent=2)


def search_semantic_scholar(query: str, limit: int = 5) -> str:
    """Search Semantic Scholar for paper metadata and return compact JSON."""
    params = urllib.parse.urlencode(
        {
            "query": query,
            "limit": max(1, min(limit, 10)),
            "fields": "title,year,authors,url,venue,externalIds",
        }
    )
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "paper-repro-agent/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        return json.dumps(
            {"source": "Semantic Scholar", "query": query, "status": "error", "error": str(exc)},
            ensure_ascii=False,
            indent=2,
        )
    return raw


def get_tools() -> list[object]:
    try:
        from langchain.tools import tool
    except Exception as exc:  # pragma: no cover - exercised only without dependencies.
        raise RuntimeError("LangChain is required to build agent tools. Install project dependencies first.") from exc

    functions = [
        load_reference_tool,
        read_workspace_file,
        write_workspace_file,
        extract_pdf_text,
        check_outputs,
        summarize_artifacts,
        search_arxiv,
        search_semantic_scholar,
    ]
    return [tool(func) for func in functions]


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_pdf_text_fallback(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"PDF file not found: {source}")
    try:
        from pypdf import PdfReader
    except Exception:
        output.write_text(
            "PDF text extraction is unavailable because `pypdf` is not installed. "
            "Install with `pip install -e .[pdf]` and rerun the reading stage.\n",
            encoding="utf-8",
        )
        return

    reader = PdfReader(str(source))
    chunks = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        chunks.append(f"\n\n# Page {index}\n\n{text}")
    output.write_text("".join(chunks).strip() + "\n", encoding="utf-8")


def _check_outputs_fallback(outputs_path: Path) -> str:
    figures = sorted((outputs_path / "figures").glob("*")) if (outputs_path / "figures").exists() else []
    tables = sorted((outputs_path / "tables").glob("*")) if (outputs_path / "tables").exists() else []
    figure_files = [path for path in figures if path.is_file()]
    table_files = [path for path in tables if path.is_file()]
    empty = [path for path in figure_files + table_files if path.stat().st_size == 0]
    lines = [
        f"Figures: {len(figure_files)}",
        f"Tables: {len(table_files)}",
        f"Empty files: {len(empty)}",
    ]
    if empty:
        lines.append("Empty file paths: " + ", ".join(_display_path(path) for path in empty))
    return "\n".join(lines)


def _summarize_artifacts_fallback(outputs_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in outputs_dir.rglob("*") if path.is_file() and path.resolve() != output.resolve())
    lines = ["# 产物清单", ""]
    if not files:
        lines.append("- 暂无产物。")
    else:
        for path in files:
            rel = path.resolve().relative_to(outputs_dir.resolve()).as_posix()
            lines.append(f"- `{rel}` ({path.stat().st_size} bytes)")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
