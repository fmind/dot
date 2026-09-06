"""Bounded, source-accounted project context generation."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from fmind_dot.commands import aliased_command, state_from
from fmind_dot.errors import DotError
from fmind_dot.repository import scan_payload_for_secrets
from fmind_dot.state import State

CONTEXT_SCHEMA_VERSION = "1.0"
DEFAULT_CONTEXT_BYTES = 50_000
BYTES_PER_TOKEN = 4
DEFAULT_COLLECTORS = ("instructions", "skills", "git", "tasks", "dependencies", "failures")


@dataclass(frozen=True)
class ContextOptions:
    """Requested output budget, representation, and reproducible timestamp."""

    bytes: int = 0
    tokens: int = 0
    format: str = "markdown"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class ContextBudget:
    """Resolved byte budget and the option that requested it."""

    effective_bytes: int
    requested_bytes: int = 0
    requested_tokens: int = 0


@dataclass
class ContextSection:
    """Collected content plus provenance and completeness metadata."""

    id: str
    priority: int
    observed_at: str
    content: str = ""
    sources: list[str] = field(default_factory=list)
    error: str = ""
    fingerprint: str = ""


@dataclass(frozen=True)
class _SectionView:
    content: str
    status: str
    total_bytes: int
    omitted_bytes: int
    omitted_lines: str


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise DotError("context generation timestamp must include a timezone")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_context_budget(state: State, options: ContextOptions) -> ContextBudget:
    """Resolve mutually exclusive byte and approximate-token budgets."""
    if options.bytes < 0 or options.tokens < 0 or (options.bytes and options.tokens):
        raise DotError("--bytes and --tokens must be positive and mutually exclusive")
    if options.bytes:
        effective = options.bytes
    elif options.tokens:
        effective = options.tokens * BYTES_PER_TOKEN
    else:
        effective = state.config.context.max_bytes or DEFAULT_CONTEXT_BYTES
    return ContextBudget(effective, options.bytes, options.tokens)


def _within_root(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _lexically_within_root(relative: Path) -> bool:
    depth = 0
    for part in relative.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if depth == 0:
                return False
            depth -= 1
        else:
            depth += 1
    return True


def read_project_file(root: Path, relative: str) -> str:
    """Read a regular, non-symlink file that resolves inside the project."""
    requested = Path(relative)
    if not relative or requested.is_absolute():
        raise DotError("path must be project-relative")
    if not _lexically_within_root(requested):
        raise DotError("path escapes project root")
    root_resolved = root.resolve(strict=True)
    candidate = root / requested
    try:
        candidate.lstat()
    except FileNotFoundError as error:
        raise DotError("source does not exist") from error
    except OSError as error:
        raise DotError("source metadata is unavailable") from error
    if candidate.is_symlink() or not candidate.is_file():
        raise DotError("source must be a regular non-symlink file")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise DotError("source resolution failed") from error
    if not _within_root(root_resolved, resolved):
        raise DotError("source resolves outside project root")
    try:
        return candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise DotError("source is unreadable UTF-8") from error


def _append_error(existing: str, path: str, error: Exception) -> str:
    message = f"{path}: {error}"
    return f"{existing}; {message}" if existing else message


def _project_files(root: Path, section_id: str, priority: int, paths: list[str], observed_at: str) -> ContextSection:
    section = ContextSection(section_id, priority, observed_at)
    if not paths:
        section.content = "No sources configured.\n"
        return section
    for relative in paths:
        try:
            content = read_project_file(root, relative)
        except DotError as error:
            section.error = _append_error(section.error, relative, error)
            continue
        source = Path(relative).as_posix()
        section.sources.append(source)
        section.content += f"## {source}\n{content}\n"
    return section


def _skill_frontmatter(content: str) -> str:
    parts = content.split("---", 2)
    if len(parts) != 3:
        return "metadata unavailable"
    lines = [line.strip() for line in parts[1].splitlines() if line.startswith(("name:", "description:"))]
    return " | ".join(lines) or "metadata unavailable"


def _skills(root: Path, observed_at: str) -> ContextSection:
    section = ContextSection("skills", 2, observed_at)
    directory = root / "skills"
    try:
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or not _within_root(root.resolve(), directory.resolve(strict=True))
        ):
            raise OSError
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:
        section.error = "skills directory unavailable"
        return section
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            continue
        relative = (Path("skills") / entry.name / "SKILL.md").as_posix()
        try:
            metadata = _skill_frontmatter(read_project_file(root, relative))
        except DotError as error:
            section.error = _append_error(section.error, relative, error)
            continue
        section.sources.append(relative)
        section.content += f"- {metadata.replace(chr(10), ' ')}\n"
    if not section.content:
        section.content = "No project-local skill metadata found.\n"
    return section


def _git_context(state: State, root: Path, observed_at: str) -> ContextSection:
    section = ContextSection("git", 3, observed_at, sources=["git status --short --branch", "git log -5"])
    failures: list[str] = []
    try:
        status = state.runner.run(["git", "status", "--short", "--branch"], cwd=root).stdout
    except DotError as error:
        status = ""
        failures.append(str(error))
    try:
        recent = state.runner.run(["git", "log", "-5", "--pretty=format:%h %s"], cwd=root).stdout
    except DotError as error:
        recent = ""
        failures.append(str(error))
    section.content = f"## Status\n{status}\n## Recent commits\n{recent}\n"
    section.error = "; ".join(failures)
    return section


def _tasks(state: State, root: Path, observed_at: str) -> ContextSection:
    section = ContextSection("tasks", 4, observed_at, sources=["mise tasks --json"])
    mise = state.runner.which("mise")
    if mise is None:
        section.error = "mise unavailable"
        return section
    try:
        raw = state.runner.run([str(mise), "tasks", "--json"], cwd=root).stdout
        decoded: Any = json.loads(raw)
        if not isinstance(decoded, list):
            raise ValueError
        tasks = []
        for item in decoded:
            if not isinstance(item, dict):
                raise ValueError
            tasks.append(
                {
                    "name": str(item.get("name", "")),
                    "description": str(item.get("description", "")),
                    "aliases": sorted(str(alias) for alias in item.get("aliases", [])),
                }
            )
        tasks.sort(key=lambda item: item["name"])
        section.content = json.dumps(tasks, indent=2, ensure_ascii=False) + "\n"
    except DotError, TypeError, ValueError, json.JSONDecodeError:
        section.error = "mise returned invalid task metadata"
    return section


def _dependencies(state: State, root: Path, observed_at: str) -> ContextSection:
    try:
        tracked = state.runner.run(["git", "ls-files", "-z"], cwd=root).stdout
    except DotError as error:
        return ContextSection("dependencies", 5, observed_at, error=str(error))
    configured = state.config.context.dependency_files or ["pyproject.toml", "uv.lock", "mise.toml"]
    allowed = set(configured)
    paths = sorted(
        path
        for path in tracked.split("\0")
        if path and (Path(path).name in allowed or Path(path).as_posix() in allowed)
    )
    return _project_files(root, "dependencies", 5, paths, observed_at)


def _redact_root(value: str, root: Path) -> str:
    spellings = {str(root), root.as_posix(), str(root.resolve()), root.resolve().as_posix()}
    for spelling in sorted(spellings, key=len, reverse=True):
        value = value.replace(spelling, ".")
    return value


def _finalize(section: ContextSection) -> None:
    material = f"{section.content}\n{section.error}\n" + "\n".join(section.sources)
    section.fingerprint = "sha256:" + hashlib.sha256(material.encode()).hexdigest()


def collect_context_sections(state: State, root: Path, observed_at: str) -> list[ContextSection]:
    """Run configured allowlisted collectors in stable priority order."""
    configured = state.config.context.collectors or list(DEFAULT_COLLECTORS)
    sections: list[ContextSection] = []
    seen: set[str] = set()
    for name in configured:
        if name in seen:
            continue
        seen.add(name)
        if name == "instructions":
            section = _project_files(root, name, 1, state.config.context.instruction_files, observed_at)
        elif name == "skills":
            section = _skills(root, observed_at)
        elif name == "git":
            section = _git_context(state, root, observed_at)
        elif name == "tasks":
            section = _tasks(state, root, observed_at)
        elif name == "dependencies":
            section = _dependencies(state, root, observed_at)
        elif name == "failures":
            section = _project_files(root, name, 6, state.config.context.failure_files, observed_at)
        else:
            section = ContextSection(name, 99, observed_at, error="collector is not allowlisted")
        section.content = _redact_root(section.content, root)
        section.error = _redact_root(section.error, root)
        _finalize(section)
        sections.append(section)
    return sorted(sections, key=lambda section: section.priority)


def _context_lines(sections: list[ContextSection]) -> tuple[list[tuple[int, int]], list[list[str]]]:
    lines = [section.content.splitlines(keepends=True) for section in sections]
    maximum = max((len(value) for value in lines), default=0)
    units = [
        (section_index, line_index)
        for line_index in range(maximum)
        for section_index in range(len(sections))
        if line_index < len(lines[section_index])
    ]
    return units, lines


def _int_ranges(values: list[int]) -> str:
    if not values:
        return "none"
    output: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        output.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    output.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(output)


def _section_view(section: ContextSection, lines: list[str], selected: set[int]) -> _SectionView:
    content = "".join(line for index, line in enumerate(lines) if index in selected)
    omitted = [index + 1 for index in range(len(lines)) if index not in selected]
    if not omitted:
        status = "complete"
    elif not selected:
        status = "omitted-section"
    else:
        status = "partial"
    total = len(section.content.encode())
    return _SectionView(content, status, total, total - len(content.encode()), _int_ranges(omitted))


def _budget_document(budget: ContextBudget) -> dict[str, int]:
    output = {"effective_bytes": budget.effective_bytes}
    if budget.requested_bytes:
        output["requested_bytes"] = budget.requested_bytes
    if budget.requested_tokens:
        output["requested_tokens"] = budget.requested_tokens
    return output


def _render_json(
    repository: str,
    head: str,
    generated_at: str,
    budget: ContextBudget,
    sections: list[ContextSection],
    lines: list[list[str]],
    selected: list[set[int]],
) -> str:
    rendered_sections = []
    for index, section in enumerate(sections):
        view = _section_view(section, lines[index], selected[index])
        rendered_sections.append(
            {
                "id": section.id,
                "fingerprint": section.fingerprint,
                "observed_at": section.observed_at,
                "status": view.status,
                "error": section.error,
                "content": view.content,
                "omitted_lines": view.omitted_lines,
                "sources": section.sources,
                "priority": section.priority,
                "total_bytes": view.total_bytes,
                "omitted_bytes": view.omitted_bytes,
            }
        )
    envelope = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "generated_at": generated_at,
        "repository": repository,
        "source_head": head,
        "sections": rendered_sections,
        "optional_adapters": ["session-metadata (optional, unavailable in project-only v1)"],
        "budget": _budget_document(budget),
    }
    return json.dumps(envelope, indent=2, ensure_ascii=False) + "\n"


def _manifest_value(value: str) -> str:
    return value.replace("\n", "; ") if value else "none"


def _render_markdown(
    repository: str,
    head: str,
    generated_at: str,
    budget: ContextBudget,
    sections: list[ContextSection],
    lines: list[list[str]],
    selected: list[set[int]],
) -> str:
    output = [
        "# Project context\n\n",
        f"- Schema: {CONTEXT_SCHEMA_VERSION}\n",
        f"- Generated: {generated_at}\n",
        f"- Repository: {repository}\n",
        f"- Source HEAD: {head}\n",
        f"- Effective budget: {budget.effective_bytes} bytes\n",
        f"- Requested bytes: {budget.requested_bytes}\n",
        f"- Requested tokens: {budget.requested_tokens}\n",
        "- Optional adapter: session-metadata (unavailable in project-only v1)\n\n",
        "## Manifest\n",
    ]
    views: list[_SectionView] = []
    for index, section in enumerate(sections):
        view = _section_view(section, lines[index], selected[index])
        views.append(view)
        output.append(
            f"- {section.id} | priority={section.priority} | status={view.status} | "
            f"total_bytes={view.total_bytes} | omitted_bytes={view.omitted_bytes} | "
            f"omitted_lines={view.omitted_lines} | observed={section.observed_at} | "
            f"fingerprint={section.fingerprint} | sources={','.join(section.sources)} | "
            f"error={_manifest_value(section.error)}\n"
        )
    for section, view in zip(sections, views, strict=True):
        if not view.content:
            continue
        output.append(f"\n## {section.id}\n\n")
        output.extend(f"    {line}" for line in view.content.splitlines(keepends=True))
    return "".join(output)


def _pack_context(
    repository: str,
    head: str,
    generated_at: str,
    budget: ContextBudget,
    sections: list[ContextSection],
    output_format: str,
) -> str:
    units, lines = _context_lines(sections)
    selected = [set() for _ in sections]
    render = _render_json if output_format == "json" else _render_markdown
    payload = render(repository, head, generated_at, budget, sections, lines, selected)
    size = len(payload.encode())
    if size > budget.effective_bytes:
        raise DotError(f"budget {budget.effective_bytes} bytes cannot hold the {size}-byte omission manifest")
    for section_index, line_index in units:
        selected[section_index].add(line_index)
        candidate = render(repository, head, generated_at, budget, sections, lines, selected)
        if len(candidate.encode()) <= budget.effective_bytes:
            payload = candidate
        else:
            selected[section_index].remove(line_index)
    return payload


def build_context(state: State, options: ContextOptions, *, cwd: Path | None = None) -> str:
    """Collect and pack repository context without performing the secret scan."""
    budget = resolve_context_budget(state, options)
    output_format = options.format.lower() or "markdown"
    if output_format not in {"markdown", "json"}:
        raise DotError(f"unsupported context format {options.format!r}")
    generated_at = _timestamp(options.generated_at)
    try:
        root_value = state.runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).stdout.strip()
    except DotError as error:
        raise DotError("failed to resolve project root") from error
    if not root_value:
        raise DotError("git returned an empty project root")
    root = Path(root_value)
    try:
        head = state.runner.run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
    except DotError as error:
        raise DotError("failed to fingerprint project HEAD") from error
    sections = collect_context_sections(state, root, generated_at)
    return _pack_context(root.name, head, generated_at, budget, sections, output_format)


def scan_context_payload(state: State, payload: str) -> None:
    """Reject secrets and configured sensitive values in the final payload."""
    try:
        scan_payload_for_secrets(state, payload)
    except DotError as error:
        raise DotError("context payload secret scan failed") from error
    for pattern in state.config.context.sensitive_path_patterns:
        if pattern and pattern in payload:
            raise DotError("context payload contains a configured sensitive path pattern")
    for pattern in state.config.context.sensitive_env_patterns:
        for name, value in os.environ.items():
            if value and fnmatch.fnmatchcase(name, pattern) and value in payload:
                raise DotError(f"context payload contains the value of sensitive environment variable {name}")


def run_context(state: State, options: ContextOptions, *, cwd: Path | None = None) -> str:
    """Build, scan, and write the exact final context payload."""
    payload = build_context(state, options, cwd=cwd)
    scan_context_payload(state, payload)
    state.stdout.write(payload)
    return payload


def context_command(
    context: typer.Context,
    max_bytes: Annotated[int, typer.Option("--bytes", min=0, help="Maximum output bytes")] = 0,
    tokens: Annotated[int, typer.Option("--tokens", min=0, help="Approximate token budget")] = 0,
    output_format: Annotated[str, typer.Option("--format", help="Output format: markdown or json")] = "markdown",
) -> None:
    run_context(state_from(context), ContextOptions(bytes=max_bytes, tokens=tokens, format=output_format))


def register_context_command(parent: typer.Typer) -> None:
    """Register the context command and its compatibility alias."""
    help_text = "Emit a bounded, redacted project context pack"
    aliased_command(parent, "context", "t", help_text=help_text)(context_command)
