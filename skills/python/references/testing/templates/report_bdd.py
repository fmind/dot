# Copy to tests/bdd/report_bdd.py alongside allurerc.yaml and tests/bdd/conftest.py.
"""Run BDD specs, sanitize Allure 3 results, generate HTML, and enforce Quality Gates."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_METADATA_SUFFIXES = ("-result.json", "-container.json")
_TEXT_ATTACHMENT_SUFFIXES = ("-attachment.txt", "-attachment.log")


def _exit_code(returncode: int) -> int:
    return 128 - returncode if returncode < 0 else returncode


def _path_patterns(cwd: Path, home: Path) -> list[tuple[re.Pattern[str], str]]:
    resolved_cwd = cwd.resolve()
    cwd_forms = [cwd, resolved_cwd]
    if (pwd := os.environ.get("PWD")) and Path(pwd).is_absolute():
        pwd_path = Path(pwd)
        if pwd_path.resolve() == resolved_cwd:
            cwd_forms.append(pwd_path)

    candidates: dict[str, tuple[str, str]] = {}
    for path, prefix_repl, bare_repl in (
        *((p, "", ".") for p in cwd_forms),
        (home, "~/", "~"),
        (home.resolve(), "~/", "~"),
    ):
        raw = str(path).rstrip("/")
        if raw:
            candidates.setdefault(raw, (prefix_repl, bare_repl))

    patterns: list[tuple[re.Pattern[str], str]] = []
    for raw, (prefix_repl, bare_repl) in sorted(candidates.items(), key=lambda item: len(item[0]), reverse=True):
        patterns.append((re.compile(re.escape(f"{raw}/")), prefix_repl))
        patterns.append((re.compile(rf"{re.escape(raw)}(?=$|[^A-Za-z0-9._/-])"), bare_repl))
    return patterns


def _scrub_text(text: str, patterns: list[tuple[re.Pattern[str], str]]) -> str:
    for pattern, replacement in patterns:
        text = pattern.sub(replacement, text)
    return text


def _scrub_value(value: object, patterns: list[tuple[re.Pattern[str], str]]) -> object:
    if isinstance(value, dict):
        return {key: _scrub_value(item, patterns) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub_value(item, patterns) for item in value]
    if isinstance(value, str):
        return _scrub_text(value, patterns)
    return value


def sanitize_results(results_dir: Path, *, cwd: Path | None = None, home: Path | None = None) -> None:
    """Strip host labels and local filesystem paths without touching JSON/binary attachments."""
    patterns = _path_patterns(cwd or Path.cwd(), home or Path.home())
    for path in sorted(results_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name.endswith(_METADATA_SUFFIXES):
            data = _scrub_value(json.loads(path.read_text(encoding="utf-8")), patterns)
            if path.name.endswith("-result.json") and isinstance(data, dict) and isinstance(data.get("labels"), list):
                data["labels"] = [
                    label for label in data["labels"] if not (isinstance(label, dict) and label.get("name") == "host")
                ]
            path.write_text(json.dumps(data), encoding="utf-8")
        elif path.name.endswith(_TEXT_ATTACHMENT_SUFFIXES):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            path.write_text(_scrub_text(text, patterns), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    results_dir = Path(".cache/allure-results")
    report_dir = Path(".cache/allure-report")
    for directory in (results_dir, report_dir):
        if directory.exists():
            shutil.rmtree(directory)
    results_dir.parent.mkdir(parents=True, exist_ok=True)

    extra_args = sys.argv[1:] if argv is None else argv
    pytest_cmd = ["uv", "run", "--locked", "pytest", "-q", "--tb=line", "tests/bdd", f"--alluredir={results_dir}"]
    pytest_rc = subprocess.run([*pytest_cmd, *extra_args], check=False).returncode
    if pytest_rc not in (0, 1):
        return _exit_code(pytest_rc)

    sanitize_results(results_dir)
    qg_rc = _exit_code(subprocess.run(["allure", "generate", str(results_dir), "--clean"], check=False).returncode)
    log_rc = _exit_code(
        subprocess.run(
            ["allure", "log", str(results_dir), "--group-by", "feature", "--all-quality-gate-results"],
            check=False,
        ).returncode
    )
    return qg_rc or log_rc


if __name__ == "__main__":
    raise SystemExit(main())
