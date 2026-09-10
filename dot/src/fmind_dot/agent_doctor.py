"""Read-only agent integration and archive diagnostics."""

import errno
import hashlib
import json
import os
import platform
import shlex
import sqlite3
import stat
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import closing
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import islice
from pathlib import Path
from urllib.parse import quote

import yaml

from fmind_dot.archive.parsers import (
    AGENT_ADAPTERS,
    AGY_TRANSCRIPT_NAMES,
    GROK_TRANSCRIPT_NAME,
    claude_session_id,
    codex_session_id,
)
from fmind_dot.archive.store import (
    SESSION_STORE_VERSION,
    SUPPORTED_PARSER_VERSIONS,
    SUPPORTED_SCHEMA_VERSIONS,
    SessionManifest,
    fingerprint_bytes,
    fingerprint_json,
    is_valid_session_id,
    read_session_manifest,
    session_digest,
    session_lineage_id,
    stored_generation,
    validate_session_generation,
)
from fmind_dot.config import expand_path
from fmind_dot.diagnostics import diagnostic_report
from fmind_dot.errors import DotError
from fmind_dot.private_files import _DIRECTORY_FLAGS
from fmind_dot.state import State

_SHARED_PERSONA = "~/.agents/AGENTS.md"


_SHARED_SKILLS = "~/.agents/skills"


@dataclass(frozen=True)
class DoctorIntegration:
    agent: str
    persona_path: str
    skills_path: str = ""
    skills_config: str = ""
    hook_path: str = ""
    hook_commands: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    hook_format: str = ""
    notifications: bool = False
    discovery_only: bool = False
    source_time_query: str = ""


_DOCTOR_INTEGRATIONS = (
    DoctorIntegration(
        "opencode",
        _SHARED_PERSONA,
        skills_config="~/.config/opencode/opencode.json",
        tools=("dot", "opencode"),
        discovery_only=True,
    ),
    DoctorIntegration(
        "agy",
        "~/.gemini/GEMINI.md",
        skills_path="~/.gemini/config/skills",
        hook_path="~/.gemini/config/hooks.json",
        hook_commands=(
            "dot agent hook session agy",
            "dot agent hook notify agy stop",
        ),
        tools=("dot", "agy"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "claude",
        "~/.claude/CLAUDE.md",
        skills_path="~/.claude/skills",
        hook_path="~/.claude/settings.json",
        hook_commands=(
            "dot agent hook session claude",
            "dot agent hook notify claude stop",
        ),
        tools=("dot", "claude"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "codex",
        "~/.codex/AGENTS.md",
        hook_path="~/.codex/config.toml",
        hook_commands=(
            "dot agent hook session codex",
            "dot agent hook notify codex stop",
        ),
        tools=("dot", "codex"),
        hook_format="toml",
        notifications=True,
    ),
    DoctorIntegration(
        "grok",
        "~/.grok/AGENTS.md",
        skills_path="~/.grok/skills",
        hook_path="~/.grok/hooks/hooks.json",
        hook_commands=(
            "dot agent hook session grok",
            "dot agent hook notify grok stop",
        ),
        tools=("dot", "grok"),
        hook_format="json",
        notifications=True,
    ),
    DoctorIntegration(
        "copilot",
        "~/.copilot/copilot-instructions.md",
        hook_path="~/.copilot/hooks/session-log.json",
        hook_commands=("dot agent hook copilot-session-end",),
        tools=("dot", "copilot"),
        hook_format="json",
        source_time_query="SELECT strftime('%Y-%m-%dT%H:%M:%SZ', MAX(updated_at)) AS at FROM sessions",
    ),
)


@dataclass(frozen=True)
class AgentDoctorResult:
    agent: str
    discovery: str
    hooks: str
    tools: str
    source: str
    last_ingestion: str
    last_failure: str
    archive_lag: str
    truncated: bool
    healthy: bool
    issue_counts: dict[str, int] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)
    repair: str = ""


@dataclass(frozen=True)
class _SourceInspection:
    status: str
    latest: datetime | None
    present: bool
    healthy: bool
    truncated: bool = False
    issue_counts: dict[str, int] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class _SkillInspection:
    status: str
    issue_counts: dict[str, int] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)
    truncated: bool = False

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"


@dataclass
class _LineageSummary:
    last_complete: datetime | None = None
    latest: datetime | None = None
    latest_partial: bool = False
    unreadable: bool = False
    truncated: bool = False


def _same_resolved_path(path: Path, target: Path) -> bool:
    try:
        return path.resolve(strict=True) == target.resolve(strict=True)
    except OSError:
        return False


def _structured_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _structured_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _structured_strings(item)


def _load_configuration(path: Path, format_name: str) -> object:
    content = path.read_bytes()
    if format_name == "json":
        return json.loads(content)
    if format_name == "toml":
        return tomllib.loads(content.decode())
    if format_name == "yaml":
        return yaml.safe_load(content)
    raise ValueError(f"unsupported configuration format {format_name!r}")


def _check_discovery(definition: DoctorIntegration) -> tuple[str, bool]:
    canonical_persona = expand_path(_SHARED_PERSONA)
    canonical_skills = expand_path(_SHARED_SKILLS)
    if not _same_resolved_path(expand_path(definition.persona_path), canonical_persona):
        return "persona-broken", False
    if not canonical_skills.is_dir():
        return "skills-missing", False
    if definition.skills_path and not _same_resolved_path(expand_path(definition.skills_path), canonical_skills):
        return "skills-broken", False
    if definition.skills_config:
        try:
            config = _load_configuration(
                expand_path(definition.skills_config), "json" if definition.agent == "opencode" else "yaml"
            )
        except OSError, UnicodeError, ValueError, yaml.YAMLError:
            return "skills-broken", False
        strings = set(_structured_strings(config))
        if not {_SHARED_SKILLS, str(expand_path(_SHARED_SKILLS))}.intersection(strings):
            return "skills-broken", False
        if definition.agent == "opencode" and not {_SHARED_PERSONA, str(expand_path(_SHARED_PERSONA))}.intersection(
            strings
        ):
            return "persona-broken", False
    return "healthy", True


def _inspect_skill_catalog(state: State) -> _SkillInspection:
    """Inspect bounded filesystem metadata, never skill instructions or resources."""
    catalog = expand_path(_SHARED_SKILLS)
    limit = state.config.agent.doctor.scan_limit
    issues: dict[str, int] = {}
    examples: list[dict[str, str]] = []

    def issue(reason: str, name: str = "") -> None:
        issues[reason] = issues.get(reason, 0) + 1
        if name and len(examples) < state.config.agent.doctor.example_limit:
            examples.append({"reason": reason, "skill": name})

    try:
        if catalog.is_symlink() or not catalog.is_dir():
            return _SkillInspection("skills-missing", {"skill-catalog-not-directory": 1})
        entries = list(islice(catalog.iterdir(), limit + 1))
        if len(entries) > limit:
            return _SkillInspection("skills-truncated", {"skill-scan-limit": 1}, truncated=True)
        installed = {path.name: path for path in entries}
        for path in sorted(entries):
            if path.name.startswith("."):
                continue
            if path.is_symlink() and not path.is_dir():
                issue("skill-broken-link", path.name)
            elif path.is_dir() and not (path / "SKILL.md").is_file():
                issue("skill-missing-entrypoint", path.name)

        # Chezmoi owns the expected links. Other installed packages need no registry.
        if state.runner.which("chezmoi") is not None:
            result = state.runner.run_bounded(
                ["chezmoi", "source-path"],
                max_output_bytes=16 * 1024,
                timeout=state.config.doctor.probe_timeout_seconds,
            )
            source_text = result.stdout.strip()
            if result.output_truncated or not source_text or len(source_text.splitlines()) != 1:
                raise ValueError("could not resolve chezmoi source")
            source = Path(source_text)
            if not source.is_absolute():
                raise ValueError("chezmoi source must be absolute")
            declarations = source / "dot_agents/skills"
            if declarations.is_dir():
                expected = list(islice(declarations.iterdir(), limit + 1))
                if len(expected) > limit:
                    return _SkillInspection("skills-truncated", {"skill-scan-limit": 1}, truncated=True)
                for declaration in sorted(expected):
                    if not declaration.name.startswith("symlink_") or not declaration.name.endswith(".tmpl"):
                        continue
                    name = declaration.name.removeprefix("symlink_").removesuffix(".tmpl")
                    path = installed.get(name)
                    if path is None:
                        issue("skill-missing-link", name)
                    elif not path.is_symlink() or path.readlink() != source / "skills" / name:
                        issue("skill-link-conflict", name)
    except DotError, OSError, ValueError:
        issue("skill-inventory-unavailable")
        return _SkillInspection("skills-unreadable", issues, examples)
    return _SkillInspection("skills-broken" if issues else "healthy", issues, examples)


def _command_arguments(command: str) -> tuple[str, ...]:
    fields = shlex.split(command)
    if len(fields) < 2 or fields[0] != "dot":
        return ()
    agents = set(AGENT_ADAPTERS)
    for index, argument in enumerate(fields[1:]):
        if argument.startswith("-") or argument in agents:
            return tuple(fields[1 : index + 1])
    return tuple(fields[1:])


def _dot_command_prober(state: State):
    binary = state.runner.which("dot")
    cache: dict[tuple[str, ...], bool] = {}

    def runnable(arguments: tuple[str, ...]) -> bool:
        if not arguments:
            return True
        if binary is None:
            return False
        if arguments not in cache:
            try:
                result = state.runner.run([str(binary), *arguments, "--help"], check=False)
            except OSError, DotError:
                cache[arguments] = False
            else:
                cache[arguments] = result.returncode == 0
        return cache[arguments]

    return runnable


def _check_hooks(definition: DoctorIntegration, runnable) -> tuple[str, bool]:
    if not definition.hook_path:
        return "sync-only", True
    try:
        config = _load_configuration(expand_path(definition.hook_path), definition.hook_format)
    except OSError, UnicodeError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError:
        return "malformed", False
    if definition.agent == "copilot" and (not isinstance(config, dict) or config.get("version") != 1):
        return "unsupported-version", False
    commands = set(_structured_strings(config))
    for command in definition.hook_commands:
        if command not in commands:
            return "command-mismatch", False
        if not runnable(_command_arguments(command)):
            return "command-unavailable", False
    return "healthy", True


def _notifier_available(state: State) -> bool:
    if platform.system() == "Darwin":
        return state.runner.which("osascript") is not None
    if platform.system() == "Linux":
        return any(state.runner.which(command) is not None for command in ("notify-send", "gdbus"))
    return False


def _check_tools(state: State, definition: DoctorIntegration) -> tuple[str, bool]:
    missing = sorted(f"{name}:missing" for name in definition.tools if state.runner.which(name) is None)
    return (",".join(missing), False) if missing else ("healthy", True)


def _raw_session_identity(root: Path, path: Path, agent: str) -> str:
    if agent in {"claude", "codex"} and path.suffix != ".jsonl":
        return ""
    if agent == "claude":
        identity = claude_session_id(path)
    elif agent == "codex":
        identity = codex_session_id(path)
    elif agent == "grok":
        identity = path.parent.name if path.name in {GROK_TRANSCRIPT_NAME, "signals.json"} else ""
    elif agent == "agy":
        try:
            relative = path.relative_to(root)
        except ValueError:
            return ""
        identity = relative.parts[0] if len(relative.parts) >= 2 and path.name in AGY_TRANSCRIPT_NAMES else ""
    else:
        return ""
    return identity if is_valid_session_id(identity) else ""


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(UTC)


def _query_database_source_time(path: Path, definition: DoctorIntegration) -> datetime | None:
    if not definition.source_time_query:
        raise ValueError("database source has no timestamp query")
    uri = f"file:{quote(str(path))}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        row = connection.execute(definition.source_time_query).fetchone()
    if row is None or row[0] is None or row[0] == "":
        return None
    return _parse_timestamp(str(row[0]))


def _database_source_time(path: Path, definition: DoctorIntegration, fallback: datetime) -> datetime | None:
    """Retain the legacy conservative fallback for callers outside doctor health."""
    try:
        return _query_database_source_time(path, definition)
    except OSError, ValueError, sqlite3.Error:
        return fallback


def _source_file_metadata(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns, info.st_size


def _source_fingerprint_at(directory_fd: int, name: str, expected: os.stat_result) -> str:
    """Hash one stable regular-file snapshot through its already-open parent."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or _source_file_metadata(before) != _source_file_metadata(expected):
            raise OSError(errno.ESTALE, "session source changed before inspection", name)
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        snapshot = _source_file_metadata(expected)
        if _source_file_metadata(after) != snapshot or _source_file_metadata(current) != snapshot:
            raise OSError(errno.ESTALE, "session source changed during inspection", name)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _grok_source_fingerprint_at(directory_fd: int) -> str:
    """Bind both provider files to stable descriptor snapshots for reconciliation."""
    snapshots: dict[str, os.stat_result | None] = {}
    for name in (GROK_TRANSCRIPT_NAME, "signals.json"):
        try:
            snapshots[name] = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            snapshots[name] = None
    fingerprints = {
        name: _source_fingerprint_at(directory_fd, name, info) if info is not None else None
        for name, info in snapshots.items()
    }
    for name, before in snapshots.items():
        try:
            after = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            after = None
        if (before is None) != (after is None) or (
            before is not None and after is not None and _source_file_metadata(before) != _source_file_metadata(after)
        ):
            raise OSError(errno.ESTALE, "session source changed during inspection", name)
    return fingerprint_json(
        {
            "transcript": fingerprints[GROK_TRANSCRIPT_NAME] or fingerprint_bytes(b""),
            "signals": fingerprints["signals.json"],
        }
    )


def _inspect_source(state: State, definition: DoctorIntegration, *, deep: bool = False) -> _SourceInspection:
    if definition.discovery_only:
        return _SourceInspection("archive-not-supported", None, False, True)
    source_text = state.config.agent.sources.get(definition.agent, "")
    if not source_text:
        return _SourceInspection("unconfigured", None, False, False)
    root = expand_path(source_text)
    try:
        info = root.lstat()
    except FileNotFoundError:
        return _SourceInspection("missing", None, False, True)
    except OSError:
        return _SourceInspection("unreadable", None, False, False)
    if stat.S_ISLNK(info.st_mode):
        return _SourceInspection("linked", None, False, False)
    if definition.source_time_query:
        if not stat.S_ISREG(info.st_mode):
            return _SourceInspection("wrong-kind", None, True, False)
        if not deep:
            return _SourceInspection("present", datetime.fromtimestamp(info.st_mtime, UTC), True, True)
        try:
            latest = _query_database_source_time(root, definition)
        except OSError, ValueError, sqlite3.Error:
            return _SourceInspection("unreadable", None, True, False)
        return _SourceInspection("present", latest, True, True)
    if definition.discovery_only:
        return _SourceInspection(
            "present", datetime.fromtimestamp(info.st_mtime, UTC), True, stat.S_ISREG(info.st_mode)
        )
    if not stat.S_ISDIR(info.st_mode):
        return _SourceInspection("wrong-kind", None, True, False)

    seen = 0
    latest: datetime | None = None
    failed = False
    reconciled = True
    limit = state.config.agent.doctor.scan_limit
    issues: dict[str, int] = {}
    examples: list[dict[str, str]] = []

    def issue(reason: str, identity: str = "") -> None:
        issues[reason] = issues.get(reason, 0) + 1
        if len(examples) < state.config.agent.doctor.example_limit:
            examples.append({"reason": reason, "session": identity})

    def onerror(_error: OSError) -> None:
        nonlocal failed
        failed = True

    try:
        root_fd = os.open(root, _DIRECTORY_FLAGS)
    except OSError:
        return _SourceInspection("unreadable", None, True, False)
    try:
        opened_root = os.fstat(root_fd)
        if (opened_root.st_dev, opened_root.st_ino) != (info.st_dev, info.st_ino):
            return _SourceInspection("unreadable", None, True, False)
        for walk_root, directories, files, directory_fd in os.fwalk(
            ".", topdown=True, onerror=onerror, follow_symlinks=False, dir_fd=root_fd
        ):
            relative = Path(walk_root)
            current_path = root if relative == Path() else root / relative
            kept_directories: list[str] = []
            for name in sorted(directories):
                try:
                    directory_info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError:
                    failed = True
                    continue
                if stat.S_ISDIR(directory_info.st_mode):
                    kept_directories.append(name)
            directories[:] = kept_directories
            for name in sorted(files):
                path = current_path / name
                try:
                    entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError:
                    failed = True
                    continue
                if not stat.S_ISREG(entry.st_mode):
                    continue
                if definition.agent == "agy" and name == AGY_TRANSCRIPT_NAMES[1] and AGY_TRANSCRIPT_NAMES[0] in files:
                    continue
                if definition.agent == "grok" and name == "signals.json" and GROK_TRANSCRIPT_NAME in files:
                    continue
                session_id = _raw_session_identity(root, path, definition.agent)
                if not session_id:
                    continue
                # Count actual session sources, not adjacent caches or binary metadata.
                if deep and seen >= limit:
                    return _SourceInspection("present", latest, True, not failed and reconciled, True, issues, examples)
                seen += 1
                modified = datetime.fromtimestamp(entry.st_mtime, UTC)
                if definition.agent == "grok" and "signals.json" in files:
                    try:
                        signals = os.stat("signals.json", dir_fd=directory_fd, follow_symlinks=False)
                        modified = max(modified, datetime.fromtimestamp(signals.st_mtime, UTC))
                    except OSError:
                        failed = True
                latest = max(latest, modified) if latest is not None else modified
                if not deep:
                    continue
                try:
                    fingerprint = (
                        _grok_source_fingerprint_at(directory_fd)
                        if definition.agent == "grok"
                        else _source_fingerprint_at(directory_fd, name, entry)
                    )
                    manifest = stored_generation(definition.agent, session_id, fingerprint)
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if _source_file_metadata(current) != _source_file_metadata(entry):
                        raise OSError(errno.ESTALE, "session source changed during archive reconciliation", name)
                except OSError, ValueError:
                    failed = True
                    issue("unreadable-or-changing-source", session_id)
                    continue
                if manifest is None or manifest.completeness != "complete":
                    reconciled = False
                    issue("missing-current-generation" if manifest is None else "partial-generation", session_id)
    finally:
        os.close(root_fd)
    if failed:
        return _SourceInspection("unreadable", latest, True, False, issue_counts=issues, examples=examples)
    if deep and not reconciled:
        return _SourceInspection("unreconciled", latest, True, False, issue_counts=issues, examples=examples)
    return _SourceInspection("present", latest, True, True)


def _valid_manifest_path(root: Path, path: Path, manifest: SessionManifest, agent: str) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return False
    if len(parts) != 3 or parts[-1] != "manifest.json":
        return False
    lineage, generation = parts[:2]
    return (
        manifest.agent == agent
        and manifest.lineage_id == lineage == session_lineage_id(agent, manifest.session_id)
        and manifest.schema_version in SUPPORTED_SCHEMA_VERSIONS
        and manifest.parser_version in SUPPORTED_PARSER_VERSIONS
        and generation == session_digest(manifest.parser_version, manifest.source_fingerprint)
    )


def _inspect_lineage(state: State, definition: DoctorIntegration, *, deep: bool = False) -> _LineageSummary:
    root = Path.home() / ".agents/sessions" / SESSION_STORE_VERSION / definition.agent
    summary = _LineageSummary()
    try:
        info = root.lstat()
    except FileNotFoundError:
        return summary
    except OSError:
        summary.unreadable = True
        return summary
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        summary.unreadable = True
        return summary

    manifests: list[Path] = []
    failed = False

    def onerror(_error: OSError) -> None:
        nonlocal failed
        failed = True

    for current, directories, files in os.walk(root, topdown=True, onerror=onerror, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(name for name in directories if not (current_path / name).is_symlink())
        manifests.extend(current_path / name for name in sorted(files) if name == "manifest.json")
        if deep and len(manifests) > state.config.agent.doctor.scan_limit:
            summary.truncated = True
            break
    if not deep and manifests:
        try:
            manifests = [max(manifests, key=lambda path: path.lstat().st_mtime_ns)]
        except OSError:
            summary.unreadable = True
            return summary
    selected = manifests[: state.config.agent.doctor.scan_limit] if deep else manifests
    for path in selected:
        try:
            manifest = read_session_manifest(path.parent)
            if not _valid_manifest_path(root, path, manifest, definition.agent):
                raise ValueError("manifest identity does not match its lineage")
            if deep:
                validate_session_generation(path.parent, manifest)
            ingested = _parse_timestamp(manifest.ingested_at)
        except OSError, UnicodeError, ValueError, json.JSONDecodeError:
            summary.unreadable = True
            continue
        if summary.latest is None or ingested > summary.latest:
            summary.latest = ingested
            summary.latest_partial = manifest.completeness != "complete"
        if manifest.completeness == "complete" and (summary.last_complete is None or ingested > summary.last_complete):
            summary.last_complete = ingested
    summary.unreadable = summary.unreadable or failed
    return summary


def _inspect_last_hook_failure(state: State, agent: str) -> tuple[str, bool]:
    root = Path.home() / ".agents/hook-failures/v1"
    try:
        info = root.lstat()
    except FileNotFoundError:
        return "none", True
    except OSError:
        return "unreadable", False
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        return "unreadable", False
    try:
        entries = sorted(root.iterdir())[-state.config.agent.hook_failures.limit :]
    except OSError:
        return "unreadable", False
    unreadable = False
    for path in reversed(entries):
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                continue
            content = path.read_bytes()
            if not content.strip():
                continue
            record = json.loads(content)
            if not isinstance(record, dict):
                raise ValueError("failure record is not an object")
            if record.get("agent") == agent:
                occurred_at, operation = record.get("occurred_at"), record.get("operation")
                if not isinstance(occurred_at, str) or not isinstance(operation, str):
                    raise ValueError("failure record metadata is invalid")
                return f"{occurred_at}:{operation}", True
        except OSError, UnicodeError, ValueError, json.JSONDecodeError:
            unreadable = True
    return ("unreadable", False) if unreadable else ("none", True)


def _format_duration(value: timedelta) -> str:
    seconds = max(0, int(value.total_seconds()))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours}h{minutes}m{seconds}s"
    if minutes:
        return f"{minutes}m{seconds}s"
    return f"{seconds}s"


def _summarize_lineage(
    state: State,
    definition: DoctorIntegration,
    now: datetime,
    source: _SourceInspection,
    summary: _LineageSummary,
) -> tuple[str, str, bool]:
    if summary.unreadable:
        return "unreadable", "unknown", False
    if definition.discovery_only:
        return "discovery-only", "unknown", True
    if summary.last_complete is None:
        if summary.latest_partial:
            return "partial-only", "unknown", False
        return "none", "unknown", not source.present or source.latest is None
    if not source.healthy:
        ingestion = summary.last_complete.isoformat(timespec="seconds").replace("+00:00", "Z")
        return ingestion, "unknown", False
    ingestion = summary.last_complete.isoformat(timespec="seconds").replace("+00:00", "Z")
    if summary.latest_partial and summary.latest is not None and summary.latest > summary.last_complete:
        return f"{ingestion}:newer-partial", "unknown", False
    if not source.present or source.latest is None or source.latest <= summary.last_complete:
        return ingestion, "0s", True
    lag = source.latest - summary.last_complete
    healthy = lag.total_seconds() <= state.config.agent.doctor.stale_lag_seconds
    healthy = healthy and source.latest <= now + timedelta(minutes=1)
    return ingestion, _format_duration(lag), healthy


def gather_agent_doctor(
    state: State,
    *,
    now: datetime | None = None,
    deep: bool = False,
    progress: bool = False,
    agent: str = "",
    explain: bool = False,
) -> list[AgentDoctorResult]:
    if agent and agent not in {item.agent for item in _DOCTOR_INTEGRATIONS}:
        raise DotError(f"unknown integration {agent!r}")
    current = now or datetime.now(UTC)
    runnable = _dot_command_prober(state)
    notifier_available = _notifier_available(state)
    skills = _inspect_skill_catalog(state)
    results: list[AgentDoctorResult] = []
    total = len(_DOCTOR_INTEGRATIONS)
    for index, definition in enumerate(_DOCTOR_INTEGRATIONS, start=1):
        if agent and definition.agent != agent:
            continue
        if progress:
            state.stderr.write(f"Deep doctor {index}/{total}: {definition.agent}\n")
        discovery, discovery_ok = _check_discovery(definition)
        if discovery_ok and not skills.healthy:
            discovery, discovery_ok = skills.status, False
        hooks, hooks_ok = _check_hooks(definition, runnable)
        if definition.notifications and not notifier_available:
            hooks, hooks_ok = "notification-unavailable", False
        tools, tools_ok = _check_tools(state, definition)
        source = _inspect_source(state, definition, deep=deep)
        lineage = _inspect_lineage(state, definition, deep=deep)
        failure, failure_ok = _inspect_last_hook_failure(state, definition.agent)
        ingestion, lag, lineage_ok = _summarize_lineage(state, definition, current, source, lineage)
        truncated = source.truncated or lineage.truncated or skills.truncated
        if not skills.healthy:
            repair = (
                "Inspect ~/.agents/skills; restore missing repository links with a reviewed chezmoi apply, "
                "and repair other packages at their source."
            )
        elif not discovery_ok or not hooks_ok:
            repair = f"dot agent doctor --agent {definition.agent} --fix --dry-run (configuration only)"
        elif definition.discovery_only:
            repair = "Archive capture is not supported; discovery and installed tool only."
        elif not source.healthy:
            repair = (
                f"dot agent session sync --agent {definition.agent}; "
                f"then dot agent doctor --agent {definition.agent} --deep --explain"
            )
        else:
            repair = ""
        results.append(
            AgentDoctorResult(
                definition.agent,
                discovery,
                hooks,
                tools,
                source.status,
                ingestion,
                failure,
                lag,
                truncated,
                discovery_ok
                and hooks_ok
                and tools_ok
                and source.healthy
                and lineage_ok
                and failure_ok
                and not truncated,
                issue_counts=skills.issue_counts | source.issue_counts,
                examples=(skills.examples + source.examples)[: state.config.agent.doctor.example_limit]
                if explain
                else [],
                repair=repair,
            )
        )
    return results


def _doctor_repair_targets(agent: str = "") -> list[Path]:
    targets = {expand_path(_SHARED_PERSONA), expand_path(_SHARED_SKILLS)}
    for definition in _DOCTOR_INTEGRATIONS:
        if agent and definition.agent != agent:
            continue
        targets.add(expand_path(definition.persona_path))
        for value in (definition.skills_path, definition.skills_config, definition.hook_path):
            if value:
                targets.add(expand_path(value))
    return sorted(targets)


def repair_agent_integrations(state: State, *, dry_run: bool = False, agent: str = "") -> None:
    args = ["chezmoi", "apply"]
    if dry_run:
        args.append("--dry-run")
    args.extend(("--force", *(str(path) for path in _doctor_repair_targets(agent))))
    try:
        state.runner.run(args)
    except (OSError, DotError) as error:
        raise DotError("failed to repair agent integrations") from error


def run_agent_doctor(
    state: State,
    *,
    fix: bool = False,
    dry_run: bool = False,
    deep: bool = False,
    as_json: bool = False,
    now: datetime | None = None,
    agent: str = "",
    explain: bool = False,
) -> list[AgentDoctorResult]:
    if dry_run and not fix:
        raise DotError("--dry-run requires --fix")
    if agent and agent not in {item.agent for item in _DOCTOR_INTEGRATIONS}:
        raise DotError(f"unknown integration {agent!r}")
    if fix:
        repair_agent_integrations(state, dry_run=dry_run, agent=agent)
    results = gather_agent_doctor(state, now=now, deep=deep, progress=deep, agent=agent, explain=explain)
    if as_json:
        json.dump(
            diagnostic_report(
                "agents",
                [
                    {"name": result.agent, "status": "pass" if result.healthy else "fail", "details": asdict(result)}
                    for result in results
                ],
            ),
            state.stdout,
            ensure_ascii=False,
            indent=2,
        )
        state.stdout.write("\n")
    else:
        state.stdout.write("Agent doctor\n")
        for result in results:
            mark = "✓" if result.healthy else "✗"
            state.stdout.write(
                f"{mark} {result.agent}: discovery={result.discovery} hooks={result.hooks} tools={result.tools} "
                f"source={result.source} ingestion={result.last_ingestion} failure={result.last_failure} "
                f"lag={result.archive_lag} truncated={str(result.truncated).lower()}\n"
            )
            if result.issue_counts:
                state.stdout.write(f"  issues={json.dumps(result.issue_counts)}\n")
            if result.repair:
                state.stdout.write(f"  next: {result.repair}\n")
            for example in result.examples:
                kind = "skill" if "skill" in example else "session"
                state.stdout.write(f"  {example['reason']}: {kind}={example[kind]}\n")
    if not all(result.healthy for result in results):
        raise DotError("agent doctor found unhealthy integrations")
    return results
