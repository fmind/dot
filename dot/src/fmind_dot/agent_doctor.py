"""Read-only agent checks: notify hooks, last sync state, and archive readability; nothing is captured or rewritten."""

import json
import shlex
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from fmind_dot.archive.parsers import AGENT_ADAPTERS
from fmind_dot.archive.store import BUNDLE_SUFFIX, ensure_session_store, read_session_manifest
from fmind_dot.archive.sync import SYNC_STATE_NAME, SYNC_STATE_SCHEMA, source_root
from fmind_dot.config import expand_path
from fmind_dot.diagnostics import diagnostic_report
from fmind_dot.errors import DotError
from fmind_dot.state import State

_CLI_NAME = "dot"
# Session capture moved to `dot agent session sync`; these hooks now fail on every event.
_RETIRED_HOOKS = (("agent", "hook", "session"), ("agent", "hook", "copilot-session-end"))


@dataclass(frozen=True)
class DoctorIntegration:
    agent: str
    config_path: str
    config_format: str
    notify_events: tuple[str, ...]


_DOCTOR_INTEGRATIONS = {
    "agy": DoctorIntegration("agy", "~/.gemini/config/hooks.json", "json", ("stop",)),
    "claude": DoctorIntegration("claude", "~/.claude/settings.json", "json", ("needs-input", "stop")),
    "codex": DoctorIntegration("codex", "~/.codex/config.toml", "toml", ("stop",)),
    "grok": DoctorIntegration("grok", "~/.grok/hooks/hooks.json", "json", ("needs-input", "stop")),
    "copilot": DoctorIntegration("copilot", "~/.copilot/hooks/session-log.json", "json", ("stop",)),
}


@dataclass(frozen=True)
class AgentDoctorResult:
    agent: str
    hooks: str
    source: str
    last_sync: str
    sync_failures: int
    archive: str
    sessions: int
    healthy: bool
    next: str = ""


def _structured_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _structured_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _structured_strings(item)


def _dot_arguments(command: str) -> tuple[str, ...] | None:
    """Return the arguments of a `dot` invocation, by bare name or absolute path."""
    try:
        fields = shlex.split(command)
    except ValueError:
        return None
    if not fields or not (
        fields[0] == _CLI_NAME or (Path(fields[0]).is_absolute() and Path(fields[0]).name == _CLI_NAME)
    ):
        return None
    return tuple(fields[1:])


def _check_hooks(definition: DoctorIntegration) -> str:
    path = expand_path(definition.config_path)
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unreadable"
    try:
        config = json.loads(content) if definition.config_format == "json" else tomllib.loads(content.decode())
    except UnicodeError, ValueError, tomllib.TOMLDecodeError:
        return "malformed"
    configured = {arguments for value in _structured_strings(config) if (arguments := _dot_arguments(value))}
    if any(arguments[: len(retired)] == retired for arguments in configured for retired in _RETIRED_HOOKS):
        return "retired-capture-hook"
    missing = [
        event
        for event in definition.notify_events
        if ("agent", "hook", "notify", definition.agent, event) not in configured
    ]
    return f"missing:{','.join(missing)}" if missing else "configured"


def _check_sync(state: State, root: Path, agent: str) -> tuple[str, str, int]:
    """Return source presence, last complete sync time, and its failure count."""
    source = "present" if source_root(state, agent).exists() else "missing"
    try:
        document = json.loads((root / agent / SYNC_STATE_NAME).read_bytes())
    except FileNotFoundError:
        return source, "never", 0
    except OSError, ValueError:
        return source, "unreadable", 0
    if not isinstance(document, dict) or document.get("schema") != SYNC_STATE_SCHEMA:
        return source, "unreadable", 0
    synced_at, failed = document.get("synced_at"), document.get("failed")
    if not isinstance(synced_at, str) or isinstance(failed, bool) or not isinstance(failed, int):
        return source, "unreadable", 0
    return source, synced_at, failed


def _check_archive(root: Path, agent: str) -> tuple[str, int]:
    directory = root / agent
    if not directory.is_dir():
        return "empty", 0
    sessions = unreadable = 0
    for path in directory.glob(f"*{BUNDLE_SUFFIX}"):
        try:
            read_session_manifest(path)
        except OSError, ValueError:
            unreadable += 1
        else:
            sessions += 1
    return (f"unreadable:{unreadable}" if unreadable else "readable"), sessions


def gather_agent_doctor(state: State, *, agent: str = "") -> list[AgentDoctorResult]:
    if agent and agent not in _DOCTOR_INTEGRATIONS:
        raise DotError(f"unknown agent {agent!r}; choose one of {', '.join(_DOCTOR_INTEGRATIONS)}")
    root = ensure_session_store()
    results: list[AgentDoctorResult] = []
    for name in AGENT_ADAPTERS:
        if agent and name != agent:
            continue
        definition = _DOCTOR_INTEGRATIONS[name]
        hooks = _check_hooks(definition)
        source, last_sync, failures = _check_sync(state, root, name)
        archive, sessions = _check_archive(root, name)
        synced = last_sync not in {"never", "unreadable"} or source == "missing"
        if hooks != "configured":
            hint = f"chezmoi diff {definition.config_path}, then chezmoi apply --force {definition.config_path}"
        elif archive not in {"readable", "empty"}:
            hint = f"inspect the unreadable bundles under ~/.agents/sessions/v3/{name}"
        elif not synced or failures:
            hint = f"dot agent session sync --agent {name}"
        else:
            hint = ""
        results.append(
            AgentDoctorResult(
                agent=name,
                hooks=hooks,
                source=source,
                last_sync=last_sync,
                sync_failures=failures,
                archive=archive,
                sessions=sessions,
                healthy=not hint,
                next=hint,
            )
        )
    return results


def run_agent_doctor(state: State, *, as_json: bool = False, agent: str = "") -> list[AgentDoctorResult]:
    results = gather_agent_doctor(state, agent=agent)
    if as_json:
        checks = [
            {"name": result.agent, "status": "pass" if result.healthy else "fail", "details": asdict(result)}
            for result in results
        ]
        json.dump(diagnostic_report("agents", checks), state.stdout, ensure_ascii=False, indent=2)
        state.stdout.write("\n")
    else:
        state.stdout.write("Agent doctor\n")
        for result in results:
            mark = "✓" if result.healthy else "✗"
            state.stdout.write(
                f"{mark} {result.agent}: hooks={result.hooks} source={result.source} "
                f"last_sync={result.last_sync} sync_failures={result.sync_failures} "
                f"archive={result.archive} sessions={result.sessions}\n"
            )
            if result.next:
                state.stdout.write(f"  next: {result.next}\n")
    if not all(result.healthy for result in results):
        raise DotError("agent doctor found unhealthy integrations")
    return results
