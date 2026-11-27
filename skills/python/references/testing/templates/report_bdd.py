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
_BINARY_SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".gz", ".tar", ".mp4", ".webm")
_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("workstation_path", re.compile(r"(?<![A-Za-z0-9._-])/(?:Users|home)/[A-Za-z0-9._-]+")),
    ("diff_hunk", re.compile(r"diff --git\s+[abciow12]/|@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")),
    (
        "secret_token",
        re.compile(
            r"\b(?:gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,}|"
            r"AIza[0-9A-Za-z_-]{20,}|(?:AKIA|ASIA)[0-9A-Z]{16}|"
            r"ya29\.[A-Za-z0-9._-]{12,}|hvs\.[A-Za-z0-9._-]{12,}|"
            r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b|"
            r"(?i:\b(?:Bearer|Basic)\s+[A-Za-z0-9._+/=-]{16,})|"
            r"BEGIN [A-Z ]*PRIVATE KEY"
        ),
    ),
)


_PYTEST_TIMEOUT_SECONDS = 600
_ALLURE_TIMEOUT_SECONDS = 120


def _exit_code(returncode: int) -> int:
    return 128 - returncode if returncode < 0 else returncode


def _run_step(cmd: list[str], *, timeout: int) -> int:
    try:
        completed = subprocess.run(cmd, check=False, stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"ERROR: command timed out after {timeout}s: {cmd[0]}\n")
        return 124
    return completed.returncode


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
    for path in sorted(results_dir.rglob("*")):
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


def _iter_json_strings(value: object) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                strings.append(key)
            strings.extend(_iter_json_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_iter_json_strings(item))
    return strings


def assert_no_leaks(results_dir: Path) -> list[tuple[str, str]]:
    """Fail-closed scan of all non-binary Allure artifacts for residual secrets, paths, or diff hunks."""
    findings: list[tuple[str, str]] = []
    for path in sorted(results_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() in _BINARY_SKIP_SUFFIXES:
            continue
        raw_text = path.read_bytes().decode("utf-8", errors="replace")
        texts: list[str] = [raw_text]
        if path.suffix.lower() == ".json":
            try:
                texts = _iter_json_strings(json.loads(raw_text))
            except json.JSONDecodeError:
                texts = [raw_text]
        rel = path.relative_to(results_dir).as_posix()
        for rule, pattern in _LEAK_PATTERNS:
            if any(pattern.search(chunk) for chunk in texts):
                findings.append((rel, rule))
    return findings


def main(argv: list[str] | None = None) -> int:
    extra_args = sys.argv[1:] if argv is None else argv
    before_sep = extra_args[: extra_args.index("--")] if "--" in extra_args else extra_args
    if "-h" in before_sep or "--help" in before_sep:
        sys.stdout.write(
            "usage: report_bdd.py [PYTEST_ARGS...]\n\n"
            "Run BDD specs, sanitize Allure 3 results, generate HTML, and enforce Quality Gates.\n"
        )
        return 0
    if shutil.which("allure") is None:
        sys.stderr.write("ERROR: 'allure' CLI not found on PATH; install npm:allure via mise and retry.\n")
        return 1

    results_dir = Path(".cache/allure-results")
    report_dir = Path(".cache/allure-report")
    for directory in (results_dir, report_dir):
        if directory.exists():
            shutil.rmtree(directory)
    results_dir.parent.mkdir(parents=True, exist_ok=True)

    pytest_cmd = ["uv", "run", "--locked", "pytest", "-q", "--tb=line", "tests/bdd", f"--alluredir={results_dir}"]
    pytest_rc = _run_step([*pytest_cmd, *extra_args], timeout=_PYTEST_TIMEOUT_SECONDS)
    if pytest_rc not in (0, 1):
        return _exit_code(pytest_rc)

    sanitize_results(results_dir)
    if leaks := assert_no_leaks(results_dir):
        for filename, rule in leaks:
            sys.stderr.write(f"ERROR: redacted {rule} match in {filename}; aborting report generation\n")
        return 1
    qg_rc = _exit_code(_run_step(["allure", "generate", str(results_dir), "--clean"], timeout=_ALLURE_TIMEOUT_SECONDS))
    log_rc = _exit_code(
        _run_step(
            ["allure", "log", str(results_dir), "--group-by", "feature", "--all-quality-gate-results"],
            timeout=_ALLURE_TIMEOUT_SECONDS,
        )
    )
    return qg_rc or log_rc


if __name__ == "__main__":
    raise SystemExit(main())
