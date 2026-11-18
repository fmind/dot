"""Offline, portable estimates of shared agent instruction and discovery costs."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Any, Literal

import yaml

from fmind_dot.command import Parser, add_json
from fmind_dot.errors import DotError, UsageError
from fmind_dot.reporting import display_path, write_json, write_report_line
from fmind_dot.state import State

CONTEXT_TOKEN_LIMIT = 5_000
SUBAGENT_TOKEN_LIMIT = 2_000
MAX_INPUT_BYTES = 1 << 20
Scope = Literal["global", "local"]
EntryKind = Literal["agents", "skill", "subagent"]
DUPLICATE_GUIDANCE = (
    "Hosts resolve duplicate skill names differently (scope precedence, both listed, or an arbitrary winner). "
    "Rename one skill or remove a copy so each name is unique across global and local scopes."
)
DUPLICATE_SUBAGENT_GUIDANCE = (
    "Hosts resolve duplicate subagent names differently (scope precedence, both listed, or an arbitrary winner). "
    "Rename one subagent or remove a copy so each name is unique across global and local scopes."
)


def estimated_tokens(characters: int) -> int:
    return (characters + 3) // 4


@dataclass(frozen=True)
class ContextEntry:
    scope: Scope
    kind: EntryKind
    name: str
    path: str
    characters: int
    discovery_characters: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {
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
    normalized = text.replace("\r\n", "\n") + ("\n" if text.replace("\r\n", "\n").endswith("\n---") else "")
    if not normalized.startswith("---\n") or "\n---\n" not in normalized[4:]:
        raise DotError(f"{path}: frontmatter must be bounded by --- lines")
    raw, body = normalized[4:].split("\n---\n", 1)
    try:
        metadata = yaml.safe_load(raw)
    except (yaml.YAMLError, RecursionError) as error:
        raise DotError(f"{path}: invalid frontmatter; repair its YAML") from error
    if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
        raise DotError(f"{path}: frontmatter must be a string-keyed mapping")
    return metadata, body


def _skill_entry(path: Path, scope: Scope, catalog: Path) -> ContextEntry:
    text = _read(path)
    metadata, _ = parse_frontmatter(text, path)
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or name != path.parent.name:
        raise DotError(f"invalid skill name: {path}; match its directory name")
    if not isinstance(description, str) or not description.strip():
        raise DotError(f"missing skill description: {path}; describe its capability and trigger")
    prefix = "~/.agents/skills" if scope == "global" else ".agents/skills"
    index_line = f"- {name}: {' '.join(description.split())} (file: {prefix}/{path.relative_to(catalog).as_posix()})\n"
    return ContextEntry(scope, "skill", name, str(path), len(text), len(index_line))


def _subagent_entry(path: Path, scope: Scope) -> ContextEntry:
    text = _read(path)
    metadata, _ = parse_frontmatter(text, path)
    name, description = metadata.get("name"), metadata.get("description")
    if not isinstance(name, str) or name != path.stem:
        raise DotError(f"invalid subagent name: {path}; match its file stem")
    if not isinstance(description, str) or not description.strip():
        raise DotError(f"missing subagent description: {path}; describe its role and scope")
    index_line = f"- {name}: {' '.join(description.split())}\n"
    return ContextEntry(scope, "subagent", name, str(path), len(text), len(index_line))


def _walk_catalog(
    root: Path, label: str, *, skip_dirs: frozenset[str] = frozenset(), skip_underscore: bool = False
) -> Iterator[Path]:
    if not root.exists() and not root.is_symlink():
        return
    if not root.is_dir():
        raise DotError(f"invalid {label} directory: {root}; repair or remove the broken link")
    pending: list[tuple[Path, frozenset[Path]]] = [(root, frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        if (resolved := directory.resolve()) in ancestors:
            raise DotError(f"cyclic {label} directory: {directory}; remove the recursive link")
        try:
            children = sorted(directory.iterdir())
        except OSError as error:
            raise DotError(f"cannot inspect {label} directory: {directory}; check its permissions") from error
        for path in children:
            if path.name.startswith(".") or path.name in skip_dirs:
                continue
            if path.is_symlink() and not path.exists():
                raise DotError(f"broken {label} link: {path}; repair or remove the retired link")
            if skip_underscore and path.name.startswith("_"):
                continue
            if path.is_dir():
                pending.append((path, ancestors | {resolved}))
            else:
                yield path


def _scope_entries(agents: Path, skills: Path, subagents: Path, scope: Scope) -> list[ContextEntry]:
    entries = (
        [ContextEntry(scope, "agents", "AGENTS.md", str(agents), len(_read(agents)))]
        if agents.exists() or agents.is_symlink()
        else []
    )
    entries.extend(
        _skill_entry(path, scope, skills)
        for path in _walk_catalog(skills, "skill", skip_dirs=frozenset({"synced"}))
        if path.name == "SKILL.md"
    )
    entries.extend(
        _subagent_entry(path, scope)
        for path in _walk_catalog(subagents, "subagent", skip_underscore=True)
        if path.suffix == ".md"
    )
    return entries


def _totals(entries: list[ContextEntry]) -> dict[str, int]:
    agents = sum(e.characters for e in entries if e.kind == "agents")
    skills = sum(e.discovery_characters for e in entries if e.kind == "skill")
    subagents = sum(e.discovery_characters for e in entries if e.kind == "subagent")
    skill_body = sum(e.characters for e in entries if e.kind == "skill")
    subagent_body = sum(e.characters for e in entries if e.kind == "subagent")
    return {
        "agents_files": sum(e.kind == "agents" for e in entries),
        "skills": sum(e.kind == "skill" for e in entries),
        "subagents": sum(e.kind == "subagent" for e in entries),
        "agents_characters": agents,
        "agents_estimated_tokens": estimated_tokens(agents),
        "skill_index_characters": skills,
        "skill_index_estimated_tokens": estimated_tokens(skills),
        "subagent_index_characters": subagents,
        "subagent_index_estimated_tokens": estimated_tokens(subagents),
        "context_estimated_tokens": estimated_tokens(agents + skills),
        "startup_estimated_tokens": estimated_tokens(agents + skills + subagents),
        "on_demand_skill_file_estimated_tokens": estimated_tokens(skill_body),
        "on_demand_subagent_file_estimated_tokens": estimated_tokens(subagent_body),
    }


def _duplicates(entries: list[ContextEntry], kind: EntryKind) -> list[dict[str, Any]]:
    by_name: dict[str, list[str]] = {}
    for entry in entries:
        if entry.kind == kind:
            by_name.setdefault(entry.name, []).append(entry.path)
    return [{"name": name, "paths": paths} for name, paths in sorted(by_name.items()) if len(paths) > 1]


def _budget(estimated: int, limit: int) -> dict[str, Any]:
    return {
        "limit_exclusive": limit,
        "estimated_tokens": estimated,
        "remaining": limit - 1 - estimated,
        "passed": estimated < limit,
    }


def _resolve_root(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise DotError(f"invalid path {path}: {error}") from error


def context_report(project: Path, *, global_root: Path | None = None, source: Path | None = None) -> dict[str, Any]:
    if not (project := _resolve_root(project)).is_dir():
        raise DotError(f"project directory does not exist: {project}")
    if source is not None:
        src = _resolve_root(source)
        if not (src / "skills").is_dir() or not (src / "dot_agents/AGENTS.md").is_file():
            raise DotError(f"invalid dot source: {src}; expected skills/ and dot_agents/AGENTS.md")
        global_agents, global_skills, global_subagents = (
            src / "dot_agents/AGENTS.md",
            src / "skills",
            src / "dot_agents/supagents",
        )
    else:
        root = _resolve_root(global_root or Path("~/.agents"))
        global_agents, global_skills, global_subagents = root / "AGENTS.md", root / "skills", root / "supagents"
    local_agents, local_skills, local_subagents = (
        project / "AGENTS.md",
        project / ".agents/skills",
        project / ".agents/supagents",
    )
    global_entries = _scope_entries(global_agents, global_skills, global_subagents, "global")
    local_entries = _scope_entries(local_agents, local_skills, local_subagents, "local")
    seen = {Path(e.path).resolve(): e for e in reversed([*global_entries, *local_entries])}
    combined = list(reversed(list(seen.values())))
    duplicates = _duplicates(combined, "skill")
    duplicate_subagents = _duplicates(combined, "subagent")
    totals = {"global": _totals(global_entries), "local": _totals(local_entries), "combined": _totals(combined)}
    budgets = {s: _budget(totals[s]["context_estimated_tokens"], CONTEXT_TOKEN_LIMIT) for s in ("global", "local")}
    subagent_budgets = {
        s: _budget(totals[s]["subagent_index_estimated_tokens"], SUBAGENT_TOKEN_LIMIT) for s in ("global", "local")
    }
    return {
        "schema": "dot.context/v6",
        "measurement": "ceil(characters / 4); portable estimate, not host tokenization or billing",
        "coverage": "Shared roots only; excludes host/plugin catalogs, ancestor/nested instructions and references. Combined counts identical resolved files once; distinct same-name skills or subagents both count and fail --check.",
        "roots": {
            "global": {"agents": str(global_agents), "skills": str(global_skills), "subagents": str(global_subagents)},
            "local": {"agents": str(local_agents), "skills": str(local_skills), "subagents": str(local_subagents)},
        },
        "totals": totals,
        "budgets": budgets,
        "subagent_budgets": subagent_budgets,
        "passed": (
            all(b["passed"] for b in [*budgets.values(), *subagent_budgets.values()])
            and not duplicates
            and not duplicate_subagents
        ),
        "duplicates": duplicates,
        "duplicate_subagents": duplicate_subagents,
        "entries": [entry.to_dict() for entry in [*global_entries, *local_entries]],
    }


def _print_table(out: IO[str], report: dict[str, Any]) -> None:
    headers = ("Scope", "AGENTS.md", "Skills", "Context", "Left", "Subagents", "Sub left", "Startup", "Status")
    rows: list[tuple[str, ...]] = []
    for scope, totals in report["totals"].items():
        budget, sub_budget = report["budgets"].get(scope), report["subagent_budgets"].get(scope)
        if budget and sub_budget:
            rem, srem = f"{budget['remaining']:,}", f"{sub_budget['remaining']:,}"
            st = "PASS" if budget["passed"] and sub_budget["passed"] else "OVER BUDGET"
        else:
            rem, srem, st = "—", "—", "—"
        rows.append(
            (
                scope.capitalize(),
                f"{totals['agents_estimated_tokens']:,}",
                f"{totals['skill_index_estimated_tokens']:,}",
                f"{totals['context_estimated_tokens']:,}",
                rem,
                f"{totals['subagent_index_estimated_tokens']:,}",
                srem,
                f"{totals['startup_estimated_tokens']:,}",
                st,
            )
        )
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(8)]
    for cells in (headers, *rows):
        cols = [f"{cells[0]:<{widths[0]}}", *(f"{cells[i]:>{widths[i]}}" for i in range(1, 8)), cells[8]]
        out.write(" ".join(cols) + "\n")


def _print_details(out: IO[str], report: dict[str, Any]) -> None:
    for label, field in (
        ("SKILL.md", "on_demand_skill_file_estimated_tokens"),
        ("subagent", "on_demand_subagent_file_estimated_tokens"),
    ):
        out.write(f"\nOn-demand {label} files · estimated tokens, excluded from budget\n")
        for scope, totals in report["totals"].items():
            out.write(f"  {scope.capitalize():<10} {totals[field]:>9,}\n")
    out.write("\nSources\n")
    for scope, roots in report["roots"].items():
        cap = scope.capitalize()
        out.write(f"  {cap + ' AGENTS.md':<17} {display_path(roots['agents'])}\n")
        out.write(f"  {cap + ' skills':<17} {display_path(roots['skills'])}\n")
        out.write(f"  {cap + ' subagents':<17} {display_path(roots['subagents'])}\n")
    out.write("\n")
    write_report_line(out, report["coverage"])


def _print_report(out: IO[str], report: dict[str, Any], *, details: bool) -> None:
    def put(text: str = "") -> None:
        write_report_line(out, text)

    t = report["totals"]
    put("Agent context · estimated tokens")
    put(
        f"Budgets: AGENTS.md + skills below {CONTEXT_TOKEN_LIMIT:,}; subagents below {SUBAGENT_TOKEN_LIMIT:,} (per scope)."
    )
    put()
    _print_table(out, report)
    put()
    put(
        f"Skill index: names, descriptions, and paths ({t['global']['skills']:,} global, {t['local']['skills']:,} local skills)."
    )
    put(
        f"Subagent index: names and descriptions ({t['global']['subagents']:,} global, {t['local']['subagents']:,} local subagents)."
    )
    put(
        f"Combined discovery: {t['combined']['skill_index_estimated_tokens']:,} skill, "
        f"{t['combined']['subagent_index_estimated_tokens']:,} subagent estimated tokens (informational)"
    )
    put("Combined startup is informational. On-demand bodies and host/plugin catalogs are excluded.")
    put("Estimated at ~4 characters/token; exact counts vary by model. Totals round independently.")
    for title, items, guidance in (
        ("Duplicate skill names · FAIL (both counted)", report["duplicates"], DUPLICATE_GUIDANCE),
        ("Duplicate subagent names · FAIL (both counted)", report["duplicate_subagents"], DUPLICATE_SUBAGENT_GUIDANCE),
    ):
        if not items:
            continue
        out.write(f"\n{title}\n")
        for item in items:
            out.write(f"  {item['name']}\n")
            out.writelines(f"    {display_path(path)}\n" for path in item["paths"])
        put(guidance)
    if details:
        _print_details(out, report)
    else:
        put("Use --details for source paths, on-demand costs, and coverage.")


def _write_check_errors(err: IO[str], report: dict[str, Any]) -> None:
    for scope, b in report["budgets"].items():
        if not b["passed"]:
            err.write(
                f"{scope.capitalize()} context budget exceeded: {b['estimated_tokens']:,} >= "
                f"{b['limit_exclusive']:,} estimated tokens; trim AGENTS.md or skill descriptions.\n"
            )
    for scope, b in report["subagent_budgets"].items():
        if not b["passed"]:
            err.write(
                f"{scope.capitalize()} subagent budget exceeded: {b['estimated_tokens']:,} >= "
                f"{b['limit_exclusive']:,} estimated tokens; trim subagent descriptions.\n"
            )
    if report["duplicates"]:
        names = ", ".join(i["name"] for i in report["duplicates"])
        err.write(f"Duplicate skill names: {names}. {DUPLICATE_GUIDANCE}\n")
    if report["duplicate_subagents"]:
        names = ", ".join(i["name"] for i in report["duplicate_subagents"])
        err.write(f"Duplicate subagent names: {names}. {DUPLICATE_SUBAGENT_GUIDANCE}\n")


def _context(state: State, args: argparse.Namespace) -> None:
    for flag, value in (("--project", args.project), ("--source", args.source)):
        if value is not None:
            try:
                value.expanduser()
            except RuntimeError:
                raise UsageError(f"{flag}: {value}") from None
    report = context_report(args.project, source=args.source)
    if args.as_json:
        write_json(state.stdout, report)
        if args.check and not report["passed"]:
            _write_check_errors(state.stderr, report)
    elif args.check and report["passed"] and not args.details:
        ctx = ", ".join(f"{s} {b['estimated_tokens']:,}" for s, b in report["budgets"].items())
        sub = ", ".join(f"{s} {b['estimated_tokens']:,}" for s, b in report["subagent_budgets"].items())
        state.stdout.write(
            f"PASS · context below {CONTEXT_TOKEN_LIMIT:,} ({ctx}); subagents below {SUBAGENT_TOKEN_LIMIT:,} ({sub})\n"
        )
    else:
        _print_report(state.stdout, report, details=args.details)
    if args.check and not report["passed"]:
        raise SystemExit(1)


def register(commands: Parser) -> None:
    desc = (
        "Measure global, project, and combined AGENTS.md, skill, and subagent discovery costs; report duplicate names"
    )
    epilog = (
        "Exit codes: 0 report or passing --check; 1 failed --check or invalid/unreadable input; 2 usage error.\n\n"
        "Examples: dot context --check · dot context --source . --project . --details · dot context --check --json"
    )
    c = commands.command("context", desc, _context, config=False, epilog=epilog)
    proj_help = "Project root (only its own instructions, skills, and subagents) [default: .]"
    c.add_argument("-p", "--project", type=Path, default=Path(), metavar="PATH", help=proj_help)
    src_help = "Measure a dot source checkout instead of installed global files"
    c.add_argument("--source", type=Path, metavar="PATH", help=src_help)
    chk_help = (
        f"Exit 1 at {CONTEXT_TOKEN_LIMIT:,} instruction + skill or {SUBAGENT_TOKEN_LIMIT:,} subagent tokens per scope, "
        "or on duplicate names"
    )
    c.add_argument("--check", action="store_true", help=chk_help)
    det_help = "Include source paths, on-demand file costs, and coverage in text output"
    c.add_argument("--details", action="store_true", help=det_help)
    add_json(c)
