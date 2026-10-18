"""Readable text reports and stable machine-readable output."""

import json
import shutil
import textwrap
from pathlib import Path
from typing import IO, Any


def write_report_line(output: IO[str], text: str = "") -> None:
    """Wrap long labels and paths while retaining their complete values."""
    width = max(40, shutil.get_terminal_size(fallback=(88, 24)).columns)
    # Never split a path or identifier: a hyphen break would print a value no one can copy back.
    filled = textwrap.fill(text, width=width, subsequent_indent="  ", break_long_words=False, break_on_hyphens=False)
    output.write(filled + "\n")


def display_path(value: str) -> str:
    """Abbreviate a path under the home directory with ``~`` for human output."""
    path, home = Path(value), Path.home()
    return str(Path("~") / path.relative_to(home)) if path.is_relative_to(home) else value


def write_json(output: IO[str], document: object) -> None:
    """Emit one UTF-8 JSON document so every --json command shares a format.

    Terminals get indentation for reading; pipes and agents get compact separators, which cut
    a third of the bytes (and tokens) without changing the document.
    """
    compact = not (hasattr(output, "isatty") and output.isatty())
    separators = (",", ":") if compact else None
    output.write(json.dumps(document, indent=None if compact else 2, separators=separators, ensure_ascii=False) + "\n")


def diagnostic_report(scope: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap workstation and agent checks in the shared dot.diagnostics/v1 schema."""
    return {
        "schema": "dot.diagnostics/v1",
        "scope": scope,
        "passed": all(check["status"] != "fail" for check in checks),
        "checks": checks,
    }
