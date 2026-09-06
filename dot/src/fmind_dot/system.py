"""System integration commands: completion, authentication, setup, notifications, and checks."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import tempfile
import tomllib
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Annotated, Any

import typer
from typer.completion import get_completion_script

from fmind_dot import __version__
from fmind_dot.commands import add_group, aliased_command, state_from
from fmind_dot.config import duration_seconds, expand_path
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, Runner
from fmind_dot.state import State

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
_NOTIFY_EVENTS = {
    "stop": ("✅", "Turn finished — waiting for you"),
    "session-end": ("🏁", "Session ended"),
    "needs-input": ("⏳", "Waiting for your input"),
}
_NOTIFY_AGENTS = {
    "agy": "Antigravity",
    "antigravity": "Antigravity",
    "claude": "Claude Code",
    "codex": "Codex",
    "copilot": "Copilot",
    "grok": "Grok Build",
}
_NOTIFY_EXPIRE_MS = "10000"
_PROBE_OUTPUT_LIMIT_BYTES = 64 * 1024
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
    "jules": ("--version",),
    "lefthook": ("version",),
    "mise": ("--version",),
    "nvim": ("--version",),
    "python": ("--version",),
    "ruff": ("--version",),
    "sqlite3": ("--version",),
    "tree-sitter": ("--version",),
    "trivy": ("--version",),
    "ty": ("--version",),
    "uv": ("--version",),
}
_PACKAGE_DIRECTORY = Path(__file__).resolve().parent
_PACKAGE_VERSION = __version__
_INSTALL_RECEIPT_NAME = ".fmind-dot-install.json"
_INSTALL_RECEIPT_SCHEMA = 2


@dataclass(frozen=True)
class Notification:
    summary: str
    headline: str = ""
    details: tuple[str, ...] = ()


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


def _tool(state: State, command: str) -> Path:
    path = state.runner.which(command)
    if path is None:
        raise DotError(f"required tool is not installed: {command}")
    return path


def _interactive(state: State, args: list[str], failure: str) -> None:
    code = state.runner.interactive(args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr)
    if code != 0:
        raise DotError(f"{failure} ({code})")


def _confirm(state: State, message: str) -> bool:
    state.stdout.write(message)
    state.stdout.flush()
    return state.stdin.readline().strip().lower() in {"y", "yes"}


def run_login_github(state: State) -> None:
    _tool(state, "gh")
    host = state.config.login.github_host
    status_result = state.runner.run(["gh", "auth", "status", "--hostname", host], check=False)
    if status_result.returncode == 0 and not _confirm(
        state, f"gh: already authenticated on {host}. Re-authenticate? [y/N]: "
    ):
        typer.echo("Canceled.", file=state.stdout)
        return
    typer.echo(f"gh: requesting OAuth login for {host}...", file=state.stdout)
    scopes = ",".join(state.config.login.github_scopes)
    _interactive(state, ["gh", "auth", "login", "--hostname", host, "--scopes", scopes], "gh login failed")


def run_login_workspace(state: State) -> None:
    _tool(state, "gws")
    scopes = ",".join(state.config.login.workspace_scopes)
    typer.echo(
        f"gws: requesting OAuth login ({len(state.config.login.workspace_scopes)} scopes)...",
        file=state.stdout,
    )
    _interactive(state, ["gws", "auth", "login", "--scopes", scopes], "gws login failed")


def run_login_gcp(state: State) -> None:
    _tool(state, "gcloud")
    typer.echo(
        "gcloud: authenticating user and Application Default Credentials (ADC)...",
        file=state.stdout,
    )
    _interactive(state, ["gcloud", "auth", "login", "--update-adc"], "gcloud login failed")
    typer.echo("gcloud: credentials successfully updated.", file=state.stdout)


def run_setup_workspace(state: State, project_id: str = "") -> None:
    _tool(state, "gws")
    _tool(state, "gcloud")
    selected = project_id or os.environ.get("GWS_PROJECT", "")
    if not selected:
        raise DotError("provide a project ID as an argument or set the GWS_PROJECT environment variable")
    apis = state.config.setup.workspace_apis
    if not apis:
        raise DotError("no Google Workspace APIs configured to enable")
    typer.echo(f"gws: enabling Workspace APIs on project {selected!r}...", file=state.stdout)
    _interactive(
        state,
        ["gcloud", "services", "enable", *apis, "--project", selected, "--quiet"],
        "failed to enable gcloud services",
    )
    typer.echo(f"gws: configuring project {selected!r}...", file=state.stdout)
    _interactive(state, ["gws", "auth", "setup", "--project", selected], "failed to configure gws project")


def _display_path(home: Path, path: Path) -> str:
    try:
        return "~" if path == home else f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def build_notification(
    agent: str,
    event: str,
    cwd: Path | None,
    home: Path,
    getenv: Callable[[str], str | None] = os.environ.get,
) -> Notification:
    if not agent:
        raise DotError("agent name is required")
    try:
        icon, headline = _NOTIFY_EVENTS[event]
    except KeyError as error:
        choices = ", ".join(sorted(_NOTIFY_EVENTS))
        raise DotError(f"unknown agent notify event {event!r} (want one of: {choices})") from error
    label = _NOTIFY_AGENTS.get(agent, agent)
    summary = f"{icon} {label}"
    details: list[str] = []
    if cwd is not None:
        expanded = cwd.expanduser()
        resolved = expanded if expanded.is_absolute() else (Path.cwd() / expanded).absolute()
        summary += f" · {resolved.name}"
        details.append(_display_path(home, resolved))
    if session := getenv("ZELLIJ_SESSION_NAME"):
        location = f"zellij {session}"
        if pane := getenv("ZELLIJ_PANE_ID"):
            location += f" · pane {pane}"
        details.append(location)
    return Notification(summary, headline, tuple(details))


def _notification_body(notification: Notification) -> str:
    return "\n".join((notification.headline, *notification.details)).strip()


def _apple_script_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notification_command(runner: Runner, notification: Notification, *, system: str | None = None) -> list[str]:
    host = (system or platform.system()).lower()
    if host == "darwin":
        details = " · ".join(notification.details)
        if details:
            script = (
                f"display notification {_apple_script_string(details)} "
                f"with title {_apple_script_string(notification.summary)} "
                f"subtitle {_apple_script_string(notification.headline)}"
            )
        else:
            script = (
                f"display notification {_apple_script_string(notification.headline)} "
                f"with title {_apple_script_string(notification.summary)}"
            )
        return ["osascript", "-e", script]
    if host != "linux":
        raise DotError(f"desktop notifications are unsupported on {host}")
    body = _notification_body(notification)
    if runner.which("notify-send") is not None:
        return [
            "notify-send",
            "--app-name=dot",
            f"--expire-time={_NOTIFY_EXPIRE_MS}",
            notification.summary,
            body,
        ]
    if runner.which("gdbus") is not None:
        return [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.freedesktop.Notifications",
            "--object-path",
            "/org/freedesktop/Notifications",
            "--method",
            "org.freedesktop.Notifications.Notify",
            "dot",
            "uint32 0",
            "dialog-information",
            notification.summary,
            body,
            "@as []",
            "@a{sv} {}",
            f"int32 {_NOTIFY_EXPIRE_MS}",
        ]
    raise DotError("install notify-send or gdbus to send desktop notifications")


def read_hook_payload(stream: IO[str] | None) -> dict[str, Any] | None:
    """Decode the common hook envelope and reject ambiguous boolean guards."""
    if stream is None:
        return None
    try:
        if stream.isatty():
            return None
    except AttributeError, OSError:
        pass
    payload = stream.read()
    if not payload.strip():
        return None
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise DotError(f"failed to parse agent hook input: {error}") from error
    if not isinstance(decoded, dict):
        raise DotError("failed to parse agent hook input: expected a JSON object")
    for field in ("stop_hook_active", "stopHookActive", "fullyIdle"):
        if field in decoded and not isinstance(decoded[field], bool):
            raise DotError(f"failed to parse agent hook input: {field} must be a boolean")
    return decoded


def _hook_payload(state: State) -> Mapping[str, Any]:
    return read_hook_payload(state.stdin) or {}


def send_notification(state: State, notification: Notification) -> None:
    host = platform.system().lower()
    if host not in {"darwin", "linux"} or (host == "linux" and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")):
        return
    command = notification_command(state.runner, notification, system=host)
    try:
        state.runner.run(command, timeout=10)
    except (DotError, OSError) as error:
        raise DotError(f"failed to send desktop notification with {command[0]}") from error


def run_notify(state: State, args: list[str]) -> None:
    if not args:
        raise DotError("agent name or notification summary is required")
    if len(args) >= 2 and (args[0] in _NOTIFY_AGENTS or args[1] in _NOTIFY_EVENTS):
        payload = _hook_payload(state)
        if payload.get("stop_hook_active") is True or payload.get("stopHookActive") is True:
            return
        if args[0] in {"agy", "antigravity"} and payload.get("fullyIdle") is not True:
            return
        raw_cwd = payload.get("cwd")
        if not raw_cwd:
            workspaces = payload.get("workspacePaths", [])
            if isinstance(workspaces, list):
                raw_cwd = next((item for item in workspaces if isinstance(item, str) and item), "")
        cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else None
        send_notification(state, build_notification(args[0], args[1], cwd, Path.home()))
        return
    send_notification(
        state,
        Notification(args[0], args[1] if len(args) > 1 else "", tuple(args[2:])),
    )


def _write_validated_fish(state: State, path: Path, content: str, mode: int) -> None:
    if not content.strip():
        raise DotError(f"generated Fish script is empty: {path.name}")
    _tool(state, "fish")
    timeout = duration_seconds(state.config.completions.timeout)
    try:
        state.runner.run(["fish", "--no-config", "--no-execute"], input_text=content, timeout=timeout)
    except (DotError, OSError) as error:
        raise DotError(f"generated Fish script failed syntax validation: {path.name}") from error
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    except OSError as error:
        raise DotError(f"failed to create temporary Fish script: {path.name}") from error
    try:
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            Path(temporary).chmod(mode)
            Path(temporary).replace(path)
        except OSError as error:
            raise DotError(f"failed to publish Fish script: {path.name}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)


def _generate_completion(state: State, tool: str) -> str:
    custom = state.config.completions.custom_commands.get(tool)
    binary = custom.binary if custom and custom.binary else tool
    if state.runner.which(tool) is None:
        raise FileNotFoundError(tool)
    if binary != tool and state.runner.which(binary) is None:
        raise DotError(f"completion generator for {tool} is not installed: {binary}")
    args = custom.args if custom and custom.args else ["completion", "fish"]
    fallback = [tool, "completion", "fish"]
    primary = [binary, *args]
    timeout = duration_seconds(state.config.completions.timeout)
    with tempfile.TemporaryDirectory(prefix="dot-completion-") as directory:
        try:
            result = state.runner.run(primary, cwd=Path(directory), timeout=timeout)
            if not result.stdout.strip():
                raise DotError("completion command returned no output")
        except (DotError, OSError) as primary_error:
            if primary == fallback:
                raise DotError(f"failed to generate completions for {tool}") from primary_error
            try:
                result = state.runner.run(fallback, cwd=Path(directory), timeout=timeout)
            except (DotError, OSError) as fallback_error:
                raise DotError(f"failed to generate completions for {tool}") from fallback_error
            if not result.stdout.strip():
                raise DotError(f"failed to generate completions for {tool}: empty output") from primary_error
    return result.stdout


def run_completion(state: State) -> None:
    directory = expand_path(state.config.completions.path)
    try:
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError("failed to create completions directory") from error
    failures: list[str] = []
    typer.echo(
        f"=> Generating Fish autocompletions for {len(state.config.completions.tools)} tools in {directory}...\n",
        file=state.stdout,
    )
    for tool in state.config.completions.tools:
        try:
            content = _generate_completion(state, tool)
            _write_validated_fish(state, directory / f"{tool}.fish", content, 0o644)
            typer.echo(f"  ✓ Generated completions for {tool}", file=state.stdout)
        except FileNotFoundError:
            typer.echo(f"  ○ {tool} is not installed, skipping", file=state.stdout)
        except DotError as error:
            failures.append(f"{tool}: {error}")
            typer.echo(f"  ✗ Failed to generate completions for {tool}", file=state.stdout)
    try:
        dot_completion = get_completion_script(  # noqa: S604 - Typer renders a static template; no shell is executed.
            prog_name="dot",
            complete_var="_DOT_COMPLETE",
            shell="fish",
        )
        _write_validated_fish(state, directory / "dot.fish", dot_completion, 0o644)
        typer.echo("  ✓ Generated completions for dot", file=state.stdout)
    except (DotError, OSError) as error:
        failures.append(f"dot.fish: {error}")
        typer.echo("  ✗ Failed to generate completions for dot", file=state.stdout)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "fish"
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
            if state.runner.which(tool) is None:
                continue
            try:
                result = state.runner.run([tool, *args], timeout=duration_seconds(state.config.completions.timeout))
                _write_validated_fish(state, cache / filename, result.stdout, 0o600)
                typer.echo(f"  ✓ Generated {filename}", file=state.stdout)
            except (DotError, OSError) as error:
                failures.append(f"{filename}: {error}")
                typer.echo(f"  ✗ Failed to generate {filename}", file=state.stdout)
    if failures:
        raise DotError("completion generation failed: " + "; ".join(failures))
    typer.echo(f"\n✓ Completions updated in {directory}", file=state.stdout)


def _environment_results(state: State) -> list[CheckResult]:
    results = [
        CheckResult(name, "pass", "set") if os.environ.get(name) else CheckResult(name, "fail", "MISSING (required)")
        for name in state.config.verify.env_vars.required
    ]
    results.extend(
        CheckResult(name, "pass", "set") if os.environ.get(name) else CheckResult(name, "warn", "unset (optional)")
        for name in state.config.verify.env_vars.optional
    )
    return results


def _secret_results(state: State, *, fix: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    for secret in state.config.verify.secrets:
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
    timeout = duration_seconds(state.config.verify.probe_timeout)

    def probe(tool: str) -> CheckResult:
        path = state.runner.which(tool)
        if path is None:
            return CheckResult(tool, "fail", "command not found", condition="missing")
        args = _TOOL_PROBE_ARGS.get(tool, ("--version",))
        try:
            result = state.runner.run_bounded(
                [str(path), *args],
                max_output_bytes=_PROBE_OUTPUT_LIMIT_BYTES,
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

    tools = state.config.verify.tools
    if not tools:
        return []
    workers = min(state.config.verify.probe_concurrency, len(tools))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(probe, tools))


def _recognized_auth_failure(result: CommandResult) -> bool:
    diagnostic = f"{result.stdout}\n{result.stderr}".lower()
    return any(marker in diagnostic for marker in _AUTH_FAILURE_MARKERS)


def _auth_results(state: State) -> list[CheckResult]:
    results: list[CheckResult] = []
    timeout = duration_seconds(state.config.verify.probe_timeout)
    probes = dict(_AUTH_PROBES)
    if os.environ.get("JULES_API_KEY"):
        probes["jules"] = (["jules", "remote", "list", "--repo"], False)
    for label, (command, requires_output) in probes.items():
        path = state.runner.which(command[0])
        if path is None:
            results.append(CheckResult(label, "skip", f"{command[0]} not installed", condition="skipped"))
            continue
        try:
            result = state.runner.run_bounded(
                command,
                max_output_bytes=_PROBE_OUTPUT_LIMIT_BYTES,
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
    if "jules" not in probes:
        results.append(
            CheckResult(
                "jules",
                "skip",
                "JULES_API_KEY not set (see Environment Variables)",
                condition="skipped",
            )
        )
    return results


def _docker_results(state: State) -> list[CheckResult]:
    path = state.runner.which("docker")
    if path is None:
        return [CheckResult("docker", "fail", "not installed")]
    try:
        result = state.runner.run_bounded(
            ["docker", "info"],
            max_output_bytes=_PROBE_OUTPUT_LIMIT_BYTES,
            timeout=duration_seconds(state.config.verify.probe_timeout),
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


def _package_digest(directory: Path) -> str:
    files = sorted(path for path in directory.rglob("*.py") if path.is_file())
    if not files:
        raise FileNotFoundError(directory)
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(directory).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _install_basis_digest(source: Path) -> str:
    package = source / "dot/src/fmind_dot"
    project = source / "dot/pyproject.toml"
    lock = source / "dot/uv.lock"
    digest = hashlib.sha256()
    for name, content in (
        ("package", _package_digest(package).encode()),
        ("pyproject", project.read_bytes()),
        ("lock", lock.read_bytes()),
    ):
        encoded_name = name.encode()
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _install_receipt(source: Path, wheel_sha256: str, basis_sha256: str) -> dict[str, str | int]:
    resolved = source.expanduser().resolve(strict=True)
    return {
        "schema_version": _INSTALL_RECEIPT_SCHEMA,
        "source_root": str(resolved),
        "basis_sha256": basis_sha256,
        "installed_version": _PACKAGE_VERSION,
        "wheel_sha256": wheel_sha256,
    }


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def write_install_receipt(source_root: Path, wheel_sha256: str, expected_basis_sha256: str) -> Path:
    """Atomically attest the exact checkout basis used to deploy this package."""
    if not _PACKAGE_DIRECTORY.is_dir() or _PACKAGE_DIRECTORY.is_symlink():
        raise DotError("installed package directory must be a real directory")
    source = source_root.expanduser().resolve(strict=True)
    if not _is_sha256(expected_basis_sha256):
        raise DotError("source basis digest must be a lowercase SHA-256")
    if _install_basis_digest(source) != expected_basis_sha256:
        raise DotError("source changed during deployment")
    if _package_digest(source / "dot/src/fmind_dot") != _package_digest(_PACKAGE_DIRECTORY):
        raise DotError("installed Python package differs from source")
    project = source / "dot/pyproject.toml"
    with project.open("rb") as stream:
        metadata = tomllib.load(stream).get("project", {})
    if metadata.get("name") != "fmind-dot":
        raise DotError("source project name is not fmind-dot")
    if metadata.get("version") != _PACKAGE_VERSION:
        raise DotError("installed version differs from source project")
    if not _is_sha256(wheel_sha256):
        raise DotError("wheel digest must be a lowercase SHA-256")
    # Recheck after reading package and project metadata, then record the pre-export basis verbatim.
    if _install_basis_digest(source) != expected_basis_sha256:
        raise DotError("source changed during deployment")
    payload = _install_receipt(source, wheel_sha256, expected_basis_sha256)
    target = _PACKAGE_DIRECTORY / _INSTALL_RECEIPT_NAME
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{_INSTALL_RECEIPT_NAME}.", dir=_PACKAGE_DIRECTORY)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


def _install_receipt_matches(source: Path) -> bool:
    receipt = _PACKAGE_DIRECTORY / _INSTALL_RECEIPT_NAME
    try:
        info = receipt.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            return False
        decoded = json.loads(receipt.read_text(encoding="utf-8"))
        wheel_sha256 = decoded.get("wheel_sha256") if isinstance(decoded, dict) else None
        return (
            isinstance(wheel_sha256, str)
            and _is_sha256(wheel_sha256)
            and decoded == _install_receipt(source, wheel_sha256, _install_basis_digest(source))
        )
    except OSError, RuntimeError, ValueError:
        return False


def _source_version(project: Path) -> str:
    with project.open("rb") as stream:
        parsed = tomllib.load(stream)
    value = parsed.get("project", {}).get("version")
    return value if isinstance(value, str) else ""


def _install_results(state: State) -> list[CheckResult]:
    name = "dot"
    chezmoi = state.runner.which("chezmoi")
    if chezmoi is None:
        return [CheckResult(name, "skip", "chezmoi not installed", condition="skipped")]
    try:
        source_result = state.runner.run_bounded(
            ["chezmoi", "source-path"],
            max_output_bytes=_PROBE_OUTPUT_LIMIT_BYTES,
            timeout=duration_seconds(state.config.verify.probe_timeout),
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
    try:
        version = _source_version(project)
        source_digest = _package_digest(source_package)
        installed_digest = _package_digest(_PACKAGE_DIRECTORY)
    except OSError, tomllib.TOMLDecodeError:
        return [CheckResult(name, "fail", "could not verify installed Python package", condition="broken")]
    installed_path = str(_PACKAGE_DIRECTORY)
    if not version or version != _PACKAGE_VERSION:
        return [CheckResult(name, "fail", "STALE: installed version differs from source", installed_path, "stale")]
    if source_digest != installed_digest:
        return [
            CheckResult(name, "fail", "STALE: installed Python package differs from source", installed_path, "stale")
        ]
    if not _install_receipt_matches(source):
        return [CheckResult(name, "fail", "STALE: install receipt differs from source", installed_path, "stale")]
    return [CheckResult(name, "pass", "installed Python package matches source", installed_path, "healthy")]


def run_verify(state: State, *, fix: bool) -> dict[str, Any]:
    sections = {
        "env_vars": _environment_results(state),
        "auth": _auth_results(state),
        "secrets": _secret_results(state, fix=fix),
        "docker": _docker_results(state),
        "tools": _tool_results(state),
        "install": _install_results(state),
    }
    passed = all(item.status != "fail" for items in sections.values() for item in items)
    return {key: [_check_result_payload(item) for item in items] for key, items in sections.items()} | {
        "passed": passed
    }


def _print_verify(state: State, results: Mapping[str, Any]) -> None:
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
                f"  {icons[item['status']]} {item['name']:<20} {item['details']}",
                file=state.stdout,
            )


def register(app: typer.Typer) -> None:
    login_app = typer.Typer(
        help="Authentication wrappers for external service CLI tools",
        context_settings=_CONTEXT_SETTINGS,
    )
    setup_app = typer.Typer(
        help="Setup wrappers for external services and environments",
        context_settings=_CONTEXT_SETTINGS,
    )

    @aliased_command(login_app, "github", "g", help_text="Interactive OAuth login via gh")
    def login_github(context: typer.Context) -> None:
        run_login_github(state_from(context))

    @aliased_command(login_app, "workspace", "w", help_text="Interactive OAuth login via gws")
    def login_workspace(context: typer.Context) -> None:
        run_login_workspace(state_from(context))

    @aliased_command(login_app, "gcp", "c", help_text="Authenticate gcloud and ADC")
    def login_gcp(context: typer.Context) -> None:
        run_login_gcp(state_from(context))

    @aliased_command(setup_app, "workspace", "w", help_text="Configure Workspace APIs for a GCP project")
    def setup_workspace(
        context: typer.Context,
        project_id: Annotated[str, typer.Argument(help="GCP project ID")] = "",
    ) -> None:
        run_setup_workspace(state_from(context), project_id)

    @aliased_command(app, "completion", "g", help_text="Generate Fish completions for installed CLI tools")
    def completion(context: typer.Context) -> None:
        run_completion(state_from(context))

    @aliased_command(app, "notify", "n", help_text="Send an OS-independent desktop notification")
    def notify(
        context: typer.Context,
        args: Annotated[list[str] | None, typer.Argument(help="Agent/event or notification fields")] = None,
    ) -> None:
        run_notify(state_from(context), args or [])

    @aliased_command(app, "verify", "v", help_text="Run environment, authentication, service, and tool checks")
    def verify(
        context: typer.Context,
        json_output: Annotated[bool, typer.Option("--json", "-j")] = False,
        fix: Annotated[bool, typer.Option("--fix", "-f")] = False,
    ) -> None:
        state = state_from(context)
        results = run_verify(state, fix=fix)
        if json_output:
            typer.echo(json.dumps(results, indent=2), file=state.stdout)
        else:
            _print_verify(state, results)
            message = "✓ Verification passed." if results["passed"] else "✗ Verification failed."
            typer.echo(f"\n{message}", file=state.stdout)
        if not results["passed"]:
            raise typer.Exit(1)

    add_group(app, login_app, "login", "l")
    add_group(app, setup_app, "setup", "u")
