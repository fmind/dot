"""On-demand live seeded-defect and clean-control calibration harness for reviewer supagents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from dot_tasks import ROOT
from fmind_dot.errors import CommandTimeoutError
from fmind_dot.process import CommandResult, Runner, run_parallel, sigterm_as_keyboard_interrupt

SCHEMA_PATH = ROOT / "skills/agent-harnesses/references/headless-review/references/review.schema.json"
COMPILED_AGY_DIR = ROOT / "private_dot_gemini/private_config/agents"
DEFAULT_MODEL = "gemini-4-hydrogen"
DEFAULT_EFFORT = "medium"
EFFORT_SUFFIXES = ("-low", "-medium", "-high", "-xhigh", "-max")
RUBRIC_RULE_RE = re.compile(r"Rubric #\d+", flags=re.IGNORECASE)
_MUTATION_ERROR = "fixture sandbox was mutated during read-only review"

CaseKind = Literal["defect", "clean", "unreadable"]
ProbeExecutor = Callable[[Sequence[str], Path, int], CommandResult]


@dataclass(frozen=True)
class CalibrationCase:
    role: str
    kind: CaseKind
    filename: str
    content: str | None
    expected_rules: tuple[str, ...] = ()
    prompt_note: str = ""


DEFAULT_CASES: tuple[CalibrationCase, ...] = (
    CalibrationCase(
        role="fmind-review-code",
        kind="defect",
        filename="bad_writer.py",
        content=(
            "import time\n\n"
            "def persist_items(path: str, items: list[str]) -> float:\n"
            "    start = time.time()\n"
            "    try:\n"
            '        with open(path, "w", encoding="utf-8") as handle:\n'
            "            for item in items:\n"
            "                handle.write(item)\n"
            "    except Exception:\n"
            "        pass\n"
            "    return time.time() - start\n"
        ),
        expected_rules=("Rubric #1", "Rubric #2"),
    ),
    CalibrationCase(
        role="fmind-review-code",
        kind="clean",
        filename="clean_math.py",
        content=(
            '"""Pure positive-sum helper."""\n\n'
            "from __future__ import annotations\n\n"
            "from collections.abc import Sequence\n\n\n"
            "def sum_positive(values: Sequence[int]) -> int:\n"
            '    """Return the sum of strictly positive integers."""\n'
            "    return sum(value for value in values if value > 0)\n"
        ),
    ),
    CalibrationCase(
        role="fmind-review-code",
        kind="unreadable",
        filename="does_not_exist.py",
        content=None,
    ),
    CalibrationCase(
        role="fmind-review-python",
        kind="defect",
        filename="bad_lib.py",
        content=(
            "import subprocess\n\n"
            "def collect(cmd: str, cache=[]):\n"
            "    res = subprocess.run([cmd], capture_output=True, text=True)\n"
            "    cache.append(res.stdout)\n"
            "    return cache\n"
        ),
        expected_rules=("Rubric #1", "Rubric #3"),
    ),
    CalibrationCase(
        role="fmind-review-python",
        kind="clean",
        filename="pyproject.toml",
        content=(
            "[project]\n"
            'name = "demo-lib"\n'
            'version = "1.0.0"\n'
            'requires-python = ">=3.12"\n'
            'dependencies = ["pyyaml>=6.0"]\n'
        ),
        prompt_note="Classify this as a pure Python library package (not a CLI).",
    ),
    CalibrationCase(
        role="fmind-review-shell",
        kind="defect",
        filename="deploy.sh",
        content='#!/bin/sh\nif [[ "$1" == "prod" ]]; then\n  rm -rf $TARGET_DIR/cache\nfi\n',
        expected_rules=("Rubric #1", "Rubric #2"),
    ),
    CalibrationCase(
        role="fmind-review-shell",
        kind="clean",
        filename="helpers.sh",
        content=('# Sourced POSIX helper library (never sets set -eu).\nquote_join() {\n  printf "%s\\n" "$@"\n}\n'),
        prompt_note="Classify this as a sourced shell library.",
    ),
    CalibrationCase(
        role="fmind-review-security",
        kind="defect",
        filename="runner.py",
        content=(
            "import subprocess\n\n"
            "def run_user_query(user_arg: str) -> str:\n"
            '    return subprocess.check_output(f"echo {user_arg}", shell=True, text=True, timeout=5)\n'
        ),
        expected_rules=("Rubric #1",),
    ),
    CalibrationCase(
        role="fmind-review-security",
        kind="clean",
        filename="safe_exec.py",
        content=(
            "from __future__ import annotations\n\n"
            "import subprocess\n\n\n"
            "def ping_version() -> str:\n"
            '    proc = subprocess.run(["/usr/bin/env", "python3", "--version"], '
            "capture_output=True, text=True, check=True, timeout=5, stdin=subprocess.DEVNULL)\n"
            "    return proc.stdout.strip()\n"
        ),
    ),
    CalibrationCase(
        role="fmind-review-human",
        kind="defect",
        filename="complex_note.md",
        content=(
            "# Executive Summary: Nightly ETL Shift (v2.1 / EU-West / Cron-0730)\n\n"
            "In today's fast-paced landscape, we should leverage a seamless shift (`PR #412` / "
            "`etl_sales_agg_v2` with `timeout=180s`) so bounded contexts and blast-radius bulkheads "
            "decouple SLA variance from BI freshness (`PASS` on `PDF`), subject to flip conditions!\n\n"
            "## Methodology and Assumptions\n\n"
            "Checked logs, patched cron, reran DAG twice.\n"
        ),
        expected_rules=("Rubric #1", "Rubric #3", "Rubric #5"),
        prompt_note="Classify this as an internal colleague note.",
    ),
    CalibrationCase(
        role="fmind-review-human",
        kind="clean",
        filename="clean_note.md",
        content=(
            "# Moving nightly reports to a simpler schedule\n\n"
            "We are moving the daily sales summary from 06:00 to 07:30 UTC starting Monday, December 1. "
            "Nothing changes in how you open or read the dashboard.\n\n"
            "- **Fewer missing rows:** waiting 90 minutes lets partner files finish loading first.\n"
            "- **Same layout:** bookmarks and weekly exports stay unchanged.\n\n"
            "**Next step:** Reply by Friday if your team needs the numbers before 07:30 UTC.\n"
        ),
        prompt_note="Classify this as an internal colleague note with clean static prose-lint output.",
    ),
)


@dataclass(frozen=True)
class ProbeOutcome:
    role: str
    kind: CaseKind
    filename: str
    passed: bool
    verdict: str | None
    finding_count: int
    errors: tuple[str, ...]
    duration_seconds: float | None = None


def _digest_tree(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            digests[rel] = f"symlink:{path.readlink()}"
        elif stat.S_ISDIR(mode):
            digests[rel] = "dir"
        elif stat.S_ISREG(mode):
            digests[rel] = f"file:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        else:
            digests[rel] = f"other:{oct(mode)}"
    return digests


def evaluate_structured_output(
    case: CalibrationCase,
    payload: Mapping[str, Any],
    *,
    mutated: bool,
) -> ProbeOutcome:
    errors: list[str] = []
    if mutated:
        errors.append(_MUTATION_ERROR)
    if payload.get("status") != "SUCCESS":
        errors.append(f"agy status={payload.get('status')!r} (expected 'SUCCESS')")
    if payload.get("finished_reason") is not None:
        errors.append(f"unexpected finished_reason={payload.get('finished_reason')!r}")
    if denied := payload.get("denied_actions"):
        errors.append(f"unexpected denied_actions={denied!r}")
    out = payload.get("structured_output")
    if not isinstance(out, Mapping):
        errors.append("missing structured_output object")
        return ProbeOutcome(case.role, case.kind, case.filename, False, None, 0, tuple(errors))

    verdict = out.get("verdict")
    findings = out.get("findings")
    if not isinstance(verdict, str) or verdict not in {"PASS", "REVISE", "BLOCK"}:
        errors.append(f"invalid verdict={verdict!r}")
    if not isinstance(findings, list):
        errors.append("findings is not a list")
        findings = []

    if case.kind == "defect":
        if verdict not in {"BLOCK", "REVISE"}:
            errors.append(f"seeded defect returned {verdict!r} (expected BLOCK or REVISE)")
        blocking = [f for f in findings if isinstance(f, Mapping) and f.get("severity") in {"P0", "P1"}]
        if not blocking:
            errors.append("seeded defect produced no P0/P1 finding")
        cited_rules = {
            match.group(0).lower()
            for finding in blocking
            for match in RUBRIC_RULE_RE.finditer(str(finding.get("rule", "")))
        }
        if blocking and not cited_rules:
            raw_rules = sorted({str(f.get("rule", "")) for f in blocking})
            errors.append(f"blocking findings lacked Rubric #N citations: {raw_rules}")
        expected_lower = {exp.lower() for exp in case.expected_rules}
        if expected_lower and not (cited_rules & expected_lower):
            errors.append(f"expected one of {case.expected_rules}, got {sorted(cited_rules)}")
    elif case.kind == "clean":
        if verdict != "PASS":
            errors.append(f"clean control returned {verdict!r} (expected PASS)")
        if findings:
            ids = [str(f.get("id", "?")) for f in findings if isinstance(f, Mapping)]
            errors.append(f"clean control invented findings: {ids}")
    elif case.kind == "unreadable" and verdict != "BLOCK":
        errors.append(f"unreadable target failed open with verdict={verdict!r} (expected BLOCK)")

    duration = payload.get("duration_seconds")
    dur_val = float(duration) if isinstance(duration, (int, float)) else None
    return ProbeOutcome(
        role=case.role,
        kind=case.kind,
        filename=case.filename,
        passed=not errors,
        verdict=verdict if isinstance(verdict, str) else None,
        finding_count=len(findings),
        errors=tuple(errors),
        duration_seconds=dur_val,
    )


def _error_outcome(case: CalibrationCase, detail: str, *, mutated: bool) -> ProbeOutcome:
    errors = (_MUTATION_ERROR, detail) if mutated else (detail,)
    return ProbeOutcome(case.role, case.kind, case.filename, False, None, 0, errors)


def run_case(
    case: CalibrationCase,
    *,
    agy_bin: str = "agy",
    model: str = DEFAULT_MODEL,
    effort: str | None = None,
    timeout_seconds: int = 120,
    compiled_dir: Path = COMPILED_AGY_DIR,
    schema_path: Path = SCHEMA_PATH,
    executor: ProbeExecutor | None = None,
    process_runner: Runner | None = None,
) -> ProbeOutcome:
    compiled_agent = compiled_dir / f"{case.role}.md"
    if not compiled_agent.is_file():
        return _error_outcome(case, f"missing compiled agent: {compiled_agent}", mutated=False)

    resolved_effort = effort if effort is not None else (None if model.endswith(EFFORT_SUFFIXES) else DEFAULT_EFFORT)
    active_runner = process_runner or Runner()
    run_cmd = executor or (lambda cmd, cwd, t: active_runner.run(cmd, cwd=cwd, timeout=float(t), check=False))

    with tempfile.TemporaryDirectory(prefix="supagent-cal-", dir="/var/tmp") as raw_dir:
        sandbox = Path(raw_dir).resolve()
        agents_dir = sandbox / ".agents/agents"
        agents_dir.mkdir(parents=True)
        shutil.copy2(compiled_agent, agents_dir / compiled_agent.name)

        target = sandbox / case.filename
        if case.content is not None:
            target.write_text(case.content, encoding="utf-8")

        before = _digest_tree(sandbox)
        prompt = f"Audit {target} read-only strictly against your Audit Rubric and Output Contract."
        if case.prompt_note:
            prompt = f"{prompt} {case.prompt_note}"
        cmd = [
            agy_bin,
            "--agent",
            case.role,
            "--model",
            model,
            *(["--effort", resolved_effort] if resolved_effort is not None else []),
            "--print-timeout",
            f"{timeout_seconds}s",
            "--output-format",
            "json",
            "--sandbox",
            "--disable-slash-commands",
            "--settings",
            '{"allowNonWorkspaceAccess":false}',
            "--json-schema",
            str(schema_path),
            "-p",
            prompt,
        ]
        proc: CommandResult | None = None
        timed_out = False
        try:
            proc = run_cmd(cmd, sandbox, timeout_seconds + 30)
        except CommandTimeoutError:
            timed_out = True
        finally:
            mutated = _digest_tree(sandbox) != before

    if timed_out or proc is None:
        return _error_outcome(case, "agy subprocess timed out", mutated=mutated)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["non-zero exit"]
        return _error_outcome(case, f"agy exit {proc.returncode}: {detail[0]}", mutated=mutated)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        return _error_outcome(case, f"invalid JSON output: {err}", mutated=mutated)
    if not isinstance(payload, Mapping):
        return _error_outcome(case, "JSON output is not an object", mutated=mutated)
    return evaluate_structured_output(case, payload, mutated=mutated)


def select_cases(roles: Sequence[str] | None) -> list[CalibrationCase]:
    if not roles:
        return list(DEFAULT_CASES)
    normalized = {r if r.startswith("fmind-review-") else f"fmind-review-{r}" for r in roles}
    known = {c.role for c in DEFAULT_CASES}
    unknown = sorted(normalized - known)
    if unknown:
        raise ValueError(f"no built-in calibration cases for: {', '.join(unknown)} (known: {', '.join(sorted(known))})")
    return [c for c in DEFAULT_CASES if c.role in normalized]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="calibrate-supagents",
        description="Run live seeded-defect, clean-control, and fail-closed calibration probes against compiled supagents.",
        allow_abbrev=False,
        suggest_on_error=True,
    )
    parser.add_argument(
        "--role",
        action="append",
        dest="roles",
        help="Role name (e.g. code or fmind-review-code); repeatable; defaults to all built-in calibration roles.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model ID for agy probes (default: {DEFAULT_MODEL}; effort-suffixed IDs skip default --effort).",
    )
    parser.add_argument(
        "--effort",
        choices=("low", "medium", "high", "xhigh"),
        default=None,
        help=f"Reasoning effort for agy probes (default: {DEFAULT_EFFORT} unless --model includes an effort suffix).",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Per-probe timeout in seconds (default: 120).")
    parser.add_argument("--workers", type=int, default=4, help="Max concurrent probes (default: 4).")
    parser.add_argument(
        "--list", action="store_true", help="List built-in calibration cases and exit without calling agy."
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON report on stdout.")
    return parser


def main(argv: Sequence[str] | None = None, *, executor: ProbeExecutor | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer")
    if args.workers <= 0:
        parser.error("--workers must be a positive integer")
    try:
        cases = select_cases(args.roles)
    except ValueError as err:
        parser.error(str(err))

    if args.list:
        listing = [{"role": c.role, "kind": c.kind, "filename": c.filename} for c in cases]
        if args.as_json:
            sys.stdout.write(json.dumps({"cases": listing}, indent=2) + "\n")
        else:
            for item in listing:
                sys.stdout.write(f"{item['role']:<26} {item['kind']:<10} {item['filename']}\n")
        return 0

    if executor is None and shutil.which("agy") is None:
        sys.stderr.write("error: `agy` CLI not found on PATH; install Antigravity CLI to run live calibration\n")
        return 1

    process_runner = Runner()
    with sigterm_as_keyboard_interrupt():
        try:
            outcomes = run_parallel(
                process_runner,
                lambda case: run_case(
                    case,
                    model=args.model,
                    effort=args.effort,
                    timeout_seconds=args.timeout,
                    executor=executor,
                    process_runner=process_runner,
                ),
                cases,
                workers=args.workers,
            )
        except KeyboardInterrupt:
            return 130
    passed = all(o.passed for o in outcomes)
    if args.as_json:
        sys.stdout.write(json.dumps({"passed": passed, "outcomes": [asdict(o) for o in outcomes]}, indent=2) + "\n")
    else:
        for o in outcomes:
            status = "PASS" if o.passed else "FAIL"
            dur = f" ({o.duration_seconds:.1f}s)" if o.duration_seconds is not None else ""
            sys.stdout.write(
                f"{status} {o.role:<24} {o.kind:<10} verdict={o.verdict or 'NONE':<6} findings={o.finding_count}{dur}\n"
            )
            for err in o.errors:
                sys.stderr.write(f"  - {o.role}/{o.filename}: {err}\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
