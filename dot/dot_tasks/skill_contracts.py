"""Validate first-party skill packages; lychee checks Markdown links in `check:skills`."""

from __future__ import annotations

import argparse
import ast
import contextlib
import os
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

import fmind_dot.context_budget as cb
from dot_tasks import ROOT
from fmind_dot.errors import DotError
from fmind_dot.private_files import write_atomic_file

MAX_DESCRIPTION = 180
MAX_MARKDOWN_TOKENS = 1_500
MAX_NAME = 64
MAX_SKILL_LINES = 500
SKILL_KINDS = ("connector", "task", "collection")
GUIDE_START = "<!-- guides:start -->"
GUIDE_END = "<!-- guides:end -->"
_REQ_META = ("author", "source", "created", "updated")

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SUPAGENT_REF = re.compile(r"\bfmind-review-[a-z0-9-]+\b")
_TASK_GUIDES_HEADING = re.compile(r"^## Task guides\b", re.MULTILINE)
_DOT_SOURCE_PREFIX = "github.com/fmind/dot/tree/main/"
_SCRIPT_MIN_PY = (3, 10)
_GIT_ENV_STRIP = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    }
)
FRONTMATTER_FIELDS = {
    "allowed-tools",
    "compatibility",
    "description",
    "disable-model-invocation",
    "license",
    "metadata",
    "name",
}
RESOURCE_DIRECTORIES = {"assets", "references", "scripts", "templates"}
MARKDOWN = MarkdownIt("commonmark")

_BUDGET_HINT = "reduce instructions or discovery without losing task triggers"
_MISSING_GUIDE = f"add {GUIDE_START} and {GUIDE_END} markers for the guide index"


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _is_unsafe_char(ch: str) -> bool:
    n = ord(ch)
    lo = (n < 32 and ch not in "\n\r\t") or n == 127
    return lo or unicodedata.category(ch) == "Cf" or 0xFE00 <= n <= 0xFE0F or 0xE0100 <= n <= 0xE01EF


def _read_utf8(path: Path, rel: str, verb: str = "cannot read") -> tuple[str | None, list[str]]:
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return None, [f"{rel}: {'is not UTF-8' if isinstance(error, UnicodeDecodeError) else verb}: {error}"]
    if not (unsafe := [c for c in set(text) if _is_unsafe_char(c)]):
        return text, []
    ch = min(unsafe, key=text.index)
    kind = "unsafe control character" if ch.isascii() else "bidirectional or invisible Unicode"
    return text, [f"{rel}: {kind} U+{ord(ch):04X}"]


def _token_errors(rel: str, text: str) -> list[str]:
    if (tokens := cb.estimated_tokens(len(text))) >= MAX_MARKDOWN_TOKENS:
        return [f"{rel}: has {tokens} estimated tokens; must be below {MAX_MARKDOWN_TOKENS}"]
    return []


def _discover_skills(root: Path) -> tuple[list[tuple[str, Path]], list[str]]:
    skills, by_name, findings = [], {}, []
    for catalog in (p for rel in ("skills", ".agents/skills") if (p := root / rel).is_dir()):
        for d in sorted(catalog.iterdir()):
            if d.is_symlink() or (d.is_dir() and (skill := d / "SKILL.md").is_symlink()):
                findings.append(f"{_relative(root, d if d.is_symlink() else skill)}: symbolic link is not allowed")
            elif d.is_dir() and not skill.exists():
                if any(p.is_symlink() or (p.is_file() and p.suffix not in {".pyc", ".pyo"}) for p in d.rglob("*")):
                    findings.append(f"{_relative(root, d)}: skill root has files but no SKILL.md")
            elif d.is_dir():
                if prior := by_name.get(d.name):
                    a, b = _relative(root, prior), _relative(root, skill)
                    findings.append(f"duplicate skill directory {d.name!r} in {a} and {b}; {cb.DUPLICATE_GUIDANCE}")
                else:
                    by_name[d.name] = skill
                skills.append((d.name, skill))
    return skills, findings


def _frontmatter(path: Path, root: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    rel = _relative(root, path)
    text, errors = _read_utf8(path, rel)
    if text is None or errors:
        return None, text or "", errors
    if len(text.splitlines()) > MAX_SKILL_LINES:
        return None, text, [f"{rel}: exceeds the {MAX_SKILL_LINES}-line limit"]
    if tok_err := _token_errors(rel, text):
        return None, text, tok_err
    try:
        meta, body = cb.parse_frontmatter(text, rel)
        return meta, body, []
    except DotError as error:
        return None, text, [str(error)]


def _reachable_resources(
    skill: Path,
    texts: dict[Path, str],
    resources: set[Path],
    *,
    cached_targets: Mapping[Path, tuple[str, ...]] | None = None,
) -> set[Path]:
    """Follow document-relative disclosures; disconnected reference cycles stay orphaned."""
    resolved_resources = {res: res.resolve() for res in resources}
    reached, pending = {skill}, [skill]
    while pending:
        doc = pending.pop()
        doc_text = texts[doc]
        targets = cached_targets[doc] if cached_targets and doc in cached_targets else _document_targets(doc_text)
        urls = (urlsplit(t) for t in targets)
        linked = {(doc.parent / unquote(u.path)).resolve() for u in urls if not u.scheme and not u.netloc and u.path}
        for res in resources - reached:
            if resolved_resources[res] in linked:
                hit = True
            else:
                rel_str = Path(os.path.relpath(res, doc.parent)).as_posix()
                if rel_str not in doc_text:
                    hit = False
                else:
                    pat = rf"(?<![A-Za-z0-9_.+\-/])(?:\./)?{re.escape(rel_str)}(?![A-Za-z0-9_.+\-/])"
                    hit = bool(re.search(pat, doc_text))
            if hit:
                reached.add(res)
                if res in texts and res.suffix == ".md" and "templates" not in res.relative_to(skill.parent).parts[:-1]:
                    pending.append(res)
    return reached


def _guides(directory: Path) -> list[Path]:
    """Guide metadata is authoritative; no parallel metadata.guides inventory."""
    refs = directory / "references"
    if refs.is_symlink() or not refs.is_dir():
        return []
    guides: list[Path] = []
    for path in sorted(refs.rglob("*.md")):
        if path.is_symlink() or not path.is_file() or "templates" in path.relative_to(directory).parts[:-1]:
            continue
        hdr = (data := path.read_bytes()).split(b"\n---", 1)[0]
        if path.name == "GUIDE.md" or (data.startswith(b"---\n") and b"\nname:" in hdr and b"\nlicense:" not in hdr):
            guides.append(path)
    return guides


def _bad_markers(text: str) -> bool:
    has_start, has_end = GUIDE_START in text, GUIDE_END in text
    return has_start != has_end or (has_start and text.index(GUIDE_START) > text.index(GUIDE_END))


def _guide_entries(directory: Path, root: Path) -> tuple[list[tuple[Path, dict[str, Any] | None]], list[str]]:
    entries: list[tuple[Path, dict[str, Any] | None]] = []
    errors: list[str] = []
    for path in _guides(directory):
        meta, _, guide_errors = _frontmatter(path, root)
        errors.extend(guide_errors)
        entries.append((path, meta))
    return entries, errors


def _guide_index(
    directory: Path,
    root: Path,
    errors: list[str] | None = None,
    *,
    entries: Sequence[tuple[Path, dict[str, Any] | None]] | None = None,
) -> str:
    if entries is None:
        entries, guide_errors = _guide_entries(directory, root)
        if errors is not None:
            errors.extend(guide_errors)
    lines = [GUIDE_START, ""]
    for path, meta in entries:
        if meta is not None:
            lines.append(f"- [{meta.get('name')}]({path.relative_to(directory).as_posix()}): {meta.get('description')}")
    return "\n".join([*lines, "", GUIDE_END])


def _guide_findings(
    root: Path,
    skill: Path,
    body: str,
    *,
    targets: tuple[str, ...],
    entries: list[tuple[Path, dict[str, Any] | None]],
    entry_errors: list[str],
) -> list[str]:
    findings: list[str] = list(entry_errors)
    rel_skill, names = _relative(root, skill), set()
    for path, meta in entries:
        if meta is None:
            continue
        rel, name = _relative(root, path), path.parent.name if path.name == "GUIDE.md" else path.stem
        if NAME_PATTERN.fullmatch(name) is None or len(name) > MAX_NAME:
            findings.append(f"{rel}: invalid guide name")
        if set(meta) != {"name", "description"}:
            findings.append(f"{rel}: first-party guide frontmatter requires only name and description")
        if meta.get("name") != name:
            findings.append(f"{rel}: guide name must match {name!r}")
        if f"-{skill.parent.name}-" in f"-{name}-":
            findings.append(f"{rel}: guide name {name!r} must not repeat its parent skill")
        if name in names:
            findings.append(f"{rel_skill}: duplicate guide {name!r}")
        names.add(name)
        desc = meta.get("description")
        if not isinstance(desc, str) or not 1 <= len(desc.strip()) <= MAX_DESCRIPTION:
            findings.append(f"{rel}: guide description must contain 1-{MAX_DESCRIPTION} characters")
        if path.relative_to(skill.parent).as_posix() not in targets:
            findings.append(f"{rel}: guide needs a direct link from SKILL.md")
    has_start, has_end = GUIDE_START in body, GUIDE_END in body
    if _bad_markers(body):
        findings.append(f"{rel_skill}: malformed or inverted {GUIDE_START} / {GUIDE_END} markers")
    elif (entries or has_start or "## Task guides" in body) and _guide_index(
        skill.parent, root, entries=entries
    ) not in body:
        hint = "stale guide index; run mise run format:skills" if has_start and has_end else _MISSING_GUIDE
        findings.append(f"{rel_skill}: {hint}")
    return findings


def _script_findings(rel: str, path: Path, text: str) -> list[str]:
    """Enforce Python 3.10+ portability and bytecode hygiene on bundled stdlib scripts."""
    findings: list[str] = []
    try:
        tree = ast.parse(text, filename=rel, feature_version=_SCRIPT_MIN_PY)
    except SyntaxError as error:
        return [f"{rel}: requires Python >3.10 syntax (line {error.lineno}): {error.msg}"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if name == "ArgumentParser" and any(kw.arg == "suggest_on_error" for kw in node.keywords):
                findings.append(
                    f"{rel}: avoid ArgumentParser(suggest_on_error=True) directly; guard via hasattr(parser, 'suggest_on_error') for Python 3.10+ portability"
                )
    siblings = {p.stem for p in path.parent.glob("*.py") if p != path and p.stem != "__init__"}
    if not siblings:
        return findings
    bytecode_disabled_line: int | None = None
    sibling_import_lines = [
        node.lineno
        for node in ast.walk(tree)
        if (isinstance(node, ast.Import) and any(alias.name.split(".", 1)[0] in siblings for alias in node.names))
        or (isinstance(node, ast.ImportFrom) and node.module and node.module.split(".", 1)[0] in siblings)
    ]
    sibling_import_line = min(sibling_import_lines, default=None)
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if (
                    isinstance(tgt, ast.Attribute)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "sys"
                    and tgt.attr == "dont_write_bytecode"
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is True
                ):
                    bytecode_disabled_line = bytecode_disabled_line or stmt.lineno
    if sibling_import_line is not None and (
        bytecode_disabled_line is None or bytecode_disabled_line > sibling_import_line
    ):
        findings.append(f"{rel}: set sys.dont_write_bytecode = True before importing sibling scripts")
    return findings


def _supagent_names(root: Path) -> set[str] | None:
    found: set[str] = set()
    has_dir = False
    for rel in ("dot_agents/supagents", ".agents/supagents"):
        d = root / rel
        if d.is_dir():
            has_dir = True
            found.update(p.stem for p in d.glob("fmind-review-*.md") if p.is_file())
    return found if has_dir else None


def _supagent_ref_findings(rel: str, text: str, valid_supagents: set[str] | None) -> list[str]:
    if valid_supagents is None:
        return []
    unknown = sorted({m.group(0) for m in _SUPAGENT_REF.finditer(text) if m.group(0) not in valid_supagents})
    return [f"{rel}: unknown reviewer supagent reference {name!r}" for name in unknown]


def _resource_findings(
    root: Path,
    skill: Path,
    *,
    skill_body: str,
    skill_targets: tuple[str, ...],
    guide_paths: set[Path],
    valid_supagents: set[str] | None = None,
) -> list[str]:
    directory, rel_skill = skill.parent, _relative(root, skill)
    texts = {skill: skill_body}
    resources, findings = set(), []
    for path in sorted(directory.rglob("*")):
        if path == skill or path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            continue
        rel_pkg = path.relative_to(directory)
        rendered, rel, parent_parts = rel_pkg.as_posix(), _relative(root, path), rel_pkg.parts[:-1]
        try:
            mode = path.stat(follow_symlinks=False).st_mode
        except OSError as error:
            findings.append(f"{rel}: cannot inspect resource: {error}")
            continue
        if stat.S_ISLNK(mode):
            findings.append(f"{rel_skill}: symbolic link {rendered!r} is not allowed")
        elif not stat.S_ISDIR(mode):
            if (first := rel_pkg.parts[0]) not in RESOURCE_DIRECTORIES:
                findings.append(f"{rel}: unsupported package path; use a standard resource directory")
                continue
            if not stat.S_ISREG(mode):
                findings.append(f"{rel_skill}: non-regular resource {rendered!r} is not allowed")
                continue
            if path.name == "SKILL.md":
                findings.append(f"{rel}: nested SKILL.md enters host discovery; use a guide instead")
            if mode & 0o111 and "scripts" not in parent_parts:
                findings.append(f"{rel_skill}: executable outside scripts/ at {rendered!r}")
            resources.add(path)
            if first != "assets":
                text, read_errors = _read_utf8(path, rel, "cannot read resource")
                findings.extend(read_errors)
                if text is not None:
                    is_ref = first == "references" and path.suffix == ".md" and "templates" not in parent_parts
                    if is_ref:
                        findings.extend(_supagent_ref_findings(rel, text, valid_supagents))
                        if _TASK_GUIDES_HEADING.search(text):
                            findings.append(
                                f"{rel}: reserve '## Task guides' for synced SKILL.md indexes; use '## References'"
                            )
                        if path not in guide_paths:
                            if text.startswith(("---\n", "---\r\n")):
                                findings.append(
                                    f"{rel}: supporting reference must not include YAML frontmatter; "
                                    "index it as a guide or remove frontmatter"
                                )
                            findings.extend(_token_errors(rel, text))
                    elif "scripts" in parent_parts and "templates" not in parent_parts and path.suffix == ".py":
                        findings.extend(_script_findings(rel, path, text))
                    texts[path] = text
    unreachable = sorted(
        resources - _reachable_resources(skill, texts, resources, cached_targets={skill: skill_targets})
    )
    findings.extend(f"{_relative(root, p)}: resource is not reachable from SKILL.md" for p in unreachable)
    return findings


def _document_targets(content: str) -> tuple[str, ...]:
    return tuple(
        val
        for token in MARKDOWN.parse(content)
        for cand in (token, *(token.children or ()))
        if (attr := "href" if cand.type == "link_open" else "src" if cand.type == "image" else "")
        and isinstance(val := cand.attrGet(attr), str)
    )


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or _ISO_DATE.fullmatch(value.strip()) is None:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _metadata_findings(relative: str, metadata: Any, *, expected_dir: str | None = None) -> list[str]:
    if not isinstance(metadata, dict):
        return [f"{relative}: metadata must be a mapping"]
    findings: list[str] = []
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
        findings.append(f"{relative}: metadata keys and values must be strings")
    if metadata.get("kind") not in SKILL_KINDS:
        findings.append(f"{relative}: metadata.kind must be connector, task, or collection")
    bad = [f for f in _REQ_META if not isinstance(v := metadata.get(f), str) or not v.strip()]
    findings.extend(f"{relative}: metadata.{f} must be a non-empty string" for f in bad)
    source = metadata.get("source")
    if (
        expected_dir
        and isinstance(source, str)
        and source.startswith(_DOT_SOURCE_PREFIX)
        and source != (expected_source := f"{_DOT_SOURCE_PREFIX}{expected_dir}")
    ):
        findings.append(f"{relative}: metadata.source ({source!r}) must match {expected_source!r}")
    dates: dict[str, date] = {}
    for field in ("created", "updated"):
        if field not in bad:
            parsed = _parse_iso_date(metadata.get(field))
            if parsed is None:
                findings.append(f"{relative}: metadata.{field} must be a valid YYYY-MM-DD date")
            else:
                dates[field] = parsed
    if "created" in dates and "updated" in dates and dates["updated"] < dates["created"]:
        findings.append(
            f"{relative}: metadata.updated ({metadata['updated']!r}) precedes metadata.created ({metadata['created']!r})"
        )
    return findings


def _git_output(root: Path, *args: str) -> str | None:
    if (git := shutil.which("git")) is None:
        return None
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_STRIP}
    try:
        res = subprocess.run(  # noqa: S603
            [git, "-C", str(root), *args], capture_output=True, text=True, check=False, env=env, timeout=15
        )
    except OSError, subprocess.SubprocessError:
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def _skill_dir_for_rel(rel_path: str) -> str | None:
    parts = Path(rel_path).parts
    if len(parts) >= 3 and parts[0] == "skills":
        return f"skills/{parts[1]}"
    if len(parts) >= 4 and parts[0] == ".agents" and parts[1] == "skills":
        return f".agents/skills/{parts[2]}"
    return None


def _git_batch_show(root: Path, specs: Sequence[str]) -> dict[str, str]:
    if not specs or (git := shutil.which("git")) is None:
        return {}
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_STRIP}
    stdin = "".join(f"{spec}\n" for spec in specs).encode("utf-8")
    try:
        res = subprocess.run(  # noqa: S603
            [git, "-C", str(root), "cat-file", "--batch"],
            input=stdin,
            capture_output=True,
            check=False,
            env=env,
            timeout=15,
        )
    except OSError, subprocess.SubprocessError:
        return {}
    if res.returncode != 0:
        return {}
    data, pos, out = res.stdout, 0, {}
    for spec in specs:
        nl = data.find(b"\n", pos)
        if nl == -1:
            break
        header = data[pos:nl].decode("utf-8", errors="replace")
        pos = nl + 1
        if header.endswith(" missing"):
            continue
        parts = header.split()
        if len(parts) != 3 or not parts[2].isdigit():
            break
        size = int(parts[2])
        end = pos + size
        if end >= len(data) or data[end : end + 1] != b"\n":
            break
        with contextlib.suppress(UnicodeDecodeError):
            out[spec] = data[pos:end].decode("utf-8")
        pos = end + 1
    return out


def _stale_updated_findings(root: Path, discovered: Sequence[tuple[str, Path]]) -> list[str]:
    """Flag skills modified since the latest v* tag whose metadata.updated was not bumped."""
    if not (root / ".git").exists():
        return []
    base_tag = _git_output(root, "describe", "--tags", "--abbrev=0", "--match", "v*", "HEAD")
    if not base_tag:
        if os.environ.get("CI") and _git_output(root, "rev-parse", "--is-shallow-repository") == "true":
            return ["skills: cannot verify metadata.updated freshness on a shallow CI clone (set fetch-depth: 0)"]
        return []
    diff_since_tag = (
        _git_output(root, "-c", "core.quotePath=false", "diff", "--name-only", base_tag) or ""
    ).splitlines()
    untracked = (
        _git_output(root, "-c", "core.quotePath=false", "ls-files", "--others", "--exclude-standard") or ""
    ).splitlines()
    touched = {d for p in (*diff_since_tag, *untracked) if (d := _skill_dir_for_rel(p))}
    if not touched:
        return []
    dirty_since_head = (
        _git_output(root, "-c", "core.quotePath=false", "diff", "--name-only", "HEAD") or ""
    ).splitlines()
    dirty_dirs = {d for p in (*dirty_since_head, *untracked) if (d := _skill_dir_for_rel(p))}
    today = datetime.now().astimezone().date().isoformat()
    touched_skills = [
        (rel_dir, _relative(root, skill_path), skill_path)
        for _, skill_path in discovered
        if (rel_dir := _relative(root, skill_path.parent)) in touched
    ]
    base_texts = _git_batch_show(root, [f"{base_tag}:{rel_skill}" for _, rel_skill, _ in touched_skills])
    findings: list[str] = []
    for rel_dir, rel_skill, skill_path in touched_skills:
        base_text = base_texts.get(f"{base_tag}:{rel_skill}")
        if base_text is None:
            continue
        try:
            base_meta, _ = cb.parse_frontmatter(base_text, rel_skill)
            cur_meta, _ = cb.parse_frontmatter(skill_path.read_text(encoding="utf-8"), rel_skill)
        except DotError, OSError, UnicodeDecodeError:
            continue
        base_upd = (
            (base_meta.get("metadata") or {}).get("updated") if isinstance(base_meta.get("metadata"), dict) else None
        )
        cur_upd = (
            (cur_meta.get("metadata") or {}).get("updated") if isinstance(cur_meta.get("metadata"), dict) else None
        )
        base_dt, cur_dt = _parse_iso_date(base_upd), _parse_iso_date(cur_upd)
        if base_dt is None or cur_dt is None or cur_dt > base_dt:
            continue
        change_date = (
            today
            if rel_dir in dirty_dirs
            else (_git_output(root, "log", "-1", "--format=%cs", f"{base_tag}..HEAD", "--", rel_dir) or "")
        )
        if change_date > base_dt.isoformat():
            findings.append(f"{rel_skill}: metadata.updated ({cur_upd!r}) must be bumped after edits since {base_tag}")
    return findings


def _skill_findings(root: Path, name: str, path: Path, *, valid_supagents: set[str] | None = None) -> list[str]:
    rel = _relative(root, path)
    meta, body, findings = _frontmatter(path, root)
    if meta is None:
        return findings
    if unknown := sorted(set(meta) - FRONTMATTER_FIELDS):
        findings.append(f"{rel}: unknown frontmatter fields: {', '.join(unknown)}")
    if "disable-model-invocation" in meta and not isinstance(meta["disable-model-invocation"], bool):
        findings.append(f"{rel}: disable-model-invocation must be a boolean")
    if (declared := meta.get("name")) != name:
        findings.append(f"{rel}: frontmatter name {declared!r} must match its directory {name!r}")
    if not isinstance(declared, str) or len(declared) > MAX_NAME or NAME_PATTERN.fullmatch(declared) is None:
        findings.append(f"{rel}: name must be a lowercase hyphenated identifier of at most {MAX_NAME} characters")
    desc = meta.get("description")
    if not isinstance(desc, str) or not 1 <= len(desc.strip()) <= MAX_DESCRIPTION:
        findings.append(f"{rel}: description must contain 1-{MAX_DESCRIPTION} characters")
    if meta.get("license") != "MIT":
        findings.append(f"{rel}: license must be MIT")
    findings.extend(_metadata_findings(rel, meta.get("metadata"), expected_dir=_relative(root, path.parent)))
    findings.extend(_supagent_ref_findings(rel, body, valid_supagents))
    targets = _document_targets(body)
    entries, entry_errors = _guide_entries(path.parent, root)
    findings.extend(_guide_findings(root, path, body, targets=targets, entries=entries, entry_errors=entry_errors))
    findings.extend(
        _resource_findings(
            root,
            path,
            skill_body=body,
            skill_targets=targets,
            guide_paths={p for p, _ in entries},
            valid_supagents=valid_supagents,
        )
    )
    return findings


def _repository_check(root: Path) -> tuple[list[str], int]:
    root = root.resolve()
    discovered, findings = _discover_skills(root)
    valid_supagents = _supagent_names(root)
    for name, path in sorted(discovered):
        findings.extend(_skill_findings(root, name, path, valid_supagents=valid_supagents))
    findings.extend(_stale_updated_findings(root, sorted(discovered)))
    try:
        context = cb.context_report(root, source=root)
        for scope, b in context["budgets"].items():
            if not b["passed"]:
                head = f"{scope} AGENTS.md + skill discovery contains {b['estimated_tokens']} estimated tokens"
                findings.append(f"{head}; must be below {cb.CONTEXT_TOKEN_LIMIT}; {_BUDGET_HINT}")
        for scope, b in context["subagent_budgets"].items():
            if not b["passed"]:
                head = f"{scope} subagent discovery contains {b['estimated_tokens']} estimated tokens"
                findings.append(f"{head}; must be below {cb.SUBAGENT_TOKEN_LIMIT}; {_BUDGET_HINT}")
        for item in context["duplicates"]:
            paths = ", ".join(_relative(root, Path(p)) for p in item["paths"])
            findings.append(f"agent context: duplicate skill name {item['name']!r} in {paths}; {cb.DUPLICATE_GUIDANCE}")
        for item in context["duplicate_subagents"]:
            paths = ", ".join(_relative(root, Path(p)) for p in item["paths"])
            findings.append(
                f"agent context: duplicate subagent name {item['name']!r} in {paths}; {cb.DUPLICATE_SUBAGENT_GUIDANCE}"
            )
    except DotError as error:
        findings.append(f"agent context: {error}")
    return sorted(set(findings)), len(discovered)


def repository_findings(root: Path) -> list[str]:
    """Return every deterministic catalog, package, and budget finding."""
    return _repository_check(root)[0]


def _sync_guides(root: Path) -> int:
    discovered, errors = _discover_skills(root)
    updates: list[tuple[Path, str, int]] = []
    for _, path in discovered:
        try:
            text, mode = path.read_text(encoding="utf-8"), stat.S_IMODE(path.lstat().st_mode)
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"{_relative(root, path)}: cannot read UTF-8 text ({error.__class__.__name__})")
            continue
        if _bad_markers(text):
            errors.append(f"{_relative(root, path)}: malformed or inverted {GUIDE_START} / {GUIDE_END} markers")
        elif GUIDE_START in text:
            before, index = len(errors), _guide_index(path.parent, root, errors)
            new = text.split(GUIDE_START, 1)[0] + index + text.split(GUIDE_END, 1)[1]
            if len(errors) == before and new != text:
                updates.append((path, new, mode))
    for path, updated, mode in () if errors else updates:
        try:
            write_atomic_file(path, updated.encode("utf-8"), mode=mode)
        except OSError as error:
            errors.append(f"{_relative(root, path)}: cannot write index ({error})")
            break
    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("--sync", action="store_true", help="refresh marked guide indexes from guide metadata")
    if parser.parse_args().sync:
        return _sync_guides(ROOT)
    findings, count = _repository_check(ROOT)
    if findings:
        sys.stderr.write("".join(f"error: {f}\n" for f in findings))
        return 1
    sys.stdout.write(f"Validated {count} first-party skills.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
