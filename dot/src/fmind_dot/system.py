"""Workstation diagnostics, completions, and installation freshness."""

import importlib.metadata
import os
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.completion import get_completion_script

from fmind_dot.auth import (
    GCLOUD_CLI_TOKEN,
    GITHUB_KEYRING_REMEDY,
    adc_ready,
    gcloud_ready,
    github_status,
    github_token_plaintext,
    workspace_ready,
)
from fmind_dot.command_group import JsonOption
from fmind_dot.config import expand_path
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import CommandResult, Runner, run_parallel
from fmind_dot.reporting import diagnostic_report, write_json
from fmind_dot.state import State, require_tools, state_from

# Operating thresholds shared with the persona and the dot-cli disk-space guide.
_GIB = 1024**3
_DISK_FAIL_GIB = 10
_DISK_WARN_GIB = 20
_MEMORY_FAIL_GIB = 1
_TOOL_PROBE_ARGS: dict[str, tuple[str, ...]] = {
    "agy": ("--help",),
    "gitleaks": ("version",),
    "lefthook": ("version",),
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    details: str
    path: str = ""
    condition: str = ""


def _check_result_payload(result: CheckResult) -> dict[str, str]:
    payload = {"name": result.name, "status": result.status}
    # Preserve the sparse Go v1 wire format instead of exposing empty implementation defaults.
    if result.condition:
        payload["condition"] = result.condition
    if result.path:
        payload["path"] = result.path
    if result.details:
        payload["details"] = result.details
    return payload


def _write_validated_fish(state: State, path: Path, content: str, mode: int) -> None:
    if not content.strip():
        raise DotError(f"generated Fish script is empty: {path.name}")
    require_tools(state, [["fish"]])
    timeout = state.config.completions.timeout_seconds
    try:
        state.runner.run(["fish", "--no-config", "--no-execute"], input_text=content, timeout=timeout)
    except (DotError, OSError) as error:
        raise DotError(f"generated Fish script failed syntax validation: {path.name}") from error
    try:
        write_atomic_file(path, content.encode("utf-8"), mode=mode)
    except OSError as error:
        raise DotError(f"failed to publish Fish script: {path.name}") from error


def _completion_available(state: State, tool: str) -> bool:
    executable = state.runner.which(tool)
    if executable is None:
        return False
    mise = state.runner.which("mise")
    # Disabled optional tools can leave executable shims pointing at mise.
    # Resolve only those shims; a real executable needs no mise configuration.
    if tool != "mise" and mise is not None and executable.resolve() == mise.resolve():
        result = state.runner.run(
            ["mise", "which", tool], timeout=state.config.completions.timeout_seconds, check=False
        )
        if result.returncode:
            if "not currently active" in result.stderr or "No version is set" in result.stderr:
                return False
            raise DotError(f"failed to resolve mise completion executable for {tool}")
    return True


def _generate_completion(state: State, tool: str) -> str:
    custom = state.config.completions.custom_commands.get(tool)
    binary = custom.binary if custom and custom.binary else tool
    if tool == "dot" and custom and custom.binary == "env" and custom.args == ["_DOT_COMPLETE=source_fish", "dot"]:
        return get_completion_script(  # noqa: S604 - static Fish protocol template, not a shell invocation.
            prog_name="dot", complete_var="_DOT_COMPLETE", shell="fish"
        )
    if not _completion_available(state, tool):
        raise FileNotFoundError(tool)
    if custom and custom.package:
        require_tools(state, [["mise"]])
        root = state.runner.run(
            ["mise", "where", "--", custom.package], timeout=state.config.completions.timeout_seconds
        ).stdout.strip()
        if not root or not Path(root).is_absolute() or not Path(root).is_dir():
            raise DotError(f"mise returned an invalid completion package directory for {tool}")
        matches = list(Path(root).rglob(f"{tool}.fish"))
        if len(matches) != 1:
            raise DotError(f"expected one bundled Fish completion for {tool}, found {len(matches)}")
        try:
            return matches[0].read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            # A per-tool DotError keeps one bad package from aborting the remaining generators.
            raise DotError(f"bundled Fish completion for {tool} is not UTF-8") from error
    if binary != tool and state.runner.which(binary) is None:
        raise DotError(f"completion generator for {tool} is not installed: {binary}")
    args = custom.args if custom and custom.args else ["completion", "fish"]
    timeout = state.config.completions.timeout_seconds
    with tempfile.TemporaryDirectory(prefix="dot-completion-") as directory:
        try:
            result = state.runner.run([binary, *args], cwd=Path(directory), timeout=timeout)
        except (DotError, OSError) as error:
            raise DotError(f"failed to generate completions for {tool}") from error
        if not result.stdout.strip():
            raise DotError(f"failed to generate completions for {tool}: empty output")
    return result.stdout


def run_completion(state: State, *, check_only: bool = False) -> None:
    if check_only:
        with tempfile.TemporaryDirectory(prefix="dot-completion-check-") as temporary:
            root = Path(temporary)
            failures = _run_completion(state, root / "completions", root / "cache")
        if failures:
            raise DotError("completion generation failed: " + "; ".join(failures))
        typer.echo("Completion check passed; installed scripts were not changed.", file=state.stdout)
        return
    directory = expand_path(state.config.completions.path)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "fish"
    # Generator failures are reported above and leave previous scripts intact; setup continues.
    if not _run_completion(state, directory, cache):
        typer.echo(f"\n✓ Completions updated in {directory}", file=state.stdout)


def _run_completion(state: State, directory: Path, cache: Path) -> list[str]:
    try:
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError("failed to create completions directory") from error
    failures: list[str] = []
    typer.echo(
        f"=> Generating Fish autocompletions for {len(state.config.completions.tools)} tools in {directory}...\n",
        file=state.stdout,
    )
    for tool in dict.fromkeys(state.config.completions.tools):
        try:
            content = _generate_completion(state, tool)
            _write_validated_fish(state, directory / f"{tool}.fish", content, 0o644)
            typer.echo(f"  ✓ Generated completions for {tool}", file=state.stdout)
        except FileNotFoundError:
            typer.echo(f"  ○ {tool} is not installed or active, skipping", file=state.stdout)
        except (DotError, OSError) as error:
            failures.append(f"{tool}: {error}")
            typer.echo(f"  ✗ Failed to generate completions for {tool}", file=state.stdout)
    try:
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        failures.append("fish cache directory: failed to create")
        typer.echo("  ✗ Failed to create fish cache directory", file=state.stdout)
        cache_ready = False
    else:
        cache_ready = True
    if cache_ready:
        for tool, filename, args in (
            # This setup does not use Atuin AI; omit its "?" key binding.
            ("atuin", "atuin-init.fish", ["init", "fish", "--disable-ai"]),
            ("carapace", "carapace-init.fish", ["_carapace", "fish"]),
        ):
            try:
                if not _completion_available(state, tool):
                    continue
                # Native scripts must win over Carapace's generic completers;
                # in particular its "dot" completer is for Graphviz, not this CLI.
                excludes = set(os.environ.get("CARAPACE_EXCLUDES", "").split(",")) | set(state.config.completions.tools)
                environment = {"CARAPACE_EXCLUDES": ",".join(sorted(excludes - {""}))} if tool == "carapace" else None
                result = state.runner.run(
                    [tool, *args], timeout=state.config.completions.timeout_seconds, env=environment
                )
                _write_validated_fish(state, cache / filename, result.stdout, 0o600)
                typer.echo(f"  ✓ Generated {filename}", file=state.stdout)
            except (DotError, OSError) as error:
                failures.append(f"{filename}: {error}")
                typer.echo(f"  ✗ Failed to generate {filename}", file=state.stdout)
    if failures:
        typer.echo("\nCompletion generation finished with failures: " + "; ".join(failures), file=state.stdout)
    return failures


def _environment_results(state: State) -> list[CheckResult]:
    results = [
        CheckResult(name, "pass", "set") if os.environ.get(name) else CheckResult(name, "fail", "MISSING (required)")
        for name in state.config.doctor.env_vars.required
    ]
    # An unset optional variable is a valid choice, reported like an absent optional tool.
    results.extend(
        CheckResult(name, "pass", "set")
        if os.environ.get(name)
        else CheckResult(name, "skip", "unset (optional)", condition="skipped")
        for name in state.config.doctor.env_vars.optional
    )
    return results


def _secret_results(state: State, *, fix: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    for secret in state.config.doctor.secrets:
        path = expand_path(secret.path)
        try:
            info = path.stat()
        except FileNotFoundError:
            results.append(CheckResult(secret.path, "warn", "MISSING"))
            continue
        except OSError:
            results.append(CheckResult(secret.path, "fail", "unable to inspect file"))
            continue
        if not stat.S_ISREG(info.st_mode):
            results.append(CheckResult(secret.path, "fail", "not a regular file"))
            continue
        current = stat.S_IMODE(info.st_mode)
        allowed = secret.required_perms
        if allowed == 0 or current & ~allowed == 0:
            results.append(CheckResult(secret.path, "pass", f"secure (permissions: {current:04o})"))
        elif fix:
            try:
                path.chmod(allowed)
            except OSError:
                results.append(
                    CheckResult(
                        secret.path,
                        "fail",
                        f"INSECURE permissions: {current:04o} (repair failed; expected {allowed:04o})",
                    )
                )
            else:
                results.append(CheckResult(secret.path, "pass", f"repaired (permissions: {allowed:04o})"))
        else:
            results.append(
                CheckResult(
                    secret.path,
                    "fail",
                    f"INSECURE permissions: {current:04o} (expected {allowed:04o})",
                )
            )
    return results


def _probe(state: State, args: Sequence[str]) -> CommandResult | str:
    """Run one doctor probe; a string names why it produced no usable result."""
    try:
        return state.runner.run(list(args), timeout=state.config.doctor.probe_timeout_seconds, check=False)
    except CommandTimeoutError:
        return "timed out"
    except DotError, OSError:
        return "failed"


def _tool_results(state: State) -> list[CheckResult]:
    def probe(tool: str) -> CheckResult:
        path = state.runner.which(tool)
        if path is None:
            return CheckResult(tool, "fail", "command not found", condition="missing")
        result = _probe(state, [str(path), *_TOOL_PROBE_ARGS.get(tool, ("--version",))])
        if isinstance(result, str):
            return CheckResult(tool, "fail", f"capability probe {result}", str(path), "broken")
        if result.returncode != 0:
            return CheckResult(tool, "fail", "capability probe failed", str(path), "broken")
        return CheckResult(tool, "pass", "capability probe passed", str(path), "healthy")

    return run_parallel(state.runner, probe, state.config.doctor.tools, state.config.doctor.probe_concurrency)


def _auth_results(state: State) -> list[CheckResult]:
    """Report authentication without authenticating: GitHub only confirms a login, since environment and
    fine-grained tokens report no OAuth scopes; Google probes check the scopes dot login requests."""

    def github() -> CheckResult | bool:
        entry = github_status(state)
        if github_token_plaintext(entry):
            details = f"authenticated; token in plaintext hosts.yml: {GITHUB_KEYRING_REMEDY}"
            return CheckResult("gh", "warn", details, condition="insecure")
        return entry is not None

    checks: dict[str, tuple[str, Callable[[], CheckResult | bool]]] = {
        "gh": ("gh", github),
        "gcloud": ("gcloud", lambda: gcloud_ready(state, GCLOUD_CLI_TOKEN)),
        "gcloud-adc": ("gcloud", lambda: adc_ready(state)),
        "gws": ("gws", lambda: workspace_ready(state)),
    }
    results: list[CheckResult] = []
    for label, (tool, check) in checks.items():
        path = state.runner.which(tool)
        if path is None:
            results.append(CheckResult(label, "skip", f"{tool} not installed", condition="skipped"))
            continue
        try:
            ready = check()
        except CommandTimeoutError:
            results.append(CheckResult(label, "fail", "auth check timed out; state unknown", str(path), "broken"))
            continue
        except DotError, OSError:
            results.append(CheckResult(label, "fail", "auth check failed; state unknown", str(path), "broken"))
            continue
        if isinstance(ready, CheckResult):
            results.append(replace(ready, path=str(path)))
        elif ready:
            results.append(CheckResult(label, "pass", "authenticated", str(path), "healthy"))
        else:
            results.append(CheckResult(label, "fail", "NOT authenticated", str(path), "unauthenticated"))
    return results


def _docker_results(state: State) -> list[CheckResult]:
    path = state.runner.which("docker")
    if path is None:
        # A container engine is optional; doctor.tools decides whether its absence fails.
        return [CheckResult("docker", "skip", "not installed (optional)", condition="skipped")]
    result = _probe(state, ["docker", "info"])
    if isinstance(result, str):
        return [CheckResult("docker", "fail", f"service probe {result}", str(path), "broken")]
    return [
        CheckResult("docker", "pass", "running", str(path), "healthy")
        if result.returncode == 0
        else CheckResult("docker", "fail", "not running", str(path), "broken")
    ]


# The running package: deployed by uv tool install, or the src-layout checkout under `uv run`.
PACKAGE_DIRECTORY = Path(__file__).resolve().parent


def _installed_version() -> str:
    return importlib.metadata.version("fmind-dot")


def _package_files(directory: Path) -> dict[str, bytes]:
    # Bundled rate cards affect runtime behavior just as Python modules do.
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in {".py", ".yaml"}
    }


def _install_staleness(source: Path) -> str:
    """Return why the installed package is stale against a source checkout, or "" when it matches."""
    with (source / "dot/pyproject.toml").open("rb") as stream:
        version = tomllib.load(stream).get("project", {}).get("version")
    if version != _installed_version():
        return "installed version differs from source"
    if _package_files(source / "dot/src/fmind_dot") != _package_files(PACKAGE_DIRECTORY):
        return "installed Python package differs from source"
    return ""


def _install_results(state: State) -> list[CheckResult]:
    name = "dot"
    chezmoi = state.runner.which("chezmoi")
    if chezmoi is None:
        return [CheckResult(name, "skip", "chezmoi not installed", condition="skipped")]
    source_result = _probe(state, ["chezmoi", "source-path"])
    source_text = "" if isinstance(source_result, str) or source_result.returncode else source_result.stdout.strip()
    if not source_text or len(source_text.splitlines()) != 1:
        return [CheckResult(name, "warn", "could not resolve chezmoi source", condition="unknown")]
    source = Path(source_text)
    source_package = source / "dot/src/fmind_dot"
    project = source / "dot/pyproject.toml"
    if not source_package.is_dir() or not project.is_file():
        return [CheckResult(name, "skip", "chezmoi source is not a Python dot checkout", condition="skipped")]
    installed_path = str(PACKAGE_DIRECTORY)
    # `uv run --project dot dot doctor` imports the src-layout checkout, which trivially matches itself.
    if PACKAGE_DIRECTORY.parent.name == "src" and (PACKAGE_DIRECTORY.parents[1] / "pyproject.toml").is_file():
        return [
            CheckResult(
                name,
                "skip",
                "running from a source checkout; check the deployed dot instead",
                installed_path,
                "skipped",
            )
        ]
    try:
        stale = _install_staleness(source)
    except OSError, tomllib.TOMLDecodeError, importlib.metadata.PackageNotFoundError:
        return [CheckResult(name, "fail", "could not verify installed Python package", condition="broken")]
    if stale:
        return [CheckResult(name, "fail", f"STALE: {stale}", installed_path, "stale")]
    return [CheckResult(name, "pass", "installed Python package matches source", installed_path, "healthy")]


def available_memory_bytes(meminfo: Path = Path("/proc/meminfo")) -> int | None:
    """MemAvailable counts reclaimable cache; sysconf's free pages would under-report."""
    if sys.platform == "darwin" and meminfo == Path("/proc/meminfo"):
        try:
            return vm_stat_available_bytes(Runner().run(["vm_stat"], timeout=10).stdout)
        except DotError, OSError:
            return None
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except OSError, ValueError, IndexError:
        return None
    return None


def vm_stat_available_bytes(output: str) -> int | None:
    """Estimate macOS available memory like psutil: non-speculative free plus inactive pages."""
    page = re.search(r"page size of (\d+) bytes", output)
    pages = dict(re.findall(r"^Pages (free|inactive|speculative):\s+(\d+)\.$", output, re.MULTILINE))
    if page is None or not {"free", "inactive"} <= pages.keys():
        return None
    free = int(pages["free"]) - int(pages.get("speculative", 0))
    return (max(free, 0) + int(pages["inactive"])) * int(page.group(1))


def headroom_results(paths: list[Path] | None = None, *, memory: int | None = None) -> list[CheckResult]:
    """Check each distinct filesystem behind the workspace, home, and large scratch directories.

    /var/tmp is the documented scratch for large work; /tmp is often a small tmpfs, so it
    counts only when TMPDIR selects it.
    """
    tmpdir = os.environ.get("TMPDIR")
    candidates = paths or [Path.cwd(), Path.home(), Path("/var/tmp"), *([Path(tmpdir)] if tmpdir else [])]  # noqa: S108
    devices: dict[int, list[str]] = {}
    for path in dict.fromkeys(candidate.resolve() for candidate in candidates):
        if path.is_dir():
            devices.setdefault(path.stat().st_dev, []).append(str(path))
    results = []
    for members in devices.values():
        free = shutil.disk_usage(members[0]).free / _GIB
        status = "fail" if free < _DISK_FAIL_GIB else "warn" if free < _DISK_WARN_GIB else "pass"
        results.append(CheckResult("disk", status, f"{free:.1f} GiB free", ", ".join(members)))
    available = memory if memory is not None else available_memory_bytes()
    if available is None:
        results.append(CheckResult("memory", "warn", "available memory unknown on this platform"))
    else:
        status = "fail" if available / _GIB < _MEMORY_FAIL_GIB else "pass"
        results.append(CheckResult("memory", status, f"{available / _GIB:.1f} GiB available"))
    return results


def _headroom_line(results: list[CheckResult]) -> str:
    statuses = {result.status for result in results}
    verdict = "FAIL" if "fail" in statuses else "WARN" if "warn" in statuses else "PASS"
    parts = [
        f"{result.name} {result.details}"
        + (f" ({result.path})" if result.path else "")
        + ("" if result.status == "pass" else f" [{result.status}]")
        for result in results
    ]
    line = f"{verdict} · headroom: " + "; ".join(parts)
    if verdict != "PASS":
        line += f" · limits: disk {_DISK_FAIL_GIB} GiB (warn below {_DISK_WARN_GIB}), memory {_MEMORY_FAIL_GIB} GiB"
    return line


def run_doctor(state: State, *, fix: bool, deep: bool = False) -> dict[str, Any]:
    sections = {
        "env_vars": _environment_results(state),
        "auth": _auth_results(state)
        if deep
        else [CheckResult("authentication", "skip", "use --deep to probe providers")],
        "secrets": _secret_results(state, fix=fix),
        "docker": _docker_results(state),
        "tools": _tool_results(state),
        "install": _install_results(state),
    }
    passed = all(item.status != "fail" for items in sections.values() for item in items)
    return {key: [_check_result_payload(item) for item in items] for key, items in sections.items()} | {
        "passed": passed
    }


def _print_doctor(state: State, results: Mapping[str, Any]) -> None:
    labels = {
        "env_vars": "Environment Variables",
        "auth": "CLI Authentication",
        "secrets": "Secrets & Encryption",
        "docker": "System Services",
        "tools": "CLI Tools",
        "install": "Install Freshness",
    }
    icons = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "○"}
    for key, label in labels.items():
        typer.echo(f"\n{label}", file=state.stdout)
        for item in results[key]:
            typer.echo(
                f"  {icons[item['status']]} {item['name']:<20} {item.get('details', '')}",
                file=state.stdout,
            )


def register(app: typer.Typer) -> None:
    @app.command("completion", help="Generate and validate Fish completions")
    def completion(
        context: typer.Context,
        check_only: Annotated[
            bool,
            typer.Option("--check", help="Validate generators in a temporary directory without installing scripts"),
        ] = False,
    ) -> None:
        run_completion(state_from(context), check_only=check_only)

    @app.command("doctor", help="Check local workstation health; --deep also probes authentication")
    def doctor(
        context: typer.Context,
        json_output: JsonOption = False,
        fix: Annotated[bool, typer.Option("--fix", help="Repair local secret-file permissions")] = False,
        deep: Annotated[bool, typer.Option("--deep", help="Also probe provider authentication")] = False,
        headroom: Annotated[
            bool,
            typer.Option(
                "--headroom",
                help="Only check disk and memory headroom before large operations; prints one line",
            ),
        ] = False,
    ) -> None:
        # Headroom never reads dot.yaml, so a broken config must not block the pre-job check.
        state = state_from(context, require_config=not headroom)
        if headroom:
            if fix or deep:
                raise typer.BadParameter("--headroom cannot be combined with --fix or --deep")
            checks = headroom_results()
            if json_output:
                payload = [dict(_check_result_payload(item), group="resources") for item in checks]
                write_json(state.stdout, diagnostic_report("headroom", payload))
            else:
                typer.echo(_headroom_line(checks), file=state.stdout)
            if any(item.status == "fail" for item in checks):
                raise typer.Exit(1)
            return
        results = run_doctor(state, fix=fix, deep=deep)
        if json_output:
            checks = [
                dict(item, group=group) for group, items in results.items() if group != "passed" for item in items
            ]
            write_json(state.stdout, diagnostic_report("workstation", checks))
        else:
            _print_doctor(state, results)
        if not results["passed"]:
            raise typer.Exit(1)
