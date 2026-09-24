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
    "copilot": DoctorIntegration("copilot", "~/.copilot/hooks/notify.json", "json", ("stop",)),
}


@dataclass(frozen=True)
class AgentDoctorResult:
    agent: str
    hooks: str
    source: str
    last_sync: str
    sync_failures: int
    sync_retained: int
    archive: str
    sessions: int
    healthy: bool
    next: str = ""


def _command_hooks(config: Mapping[str, object], agent: str) -> Iterator[tuple[str, tuple[str, ...]]]:
    """Read executable command fields from native event structures, never arbitrary metadata."""
    events = config.get("notify" if agent == "agy" else "hooks")
    if not isinstance(events, Mapping):
        return
    for event, groups in events.items():
        if not isinstance(event, str) or not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, Mapping):
                continue
            handlers = [group] if agent in {"agy", "copilot"} else group.get("hooks")
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, Mapping) or handler.get("type") != "command":
                    continue
                command = handler.get("bash" if agent == "copilot" else "command")
                if isinstance(command, str) and (arguments := _dot_arguments(command)):
                    yield event, arguments


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
    if not isinstance(config, dict):
        return "malformed"
    if definition.agent == "claude" and config.get("disableAllHooks") is True:
        return "disabled"
    if definition.agent == "codex":
        features = config.get("features", {})
        if not isinstance(features, dict):
            return "malformed"
        if features.get("hooks", features.get("codex_hooks")) is False:
            return "disabled"
    configured = set(_command_hooks(config, definition.agent))
    if any(arguments[: len(retired)] == retired for _, arguments in configured for retired in _RETIRED_HOOKS):
        return "retired-capture-hook"
    stop_event = "agentStop" if definition.agent == "copilot" else "Stop"
    missing = [
        event
        for event in definition.notify_events
        if (
            "Notification" if event == "needs-input" else stop_event,
            ("agent", "hook", "notify", definition.agent, event),
        )
        not in configured
    ]
    return f"missing:{','.join(missing)}" if missing else "configured"


def _count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _check_sync(state: State, root: Path, agent: str) -> tuple[str, str, int, int]:
    """Return source presence, last complete sync time, and its failure and retained counts."""
    source = "present" if source_root(state, agent).exists() else "missing"
    try:
        document = json.loads((root / agent / SYNC_STATE_NAME).read_bytes())
    except FileNotFoundError:
        return source, "never", 0, 0
    except OSError, ValueError:
        return source, "unreadable", 0, 0
    if not isinstance(document, dict) or document.get("schema") != SYNC_STATE_SCHEMA:
        return source, "unreadable", 0, 0
    synced_at, failed = document.get("synced_at"), _count(document.get("failed"))
    # States written before the retained count existed report none.
    retained = _count(document.get("retained", 0))
    if not isinstance(synced_at, str) or failed is None or retained is None:
        return source, "unreadable", 0, 0
    return source, synced_at, failed, retained


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
        source, last_sync, failures, retained = _check_sync(state, root, name)
        archive, sessions = _check_archive(root, name)
        synced = last_sync not in {"never", "unreadable"} or source == "missing"
        if hooks == "disabled":
            setting = "disableAllHooks" if name == "claude" else "features.hooks / features.codex_hooks"
            hint = f"review {setting} in the chezmoi source for {definition.config_path}"
        elif hooks != "configured":
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
                sync_retained=retained,
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
                f"sync_retained={result.sync_retained} archive={result.archive} sessions={result.sessions}\n"
            )
            if result.next:
                state.stdout.write(f"  next: {result.next}\n")
            if result.sync_retained:
                # Informational: truncated sources are retained by design; a measurement that
                # a new parse would lose points at a parser gap. Sync names each session.
                state.stdout.write(
                    f"  note: {result.sync_retained} session(s) kept their archived copy; "
                    f"dot agent session sync --agent {result.agent} lists them\n"
                )
    if not all(result.healthy for result in results):
        raise DotError("agent doctor found unhealthy integrations")
    return results
