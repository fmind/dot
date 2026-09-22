"""Workstation diagnostics, completions, and installation freshness."""

import json
import os
import stat
import tempfile
import tomllib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.completion import get_completion_script

from fmind_dot import deploy
from fmind_dot.command_group import JsonOption
from fmind_dot.config import expand_path
from fmind_dot.diagnostics import diagnostic_report
from fmind_dot.errors import DotError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import PROBE_OUTPUT_LIMIT_BYTES, CommandResult
from fmind_dot.state import State, require_tools, state_from

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_AUTH_PROBES = {
    "gh": (["gh", "auth", "status"], False),
    "gcloud": (["gcloud", "auth", "print-access-token"], True),
    "gcloud-adc": (["gcloud", "auth", "application-default", "print-access-token"], True),
    "gws": (["gws", "auth", "status"], False),
}
_AUTH_FAILURE_MARKERS = (
    "invalid_grant",
    "expired or revoked",
    "reauthentication failed",
    "not currently logged in",
    "do not currently have an active account",
    "no credentialed accounts",
    "not logged into any github hosts",
    "authentication token is invalid",
    "invalid authentication credentials",
    "credentials not found",
    "login required",
)
_TOOL_PROBE_ARGS: dict[str, tuple[str, ...]] = {
    "age": ("--version",),
    "agy": ("--help",),
    "chezmoi": ("--version",),
    "claude": ("--version",),
    "codex": ("--version",),
    "copilot": ("--version",),
    "docker": ("--version",),
    "dprint": ("--version",),
    "gcloud": ("--version",),
    "gh": ("--version",),
    "git": ("--version",),
    "git-cliff": ("--version",),
    "gitleaks": ("version",),
    "grok": ("--version",),
    "gws": ("--version",),
    "lefthook": ("version",),
    "mise": ("--version",),
    "nvim": ("--version",),
    "pgcli": ("--version",),
    "python": ("--version",),
    "ruff": ("--version",),
    "sqlite3": ("--version",),
    "tree-sitter": ("--version",),
    "trivy": ("--version",),
    "ty": ("--version",),
    "uv": ("--version",),
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
        return matches[0].read_text(encoding="utf-8")
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
            ("atuin", "atuin-init.fish", ["init", "fish"]),
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
    results.extend(
        CheckResult(name, "pass", "set") if os.environ.get(name) else CheckResult(name, "warn", "unset (optional)")
        for name in state.config.doctor.env_vars.optional
    )
    if "opencode" in state.config.doctor.tools:
        results.append(_opencode_project_result(state))
    return results


def _opencode_project_result(state: State) -> CheckResult:
    name = "opencode-project"
    if state.runner.which("opencode") is None:
        return CheckResult(name, "skip", "opencode not installed (see Tools)")
    try:
        # Let OpenCode resolve JSONC, overrides, and environment substitution.
        # Disable external plugins and never render the potentially secret output.
        result = state.runner.run_bounded(
            ["opencode", "debug", "config", "--pure"],
            max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
            timeout=state.config.doctor.probe_timeout_seconds,
            check=False,
        )
        if result.returncode or result.output_truncated:
            return CheckResult(name, "fail", "resolved configuration probe failed; run opencode debug config privately")
        config = json.loads(result.stdout)
        if not isinstance(config, dict) or not isinstance(config.get("provider", {}), dict):
            raise ValueError("invalid configuration shape")
        vertex = config.get("provider", {}).get("google-vertex")
        uses_vertex = any(
            isinstance(config.get(key), str) and config[key].startswith("google-vertex/")
            for key in ("model", "small_model")
        )
        if vertex is None and not uses_vertex:
            return CheckResult(name, "skip", "Google Vertex provider not configured")
        if not isinstance(vertex, dict) or not isinstance(vertex.get("options", {}), dict):
            raise ValueError("invalid provider options")
        project = vertex.get("options", {}).get("project")
    except DotError, OSError, ValueError:
        return CheckResult(name, "fail", "unable to resolve configuration; run opencode debug config privately")
    if not isinstance(project, str) or not project.strip() or "{" in project or "}" in project:
        return CheckResult(
            name,
            "fail",
            "set the Google Vertex project in OpenCode configuration or its referenced environment variable",
        )
    return CheckResult(name, "pass", "Google Vertex project selected (access not checked)")


def _secret_results(state: State, *, fix: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    for secret in state.config.doctor.secrets:
        path = expand_path(secret.path)
        try:
            current = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError:
            results.append(CheckResult(secret.path, "warn", "MISSING"))
            continue
        except OSError:
            results.append(CheckResult(secret.path, "fail", "unable to inspect file"))
            continue
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


def _tool_results(state: State) -> list[CheckResult]:
    timeout = state.config.doctor.probe_timeout_seconds

    def probe(tool: str) -> CheckResult:
        path = state.runner.which(tool)
        if path is None:
            return CheckResult(tool, "fail", "command not found", condition="missing")
        args = _TOOL_PROBE_ARGS.get(tool, ("--version",))
        try:
            result = state.runner.run_bounded(
                [str(path), *args],
                max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
                timeout=timeout,
                check=False,
            )
        except (DotError, OSError) as error:
            detail = "capability probe timed out" if "timed out" in str(error).lower() else "capability probe failed"
            return CheckResult(tool, "fail", detail, str(path), "broken")
        if result.output_truncated:
            return CheckResult(tool, "fail", "capability probe output exceeded limit", str(path), "broken")
        if result.returncode != 0:
            return CheckResult(tool, "fail", "capability probe failed", str(path), "broken")
        return CheckResult(tool, "pass", "capability probe passed", str(path), "healthy")

    tools = state.config.doctor.tools
    if not tools:
        return []
    workers = min(state.config.doctor.probe_concurrency, len(tools))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(probe, tools))


def _recognized_auth_failure(result: CommandResult) -> bool:
    diagnostic = f"{result.stdout}\n{result.stderr}".lower()
    return any(marker in diagnostic for marker in _AUTH_FAILURE_MARKERS)


def _auth_results(state: State) -> list[CheckResult]:
    results: list[CheckResult] = []
    timeout = state.config.doctor.probe_timeout_seconds
    probes = dict(_AUTH_PROBES)
    probes["gh"] = (["gh", "auth", "status", "--hostname", state.config.doctor.github_host], False)
    for label, (command, requires_output) in probes.items():
        path = state.runner.which(command[0])
        if path is None:
            results.append(CheckResult(label, "skip", f"{command[0]} not installed", condition="skipped"))
            continue
        try:
            result = state.runner.run_bounded(
                command,
                max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
                timeout=timeout,
                check=False,
            )
        except (DotError, OSError) as error:
            detail = (
                "auth check timed out; state unknown"
                if "timed out" in str(error).lower()
                else "auth check failed; state unknown"
            )
            results.append(CheckResult(label, "fail", detail, str(path), "broken"))
            continue
        if result.output_truncated:
            results.append(
                CheckResult(label, "fail", "auth check output exceeded limit; state unknown", str(path), "broken")
            )
        elif result.returncode == 0 and (not requires_output or result.stdout.strip()):
            results.append(CheckResult(label, "pass", "authenticated", str(path), "healthy"))
        elif result.returncode == 0:
            results.append(
                CheckResult(label, "fail", "auth check returned no usable output; state unknown", str(path), "broken")
            )
        elif _recognized_auth_failure(result):
            results.append(CheckResult(label, "fail", "NOT authenticated", str(path), "unauthenticated"))
        else:
            results.append(CheckResult(label, "fail", "auth check failed; state unknown", str(path), "broken"))
    return results


def _docker_results(state: State) -> list[CheckResult]:
    path = state.runner.which("docker")
    if path is None:
        return [CheckResult("docker", "fail", "not installed")]
    try:
        result = state.runner.run_bounded(
            ["docker", "info"],
            max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
            timeout=state.config.doctor.probe_timeout_seconds,
            check=False,
        )
    except DotError, OSError:
        return [CheckResult("docker", "fail", "service probe failed", str(path), "broken")]
    if result.output_truncated:
        return [CheckResult("docker", "fail", "service probe output exceeded limit", str(path), "broken")]
    return [
        CheckResult("docker", "pass", "running", str(path), "healthy")
        if result.returncode == 0
        else CheckResult("docker", "fail", "not running", str(path), "broken")
    ]


def _install_results(state: State) -> list[CheckResult]:
    name = "dot"
    chezmoi = state.runner.which("chezmoi")
    if chezmoi is None:
        return [CheckResult(name, "skip", "chezmoi not installed", condition="skipped")]
    try:
        source_result = state.runner.run_bounded(
            ["chezmoi", "source-path"],
            max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES,
            timeout=state.config.doctor.probe_timeout_seconds,
            check=False,
        )
    except DotError, OSError:
        return [CheckResult(name, "warn", "could not resolve chezmoi source", condition="unknown")]
    source_text = source_result.stdout.strip()
    if (
        source_result.output_truncated
        or source_result.returncode != 0
        or not source_text
        or len(source_text.splitlines()) != 1
    ):
        return [CheckResult(name, "warn", "could not resolve chezmoi source", condition="unknown")]
    source = Path(source_text)
    source_package = source / "dot/src/fmind_dot"
    project = source / "dot/pyproject.toml"
    if not source_package.is_dir() or not project.is_file():
        return [CheckResult(name, "skip", "chezmoi source is not a Python dot checkout", condition="skipped")]
    installed_path = str(deploy.PACKAGE_DIRECTORY)
    # `uv run --project dot dot doctor` imports a src-layout checkout, which has no deployed receipt.
    if (
        deploy.PACKAGE_DIRECTORY.parent.name == "src"
        and (deploy.PACKAGE_DIRECTORY.parents[1] / "pyproject.toml").is_file()
    ):
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
        stale = deploy.install_staleness(source)
    except OSError, tomllib.TOMLDecodeError:
        return [CheckResult(name, "fail", "could not verify installed Python package", condition="broken")]
    if stale:
        return [CheckResult(name, "fail", f"STALE: {stale}", installed_path, "stale")]
    return [CheckResult(name, "pass", "installed Python package matches source", installed_path, "healthy")]


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
        fix: Annotated[bool, typer.Option("--fix", "-f", help="Repair local secret-file permissions")] = False,
        deep: Annotated[bool, typer.Option("--deep", help="Also probe provider authentication")] = False,
    ) -> None:
        state = state_from(context)
        results = run_doctor(state, fix=fix, deep=deep)
        if json_output:
            checks = [
                dict(item, group=group) for group, items in results.items() if group != "passed" for item in items
            ]
            typer.echo(json.dumps(diagnostic_report("workstation", checks), indent=2), file=state.stdout)
        else:
            _print_doctor(state, results)
        if not results["passed"]:
            raise typer.Exit(1)
