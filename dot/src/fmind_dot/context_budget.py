"""Offline, portable estimates of shared agent instruction and discovery costs."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Any, Literal

import yaml

from fmind_dot.command import Parser, add_json
from fmind_dot.errors import DotError, UsageError
from fmind_dot.reporting import display_path, write_json, write_report_line
from fmind_dot.state import State

CONTEXT_TOKEN_LIMIT = 5_000
MAX_INPUT_BYTES = 1 << 20
Scope = Literal["global", "local"]
DUPLICATE_GUIDANCE = (
    "Hosts resolve duplicate skill names differently (scope precedence, both listed, or an arbitrary winner). "
    "Rename one skill or remove a copy so each name is unique across global and local scopes."
)


def estimated_tokens(characters: int) -> int:
    return (characters + 3) // 4


@dataclass(frozen=True)
class ContextEntry:
    scope: Scope
    kind: Literal["agents", "skill"]
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


def _scope_entries(agents: Path, skills: Path, scope: Scope) -> list[ContextEntry]:
    entries = (
        [ContextEntry(scope, "agents", "AGENTS.md", str(agents), len(_read(agents)))]
        if agents.exists() or agents.is_symlink()
        else []
    )
    if not skills.exists() and not skills.is_symlink():
        return entries
    if not skills.is_dir():
        raise DotError(f"invalid skill directory: {skills}; repair or remove the broken link")
    pending: list[tuple[Path, frozenset[Path]]] = [(skills, frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        if (resolved := directory.resolve()) in ancestors:
            raise DotError(f"cyclic skill directory: {directory}; remove the recursive link")
        try:
            children = sorted(directory.iterdir())
        except OSError as error:
            raise DotError(f"cannot inspect skill directory: {directory}; check its permissions") from error
        for path in children:
            if path.name.startswith(".") or path.name == "synced":
                continue
            if path.is_symlink() and not path.exists():
                raise DotError(f"broken skill link: {path}; repair or remove the retired link")
            if path.is_dir():
                pending.append((path, ancestors | {resolved}))
            elif path.name == "SKILL.md":
                entries.append(_skill_entry(path, scope, skills))
    return entries


def _totals(entries: list[ContextEntry]) -> dict[str, int]:
    agents = sum(e.characters for e in entries if e.kind == "agents")
    skills = sum(e.discovery_characters for e in entries)
    body = sum(e.characters for e in entries if e.kind == "skill")
    return {
        "agents_files": sum(e.kind == "agents" for e in entries),
        "skills": sum(e.kind == "skill" for e in entries),
        "agents_characters": agents,
        "agents_estimated_tokens": estimated_tokens(agents),
        "skill_index_characters": skills,
        "skill_index_estimated_tokens": estimated_tokens(skills),
        "startup_estimated_tokens": estimated_tokens(agents + skills),
        "on_demand_skill_file_estimated_tokens": estimated_tokens(body),
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
        global_agents, global_skills = src / "dot_agents/AGENTS.md", src / "skills"
    else:
        root = _resolve_root(global_root or Path.home() / ".agents")
        global_agents, global_skills = root / "AGENTS.md", root / "skills"
    global_entries = _scope_entries(global_agents, global_skills, "global")
    local_entries = _scope_entries(project / "AGENTS.md", project / ".agents/skills", "local")
    seen = {Path(e.path).resolve(): e for e in reversed([*global_entries, *local_entries])}
    combined = list(reversed(list(seen.values())))
    by_name: dict[str, list[str]] = {}
    for entry in combined:
        if entry.kind == "skill":
            by_name.setdefault(entry.name, []).append(entry.path)
    duplicates = [{"name": name, "paths": paths} for name, paths in sorted(by_name.items()) if len(paths) > 1]
    totals = {"global": _totals(global_entries), "local": _totals(local_entries), "combined": _totals(combined)}
    budgets = {
        s: {
            "limit_exclusive": CONTEXT_TOKEN_LIMIT,
            "estimated_tokens": (est := totals[s]["startup_estimated_tokens"]),
            "remaining": CONTEXT_TOKEN_LIMIT - 1 - est,
            "passed": est < CONTEXT_TOKEN_LIMIT,
        }
        for s in ("global", "local")
    }
    return {
        "schema": "dot.context/v5",
        "measurement": "ceil(characters / 4); portable estimate, not host tokenization or billing",
        "coverage": "Shared roots only; excludes host/plugin catalogs, ancestor/nested instructions and references. Combined counts identical resolved files once; distinct same-name skills both count and fail --check.",
        "roots": {
            "global": {"agents": str(global_agents), "skills": str(global_skills)},
            "local": {"agents": str(project / "AGENTS.md"), "skills": str(project / ".agents/skills")},
        },
        "totals": totals,
        "budgets": budgets,
        "passed": all(b["passed"] for b in budgets.values()) and not duplicates,
        "duplicates": duplicates,
        "entries": [entry.to_dict() for entry in [*global_entries, *local_entries]],
    }


def _print_report(out: IO[str], report: dict[str, Any], *, details: bool) -> None:
    def put(text: str = "") -> None:
        write_report_line(out, text)

    t = report["totals"]
    put("Agent context · estimated tokens")
    put(f"Budget: below {CONTEXT_TOKEN_LIMIT:,} tokens for global and local, separately.")
    put()
    put(f"{'Scope':<10} {'AGENTS.md':>9} {'Skill index':>11} {'Total':>7} {'Remaining':>10}  Status")
    for scope, totals in t.items():
        budget = report["budgets"].get(scope)
        rem, st = (f"{budget['remaining']:,}", "PASS" if budget["passed"] else "OVER BUDGET") if budget else ("—", "—")
        put(
            f"{scope.capitalize():<10} {totals['agents_estimated_tokens']:>9,} {totals['skill_index_estimated_tokens']:>11,} {totals['startup_estimated_tokens']:>7,} {rem:>10}  {st}"
        )
    put()
    put(
        f"Skill index: names, descriptions, and paths ({t['global']['skills']:,} global, {t['local']['skills']:,} local skills)."
    )
    put(f"Combined discovery: {t['combined']['skill_index_estimated_tokens']:,} estimated tokens (informational)")
    put("Combined startup is informational. On-demand bodies and host/plugin catalogs are excluded.")
    put("Estimated at ~4 characters/token; exact counts vary by model. Totals round independently.")
    if report["duplicates"]:
        put()
        put("Duplicate skill names · FAIL (both counted)")
        for item in report["duplicates"]:
            put(f"  {item['name']}")
            for path in item["paths"]:
                put(f"    {display_path(path)}")
        put(DUPLICATE_GUIDANCE)
    if details:
        put()
        put("On-demand SKILL.md files · estimated tokens, excluded from budget")
        for s, v in t.items():
            put(f"  {s.capitalize():<10} {v['on_demand_skill_file_estimated_tokens']:>9,}")
        put()
        put("Sources")
        for s, roots in report["roots"].items():
            put(f"  {s.capitalize() + ' AGENTS.md':<17} {display_path(roots['agents'])}")
            put(f"  {s.capitalize() + ' skills':<17} {display_path(roots['skills'])}")
        put()
        put(report["coverage"])
    else:
        put("Use --details for source paths, on-demand costs, and coverage.")


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
        if args.check and report["duplicates"]:
            names = ", ".join(i["name"] for i in report["duplicates"])
            state.stderr.write(f"Duplicate skill names: {names}. {DUPLICATE_GUIDANCE}\n")
    elif args.check and report["passed"] and not args.details:
        scopes = ", ".join(f"{scope} {b['estimated_tokens']:,}" for scope, b in report["budgets"].items())
        state.stdout.write(f"PASS · context below {CONTEXT_TOKEN_LIMIT:,} estimated tokens ({scopes})\n")
    else:
        _print_report(state.stdout, report, details=args.details)
    if args.check and not report["passed"]:
        raise SystemExit(1)


def register(commands: Parser) -> None:
    desc = "Measure global, project, and combined AGENTS.md and skill discovery costs; report duplicate skill names"
    c = commands.command("context", desc, _context, config=False)
    proj_help = "Project root (only its own instructions and skills)"
    c.add_argument("-p", "--project", type=Path, default=Path(), metavar="PATH", help=proj_help)
    src_help = "Measure a dot source checkout instead of installed global files"
    c.add_argument("--source", type=Path, metavar="PATH", help=src_help)
    chk_help = f"Exit 1 at {CONTEXT_TOKEN_LIMIT} instruction + discovery tokens in either global or local scope, or on duplicate skill names"
    c.add_argument("--check", action="store_true", help=chk_help)
    det_help = "Include source paths, on-demand file costs, and coverage in text output"
    c.add_argument("--details", action="store_true", help=det_help)
    add_json(c)
