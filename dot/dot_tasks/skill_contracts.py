"""Validate first-party skill packages; lychee checks Markdown links in `check:skills`."""

from __future__ import annotations

import argparse
import functools
import os
import re
import socket as socket  # Re-exported for contract test monkeypatching.
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

import fmind_dot.context_budget as cb
from dot_tasks import ROOT
from dot_tasks.privacy_checks import (
    EMAIL_PATTERN as EMAIL_PATTERN,
)
from dot_tasks.privacy_checks import (
    _workstation_tokens as _workstation_tokens,
)
from dot_tasks.privacy_checks import (
    privacy_findings as _privacy_findings,
)
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
        return *cb.parse_frontmatter(text, rel), []
    except DotError as error:
        return None, text, [str(error)]


def _reachable_resources(skill: Path, texts: dict[Path, str], resources: set[Path]) -> set[Path]:
    """Follow document-relative disclosures; disconnected reference cycles stay orphaned."""
    reached, pending = {skill}, [skill]
    while pending:
        doc = pending.pop()
        urls = (urlsplit(t) for t in _document_targets(texts[doc]))
        linked = {(doc.parent / unquote(u.path)).resolve() for u in urls if not u.scheme and not u.netloc and u.path}
        for res in resources - reached:
            rel_esc = re.escape(Path(os.path.relpath(res, doc.parent)).as_posix())
            pat = rf"(?<![A-Za-z0-9_.+\-/])(?:\./)?{rel_esc}(?![A-Za-z0-9_.+\-/])"
            if res.resolve() in linked or re.search(pat, texts[doc]):
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


def _guide_index(directory: Path, root: Path, errors: list[str] | None = None) -> str:
    lines = [GUIDE_START, ""]
    for path in _guides(directory):
        meta, _, guide_errors = _frontmatter(path, root)
        if errors is not None:
            errors.extend(guide_errors)
        if meta is not None:
            lines.append(f"- [{meta.get('name')}]({path.relative_to(directory).as_posix()}): {meta.get('description')}")
    return "\n".join([*lines, "", GUIDE_END])


def _guide_findings(root: Path, skill: Path, body: str) -> list[str]:
    findings: list[str] = []
    rel_skill, guides, names, targets = _relative(root, skill), _guides(skill.parent), set(), _document_targets(body)
    for path in guides:
        meta, _, errors = _frontmatter(path, root)
        findings.extend(errors)
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
    elif (guides or has_start or "## Task guides" in body) and _guide_index(skill.parent, root) not in body:
        hint = "stale guide index; run mise run format:skills" if has_start and has_end else _MISSING_GUIDE
        findings.append(f"{rel_skill}: {hint}")
    return findings


def _resource_findings(root: Path, skill: Path) -> list[str]:
    directory, rel_skill = skill.parent, _relative(root, skill)
    guides, texts, resources, findings = set(_guides(directory)), {skill: skill.read_text(encoding="utf-8")}, set(), []
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
                    if is_ref and path not in guides:
                        findings.extend(_token_errors(rel, text))
                    texts[path] = text
    unreachable = sorted(resources - _reachable_resources(skill, texts, resources))
    findings.extend(f"{_relative(root, p)}: resource is not reachable from SKILL.md" for p in unreachable)
    return findings


@functools.cache
def _document_targets(content: str) -> tuple[str, ...]:
    return tuple(
        val
        for token in MARKDOWN.parse(content)
        for cand in (token, *(token.children or ()))
        if (attr := "href" if cand.type == "link_open" else "src" if cand.type == "image" else "")
        and isinstance(val := cand.attrGet(attr), str)
    )


def _metadata_findings(relative: str, metadata: Any) -> list[str]:
    if not isinstance(metadata, dict):
        return [f"{relative}: metadata must be a mapping"]
    findings: list[str] = []
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
        findings.append(f"{relative}: metadata keys and values must be strings")
    if metadata.get("kind") not in SKILL_KINDS:
        findings.append(f"{relative}: metadata.kind must be connector, task, or collection")
    bad = [f for f in _REQ_META if not isinstance(v := metadata.get(f), str) or not v.strip()]
    return [*findings, *(f"{relative}: metadata.{f} must be a non-empty string" for f in bad)]


def _skill_findings(root: Path, name: str, path: Path) -> list[str]:
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
    findings.extend(_metadata_findings(rel, meta.get("metadata")))
    findings.extend(_guide_findings(root, path, body))
    findings.extend(_resource_findings(root, path))
    return findings


def privacy_findings(root: Path, home: Path | None = None) -> list[str]:
    """Scan non-encrypted repo files and local Git commits for emails, SSH comments, and local tokens."""
    return _privacy_findings(root, home=home, repo_root=ROOT)


def _repository_check(root: Path) -> tuple[list[str], int]:
    root = root.resolve()
    discovered, findings = _discover_skills(root)
    for name, path in sorted(discovered):
        findings.extend(_skill_findings(root, name, path))
    if root == ROOT:
        findings.extend(privacy_findings(root))
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
