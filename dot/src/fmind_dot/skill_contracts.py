"""Validate first-party skill packages and report lexical routing diagnostics."""

from __future__ import annotations

import argparse
import json
import math
import re
import stat
import subprocess
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt

MAX_DESCRIPTION = 240
MAX_DESCRIPTION_AVERAGE = 175
MAX_NAME = 64
MAX_SKILL_BYTES = 1 << 20
MAX_SKILL_LINES = 500
MAX_RESOURCE_BYTES = 1 << 20

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOOL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
LINK_PATTERN = re.compile(r"(?<!!)\[[^]]*]\(([^)]+)\)")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
ACTIVE_STACK_PATTERN = re.compile(r"\b(?:Go|Golang|TypeScript)\b")
HISTORY_PATTERN = re.compile(r"\b(?:archive|archived|external|historical|history|retired|third-party)\b", re.IGNORECASE)
FRONTMATTER_FIELDS = {"allowed-tools", "compatibility", "description", "license", "metadata", "name"}
RESOURCE_DIRECTORIES = {"agents", "assets", "references", "resources", "scripts", "templates", "tests"}
CACHE_NAMES = {".DS_Store", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
HTML_LINK_ATTRIBUTES = {"action", "background", "cite", "data", "formaction", "href", "poster", "src", "xlink:href"}
ROUTING_FIELDS = {"cases", "construction", "created", "proof_boundary", "purpose", "version"}
CASE_FIELDS = {
    "categories",
    "expected",
    "forbidden",
    "id",
    "primary",
    "prompt",
    "require_all_top_k",
    "route",
    "top_k",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "for",
    "from",
    "help",
    "i",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "need",
    "needs",
    "of",
    "on",
    "or",
    "our",
    "rather",
    "so",
    "than",
    "that",
    "the",
    "them",
    "this",
    "through",
    "to",
    "use",
    "using",
    "want",
    "we",
    "when",
    "where",
    "with",
    "you",
    "your",
}
MARKDOWN = MarkdownIt("commonmark")


class _HTMLTargetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.targets: list[str] = []

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
            # Locally installed skills are untracked symlinked peers, outside this catalog's contract.
            if directory.is_symlink():
                tracked = subprocess.run(  # noqa: S603
                    ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", _relative(root, directory)],  # noqa: S607
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if tracked.returncode == 1:
                    continue
                findings.append(f"{_relative(root, directory)}: symbolic link is not allowed")
                continue
            if not directory.is_dir():
                continue
            skill = directory / "SKILL.md"
            if not skill.exists():
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


def _unsafe_text_finding(relative: str, text: str) -> str | None:
    for character in text:
        if character not in "\n\r\t" and (ord(character) < 32 or ord(character) == 127):
            return f"{relative}: unsafe control character U+{ord(character):04X}"
        if unicodedata.category(character) == "Cf":
            return f"{relative}: bidirectional or invisible Unicode U+{ord(character):04X}"
    return None


def _directly_disclosed(content: str, relative: str) -> bool:
    boundary = r"A-Za-z0-9_.+\-/"
    return re.search(rf"(?<![{boundary}])(?:\./)?{re.escape(relative)}(?![{boundary}])", content) is not None


def _resource_findings(root: Path, skill: Path) -> tuple[list[str], str]:
    directory = skill.parent
    root_content = skill.read_text(encoding="utf-8")
    chunks = [root_content]
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
        if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
            findings.append(f"{_relative(root, skill)}: Python bytecode cache {rendered!r} is generated state")
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
        if mode & 0o111 and first != "scripts":
            findings.append(f"{_relative(root, skill)}: executable outside scripts/ at {rendered!r}")
        if not _directly_disclosed(root_content, rendered):
            findings.append(f"{_relative(root, skill)}: resource {rendered!r} is not directly disclosed")
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
    return findings, "\n".join(chunks)


def _contains_tool(content: str, tool: str) -> bool:
    boundary = r"A-Za-z0-9_.+\-"
    return re.search(rf"(?<![{boundary}]){re.escape(tool)}(?![{boundary}])", content, re.IGNORECASE) is not None


def _document_targets(content: str) -> list[str]:
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
    return targets


def _link_findings(root: Path, directory: Path) -> list[str]:
    findings: list[str] = []
    resolved_root = root.resolve()
    resolved_directory = directory.resolve()
    pending = [directory / "SKILL.md"]
    seen: set[Path] = set()
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
            if not target or target.startswith(("#", "{")):
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
            if relative_document.parts[0] == "templates":
                # Template links become relative to the generated project after copying.
                continue
            local = unquote(target.split("#", 1)[0].split("?", 1)[0])
            candidates = [(document.parent / local).resolve(), (directory / local).resolve()]
            resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
            if not resolved.is_relative_to(resolved_root):
                findings.append(f"{_relative(root, document)}: local link {target!r} escapes the repository")
            elif not resolved.exists():
                findings.append(f"{_relative(root, document)}: missing local link {target!r}")
            elif resolved.suffix.lower() == ".md" and resolved.is_relative_to(resolved_directory):
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
    findings.extend(_link_findings(root, path.parent))
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


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return value


def _routing_findings(root: Path, catalog: set[str]) -> list[str]:
    path = root / "dot/testdata/skills/routing-boundaries.json"
    data, findings = _read_json(path)
    if data is None:
        return findings
    if set(data) != ROUTING_FIELDS:
        findings.append(f"{_relative(root, path)}: unexpected or missing top-level fields")
    if data.get("version") != 1:
        findings.append(f"{_relative(root, path)}: version must be 1")
    for field in ("created", "purpose", "construction", "proof_boundary"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            findings.append(f"{_relative(root, path)}: {field} must be a non-empty string")
    cases = data.get("cases")
    if not isinstance(cases, list):
        findings.append(f"{_relative(root, path)}: cases must be an array")
        return findings

    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    primaries: set[str] = set()
    routed = multi = no_route = 0
    for index, case in enumerate(cases):
        owner = f"{_relative(root, path)}: case {index}"
        if not isinstance(case, dict):
            findings.append(f"{owner} must be an object")
            continue
        unknown = sorted(set(case) - CASE_FIELDS)
        if unknown:
            findings.append(f"{owner} has unknown fields: {', '.join(unknown)}")
        identifier = case.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            findings.append(f"{owner} requires a non-empty id")
        elif identifier in seen_ids:
            findings.append(f"{owner} repeats id {identifier!r}")
        else:
            seen_ids.add(identifier)
            owner = f"{_relative(root, path)}: {identifier}"
        prompt = case.get("prompt")
        normalized = " ".join(prompt.lower().split()) if isinstance(prompt, str) else ""
        if len(normalized) < 20:
            findings.append(f"{owner}: prompt is too short")
        elif normalized in seen_prompts:
            findings.append(f"{owner}: prompt is duplicated")
        else:
            seen_prompts.add(normalized)
        categories = _string_list(case.get("categories"))
        if categories is None or len(categories) != len(set(categories)):
            findings.append(f"{owner}: categories must be a non-empty unique string array")

        if case.get("route", True) is False:
            no_route += 1
            if any(field in case for field in ("expected", "primary", "top_k", "require_all_top_k", "forbidden")):
                findings.append(f"{owner}: a no-route probe cannot declare skill or rank fields")
            continue
        if "route" in case and case["route"] is not True:
            findings.append(f"{owner}: route must be a boolean")
        routed += 1
        expected = _string_list(case.get("expected"))
        if expected is None or len(expected) != len(set(expected)):
            findings.append(f"{owner}: expected must be a non-empty unique string array")
            expected = []
        primary = case.get("primary")
        if not isinstance(primary, str) or primary not in expected:
            findings.append(f"{owner}: primary must name one expected skill")
        elif primary in catalog:
            primaries.add(primary)
        top_k = case.get("top_k")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 5:
            findings.append(f"{owner}: top_k must be an integer from 1 to 5")
        forbidden = case.get("forbidden", [])
        if not isinstance(forbidden, list) or not all(isinstance(item, str) for item in forbidden):
            findings.append(f"{owner}: forbidden must be a string array")
            forbidden = []
        for skill in [*expected, *forbidden]:
            if skill not in catalog:
                findings.append(f"{owner}: referenced skill {skill!r} is absent from the catalog")
        if set(expected) & set(forbidden):
            findings.append(f"{owner}: a skill cannot be both expected and forbidden")
        if len(expected) > 1:
            multi += 1
            all_top_k = case.get("require_all_top_k")
            if (
                isinstance(all_top_k, bool)
                or not isinstance(all_top_k, int)
                or not isinstance(top_k, int)
                or not top_k <= all_top_k <= 5
            ):
                findings.append(f"{owner}: require_all_top_k must be between top_k and 5 for multi-intent probes")
        elif "require_all_top_k" in case:
            findings.append(f"{owner}: require_all_top_k is only valid for multi-intent probes")
    if routed == 0:
        findings.append(f"{_relative(root, path)}: corpus needs a routable probe")
    if multi == 0:
        findings.append(f"{_relative(root, path)}: corpus needs a multi-intent probe")
    if no_route == 0:
        findings.append(f"{_relative(root, path)}: corpus needs a no-route probe")
    missing_primaries = sorted(catalog - primaries)
    if missing_primaries:
        findings.append(
            f"{_relative(root, path)}: active skills without a primary routing probe: {', '.join(missing_primaries)}"
        )
    return findings


def documentation_findings(root: Path) -> list[str]:
    """Reject stale active-stack claims while allowing explicit archive or external context."""
    findings: list[str] = []
    documents = (root / "README.md", root / "AGENTS.md", root / "dot_agents/AGENTS.md")
    for path in documents:
        if not path.is_file():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if ACTIVE_STACK_PATTERN.search(line) and HISTORY_PATTERN.search(line) is None:
                findings.append(f"{_relative(root, path)}:{line_number}: active Go or TypeScript implementation claim")
    return findings


def repository_findings(root: Path) -> list[str]:
    """Return every deterministic catalog, package, routing, and documentation finding."""
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
    total = sum(len(description) for description in descriptions.values())
    if descriptions and total > MAX_DESCRIPTION_AVERAGE * len(descriptions):
        findings.append(
            f"catalog descriptions contain {total} characters, exceeding {len(descriptions)} x {MAX_DESCRIPTION_AVERAGE}"
        )
    findings.extend(_routing_findings(root, set(discovered)))
    findings.extend(documentation_findings(root))
    return sorted(set(findings))


def _words(text: str) -> set[str]:
    # Two-character CLI names such as uv, ty, hf, xh, and d2 are high-signal routing cues.
    return {word for word in TOKEN_PATTERN.findall(text.lower()) if len(word) >= 2 and word not in STOP_WORDS}


def _descriptions(root: Path) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    discovered, _ = _discover_skills(root)
    for name, path in discovered.items():
        metadata, _, _ = _frontmatter(path, root)
        if metadata is not None and isinstance(metadata.get("description"), str):
            descriptions[name] = metadata["description"]
    return descriptions


def overlap_report(root: Path) -> str:
    """Render a transparent lexical ranking without creating a pass threshold."""
    descriptions = _descriptions(root)
    routing, errors = _read_json(root / "dot/testdata/skills/routing-boundaries.json")
    if routing is None or errors or not isinstance(routing.get("cases"), list):
        return "Skill routing overlap: informational only; routing corpus is unavailable."
    lines = ["Skill routing overlap (informational only; not host routing or safety evidence):"]
    matched = total = 0
    for case in routing["cases"]:
        if not isinstance(case, dict) or case.get("route", True) is False:
            continue
        prompt = case.get("prompt", "")
        query = _words(prompt) if isinstance(prompt, str) else set()
        ranking: list[tuple[float, str]] = []
        for name, description in descriptions.items():
            words = _words(f"{name} {description}")
            shared = len(query & words)
            score = shared / math.sqrt(len(query) * len(words)) if query and words else 0.0
            ranking.append((score, name))
        ranking.sort(key=lambda item: (-item[0], item[1]))
        primary = case.get("primary", "")
        if ranking and ranking[0][1] == primary and ranking[0][0] > 0:
            matched += 1
        total += 1
        leaders = ", ".join(f"{name}={score:.3f}" for score, name in ranking[:3])
        lines.append(f"- {case.get('id', '<missing>')}: expected={primary}; leaders=[{leaders}]")
    lines.append(f"Lexical rank-1 matches: {matched}/{total}; informational only.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print informational lexical routing diagnostics")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    findings = repository_findings(root)
    if findings:
        for finding in findings:
            sys.stderr.write(f"error: {finding}\n")
        return 1
    if args.report:
        sys.stdout.write(f"{overlap_report(root)}\n")
    else:
        sys.stdout.write(f"Validated {len(_descriptions(root))} first-party skills.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
