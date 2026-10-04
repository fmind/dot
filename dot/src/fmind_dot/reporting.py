"""Readable text reports and stable machine-readable output."""

import json
import shutil
import textwrap
from pathlib import Path
from typing import IO, Any


def write_report_line(output: IO[str], text: str = "") -> None:
    """Wrap long labels and paths while retaining their complete values."""
    width = max(40, shutil.get_terminal_size(fallback=(88, 24)).columns)
    output.write(textwrap.fill(text, width=width, subsequent_indent="  ") + "\n")


def display_path(value: str) -> str:
    """Abbreviate a path under the home directory with ``~`` for human output."""
    path, home = Path(value), Path.home()
    return str(Path("~") / path.relative_to(home)) if path.is_relative_to(home) else value


def write_json(output: IO[str], document: object) -> None:
    """Emit one indented UTF-8 JSON document so every --json command shares a format."""
    output.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")


def diagnostic_report(scope: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap workstation and agent checks in the shared dot.diagnostics/v1 schema."""
    return {
        "schema": "dot.diagnostics/v1",
        "scope": scope,
        "passed": all(check["status"] != "fail" for check in checks),
        "checks": checks,
    }
