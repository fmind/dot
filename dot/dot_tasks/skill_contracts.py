"""Validate first-party skill packages and repository documentation links."""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import stat
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt

from fmind_dot.context_budget import (
    CONTEXT_TOKEN_LIMIT,
    DUPLICATE_GUIDANCE,
    context_report,
    estimated_tokens,
    skill_index_entry,
)
from fmind_dot.errors import DotError

MAX_DESCRIPTION = 180
MAX_DESCRIPTION_AVERAGE = 100
MAX_NAME = 64
MAX_SKILL_BYTES = 1 << 20
MAX_SKILL_LINES = 500
MAX_RESOURCE_BYTES = 1 << 20
SKILL_KINDS = {"connector", "task", "collection"}
GUIDE_START = "<!-- guides:start -->"
GUIDE_END = "<!-- guides:end -->"

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOOL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
FRONTMATTER_FIELDS = {
    "allowed-tools",
    "compatibility",
    "description",
    "disable-model-invocation",
    "license",
    "metadata",
    "name",
}
RESOURCE_DIRECTORIES = {"agents", "assets", "references", "resources", "scripts", "templates", "tests"}
CACHE_NAMES = {".DS_Store", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
HTML_LINK_ATTRIBUTES = {"action", "background", "cite", "data", "formaction", "href", "poster", "src", "xlink:href"}
MARKDOWN = MarkdownIt("commonmark")


class _HTMLTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(tag, attrs)

    def _collect(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        for name, value in attrs:
            if value is None:
                continue
            name = name.lower()
            if name == "id" or (tag == "a" and name == "name"):
                self.anchors.add(value)
            if name == "data" and tag != "object":
                continue
            if name in HTML_LINK_ATTRIBUTES:
                self.targets.append(value)
            elif name == "srcset":
                self.targets.extend(_srcset_targets(value))


def _srcset_targets(value: str) -> list[str]:
    targets: list[str] = []
    index = 0
    while index < len(value):
        while index < len(value) and (value[index].isspace() or value[index] == ","):
            index += 1
        start = index
        while index < len(value) and not value[index].isspace():
            index += 1
        if start == index:
            break
        target = value[start:index]
        if target.endswith(","):
            target = target.rstrip(",")
            if target:
                targets.append(target)
            continue
        targets.append(target)

        parentheses = 0
        while index < len(value):
            if value[index] == "(":
                parentheses += 1
            elif value[index] == ")" and parentheses:
                parentheses -= 1
            elif value[index] == "," and not parentheses:
                index += 1
                break
            index += 1
    return targets


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _read_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return None, [f"{path.as_posix()}: invalid JSON: {error}"]
    if not isinstance(value, dict):
        return None, [f"{path.as_posix()}: expected a JSON object"]
    return value, []


def _discover_skills(root: Path) -> tuple[dict[str, Path], list[str]]:
    skills: dict[str, Path] = {}
    findings: list[str] = []
    for relative in (Path("skills"), Path(".agents/skills")):
        catalog = root / relative
        if not catalog.is_dir():
            continue
        for directory in sorted(catalog.iterdir()):
            if directory.is_symlink():
                findings.append(f"{_relative(root, directory)}: symbolic link is not allowed")
                continue
            if not directory.is_dir():
                continue
            skill = directory / "SKILL.md"
            if not skill.exists():
                # Git cannot track an empty tree; any file makes this an unregistered package.
                if any(
                    path.is_symlink() or (path.is_file() and path.suffix not in {".pyc", ".pyo"})
                    for path in directory.rglob("*")
                ):
                    findings.append(f"{_relative(root, directory)}: skill root has files but no SKILL.md")
                continue
            name = directory.name
            if name in skills:
                findings.append(
                    f"duplicate skill name {name!r} in {_relative(root, skills[name])} and {_relative(root, skill)}"
                )
                continue
            if skill.is_symlink():
                findings.append(f"{_relative(root, skill)}: symbolic link is not allowed")
                continue
            skills[name] = skill
    return skills, findings


def _frontmatter(path: Path, root: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    relative = _relative(root, path)
    try:
        data = path.read_bytes()
    except OSError as error:
        return None, "", [f"{relative}: cannot read: {error}"]
    if len(data) > MAX_SKILL_BYTES:
        return None, "", [f"{relative}: exceeds the {MAX_SKILL_BYTES}-byte limit"]
    try:
        text = data.decode()
    except UnicodeDecodeError as error:
        return None, "", [f"{relative}: is not UTF-8: {error}"]
    if unsafe := _unsafe_text_finding(relative, text):
        return None, text, [unsafe]
    if len(text.splitlines()) > MAX_SKILL_LINES:
        return None, text, [f"{relative}: exceeds the {MAX_SKILL_LINES}-line limit"]
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n") or "\n---\n" not in normalized[4:]:
        return None, text, [f"{relative}: frontmatter must be bounded by --- lines"]
    raw, body = normalized[4:].split("\n---\n", 1)
    try:
        metadata = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        return None, body, [f"{relative}: invalid frontmatter: {error}"]
    if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
        return None, body, [f"{relative}: frontmatter must be a string-keyed mapping"]
    return metadata, body, []


def _unsafe_character(character: str) -> bool:
    code = ord(character)
    # Variation selectors are combining marks (Mn), not format characters (Cf), but
    # runs of them can smuggle hidden instructions just as Unicode tag characters can.
    return (
        (code < 32 and character not in "\n\r\t")
        or code == 127
        or unicodedata.category(character) == "Cf"
        or 0xFE00 <= code <= 0xFE0F
        or 0xE0100 <= code <= 0xE01EF
    )


def _unsafe_text_finding(relative: str, text: str) -> str | None:
    # Inspect each distinct character once, then report the earliest occurrence.
    unsafe = [character for character in set(text) if _unsafe_character(character)]
    if not unsafe:
        return None
    character = min(unsafe, key=text.index)
    if character.isascii():
        return f"{relative}: unsafe control character U+{ord(character):04X}"
    return f"{relative}: bidirectional or invisible Unicode U+{ord(character):04X}"


def _directly_disclosed(content: str, relative: str) -> bool:
    boundary = r"A-Za-z0-9_.+\-/"
    return re.search(rf"(?<![{boundary}])(?:\./)?{re.escape(relative)}(?![{boundary}])", content) is not None


def _reachable_resources(skill: Path, texts: dict[Path, str], resources: set[Path]) -> set[Path]:
    """Follow document-relative disclosures; disconnected reference cycles stay orphaned."""
    reached = {skill}
    pending = [skill]
    while pending:
        document = pending.pop()
        linked = {
            (document.parent / unquote(urlsplit(target).path)).resolve()
            for target in _document_targets(texts[document])
            if not urlsplit(target).scheme and not urlsplit(target).netloc and urlsplit(target).path
        }
        for resource in resources - reached:
            relative = Path(os.path.relpath(resource, document.parent)).as_posix()
            if resource.resolve() in linked or _directly_disclosed(texts[document], relative):
                reached.add(resource)
                # Output templates are artifacts, not routing documents.
                if (
                    resource in texts
                    and (resource.suffix == ".md" or resource.name == "openai.yaml")
                    and "templates" not in resource.relative_to(skill.parent).parts[:-1]
                ):
                    pending.append(resource)
    return reached


def _guides(directory: Path) -> list[Path]:
    """Guide metadata is authoritative; no parallel metadata.guides inventory."""
    guides: list[Path] = []
    for path in sorted((directory / "references").rglob("*.md")):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RESOURCE_BYTES:
            continue
        if "templates" in path.relative_to(directory).parts[:-1]:
            continue
        data = path.read_bytes()
        # Preserved upstream skill documents have a license/provenance header;
        # they remain references rather than first-party routing metadata.
        header = data.split(b"\n---", 1)[0]
        if path.name == "GUIDE.md" or (
            data.startswith(b"---\n") and b"\nname:" in header and b"\nlicense:" not in header
        ):
            guides.append(path)
    return guides


def _guide_index(directory: Path, root: Path) -> str:
    lines = [GUIDE_START, ""]
    for path in _guides(directory):
        metadata, _, _ = _frontmatter(path, root)
        if metadata is not None:
            lines.append(
                f"- [{metadata.get('name')}]({path.relative_to(directory).as_posix()}): {metadata.get('description')}"
            )
    lines.extend(["", GUIDE_END])
    return "\n".join(lines)


def _guide_findings(root: Path, skill: Path, body: str) -> list[str]:
    findings: list[str] = []
    guides = _guides(skill.parent)
    names: set[str] = set()
    for path in guides:
        metadata, _, errors = _frontmatter(path, root)
        findings.extend(errors)
        if metadata is None:
            continue
        name = path.parent.name if path.name == "GUIDE.md" else path.stem
        if NAME_PATTERN.fullmatch(name) is None or len(name) > MAX_NAME:
            findings.append(f"{_relative(root, path)}: invalid guide name")
        if set(metadata) != {"name", "description"}:
            findings.append(
                f"{_relative(root, path)}: first-party guide frontmatter requires only name and description"
            )
        if metadata.get("name") != name:
            findings.append(f"{_relative(root, path)}: guide name must match {name!r}")
        if name in names:
            findings.append(f"{_relative(root, skill)}: duplicate guide {name!r}")
        names.add(name)
        description = metadata.get("description")
        if not isinstance(description, str) or not 1 <= len(description.strip()) <= MAX_DESCRIPTION:
            findings.append(f"{_relative(root, path)}: guide description must contain 1-{MAX_DESCRIPTION} characters")
        if path.relative_to(skill.parent).as_posix() not in _document_targets(body):
            findings.append(f"{_relative(root, path)}: guide needs a direct link from SKILL.md")
    if (guides or GUIDE_START in body or "## Task guides" in body) and _guide_index(skill.parent, root) not in body:
        findings.append(f"{_relative(root, skill)}: stale guide index; run mise run format:skills")
    return findings


def _resource_findings(root: Path, skill: Path) -> tuple[list[str], str]:
    directory = skill.parent
    root_content = skill.read_text(encoding="utf-8")
    chunks = [root_content]
    texts = {skill: root_content}
    resources: set[Path] = set()
    findings: list[str] = []
    for path in sorted(directory.rglob("*")):
        if path == skill:
            continue
        relative = path.relative_to(directory)
        rendered = relative.as_posix()
        try:
            mode = path.stat(follow_symlinks=False).st_mode
        except OSError as error:
            findings.append(f"{_relative(root, path)}: cannot inspect resource: {error}")
            continue
        # .gitignore (*.py[co], __pycache__/) already keeps bytecode out of every clone.
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name in CACHE_NAMES:
            findings.append(f"{_relative(root, skill)}: generated cache or metadata {rendered!r} is not package source")
            continue
        if stat.S_ISLNK(mode):
            findings.append(f"{_relative(root, skill)}: symbolic link {rendered!r} is not allowed")
            continue
        if stat.S_ISDIR(mode):
            continue
        first = relative.parts[0]
        if first not in RESOURCE_DIRECTORIES:
            findings.append(f"{_relative(root, path)}: unsupported package path; use a standard resource directory")
            continue
        if not stat.S_ISREG(mode):
            findings.append(f"{_relative(root, skill)}: non-regular resource {rendered!r} is not allowed")
            continue
        if path.name == "SKILL.md":
            findings.append(f"{_relative(root, path)}: nested SKILL.md enters host discovery; use a guide instead")
        if mode & 0o111 and "scripts" not in relative.parts[:-1]:
            findings.append(f"{_relative(root, skill)}: executable outside scripts/ at {rendered!r}")
        resources.add(path)
        if first == "assets":
            continue
        try:
            data = path.read_bytes()
        except OSError as error:
            findings.append(f"{_relative(root, path)}: cannot read resource: {error}")
            continue
        if len(data) > MAX_RESOURCE_BYTES:
            findings.append(f"{_relative(root, path)}: exceeds the {MAX_RESOURCE_BYTES}-byte parsed-file limit")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            findings.append(f"{_relative(root, path)}: is not UTF-8: {error}")
            continue
        unsafe = _unsafe_text_finding(_relative(root, path), text)
        if unsafe:
            findings.append(unsafe)
        chunks.append(text)
        texts[path] = text
    reached = _reachable_resources(skill, texts, resources)
    findings.extend(
        f"{_relative(root, path)}: resource is not reachable from SKILL.md" for path in sorted(resources - reached)
    )
    # Code-path disclosures also expose Markdown; validate those documents even
    # when no hyperlink led the normal link walker to them.
    findings.extend(
        _link_findings(
            root, directory, documents=tuple(path for path in sorted(reached) if path in texts and path.suffix == ".md")
        )
    )
    return findings, "\n".join(chunks)


def _contains_tool(content: str, tool: str) -> bool:
    boundary = r"A-Za-z0-9_.+\-"
    return re.search(rf"(?<![{boundary}]){re.escape(tool)}(?![{boundary}])", content, re.IGNORECASE) is not None


@functools.cache
def _document_targets(content: str) -> tuple[str, ...]:
    targets: list[str] = []
    for token in MARKDOWN.parse(content):
        for candidate in [token, *(token.children or [])]:
            if candidate.type == "link_open" and isinstance(href := candidate.attrGet("href"), str):
                targets.append(href)
            elif candidate.type == "image" and isinstance(src := candidate.attrGet("src"), str):
                targets.append(src)
            elif candidate.type in {"html_block", "html_inline"}:
                parser = _HTMLTargetParser()
                parser.feed(candidate.content)
                targets.extend(parser.targets)
    return tuple(targets)


@functools.cache
def _markdown_anchors(content: str) -> frozenset[str]:
    """Match GitHub heading slugs, duplicate suffixes, and explicit HTML anchors."""
    tokens = MARKDOWN.parse(content)
    anchors: set[str] = set()
    parser = _HTMLTargetParser()
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            title = "".join(
                child.content
                for child in tokens[index + 1].children or []
                if child.type in {"text", "code_inline", "image"}
            ).lower()
            slug = "".join(
                character
                for character in title
                if character in " _-" or unicodedata.category(character)[0] in {"L", "N", "M"}
            ).replace(" ", "-")
            unique, suffix = slug, 0
            while unique in anchors:
                suffix += 1
                unique = f"{slug}-{suffix}"
            anchors.add(unique)
        for candidate in [token, *(token.children or [])]:
            if candidate.type in {"html_block", "html_inline"}:
                parser.feed(candidate.content)
    return frozenset(anchors | parser.anchors)


def _link_findings(root: Path, directory: Path, *, documents: tuple[Path, ...] | None = None) -> list[str]:
    findings: list[str] = []
    resolved_root = root.resolve()
    resolved_directory = directory.resolve()
    pending = list(documents) if documents is not None else [directory / "SKILL.md"]
    seen: set[Path] = set()
    anchors: dict[Path, frozenset[str]] = {}
    while pending:
        document = pending.pop()
        if document in seen:
            continue
        seen.add(document)
        if document.is_symlink():
            findings.append(f"{_relative(root, document)}: symbolic link is not allowed")
            continue
        try:
            content = document.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            findings.append(f"{_relative(root, document)}: cannot read Markdown: {error}")
            continue
        for raw_target in _document_targets(content):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("{"):
                continue
            parsed = urlsplit(target)
            if parsed.scheme:
                if parsed.scheme.lower() == "file":
                    findings.append(f"{_relative(root, document)}: unsupported local link {target!r}")
                continue
            if parsed.netloc:
                continue
            if target.startswith(("/", "~")):
                findings.append(f"{_relative(root, document)}: local link {target!r} must be repository-relative")
                continue
            relative_document = document.relative_to(directory)
            if "templates" in relative_document.parts[:-1]:
                # Template links become relative to the generated project after copying.
                continue
            local = unquote(parsed.path)
            resolved = (document.parent / local).resolve() if local else document.resolve()
            if not resolved.is_relative_to(resolved_root):
                findings.append(f"{_relative(root, document)}: local link {target!r} escapes the repository")
            elif not resolved.exists():
                findings.append(f"{_relative(root, document)}: missing local link {target!r}")
            elif resolved.is_file() and resolved.suffix.lower() == ".md":
                if parsed.fragment:
                    try:
                        if resolved not in anchors:
                            anchors[resolved] = _markdown_anchors(resolved.read_text(encoding="utf-8"))
                        if unquote(parsed.fragment) not in anchors[resolved]:
                            findings.append(f"{_relative(root, document)}: missing local anchor {target!r}")
                    except OSError, UnicodeError:
                        findings.append(f"{_relative(root, document)}: cannot inspect local anchor {target!r}")
                if documents is None and resolved.is_relative_to(resolved_directory):
                    pending.append(resolved)
    return findings


def _skill_findings(root: Path, name: str, path: Path, tools: list[str]) -> tuple[list[str], str | None]:
    relative = _relative(root, path)
    metadata, body, findings = _frontmatter(path, root)
    if metadata is None:
        return findings, None
    unknown = sorted(set(metadata) - FRONTMATTER_FIELDS)
    if unknown:
        findings.append(f"{relative}: unknown frontmatter fields: {', '.join(unknown)}")
    if "disable-model-invocation" in metadata and not isinstance(metadata["disable-model-invocation"], bool):
        findings.append(f"{relative}: disable-model-invocation must be a boolean")
    declared_name = metadata.get("name")
    if declared_name != name:
        findings.append(f"{relative}: frontmatter name {declared_name!r} must match its directory {name!r}")
    if (
        not isinstance(declared_name, str)
        or len(declared_name) > MAX_NAME
        or NAME_PATTERN.fullmatch(declared_name) is None
    ):
        findings.append(f"{relative}: name must be a lowercase hyphenated identifier of at most {MAX_NAME} characters")
    description = metadata.get("description")
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= MAX_DESCRIPTION:
        findings.append(f"{relative}: description must contain 1-{MAX_DESCRIPTION} characters")
        description = None
    if metadata.get("license") != "MIT":
        findings.append(f"{relative}: license must be MIT")
    if not isinstance(metadata.get("metadata"), dict):
        findings.append(f"{relative}: metadata must be a mapping")
    else:
        kind = metadata["metadata"].get("kind")
        if not isinstance(kind, str) or kind not in SKILL_KINDS:
            findings.append(f"{relative}: metadata.kind must be connector, task, or collection")
        if "guides" in metadata["metadata"]:
            findings.append(f"{relative}: remove metadata.guides; guide frontmatter owns the generated index")
    findings.extend(_guide_findings(root, path, body))

    body_lines = [line for line in body.splitlines() if line.strip()]
    if not body_lines or not body_lines[0].startswith("# "):
        findings.append(f"{relative}: body must start with an H1 heading")
    first_section = next((index for index, line in enumerate(body_lines) if line.startswith("## ")), None)
    if first_section is None:
        findings.append(f"{relative}: body must contain at least one H2 section")
    elif first_section < 2:
        findings.append(f"{relative}: H1 must be followed by a one-line intent before the first H2 section")

    resource_findings, package_text = _resource_findings(root, path)
    findings.extend(resource_findings)
    for tool in tools:
        if not TOOL_PATTERN.fullmatch(tool):
            findings.append(f"skills/contracts.json: skill {name!r} has invalid required tool {tool!r}")
        elif not _contains_tool(package_text, tool):
            findings.append(f"{relative}: required tool {tool!r} is undocumented")
    return findings, description


def _manifest(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    path = root / "skills/contracts.json"
    data, findings = _read_json(path)
    if data is None:
        return {}, findings
    if set(data) != {"skills", "version"}:
        findings.append("skills/contracts.json: expected only 'version' and 'skills' fields")
    if data.get("version") != 1:
        findings.append("skills/contracts.json: version must be 1")
    raw_skills = data.get("skills")
    if not isinstance(raw_skills, dict):
        findings.append("skills/contracts.json: skills must be an object")
        return {}, findings
    skills: dict[str, list[str]] = {}
    for name, raw_tools in raw_skills.items():
        if (
            not isinstance(name, str)
            or not isinstance(raw_tools, list)
            or not all(isinstance(tool, str) for tool in raw_tools)
        ):
            findings.append(f"skills/contracts.json: skill {name!r} must map to an array of tool names")
            continue
        if len(raw_tools) != len(set(raw_tools)):
            findings.append(f"skills/contracts.json: skill {name!r} repeats a required tool")
        skills[name] = raw_tools
    return skills, findings


def documentation_findings(root: Path) -> list[str]:
    """Check local links and anchors in the root documentation."""
    documents = tuple(
        path
        for path in (
            root / "README.md",
            root / "AGENTS.md",
            root / "dot_agents/AGENTS.md",
            root / ".github/SECURITY.md",
        )
        if path.is_file()
    )
    return _link_findings(root, root, documents=documents)


def repository_findings(root: Path) -> list[str]:
    """Return every deterministic catalog, package, budget, and documentation finding."""
    root = root.resolve()
    manifest, findings = _manifest(root)
    discovered, discovery_findings = _discover_skills(root)
    findings.extend(discovery_findings)
    for name in sorted(set(discovered) - set(manifest)):
        findings.append(f"skills/contracts.json: active skill {name!r} has no required-tools declaration")
    for name in sorted(set(manifest) - set(discovered)):
        findings.append(f"skills/contracts.json: registered skill {name!r} has no active SKILL.md")

    descriptions: dict[str, str] = {}
    for name, path in sorted(discovered.items()):
        package_findings, description = _skill_findings(root, name, path, manifest.get(name, []))
        findings.extend(package_findings)
        if description is not None:
            descriptions[name] = description
    normalized: dict[str, str] = {}
    for name, description in sorted(descriptions.items()):
        key = " ".join(description.lower().split())
        if key in normalized:
            findings.append(f"skills {normalized[key]!r} and {name!r} have identical descriptions")
        normalized[key] = name
    # `dot agent context` owns the measurement; each scope is budgeted, the combined total is not.
    try:
        context = context_report(root, source=root)
    except DotError as error:
        findings.append(f"agent context: {error}")
    else:
        findings.extend(
            f"{scope} AGENTS.md + skill discovery contains {budget['estimated_tokens']} estimated tokens; "
            f"must be below {CONTEXT_TOKEN_LIMIT}; reduce instructions or discovery without losing task triggers"
            for scope, budget in context["budgets"].items()
            if not budget["passed"]
        )
        # Declared names can collide even when directory names differ; hosts then shadow one copy.
        findings.extend(
            f"agent context: duplicate skill name {item['name']!r} in "
            + ", ".join(_relative(root, Path(path)) for path in item["paths"])
            + f"; {DUPLICATE_GUIDANCE}"
            for item in context["duplicates"]
        )
    findings.extend(documentation_findings(root))
    return sorted(set(findings))


def _render_global_index(descriptions: dict[str, str]) -> str:
    """Use a stable display path so moving a checkout cannot change its budget."""
    return "".join(skill_index_entry(name, description, "global") for name, description in sorted(descriptions.items()))


def catalog_report(root: Path, *, details: bool = True) -> str:
    """Report reproducible discovery cost without claiming provider token counts."""
    root = root.resolve()
    discovered, _ = _discover_skills(root)
    descriptions = {
        name: description
        for name, description in _descriptions(root).items()
        if discovered[name].parent.parent == root / "skills"
    }
    index_size = len(_render_global_index(descriptions))
    local_descriptions = {
        name: description
        for name, description in _descriptions(root).items()
        if discovered[name].parent.parent == root / ".agents/skills"
    }
    local_size = sum(
        len(skill_index_entry(name, description, "local")) for name, description in local_descriptions.items()
    )
    startup = context_report(root, source=root)["budgets"]
    average = sum(map(len, descriptions.values())) / len(descriptions) if descriptions else 0.0
    kinds = dict.fromkeys(sorted(SKILL_KINDS), 0)
    members: dict[str, list[str]] = {kind: [] for kind in sorted(SKILL_KINDS)}
    costs: list[str] = []
    guide_costs: list[tuple[int, str]] = []
    for name, path in sorted(discovered.items()):
        metadata, body, _ = _frontmatter(path, root)
        if metadata is None:
            continue
        kind = metadata.get("metadata", {}).get("kind")
        if kind in kinds:
            kinds[kind] += 1
            members[kind].append(name)
        tokens = estimated_tokens(len(body))
        target = 600 if kind == "collection" else 1_500
        if tokens > target:
            costs.append(f"- {name}: {tokens} body tokens; consider the {target}-token authoring target")
        for guide in _guides(path.parent):
            label = f"{name}/{guide.stem if guide.name != 'GUIDE.md' else guide.parent.name}"
            guide_costs.append((estimated_tokens(len(path.read_text()) + len(guide.read_text())), label))
    selected_costs = sorted(guide_costs, reverse=True)
    if not details:
        selected_costs = selected_costs[:5]
    costs.extend(f"- {label}: {tokens} tokens for parent + guide" for tokens, label in selected_costs)
    discovery = estimated_tokens(index_size + local_size)
    classification = "".join(f"- {kind}: {', '.join(names)}\n" for kind, names in members.items()) if details else ""
    return (
        f"Global skills: {len(descriptions)}; local skills: {len(local_descriptions)}\n"
        f"Kinds (both scopes): {kinds}\n"
        + classification
        + f"Global description average: {average:.1f} characters (advisory target: {MAX_DESCRIPTION_AVERAGE})\n"
        f"Global skill index: {index_size} characters "
        "(names, descriptions, and portable paths)\n"
        f"Combined estimated index tokens: {discovery} (informational) "
        "(characters / 4; not host tokenization or billing)\n"
        f"Global AGENTS.md + skill discovery: {startup['global']['estimated_tokens']} / <{CONTEXT_TOKEN_LIMIT} "
        "estimated tokens\n"
        f"Local AGENTS.md + skill discovery: {startup['local']['estimated_tokens']} / <{CONTEXT_TOKEN_LIMIT} "
        "estimated tokens\n"
        "Full breakdown: dot agent context --source . --project .\n"
        f"On-demand paths ({'all' if details else 'five largest'}; estimates exclude resources and runtime output):\n"
        + "\n".join(costs)
    )


def _descriptions(root: Path) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    discovered, _ = _discover_skills(root)
    for name, path in discovered.items():
        metadata, _, _ = _frontmatter(path, root)
        if metadata is not None and isinstance(metadata.get("description"), str):
            descriptions[name] = metadata["description"]
    return descriptions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print informational catalog and load estimates")
    parser.add_argument("--details", action="store_true", help="include category members and every guide cost")
    parser.add_argument("--sync", action="store_true", help="refresh marked guide indexes from guide metadata")
    args = parser.parse_args()
    if args.details and not args.report:
        parser.error("--details requires --report")
    if args.sync and args.report:
        parser.error("choose --sync or --report")
    root = Path(__file__).resolve().parents[2]
    if args.sync:
        discovered, errors = _discover_skills(root)
        if errors:
            sys.stderr.write("\n".join(errors) + "\n")
            return 1
        for path in discovered.values():
            text = path.read_text(encoding="utf-8")
            if GUIDE_START in text and GUIDE_END in text:
                before, rest = text.split(GUIDE_START, 1)
                _, after = rest.split(GUIDE_END, 1)
                updated = before + _guide_index(path.parent, root) + after
                if updated != text:
                    path.write_text(updated, encoding="utf-8")
        return 0
    findings = repository_findings(root)
    if findings:
        for finding in findings:
            sys.stderr.write(f"error: {finding}\n")
        return 1
    if args.report:
        sys.stdout.write(f"{catalog_report(root, details=args.details)}\n")
        if not args.details:
            sys.stdout.write("Use mise run report:skills -- --details for category members and every guide cost.\n")
    else:
        sys.stdout.write(f"Validated {len(_descriptions(root))} first-party skills.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
