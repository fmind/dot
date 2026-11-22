"""Workstation diagnostics and installation freshness."""

import argparse
import os
import shutil
import stat
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from fmind_dot import __version__
from fmind_dot.auth_probes import (
    GCLOUD_CLI_TOKEN,
    PROBE_TIMEOUT_SECONDS,
    adc_ready,
    gcloud_ready,
    github_plaintext_headless_ok,
    github_ready,
    github_status,
    github_token_plaintext,
    workspace_ready,
)
from fmind_dot.command import Parser, add_json, add_quiet
from fmind_dot.config import expand_path, policy
from fmind_dot.errors import CommandTimeoutError, DotError, UsageError
from fmind_dot.process import CommandResult, run_parallel
from fmind_dot.reporting import diagnostic_report, write_json
from fmind_dot.state import State

_GIB = 1024**3
_DISK_FAIL_GIB, _DISK_WARN_GIB, _MEMORY_FAIL_GIB = 10, 20, 1
_PROBE_CONCURRENCY = 8
_SIGNING_PRIVATE_KEY, _SIGNING_PUBLIC_KEY = "~/.ssh/id_ed25519_signing", "~/.ssh/id_ed25519_signing.pub"
DOCTOR_SECRETS = ("~/.config/chezmoi/key.txt", _SIGNING_PRIVATE_KEY)
_SHARED_PERSONA, _SHARED_SKILLS = "~/.agents/AGENTS.md", "~/.agents/skills"
_AGENT_HOSTS: dict[str, tuple[str, str]] = {
    "agy": ("~/.gemini/GEMINI.md", "~/.gemini/config/skills"),
    "copilot": ("~/.copilot/copilot-instructions.md", ""),
}
_AGENT_REVIEWERS: dict[str, tuple[str, str]] = {
    "agy": ("~/.gemini/config/agents", "fmind-review-*.md"),
    "copilot": ("~/.copilot/agents", "fmind-review-*.agent.md"),
}

_DOCTOR_GROUPS = (
    ("auth", "CLI Authentication"),
    ("secrets", "Secrets & Encryption"),
    ("docker", "System Services"),
    ("resources", "System Resources"),
    ("tools", "CLI Tools"),
    ("install", "Install Freshness"),
    ("agents", "Agent Harnesses"),
)
DOCTOR_TOOLS: tuple[str, ...] = tuple(policy()["doctor_tools"])
PACKAGE_DIRECTORY = Path(__file__).resolve().parent


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    details: str
    path: str = ""
    condition: str = ""
    group: str = ""

    def payload(self) -> dict[str, str]:
        fields = {"condition": self.condition, "path": self.path, "details": self.details, "group": self.group}
        return {"name": self.name, "status": self.status} | {k: v for k, v in fields.items() if v}


def _inspect_secret(label: str, *, fix: bool) -> CheckResult:
    try:
        info = (path := expand_path(label)).lstat()
    except FileNotFoundError:
        return CheckResult(label, "warn", "MISSING")
    except OSError:
        return CheckResult(label, "fail", "unable to inspect file")
    if not stat.S_ISREG(info.st_mode):
        return CheckResult(label, "fail", "not a regular file")
    if info.st_uid != os.getuid():
        return CheckResult(label, "fail", "not owned by current user")
    if (current := stat.S_IMODE(info.st_mode)) & ~0o600 == 0:
        return CheckResult(label, "pass", f"secure (permissions: {current:04o})")
    if not fix:
        return CheckResult(label, "fail", f"INSECURE permissions: {current:04o} (expected 0600)")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        return CheckResult(label, "pass", "repaired (permissions: 0600)")
    except OSError:
        return CheckResult(label, "fail", f"INSECURE permissions: {current:04o} (repair failed; expected 0600)")


def _secret_results(*, fix: bool) -> list[CheckResult]:
    results = [_inspect_secret(secret, fix=fix) for secret in DOCTOR_SECRETS]
    if expand_path(_SIGNING_PRIVATE_KEY).is_file() and not expand_path(_SIGNING_PUBLIC_KEY).is_file():
        results.append(CheckResult(_SIGNING_PUBLIC_KEY, "warn", "MISSING"))
    if os.path.lexists(expand_path("~/.private.fish")):
        results.append(_inspect_secret("~/.private.fish", fix=fix))
    return results


def _probe(state: State, args: Sequence[str]) -> CommandResult | str:
    try:
        return state.runner.run(list(args), timeout=PROBE_TIMEOUT_SECONDS, check=False)
    except CommandTimeoutError:
        return "timed out"
    except DotError, OSError:
        return "failed"


def _tool_results(state: State) -> list[CheckResult]:
    def check(tool: str) -> CheckResult:
        if (path := state.runner.which(tool)) is None:
            return CheckResult(tool, "fail", "command not found", condition="missing")
        if isinstance(res := _probe(state, [str(path), "--version"]), str):
            return CheckResult(tool, "fail", f"capability probe {res}", str(path), "broken")
        ok = res.returncode == 0
        status, cond, word = ("pass", "healthy", "passed") if ok else ("fail", "broken", "failed")
        return CheckResult(tool, status, f"capability probe {word}", str(path), cond)

    return run_parallel(state.runner, check, DOCTOR_TOOLS, _PROBE_CONCURRENCY)


def _auth_results(state: State) -> list[CheckResult]:
    def github() -> CheckResult | bool:
        entry = github_status(state)
        if not github_ready(entry, reconcile=False):
            return False
        if not github_token_plaintext(entry):
            return True
        if github_plaintext_headless_ok(entry):
            return CheckResult("gh", "pass", "authenticated (headless 0600 hosts.yml)", condition="healthy")
        msg = "authenticated; token in plaintext hosts.yml: unlock the system keyring, then run gh auth logout and dot login github"
        return CheckResult("gh", "warn", msg, condition="insecure")

    configured = set(state.config.auth.login)
    checks: dict[str, tuple[str, bool, Callable[[], CheckResult | bool]]] = {
        "gh": ("gh", "github" in configured, github),
        "gcloud": ("gcloud", "gcp" in configured, lambda: gcloud_ready(state, GCLOUD_CLI_TOKEN)),
        "gcloud-adc": ("gcloud", "gcp" in configured, lambda: adc_ready(state)),
        "gws": ("gws", "workspace" in configured, lambda: workspace_ready(state)),
    }

    def run(item: tuple[str, tuple[str, bool, Callable[[], CheckResult | bool]]]) -> CheckResult:
        label, (tool, enabled, check) = item
        if not enabled:
            return CheckResult(label, "skip", "not configured in auth.login", condition="skipped")
        if (path := state.runner.which(tool)) is None:
            return CheckResult(label, "skip", f"{tool} not installed", condition="skipped")
        try:
            ready = check()
        except CommandTimeoutError:
            return CheckResult(label, "fail", "auth check timed out; state unknown", str(path), "broken")
        except DotError, OSError:
            return CheckResult(label, "fail", "auth check failed; state unknown", str(path), "broken")
        if isinstance(ready, CheckResult):
            return replace(ready, path=str(path))
        st, msg, cond = (
            ("pass", "authenticated", "healthy") if ready else ("fail", "NOT authenticated", "unauthenticated")
        )
        return CheckResult(label, st, msg, str(path), cond)

    return run_parallel(state.runner, run, list(checks.items()), _PROBE_CONCURRENCY)


def _docker_results(state: State) -> list[CheckResult]:
    if (path := state.runner.which("docker")) is None:
        return [CheckResult("docker", "skip", "not installed (optional)", condition="skipped")]
    if isinstance(res := _probe(state, ["docker", "info"]), str):
        return [CheckResult("docker", "fail", f"service probe {res}", str(path), "broken")]
    st, msg, cond = ("pass", "running", "healthy") if res.returncode == 0 else ("warn", "not running", "stopped")
    return [CheckResult("docker", st, msg, str(path), cond)]


def _install_results(state: State) -> list[CheckResult]:
    if state.runner.which("chezmoi") is None:
        return [CheckResult("dot", "skip", "chezmoi not installed", condition="skipped")]
    src_res = _probe(state, ["chezmoi", "source-path"])
    source_text = "" if isinstance(src_res, str) or src_res.returncode else src_res.stdout.strip()
    if not source_text or len(source_text.splitlines()) != 1:
        return [CheckResult("dot", "warn", "could not resolve chezmoi source", condition="unknown")]
    source, installed = Path(source_text), str(PACKAGE_DIRECTORY)
    if not (source / "dot/src/fmind_dot").is_dir() or not (source / "dot/pyproject.toml").is_file():
        return [CheckResult("dot", "skip", "chezmoi source is not a Python dot checkout", condition="skipped")]
    if PACKAGE_DIRECTORY.parent.name == "src" and (PACKAGE_DIRECTORY.parents[1] / "pyproject.toml").is_file():
        msg = "running from a source checkout; check the deployed dot instead"
        return [CheckResult("dot", "skip", msg, installed, "skipped")]
    try:
        data = tomllib.loads((source / "dot/pyproject.toml").read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version")
    except OSError, tomllib.TOMLDecodeError:
        return [CheckResult("dot", "fail", "could not verify installed Python package", condition="broken")]
    if version != __version__:
        return [CheckResult("dot", "fail", "STALE: installed version differs from source", installed, "stale")]
    return [CheckResult("dot", "pass", "installed Python package matches source", installed, "healthy")]


def _same_file(path: Path, target: Path) -> bool:
    try:
        return path.samefile(target)
    except OSError:
        return False


def _inspect_agent(name: str) -> CheckResult:
    persona_path, skills_path = _AGENT_HOSTS[name]
    shared = expand_path(_SHARED_SKILLS)
    checks: list[tuple[str, bool]] = [
        ("persona", _same_file(expand_path(persona_path), expand_path(_SHARED_PERSONA))),
        ("skills", _same_file(expand_path(skills_path or _SHARED_SKILLS), shared) and any(shared.glob("*/SKILL.md"))),
    ]
    if reviewer_spec := _AGENT_REVIEWERS.get(name):
        rev_dir = expand_path(reviewer_spec[0])
        checks.append(("reviewers", rev_dir.is_dir() and any(rev_dir.glob(reviewer_spec[1]))))
    if problems := [lbl for lbl, ok in checks if not ok]:
        msg = f"discovery broken ({','.join(problems)}); run chezmoi apply --force"
        return CheckResult(name, "fail", msg, condition="broken")
    return CheckResult(name, "pass", "persona, skills, and reviewers configured", condition="healthy")


def available_memory_bytes(meminfo: Path = Path("/proc/meminfo")) -> int | None:
    if sys.platform != "linux" and meminfo == Path("/proc/meminfo"):
        return None
    try:
        return next(
            (
                int(ln.split()[1]) * 1024
                for ln in meminfo.read_text(encoding="utf-8").splitlines()
                if ln.startswith("MemAvailable:")
            ),
            None,
        )
    except OSError, ValueError, IndexError:
        return None


def headroom_results(paths: list[Path] | None = None, *, memory: int | None = None) -> list[CheckResult]:
    tmpdir = os.environ.get("TMPDIR")
    candidates = paths or [Path.cwd(), Path.home(), Path("/var/tmp"), *([Path(tmpdir)] if tmpdir else [])]  # noqa: S108
    devices: dict[int, list[str]] = {}
    results: list[CheckResult] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            if (path := candidate.resolve()) not in seen and path.is_dir():
                seen.add(path)
                devices.setdefault(path.stat().st_dev, []).append(str(path))
        except OSError as error:
            results.append(CheckResult("disk", "warn", f"inaccessible path: {error}", str(candidate)))
    for members in devices.values():
        try:
            free = shutil.disk_usage(members[0]).free / _GIB
            status = "fail" if free < _DISK_FAIL_GIB else "warn" if free < _DISK_WARN_GIB else "pass"
            results.append(CheckResult("disk", status, f"{free:.1f} GiB free", ", ".join(members)))
        except OSError as error:
            results.append(CheckResult("disk", "warn", f"disk usage unavailable: {error}", ", ".join(members)))
    avail = available_memory_bytes() if memory is None else memory
    if avail is None:
        return [*results, CheckResult("memory", "warn", "available memory unknown on this platform")]
    gibs = avail / _GIB
    mem = CheckResult("memory", "fail" if gibs < _MEMORY_FAIL_GIB else "pass", f"{gibs:.1f} GiB available")
    return [*results, mem]


def run_doctor(state: State, *, fix: bool, deep: bool = False) -> list[CheckResult]:
    names = list(_AGENT_HOSTS)
    remedy = "free disk space or verify with `dot doctor --headroom`"
    disk = [
        r if r.status == "pass" else replace(r, details=f"{r.details}; {remedy}")
        for r in headroom_results(memory=0)
        if r.name == "disk"
    ]
    tasks: list[tuple[str, Callable[[], list[CheckResult]]]] = [
        ("docker", lambda: _docker_results(state)),
        ("tools", lambda: _tool_results(state)),
        ("install", lambda: _install_results(state)),
        ("agents", lambda: run_parallel(state.runner, _inspect_agent, names, len(names))),
    ]
    if deep:
        tasks.insert(0, ("auth", lambda: _auth_results(state)))
    probed = dict(run_parallel(state.runner, lambda item: (item[0], item[1]()), tasks, len(tasks)))
    sections = {
        "auth": probed.get("auth") or [CheckResult("authentication", "skip", "use --deep to probe providers")],
        "secrets": _secret_results(fix=fix),
        "docker": probed["docker"],
        "resources": disk,
        "tools": probed["tools"],
        "install": probed["install"],
        "agents": probed["agents"],
    }
    return [replace(item, group=group) for group, items in sections.items() for item in items]


_DOCTOR_ICONS = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "○"}


def _attention_results(results: Sequence[CheckResult], *, quiet: bool) -> list[CheckResult]:
    return [i for i in results if i.status in {"fail", "warn"}] if quiet else list(results)


def _write_headroom(state: State, results: Sequence[CheckResult], *, as_json: bool, quiet: bool) -> None:
    shown = _attention_results(results, quiet=quiet)
    if as_json:
        payload = [replace(i, group="resources").payload() for i in shown]
        write_json(state.stdout, diagnostic_report("headroom", payload))
        return
    verdict = next((s.upper() for s in ("fail", "warn") if any(i.status == s for i in results)), "PASS")
    parts = [
        f"{r.name} {r.details}" + (f" ({r.path})" if r.path else "") + ("" if r.status == "pass" else f" [{r.status}]")
        for r in shown
    ]
    summary = "; ".join(parts) if parts else f"{len(results)} passed"
    lim = f" · limits: disk {_DISK_FAIL_GIB} GiB (warn below {_DISK_WARN_GIB}), memory {_MEMORY_FAIL_GIB} GiB"
    print(f"{verdict} · headroom: {summary}{'' if verdict == 'PASS' else lim}", file=state.stdout)


def _write_workstation_group(state: State, group: str, label: str, items: Sequence[CheckResult]) -> None:
    print(f"\n{label}", file=state.stdout)
    if group == "tools":
        passed_tools = sum(1 for item in items if item.status == "pass")
        for item in items:
            if item.status != "pass":
                print(f"  {_DOCTOR_ICONS[item.status]} {item.name:<20} {item.details}", file=state.stdout)
        if passed_tools:
            print(f"  ✓ {f'tools ({passed_tools})':<20} capability probes passed", file=state.stdout)
        return
    for item in items:
        detail = f"{item.details} ({item.path})" if item.name == "disk" else item.details
        print(f"  {_DOCTOR_ICONS[item.status]} {item.name:<20} {detail}", file=state.stdout)


def _write_workstation_text(state: State, results: Sequence[CheckResult], *, quiet: bool) -> None:
    if quiet:
        for item in _attention_results(results, quiet=True):
            detail = f"{item.details} ({item.path})" if item.name == "disk" else item.details
            print(f"  {_DOCTOR_ICONS[item.status]} [{item.group}] {item.name:<18} {detail}", file=state.stdout)
        verdict = "FAIL" if any(i.status == "fail" for i in results) else "PASS"
        labels = (("fail", "failed"), ("warn", "warned"), ("pass", "passed"), ("skip", "skipped"))
        counts = ((sum(1 for i in results if i.status == s), lbl) for s, lbl in labels)
        print(f"{verdict} · doctor: {', '.join(f'{n} {lbl}' for n, lbl in counts if n)}", file=state.stdout)
        return
    for group, label in _DOCTOR_GROUPS:
        _write_workstation_group(state, group, label, [i for i in results if i.group == group])


def _doctor(state: State, args: argparse.Namespace) -> None:
    if args.headroom:
        if args.fix or args.deep:
            raise UsageError("--headroom cannot be combined with --fix or --deep")
        results = headroom_results()
        _write_headroom(state, results, as_json=args.as_json, quiet=args.quiet)
    else:
        _ = state.config
        results = run_doctor(state, fix=args.fix, deep=args.deep)
        if args.as_json:
            shown = _attention_results(results, quiet=args.quiet)
            write_json(state.stdout, diagnostic_report("workstation", [item.payload() for item in shown]))
        else:
            _write_workstation_text(state, results, quiet=args.quiet)
    if any(i.status == "fail" for i in results):
        raise SystemExit(1)


def register_doctor(commands: Parser) -> None:
    epilog = (
        f"Exit 1 on any failed check, including disk below {_DISK_FAIL_GIB} GiB free (warns below {_DISK_WARN_GIB}). "
        f"--headroom also fails below {_MEMORY_FAIL_GIB} GiB available memory; exit 2 when --headroom is combined with --fix or --deep.\n\n"
        "Examples: dot doctor --deep · dot doctor --headroom · dot doctor -q --json"
    )
    summary = "Check local workstation health; --deep also probes provider authentication"
    d = commands.command("doctor", summary, _doctor, config=False, epilog=epilog)
    add_json(d)
    add_quiet(d)
    d.add_argument("--fix", action="store_true", help="Repair local secret-file permissions")
    d.add_argument("--deep", action="store_true", help="Also probe provider authentication")
    headroom_help = f"Only check disk (≥{_DISK_FAIL_GIB} GiB) and memory (≥{_MEMORY_FAIL_GIB} GiB) headroom before large downloads or builds; prints one line"
    d.add_argument("--headroom", action="store_true", help=headroom_help)
