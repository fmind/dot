"""Validate first-party skill packages; lychee checks Markdown links in `check:skills`."""

from __future__ import annotations

import argparse
import functools
import os
import re
import socket
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt

from dot_tasks import ROOT
from fmind_dot.context_budget import (
    CONTEXT_TOKEN_LIMIT,
    DUPLICATE_GUIDANCE,
    context_report,
)
from fmind_dot.errors import DotError

MAX_DESCRIPTION = 180
MAX_NAME = 64
MAX_SKILL_LINES = 500
SKILL_KINDS = {"connector", "task", "collection"}
GUIDE_START = "<!-- guides:start -->"
GUIDE_END = "<!-- guides:end -->"

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
RESOURCE_DIRECTORIES = {"agents", "assets", "references", "resources", "scripts", "templates", "tests"}
MARKDOWN = MarkdownIt("commonmark")

ALLOWED_EMAIL_DOMAINS = {
    "fmind.dev",
    "fmind.ai",
    "github.com",
    "users.noreply.github.com",
    "example.iam.gserviceaccount.com",
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
}
ALLOWED_EMAIL_SUFFIXES = (
    ".fmind.dev",
    ".fmind.ai",
    ".example.com",
    ".example.org",
    ".example.net",
    ".example.edu",
    ".example",
    ".test",
    ".invalid",
    ".localhost",
)
EMAIL_PATTERN = re.compile(
    r"(?:(?<=\\n)|(?<=\\r)|(?<=\\t)|(?<![A-Za-z0-9._%+\\-]))"
    r"([A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}))\b"
)
PRIVACY_SKIP_PATHS = {
    "dot/uv.lock",
    "dot_config/mise/mise.lock",
    "dot_config/nvim/lazy-lock.json",
    "mise.lock",
}
PRIVACY_SKIP_PREFIXES = ("dot_config/mise/locks/",)
SAFE_HOST_TOKENS = {
    "courses",
    "debian",
    "default",
    "example",
    "fmind",
    "github",
    "google",
    "hurier",
    "local",
    "localhost",
    "macbook",
    "mederic",
    "mlops-courses",
    "penguin",
    "ubuntu",
}


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


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
            if skill.is_symlink():
                findings.append(f"{_relative(root, skill)}: symbolic link is not allowed")
                continue
            skills[directory.name] = skill
    return skills, findings


def _frontmatter(path: Path, root: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    relative = _relative(root, path)
    try:
        data = path.read_bytes()
    except OSError as error:
        return None, "", [f"{relative}: cannot read: {error}"]
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
    except (yaml.YAMLError, RecursionError) as error:
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
                    and resource.suffix == ".md"
                    and "templates" not in resource.relative_to(skill.parent).parts[:-1]
                ):
                    pending.append(resource)
    return reached


def _guides(directory: Path) -> list[Path]:
    """Guide metadata is authoritative; no parallel metadata.guides inventory."""
    guides: list[Path] = []
    for path in sorted((directory / "references").rglob("*.md")):
        if path.is_symlink() or not path.is_file():
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
        if GUIDE_START in body and GUIDE_END in body:
            findings.append(f"{_relative(root, skill)}: stale guide index; run mise run format:skills")
        else:
            findings.append(f"{_relative(root, skill)}: add {GUIDE_START} and {GUIDE_END} markers for the guide index")
    return findings


def _resource_findings(root: Path, skill: Path) -> list[str]:
    directory = skill.parent
    texts = {skill: skill.read_text(encoding="utf-8")}
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
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            findings.append(f"{_relative(root, path)}: is not UTF-8: {error}")
            continue
        unsafe = _unsafe_text_finding(_relative(root, path), text)
        if unsafe:
            findings.append(unsafe)
        texts[path] = text
    reached = _reachable_resources(skill, texts, resources)
    findings.extend(
        f"{_relative(root, path)}: resource is not reachable from SKILL.md" for path in sorted(resources - reached)
    )
    return findings


@functools.cache
def _document_targets(content: str) -> tuple[str, ...]:
    targets: list[str] = []
    for token in MARKDOWN.parse(content):
        for candidate in [token, *(token.children or [])]:
            if candidate.type == "link_open" and isinstance(href := candidate.attrGet("href"), str):
                targets.append(href)
            elif candidate.type == "image" and isinstance(src := candidate.attrGet("src"), str):
                targets.append(src)
    return tuple(targets)


def _metadata_findings(relative: str, metadata: Any) -> list[str]:
    if not isinstance(metadata, dict):
        return [f"{relative}: metadata must be a mapping"]
    findings: list[str] = []
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()):
        findings.append(f"{relative}: metadata keys and values must be strings")
    kind = metadata.get("kind")
    if not isinstance(kind, str) or kind not in SKILL_KINDS:
        findings.append(f"{relative}: metadata.kind must be connector, task, or collection")
    for field in ("author", "source", "created", "updated"):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(f"{relative}: metadata.{field} must be a non-empty string")
    return findings


def _skill_findings(root: Path, name: str, path: Path) -> list[str]:
    relative = _relative(root, path)
    metadata, body, findings = _frontmatter(path, root)
    if metadata is None:
        return findings
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
    if metadata.get("license") != "MIT":
        findings.append(f"{relative}: license must be MIT")
    findings.extend(_metadata_findings(relative, metadata.get("metadata")))
    findings.extend(_guide_findings(root, path, body))

    findings.extend(_resource_findings(root, path))
    return findings


def _is_allowed_email_domain(domain: str) -> bool:
    lowered = domain.lower().strip(".")
    return lowered in ALLOWED_EMAIL_DOMAINS or lowered.endswith(ALLOWED_EMAIL_SUFFIXES)


def _workstation_tokens(home: Path, *, include_hostname: bool = False) -> set[str]:
    """Extract non-public employer/workstation identifiers from untracked local config."""
    tokens: set[str] = set()

    def _add(candidate: str) -> None:
        cleaned = candidate.strip().lower()
        if (
            len(cleaned) >= 4
            and cleaned not in SAFE_HOST_TOKENS
            and not cleaned.startswith(("fmind-", "fmind.", "fmind_"))
        ):
            tokens.add(cleaned)

    dot_yaml = home / ".config/dot.yaml"
    if dot_yaml.is_file():
        try:
            config = yaml.safe_load(dot_yaml.read_text(encoding="utf-8"))
        except OSError, yaml.YAMLError:
            config = None
        if isinstance(config, dict):
            auth = config.get("auth")
            if isinstance(auth, dict):
                for section in auth.values():
                    if isinstance(section, dict) and isinstance(project := section.get("project"), str):
                        _add(project)
            pull = config.get("pull")
            if isinstance(pull, dict) and isinstance(dirs := pull.get("directories"), list):
                for entry in dirs:
                    if isinstance(entry, str):
                        _add(Path(entry.rstrip("/")).name)
            trust = config.get("trust")
            if isinstance(trust, dict) and isinstance(owners := trust.get("github_owners"), list):
                for owner in owners:
                    if isinstance(owner, str):
                        _add(owner)

    git_dir = home / ".config/git"
    if git_dir.is_dir():
        for path in sorted(git_dir.iterdir()):
            if not path.is_file() or path.name in {"allowed_signers", "personal.gitconfig", "theme.gitconfig"}:
                continue
            if path.name.startswith("config.") and len(suffix := path.name.removeprefix("config.")) >= 4:
                _add(suffix)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for match in EMAIL_PATTERN.finditer(text):
                full_email, domain = match.group(1), match.group(2)
                if not _is_allowed_email_domain(domain):
                    _add(full_email)
                    _add(domain)
                    for label in domain.split(".")[:-1]:
                        _add(label)
            for user_match in re.finditer(r"^\s*user\s*=\s*(.+?)\s*$", text, re.MULTILINE):
                _add(user_match.group(1))

    if include_hostname:
        _add(socket.gethostname().split(".")[0])

    return tokens


def privacy_findings(root: Path, home: Path | None = None) -> list[str]:
    """Check tracked sources and git history for unapproved email domains and local host tokens."""
    root = root.resolve()
    resolved_home = (home if home is not None else Path.home()).resolve()
    tokens = _workstation_tokens(resolved_home, include_hostname=(home is None and root == ROOT))
    token_pattern = (
        re.compile(
            r"(?<![A-Za-z0-9])(?:"
            + "|".join(re.escape(t) for t in sorted(tokens, key=len, reverse=True))
            + r")(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        if tokens
        else None
    )

    has_git = (root / ".git").exists()
    if has_git:
        listed = subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],  # noqa: S607
            check=True,
            capture_output=True,
            timeout=30,
        ).stdout
        relatives = [item.decode("utf-8", errors="replace") for item in listed.split(b"\0") if item]
    else:
        relatives = [
            path.relative_to(root).as_posix()
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()
        ]

    findings: list[str] = []
    for relative in sorted(relatives):
        if relative in PRIVACY_SKIP_PATHS or relative.startswith(PRIVACY_SKIP_PREFIXES) or relative.endswith(".age"):
            continue
        path = root / relative
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        for match in EMAIL_PATTERN.finditer(text):
            email, domain = match.group(1), match.group(2)
            if not _is_allowed_email_domain(domain):
                findings.append(
                    f"{relative}: unapproved email domain {domain!r} in {email!r}; "
                    "use fmind.dev, fmind.ai, or RFC 2606 domains (@example.com, @example.test)"
                )
        if token_pattern is not None and (hit := token_pattern.search(text)) is not None:
            findings.append(
                f"{relative}: contains local workstation identifier {hit.group(0)!r} from untracked host config"
            )

    if has_git:
        log_out = subprocess.run(  # noqa: S603 # nosemgrep: dangerous-subprocess-use-audit
            ["git", "-C", str(root), "log", "HEAD", "--format=%h%x09%ae%x09%ce"],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        for line in log_out.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            sha, author_email, committer_email = parts
            for role, email in (("author", author_email), ("committer", committer_email)):
                domain = email.partition("@")[2]
                if not domain or not _is_allowed_email_domain(domain):
                    findings.append(
                        f"git commit {sha}: unapproved {role} email {email!r}; use fmind.dev, fmind.ai, or github.com"
                    )
                elif token_pattern is not None and (hit := token_pattern.search(email)) is not None:
                    findings.append(
                        f"git commit {sha}: {role} email contains local workstation identifier {hit.group(0)!r}"
                    )

    return sorted(set(findings))


def repository_findings(root: Path) -> list[str]:
    """Return every deterministic catalog, package, and budget finding."""
    root = root.resolve()
    discovered, findings = _discover_skills(root)

    for name, path in sorted(discovered.items()):
        findings.extend(_skill_findings(root, name, path))
    findings.extend(privacy_findings(root))
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
    return sorted(set(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="refresh marked guide indexes from guide metadata")
    args = parser.parse_args()
    root = ROOT
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
    sys.stdout.write(f"Validated {len(_discover_skills(root)[0])} first-party skills.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
