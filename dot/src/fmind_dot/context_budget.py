"""Offline, portable estimates of shared agent instruction and discovery costs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
import yaml

from fmind_dot.command_group import JsonOption
from fmind_dot.errors import DotError

CONTEXT_TOKEN_LIMIT = 5_000
DISCOVERY_TOKEN_LIMIT = 3_500
MAX_INPUT_BYTES = 1 << 20
Scope = Literal["global", "local"]


def estimated_tokens(characters: int) -> int:
    """Use one reproducible estimate without network calls or a model dependency."""
    return (characters + 3) // 4


def skill_index_entry(name: str, description: str, scope: Scope, *, relative: str | None = None) -> str:
    """Normalize checkout paths so moving a repository cannot change its budget."""
    prefix = "~/.agents/skills" if scope == "global" else ".agents/skills"
    path = relative or f"{name}/SKILL.md"
    return f"- {name}: {' '.join(description.split())} (file: {prefix}/{path})\n"


@dataclass(frozen=True)
class ContextEntry:
    """A measured input; reports never contain its instruction text."""

    scope: Scope
    kind: Literal["agents", "skill"]
    name: str
    path: str
    characters: int
    discovery_characters: int = 0
    first_party: bool = False

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


def _skill_entry(path: Path, scope: Scope, *, catalog: Path) -> ContextEntry:
    text = _read(path)
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise DotError(f"missing skill frontmatter: {path}; add name and description")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise DotError(f"unclosed skill frontmatter: {path}; add the closing --- delimiter")
    try:
        metadata = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError as error:
        # YAML exceptions can contain source text. Keep private instructions out of errors.
        raise DotError(f"invalid skill frontmatter: {path}; repair its YAML") from error
    if not isinstance(metadata, dict):
        raise DotError(f"invalid skill frontmatter: {path}; expected a mapping")
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or name != path.parent.name:
        raise DotError(f"invalid skill name: {path}; match its directory name")
    if not isinstance(description, str) or not description.strip():
        raise DotError(f"missing skill description: {path}; describe its capability and trigger")
    provenance = metadata.get("metadata")
    source = provenance.get("source", "") if isinstance(provenance, dict) else ""
    first_party = isinstance(source, str) and source.startswith("github.com/fmind/dot/tree/")
    return ContextEntry(
        scope,
        "skill",
        name,
        str(path),
        len(text),
        len(skill_index_entry(name, description, scope, relative=path.relative_to(catalog).as_posix())),
        first_party,
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
            if path.name.startswith("."):
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


def context_report(project: Path, *, global_root: Path | None = None, source: Path | None = None) -> dict[str, Any]:
    """Measure explicit shared roots, not a guessed host prompt or recursive workspace."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise DotError(f"project directory does not exist: {project}")
    if source is not None and global_root is not None:
        raise DotError("choose --source or --global-root, not both")
    if source is not None:
        source = source.expanduser().resolve()
        if not (source / "skills").is_dir() or not (source / "dot_agents/AGENTS.md").is_file():
            raise DotError(f"invalid dot source: {source}; expected skills/ and dot_agents/AGENTS.md")
        global_agents, global_skills = source / "dot_agents/AGENTS.md", source / "skills"
    else:
        root = (global_root or Path.home() / ".agents").expanduser().resolve()
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
    names: set[str] = set()
    collisions: set[str] = set()
    for entry in combined:
        if entry.kind == "skill":
            if entry.name in names:
                collisions.add(entry.name)
            names.add(entry.name)
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
    discovery = totals["combined"]["skill_index_estimated_tokens"]
    budgets["discovery"] = {
        "limit_exclusive": DISCOVERY_TOKEN_LIMIT,
        "estimated_tokens": discovery,
        "remaining": DISCOVERY_TOKEN_LIMIT - 1 - discovery,
        "passed": discovery < DISCOVERY_TOKEN_LIMIT,
    }
    return {
        "schema": "dot.agent.context/v3",
        "measurement": "ceil(characters / 4); portable estimate, not host tokenization or billing",
        "coverage": "Shared roots only; excludes host/plugin catalogs, ancestor/nested instructions and references. "
        "Combined counts identical resolved files once; distinct same-name skills both count.",
        "roots": roots,
        "totals": totals,
        "budgets": budgets,
        "passed": all(budget["passed"] for budget in budgets.values()),
        "collisions": sorted(collisions),
        "entries": [entry.to_dict() for entry in [*global_entries, *local_entries]],
    }


def _display_path(value: str) -> str:
    path = Path(value)
    return str(Path("~") / path.relative_to(Path.home())) if path.is_relative_to(Path.home()) else value


def _print_report(report: dict[str, Any], *, details: bool) -> None:
    typer.echo("Agent context · estimated tokens")
    typer.echo(f"Budget: below {CONTEXT_TOKEN_LIMIT:,} tokens for global and local, separately.\n")
    typer.echo(f"{'Scope':<10} {'AGENTS.md':>9} {'Skill index':>11} {'Total':>7} {'Remaining':>10}  Status")
    for scope, totals in report["totals"].items():
        budget = report["budgets"].get(scope)
        remaining = f"{budget['remaining']:,}" if budget else "—"
        status = ("PASS" if budget["passed"] else "OVER BUDGET") if budget else "—"
        typer.echo(
            f"{scope.capitalize():<10} {totals['agents_estimated_tokens']:>9,} "
            f"{totals['skill_index_estimated_tokens']:>11,} {totals['startup_estimated_tokens']:>7,} "
            f"{remaining:>10}  {status}"
        )
    global_count = report["totals"]["global"]["skills"]
    local_count = report["totals"]["local"]["skills"]
    typer.echo(
        f"\nSkill index: names, descriptions, and paths ({global_count:,} global, {local_count:,} local skills)."
    )
    discovery = report["budgets"]["discovery"]
    status = "PASS" if discovery["passed"] else "OVER BUDGET"
    typer.echo(f"Combined discovery: {discovery['estimated_tokens']:,} / <{DISCOVERY_TOKEN_LIMIT:,} · {status}")
    typer.echo("Combined startup is informational. On-demand bodies and host/plugin extras are excluded.")
    typer.echo("Estimated at ~4 characters/token; exact counts vary by model. Totals round independently.")
    if report["collisions"]:
        typer.echo("\nName collisions (both counted): " + ", ".join(report["collisions"]))
    if details:
        typer.echo("\nOn-demand SKILL.md files · estimated tokens, excluded from budget")
        for scope, totals in report["totals"].items():
            typer.echo(f"  {scope.capitalize():<10} {totals['on_demand_skill_file_estimated_tokens']:>9,}")
        typer.echo("\nSources")
        for scope, roots in report["roots"].items():
            typer.echo(f"  {scope.capitalize() + ' AGENTS.md':<17} {_display_path(roots['agents'])}")
            typer.echo(f"  {scope.capitalize() + ' skills':<17} {_display_path(roots['skills'])}")
        typer.echo(f"\n{report['coverage']}")
    else:
        typer.echo("Use --details for source paths, on-demand costs, and coverage.")


def register(agent_app: typer.Typer) -> None:
    """Expose the report under the existing agent command group."""

    @agent_app.command("context", help="Measure global, project, and combined AGENTS.md and skill discovery costs")
    def context_command(
        project: Annotated[
            Path, typer.Option("--project", "-p", help="Project root (only its own instructions and skills)")
        ] = Path(),
        global_root: Annotated[
            Path | None, typer.Option("--global-root", help="Shared global root; defaults to ~/.agents")
        ] = None,
        source: Annotated[
            Path | None,
            typer.Option("--source", help="Measure a dot source checkout instead of installed global files"),
        ] = None,
        check: Annotated[
            bool,
            typer.Option(
                "--check",
                help="Exit 1 at 3500 discovery tokens combined or 5000 instruction + discovery tokens per scope",
            ),
        ] = False,
        details: Annotated[
            bool,
            typer.Option("--details", help="Include source paths, on-demand file costs, and coverage in text output"),
        ] = False,
        as_json: JsonOption = False,
    ) -> None:
        if source is not None and global_root is not None:
            raise typer.BadParameter("choose --source or --global-root, not both")
        report = context_report(project, global_root=global_root, source=source)
        if as_json:
            typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_report(report, details=details)
        if check and not report["passed"]:
            raise typer.Exit(1)
