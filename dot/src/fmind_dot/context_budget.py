"""Offline, portable estimates of shared agent instruction and discovery costs."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Any, Literal

import yaml

from fmind_dot.command import Parser, add_json
from fmind_dot.errors import DotError, UsageError
from fmind_dot.reporting import display_path, write_json
from fmind_dot.state import State

CONTEXT_TOKEN_LIMIT = 5_000
MAX_INPUT_BYTES = 1 << 20
Scope = Literal["global", "local"]
_RESERVED_SKILL_DIRECTORIES = frozenset({"synced"})
# Hosts disagree on same-name skills: some prefer one scope, some list both, some pick arbitrarily.
DUPLICATE_GUIDANCE = (
    "Hosts resolve duplicate skill names differently (scope precedence, both listed, or an arbitrary winner). "
    "Rename one skill or remove a copy so each name is unique across global and local scopes."
)


def estimated_tokens(characters: int) -> int:
    """Use one reproducible estimate without network calls or a model dependency."""
    return (characters + 3) // 4


def skill_index_entry(name: str, description: str, scope: Scope, *, relative: str) -> str:
    """Normalize checkout paths so moving a repository cannot change its budget."""
    prefix = "~/.agents/skills" if scope == "global" else ".agents/skills"
    return f"- {name}: {' '.join(description.split())} (file: {prefix}/{relative})\n"


@dataclass(frozen=True)
class ContextEntry:
    """A measured input; reports never contain its instruction text."""

    scope: Scope
    kind: Literal["agents", "skill"]
    name: str
    path: str
    characters: int
    discovery_characters: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "estimated_tokens": estimated_tokens(self.characters),
            "discovery_estimated_tokens": estimated_tokens(self.discovery_characters),
        }


def _read(path: Path) -> str:
    try:
        if not path.is_file():
            raise DotError(f"context input is not a regular file: {path}; repair the file or link")
        with path.open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise DotError(f"context input exceeds 1 MiB: {path}; split it before measuring")
        return data.decode("utf-8")
    except (OSError, UnicodeError) as error:
        raise DotError(f"cannot read context input: {path}; check its link, permissions, and UTF-8 encoding") from error


def parse_frontmatter(text: str, path: Path | str) -> tuple[dict[str, Any], str]:
    """Parse bounded YAML frontmatter into a string-keyed mapping and body without leaking source text."""
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise DotError(f"{path}: frontmatter must be bounded by --- lines")
    if normalized.endswith("\n---"):
        normalized += "\n"
    if "\n---\n" not in normalized[4:]:
        raise DotError(f"{path}: frontmatter must be bounded by --- lines")
    raw, body = normalized[4:].split("\n---\n", 1)
    try:
        metadata = yaml.safe_load(raw)
    except (yaml.YAMLError, RecursionError) as error:
        # YAML exceptions can contain source text. Keep private instructions out of errors.
        raise DotError(f"{path}: invalid frontmatter; repair its YAML") from error
    if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
        raise DotError(f"{path}: frontmatter must be a string-keyed mapping")
    return metadata, body


def _skill_entry(path: Path, scope: Scope, *, catalog: Path) -> ContextEntry:
    text = _read(path)
    metadata, _ = parse_frontmatter(text, path)
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or name != path.parent.name:
        raise DotError(f"invalid skill name: {path}; match its directory name")
    if not isinstance(description, str) or not description.strip():
        raise DotError(f"missing skill description: {path}; describe its capability and trigger")
    return ContextEntry(
        scope,
        "skill",
        name,
        str(path),
        len(text),
        len(skill_index_entry(name, description, scope, relative=path.relative_to(catalog).as_posix())),
    )


def _scope_entries(agents: Path, skills: Path, scope: Scope) -> list[ContextEntry]:
    entries: list[ContextEntry] = []
    if agents.exists() or agents.is_symlink():
        entries.append(ContextEntry(scope, "agents", "AGENTS.md", str(agents), len(_read(agents))))
    if not skills.exists() and not skills.is_symlink():
        return entries
    if not skills.is_dir():
        raise DotError(f"invalid skill directory: {skills}; repair or remove the broken link")
    # Hosts can discover nested SKILL.md files, including through package links.
    # Traverse them too; a shallow estimate would silently reward accidental exposure.
    pending: list[tuple[Path, frozenset[Path]]] = [(skills, frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        resolved = directory.resolve()
        if resolved in ancestors:
            raise DotError(f"cyclic skill directory: {directory}; remove the recursive link")
        try:
            children = sorted(directory.iterdir())
        except OSError as error:
            raise DotError(f"cannot inspect skill directory: {directory}; check its permissions") from error
        for path in children:
            if path.name.startswith(".") or path.name in _RESERVED_SKILL_DIRECTORIES:
                continue
            if path.is_symlink() and not path.exists():
                raise DotError(f"broken skill link: {path}; repair or remove the retired link")
            if path.is_dir():
                pending.append((path, ancestors | {resolved}))
            elif path.name == "SKILL.md":
                entries.append(_skill_entry(path, scope, catalog=skills))
    return entries


def _totals(entries: list[ContextEntry]) -> dict[str, int]:
    agents = sum(item.characters for item in entries if item.kind == "agents")
    skills = sum(item.discovery_characters for item in entries)
    bodies = sum(item.characters for item in entries if item.kind == "skill")
    return {
        "agents_files": sum(item.kind == "agents" for item in entries),
        "skills": sum(item.kind == "skill" for item in entries),
        "agents_characters": agents,
        "agents_estimated_tokens": estimated_tokens(agents),
        "skill_index_characters": skills,
        "skill_index_estimated_tokens": estimated_tokens(skills),
        "startup_estimated_tokens": estimated_tokens(agents + skills),
        "on_demand_skill_file_estimated_tokens": estimated_tokens(bodies),
    }


def _duplicates(entries: list[ContextEntry]) -> list[dict[str, Any]]:
    """Group distinct resolved files by declared name; callers pass entries already deduplicated by file."""
    paths: dict[str, list[str]] = {}
    for entry in entries:
        if entry.kind == "skill":
            paths.setdefault(entry.name, []).append(entry.path)
    return [{"name": name, "paths": found} for name, found in sorted(paths.items()) if len(found) > 1]


def _resolve_root(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise DotError(f"invalid path {path}: {error}") from error


def context_report(project: Path, *, global_root: Path | None = None, source: Path | None = None) -> dict[str, Any]:
    """Measure explicit shared roots, not a guessed host prompt or recursive workspace; source wins over global_root."""
    project = _resolve_root(project)
    if not project.is_dir():
        raise DotError(f"project directory does not exist: {project}")
    if source is not None:
        source = _resolve_root(source)
        if not (source / "skills").is_dir() or not (source / "dot_agents/AGENTS.md").is_file():
            raise DotError(f"invalid dot source: {source}; expected skills/ and dot_agents/AGENTS.md")
        global_agents, global_skills = source / "dot_agents/AGENTS.md", source / "skills"
    else:
        root = _resolve_root(global_root or Path.home() / ".agents")
        global_agents, global_skills = root / "AGENTS.md", root / "skills"
    roots = {
        "global": {"agents": str(global_agents), "skills": str(global_skills)},
        "local": {"agents": str(project / "AGENTS.md"), "skills": str(project / ".agents/skills")},
    }
    global_entries = _scope_entries(global_agents, global_skills, "global")
    local_entries = _scope_entries(project / "AGENTS.md", project / ".agents/skills", "local")
    unique: dict[Path, ContextEntry] = {}
    for entry in [*global_entries, *local_entries]:
        unique.setdefault(Path(entry.path).resolve(), entry)
    combined = list(unique.values())
    duplicates = _duplicates(combined)
    totals = {"global": _totals(global_entries), "local": _totals(local_entries), "combined": _totals(combined)}
    budgets = {
        scope: {
            "limit_exclusive": CONTEXT_TOKEN_LIMIT,
            "estimated_tokens": totals[scope]["startup_estimated_tokens"],
            "remaining": CONTEXT_TOKEN_LIMIT - 1 - totals[scope]["startup_estimated_tokens"],
            "passed": totals[scope]["startup_estimated_tokens"] < CONTEXT_TOKEN_LIMIT,
        }
        for scope in ("global", "local")
    }
    return {
        "schema": "dot.agent.context/v5",
        "measurement": "ceil(characters / 4); portable estimate, not host tokenization or billing",
        "coverage": "Shared roots only; excludes host/plugin catalogs, ancestor/nested instructions and references. "
        "Combined counts identical resolved files once; distinct same-name skills both count and fail --check.",
        "roots": roots,
        "totals": totals,
        "budgets": budgets,
        "passed": all(budget["passed"] for budget in budgets.values()) and not duplicates,
        "duplicates": duplicates,
        "entries": [entry.to_dict() for entry in [*global_entries, *local_entries]],
    }


def _print_report(output: IO[str], report: dict[str, Any], *, details: bool) -> None:
    def write(text: str = "") -> None:
        output.write(text + "\n")

    write("Agent context · estimated tokens")
    write(f"Budget: below {CONTEXT_TOKEN_LIMIT:,} tokens for global and local, separately.\n")
    write(f"{'Scope':<10} {'AGENTS.md':>9} {'Skill index':>11} {'Total':>7} {'Remaining':>10}  Status")
    for scope, totals in report["totals"].items():
        budget = report["budgets"].get(scope)
        remaining = f"{budget['remaining']:,}" if budget else "—"
        status = ("PASS" if budget["passed"] else "OVER BUDGET") if budget else "—"
        write(
            f"{scope.capitalize():<10} {totals['agents_estimated_tokens']:>9,} "
            f"{totals['skill_index_estimated_tokens']:>11,} {totals['startup_estimated_tokens']:>7,} "
            f"{remaining:>10}  {status}"
        )
    global_count = report["totals"]["global"]["skills"]
    local_count = report["totals"]["local"]["skills"]
    write(f"\nSkill index: names, descriptions, and paths ({global_count:,} global, {local_count:,} local skills).")
    discovery = report["totals"]["combined"]["skill_index_estimated_tokens"]
    write(f"Combined discovery: {discovery:,} estimated tokens (informational)")
    write("Combined startup is informational. On-demand bodies and host/plugin catalogs are excluded.")
    write("Estimated at ~4 characters/token; exact counts vary by model. Totals round independently.")
    if report["duplicates"]:
        write("\nDuplicate skill names · FAIL (both counted)")
        for item in report["duplicates"]:
            write(f"  {item['name']}")
            for path in item["paths"]:
                write(f"    {display_path(path)}")
        write(DUPLICATE_GUIDANCE)
    if details:
        write("\nOn-demand SKILL.md files · estimated tokens, excluded from budget")
        for scope, totals in report["totals"].items():
            write(f"  {scope.capitalize():<10} {totals['on_demand_skill_file_estimated_tokens']:>9,}")
        write("\nSources")
        for scope, roots in report["roots"].items():
            write(f"  {scope.capitalize() + ' AGENTS.md':<17} {display_path(roots['agents'])}")
            write(f"  {scope.capitalize() + ' skills':<17} {display_path(roots['skills'])}")
        write(f"\n{report['coverage']}")
    else:
        write("Use --details for source paths, on-demand costs, and coverage.")


def _check_summary(report: dict[str, Any]) -> str:
    scopes = ", ".join(f"{scope} {budget['estimated_tokens']:,}" for scope, budget in report["budgets"].items())
    return f"PASS · agent context below {CONTEXT_TOKEN_LIMIT:,} estimated tokens ({scopes})"


def _context(state: State, args: argparse.Namespace) -> None:
    for flag, value in (("--project", args.project), ("--source", args.source)):
        if value is not None:
            try:
                value.expanduser()
            except RuntimeError as error:
                raise UsageError(f"{flag}: {error}") from None
    check = args.check
    report = context_report(args.project, source=args.source)
    if args.as_json:
        write_json(state.stdout, report)
        if check and report["duplicates"]:
            # Keep stdout parseable; the text report already carries this guidance.
            names = ", ".join(item["name"] for item in report["duplicates"])
            state.stderr.write(f"Duplicate skill names: {names}. {DUPLICATE_GUIDANCE}\n")
    elif check and report["passed"] and not args.details:
        # Agents run the gate often; a pass needs one line, a failure keeps the full table.
        state.stdout.write(_check_summary(report) + "\n")
    else:
        _print_report(state.stdout, report, details=args.details)
    if check and not report["passed"]:
        raise SystemExit(1)


def register(commands: Parser) -> None:
    """Expose the report under the agent command group; it never reads dot.yaml."""
    context = commands.command(
        "context",
        "Measure global, project, and combined AGENTS.md and skill discovery costs; report duplicate skill names",
        _context,
        config=False,
    )
    context.add_argument(
        "-p",
        "--project",
        type=Path,
        default=Path(),
        metavar="PATH",
        help="Project root (only its own instructions and skills)",
    )
    context.add_argument(
        "--source", type=Path, metavar="PATH", help="Measure a dot source checkout instead of installed global files"
    )
    context.add_argument(
        "--check",
        action="store_true",
        help=f"Exit 1 at {CONTEXT_TOKEN_LIMIT} instruction + discovery tokens in either global or local scope, "
        "or on duplicate skill names",
    )
    context.add_argument(
        "--details",
        action="store_true",
        help="Include source paths, on-demand file costs, and coverage in text output",
    )
    add_json(context)
