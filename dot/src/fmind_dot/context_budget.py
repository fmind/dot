"""Offline, portable estimates of shared agent instruction and discovery costs."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Any, Literal

import yaml
from yaml.constructor import ConstructorError
from yaml.resolver import BaseResolver

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


_FRONTMATTER_FENCE_RE = re.compile(r"---[ \t]*")


class UniqueKeySafeLoader(yaml.SafeLoader):
    """Reject duplicate YAML mapping keys so shadowed frontmatter names fail closed."""


def _construct_unique_mapping(loader: UniqueKeySafeLoader, node: yaml.Node, deep: bool = False) -> dict[Any, Any]:
    if not isinstance(node, yaml.MappingNode):
        raise ConstructorError(None, None, f"expected a mapping node, but found {type(node).__name__}", node.start_mark)
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        try:
            seen = key in mapping
        except TypeError as error:
            raise ConstructorError(
                "while constructing a mapping", node.start_mark, "found unhashable key", key_node.start_mark
            ) from error
        if seen:
            raise ConstructorError(
                "while constructing a mapping", node.start_mark, f"duplicate YAML key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def parse_frontmatter(text: str, path: Path | str) -> tuple[dict[str, Any], str]:
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").splitlines()
    if not lines or _FRONTMATTER_FENCE_RE.fullmatch(lines[0]) is None:
        raise DotError(f"{path}: frontmatter must be bounded by --- lines")
    closing = next((i for i in range(1, len(lines)) if _FRONTMATTER_FENCE_RE.fullmatch(lines[i])), None)
    if closing is None:
        raise DotError(f"{path}: frontmatter must be bounded by --- lines")
    raw = "\n".join(lines[1:closing])
    body = "\n".join(lines[closing + 1 :])
    try:
        metadata = yaml.load(raw, Loader=UniqueKeySafeLoader)  # noqa: S506 - SafeLoader subclass
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
    root: Path,
    label: str,
    *,
    skip_dirs: frozenset[str] = frozenset(),
    skip_underscore: bool = False,
    include_hidden: bool = False,
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
            if (not include_hidden and path.name.startswith(".")) or path.name in skip_dirs:
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


def _host_agent_names(path: Path, root: Path) -> set[str]:
    """Infer host-discovered agent identifiers from filename convention and strict frontmatter."""
    names: set[str] = set()
    lower_name = path.name.lower()
    if lower_name.endswith(".agent.md"):
        names.add(path.name[: -len(".agent.md")])
    elif lower_name == "agent.md" and path.parent != root:
        names.add(path.parent.name)
    else:
        names.add(path.stem)
    text = _read(path)
    lines = text.removeprefix("\ufeff").replace("\r\n", "\n").splitlines()
    if lines and _FRONTMATTER_FENCE_RE.fullmatch(lines[0]):
        meta, _ = parse_frontmatter(text, path)
        declared = meta.get("name")
        if isinstance(declared, str) and declared.strip():
            names.add(declared.strip())
    return names


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise DotError(f"duplicate JSON key {key!r} in agents manifest")
        obj[key] = value
    return obj


def _project_agents_manifest_dirs(project: Path) -> list[Path]:
    """Inspect .agents/agents.json fail-closed and return declared in-repo agent directories."""
    manifest = project / ".agents/agents.json"
    if not manifest.exists() and not manifest.is_symlink():
        return []
    if manifest.is_symlink() or not manifest.is_file():
        raise DotError(f"{manifest}: invalid or symlinked agents manifest; inspect or remove it")
    try:
        parsed = json.loads(_read(manifest), object_pairs_hook=_reject_duplicate_json_keys)
    except json.JSONDecodeError as error:
        raise DotError(f"{manifest}: invalid JSON in agents manifest; inspect or remove it") from error

    if isinstance(parsed, dict):
        unknown = set(parsed) - {"entries", "directories"}
        if unknown:
            raise DotError(f"{manifest}: unsupported agents.json keys ({', '.join(sorted(unknown))}); inspect it")
        raw_items: list[Any] = []
        for key in ("entries", "directories"):
            val = parsed.get(key)
            if val is not None:
                if not isinstance(val, list):
                    raise DotError(f"{manifest}: {key} must be a list")
                raw_items.extend(val)
    elif isinstance(parsed, list):
        raw_items = parsed
    else:
        raise DotError(f"{manifest}: agents.json must be a JSON object or array")

    project_resolved = project.resolve()
    dirs: list[Path] = []
    for item in raw_items:
        raw_path: object
        if isinstance(item, str):
            raw_path = item
        elif isinstance(item, dict):
            extra = set(item) - {"path", "dir", "include_only", "exclude"}
            if extra:
                raise DotError(f"{manifest}: unsupported entry keys ({', '.join(sorted(extra))})")
            if "path" in item and "dir" in item:
                raise DotError(f"{manifest}: entry must not specify both 'path' and 'dir'")
            raw_path = item.get("path") if "path" in item else item.get("dir")
        else:
            raise DotError(f"{manifest}: invalid entry in agents.json")
        if not isinstance(raw_path, str) or not raw_path.strip() or raw_path.startswith("~"):
            raise DotError(f"{manifest}: agents.json path must stay relative inside the repository")
        candidate = Path(raw_path)
        parts = tuple(p for p in candidate.parts if p != ".")
        pure_manifest_parent = bool(parts) and parts[0] == ".." and ".." not in parts[1:]
        manifest_dir = manifest.parent
        bases: tuple[Path | None, ...] = (manifest_dir, project) if not candidate.is_absolute() else (None,)
        manifest_exists = False
        for base in bases:
            target = (base / candidate) if base is not None else candidate
            try:
                resolved = target.resolve(strict=False)
            except OSError as error:
                raise DotError(f"{manifest}: cannot resolve agents.json path") from error
            if not resolved.is_relative_to(project_resolved):
                if base != project or not pure_manifest_parent:
                    raise DotError(f"{manifest}: agents.json points outside the repository; inspect or remove it")
                continue
            if base == manifest_dir:
                manifest_exists = target.exists() or target.is_symlink()
            elif manifest_exists and target.exists() and not target.is_dir():
                continue
            if resolved not in dirs:
                dirs.append(resolved)
    return dirs


def _duplicate_subagents(project: Path, entries: list[ContextEntry]) -> list[dict[str, Any]]:
    """Detect duplicate subagent names across supagents/ catalogs and repo-local host agent directories/manifests."""
    display_by_lower: dict[str, str] = {}
    by_lower: dict[str, list[str]] = {}
    resolved_by_lower: dict[str, set[Path]] = {}
    for entry in entries:
        if entry.kind == "subagent":
            low = entry.name.lower()
            display_by_lower.setdefault(low, entry.name)
            by_lower.setdefault(low, []).append(entry.path)
            resolved_by_lower.setdefault(low, set()).add(Path(entry.path).resolve())
    global_lowers = {entry.name.lower() for entry in entries if entry.kind == "subagent" and entry.scope == "global"}
    if global_lowers:
        host_dirs = [project / ".agents/agents", project / ".github/agents", *_project_agents_manifest_dirs(project)]
        for host_dir in host_dirs:
            for path in _walk_catalog(host_dir, "host agent", skip_underscore=False, include_hidden=True):
                if path.suffix.lower() != ".md":
                    continue
                resolved = path.resolve()
                matched = {low for name in _host_agent_names(path, host_dir) if (low := name.lower()) in global_lowers}
                for low in sorted(matched):
                    if resolved not in resolved_by_lower[low]:
                        resolved_by_lower[low].add(resolved)
                        by_lower[low].append(str(path))
    return [
        {"name": display_by_lower[low], "paths": paths}
        for low, paths in sorted(by_lower.items(), key=lambda pair: display_by_lower[pair[0]])
        if len(paths) > 1
    ]


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
    duplicate_subagents = _duplicate_subagents(project, combined)
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


_QUIET_JSON_KEYS = ("schema", "passed", "budgets", "subagent_budgets", "duplicates", "duplicate_subagents")


def _context(state: State, args: argparse.Namespace) -> None:
    if args.quiet and args.details:
        raise UsageError("--quiet cannot be combined with --details")
    for flag, value in (("--project", args.project), ("--source", args.source)):
        if value is not None:
            try:
                value.expanduser()
            except RuntimeError:
                raise UsageError(f"{flag}: {value}") from None
    report = context_report(args.project, source=args.source)
    if args.as_json:
        out = {k: report[k] for k in _QUIET_JSON_KEYS} if args.quiet else report
        write_json(state.stdout, out)
        if args.check and not report["passed"]:
            _write_check_errors(state.stderr, report)
    elif (args.check or args.quiet) and report["passed"] and not args.details:
        ctx = ", ".join(f"{s} {b['estimated_tokens']:,}" for s, b in report["budgets"].items())
        sub = ", ".join(f"{s} {b['estimated_tokens']:,}" for s, b in report["subagent_budgets"].items())
        state.stdout.write(
            f"PASS · context below {CONTEXT_TOKEN_LIMIT:,} ({ctx}); subagents below {SUBAGENT_TOKEN_LIMIT:,} ({sub})\n"
        )
    elif args.quiet and not report["passed"]:
        _write_check_errors(state.stdout, report)
    else:
        _print_report(state.stdout, report, details=args.details)
    if args.check and not report["passed"]:
        raise SystemExit(1)
