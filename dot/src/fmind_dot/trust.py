"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import argparse
import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from fmind_dot.command import Parser, add_json
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError, NotGitWorkTreeError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import run_parallel
from fmind_dot.reporting import write_json
from fmind_dot.repository import find_git_repositories, resolve_git_metadata_dir
from fmind_dot.state import State

# Each harness stores trust in a file it also writes itself; preserve unrelated state.
# Claude and agy key trust on the repository root, so a trusted parent
# never covers the repositories below it; Copilot and Pi trust every path below an entry.
_COPILOT_COMMENT = re.compile(r"^\s*//")
# github.com origins over HTTPS, ssh:// URLs, or scp-like SSH; the owner is the first path segment.
_GITHUB_ORIGIN = re.compile(
    r"^(?:https://(?:[^@/]+@)?github\.com(?::443)?/|ssh://(?:[^@/]+@)?github\.com(?::22)?/|[^@/:]+@github\.com:)"
    r"(?P<owner>[A-Za-z0-9-]+)/[^/]+?/?$",
    re.IGNORECASE,
)
_ORIGIN_TIMEOUT_SECONDS = 10
_ORIGIN_CONCURRENCY = 8


# A harness edit applies every folder to the file text: it returns the new text and the folders it changed.
_Edit = Callable[[Path, str, list[str]], tuple[str, list[str]]]
_WRITE_ATTEMPTS = 3


def _lstat_regular(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        raise DotError(f"refusing symlinked trust file: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise DotError(f"refusing non-regular trust file: {path}")
    return info


def _write(path: Path, text: str) -> None:
    """Replace the file atomically, keeping its permissions (new files are owner-only)."""
    info = _lstat_regular(path)
    mode = stat.S_IMODE(info.st_mode) if info is not None else 0o600
    try:
        write_atomic_file(path, text.encode("utf-8"), mode=mode)
    except OSError as error:
        raise DotError(f"failed to write trust file {path}: {error}") from error


def _file_state(path: Path) -> tuple[int, int, int] | None:
    info = _lstat_regular(path)
    return None if info is None else (info.st_ino, info.st_size, info.st_mtime_ns)


def _read_utf8(path: Path) -> str:
    _lstat_regular(path)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except UnicodeDecodeError as error:
        raise DotError(f"{path} is not valid UTF-8") from error
    except OSError as error:
        raise DotError(f"failed to read trust file {path}: {error}") from error


def _update(path: Path, edit: _Edit, folders: list[str], *, dry_run: bool) -> list[str]:
    """Apply all folders in one read-modify-write; return the folders that changed.

    Each host also writes its own file. Replace it only if it still matches what was read,
    and re-apply to the host's newer content otherwise, a bounded number of times.
    """
    for _ in range(_WRITE_ATTEMPTS):
        observed = _file_state(path)
        try:
            text = _read_utf8(path)
        except FileNotFoundError:
            text = ""
        updated, changed = edit(path, text, folders)
        if dry_run or not changed:
            return changed
        if _file_state(path) == observed:
            _write(path, updated)
            return changed
    raise DotError(f"{path} kept changing while trusting folders; retry once its harness is idle")


def _load_json(path: Path, text: str) -> dict[str, Any]:
    try:
        value = json.loads(text) if text.strip() else {}
    except (ValueError, RecursionError) as error:
        raise DotError(f"{path} is not valid JSON; repair it before trusting folders") from error
    if not isinstance(value, dict):
        raise DotError(f"{path} must contain a JSON object")
    return value


def _json_list(path: Path, raw: str, folders: list[str], key: str) -> tuple[str, list[str]]:
    """Append folders to a top-level JSON array (agy trustedWorkspaces, Copilot trustedFolders)."""
    # Copilot prefixes // comment lines that strict JSON rejects; keep them in place.
    lines = raw.splitlines(keepends=True)
    header = "".join(line for line in lines if _COPILOT_COMMENT.match(line))
    data = _load_json(path, "".join(line for line in lines if not _COPILOT_COMMENT.match(line)))
    trusted = data.setdefault(key, [])
    if not isinstance(trusted, list):
        raise DotError(f"{path}: {key} must be a JSON array")
    changed = [folder for folder in folders if folder not in trusted]
    trusted.extend(changed)
    return header + json.dumps(data, indent=2, ensure_ascii=False) + "\n", changed


def _claude(path: Path, text: str, folders: list[str]) -> tuple[str, list[str]]:
    data = _load_json(path, text)
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        raise DotError(f"{path}: projects must be a JSON object")
    changed = []
    for folder in folders:
        project = projects.setdefault(folder, {})
        if not isinstance(project, dict):
            raise DotError(f"{path}: project {folder} must be a JSON object")
        if project.get("hasTrustDialogAccepted") is not True:
            # Claude re-reads and merges this file under its own lock before it writes.
            project["hasTrustDialogAccepted"] = True
            changed.append(folder)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", changed


def _claude_settings(path: Path, text: str, folders: list[str], *, home: Path | None = None) -> tuple[str, list[str]]:
    """Add uncovered roots to Claude's permissions.additionalDirectories, keeping host entries."""
    resolved_home = (home or Path.home()).resolve()
    data = _load_json(path, text)
    permissions = data.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise DotError(f"{path}: permissions must be a JSON object")
    directories = permissions.setdefault("additionalDirectories", [])
    if not isinstance(directories, list) or not all(isinstance(item, str) for item in directories):
        raise DotError(f"{path}: permissions.additionalDirectories must be a JSON array of strings")
    expanded = [expand_path(item, home=resolved_home) for item in directories]
    covered = {item.resolve() for item in expanded} | set(expanded)
    changed = []
    for raw in folders:
        folder = Path(raw)
        resolved = folder.resolve()
        if any(resolved.is_relative_to(parent) or folder.is_relative_to(parent) for parent in covered):
            continue
        directories.append(raw)
        covered.update((folder, resolved))
        changed.append(raw)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", changed


def register_claude_directories(
    folders: Sequence[Path], *, dry_run: bool = False, home: Path | None = None
) -> list[Path]:
    """Extend Claude's permissions.additionalDirectories with ~/.agents and uncovered roots."""
    home = (home or Path.home()).resolve()
    if not (home / ".claude").is_dir():
        return []
    # Parents precede children so workspace roots subsume the repositories below them.
    ordered = [home / ".agents", *sorted(set(folders), key=lambda item: (len(item.parts), str(item)))]
    selected = {str(folder): folder for folder in ordered}
    added = _update(
        home / ".claude" / "settings.json",
        lambda path, text, items: _claude_settings(path, text, items, home=home),
        list(selected),
        dry_run=dry_run,
    )
    return [selected[raw] for raw in added]


def _pi(path: Path, text: str, folders: list[str]) -> tuple[str, list[str]]:
    """Trust repository roots only: Pi applies a decision to every folder below it and then loads
    that folder's `.pi/` extensions, so a trusted workspace would run code from any clone inside it."""
    data = _load_json(path, text)
    changed = [folder for folder in folders if data.get(folder) is not True and (Path(folder) / ".git").exists()]
    data.update(dict.fromkeys(changed, True))
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", changed


def _harnesses(home: Path) -> dict[str, tuple[Path, _Edit]]:
    # Claude keeps trust in ~/.claude.json but its state directory is ~/.claude.
    return {
        "claude": (home / ".claude.json", _claude),
        "agy": (
            home / ".gemini" / "antigravity-cli" / "settings.json",
            lambda path, text, folders: _json_list(path, text, folders, "trustedWorkspaces"),
        ),
        "copilot": (
            home / ".copilot" / "config.json",
            lambda path, text, folders: _json_list(path, text, folders, "trustedFolders"),
        ),
        "pi": (home / ".pi" / "agent" / "trust.json", _pi),
    }


def installed_harnesses(home: Path | None = None) -> list[str]:
    """Name the harnesses that have state to extend; one that was never started has no state directory."""
    home = home or Path.home()
    return [
        name
        for name, (path, _) in _harnesses(home).items()
        if (home / ".claude" if name == "claude" else path.parent).is_dir()
    ]


def trust_folders(folders: list[Path], *, dry_run: bool = False, home: Path | None = None) -> dict[Path, list[str]]:
    """Trust folders in every installed harness, writing each file once; return each folder's changed harnesses."""
    home = home or Path.home()
    selected = {str(folder): folder for folder in folders}
    changed: dict[Path, list[str]] = {folder: [] for folder in selected.values()}
    harnesses = _harnesses(home)
    for name in installed_harnesses(home):
        path, edit = harnesses[name]
        for folder in _update(path, edit, list(selected), dry_run=dry_run):
            changed[selected[folder]].append(name)
    return changed


def _agy_project_folders(path: Path, text: str) -> set[str]:
    """Return the folders an agy project lists; agy's default project lists none."""
    project = _load_json(path, text)
    resources = project.get("projectResources", {})
    entries = resources.get("resources", []) if isinstance(resources, dict) else None
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise DotError(f"{path}: projectResources.resources must be a JSON array of objects")
    folders = set()
    for entry in entries:
        git_folder = entry.get("gitFolder")
        uri = entry.get("folderUri") or (git_folder.get("folderUri") if isinstance(git_folder, dict) else None)
        if isinstance(uri, str) and uri.startswith("file://"):
            folders.add(unquote(urlparse(uri).path))
    return folders


def register_agy_projects(
    folders: list[Path], include: Sequence[str], *, dry_run: bool = False, home: Path | None = None
) -> list[Path]:
    """Add selected trusted repositories to agy's Remote Control project picker; return the ones added.

    Like trust, this only adds: entries agy or the owner created, even for removed checkouts, stay.
    """
    home = (home or Path.home()).resolve()
    registry = home / ".gemini" / "config" / "projects"
    if registry.is_symlink():
        raise DotError(f"refusing symlinked project registry: {registry}")
    # agy creates the registry on its first start; until then there is nothing to extend.
    if not registry.is_dir():
        return []
    listed: set[str] = set()
    for path in sorted(registry.glob("*.json")):
        listed |= _agy_project_folders(path, _read_utf8(path))
    # Folders arrive resolved, so patterns resolve too: a symlinked home would otherwise never match.
    patterns = [expand_path(pattern, home=home).resolve() for pattern in include]
    chezmoi = (home / ".local" / "share" / "chezmoi").resolve()
    added = []
    for folder in folders:
        # Workspaces and plain folders are trusted too, but only selected repositories become projects.
        if not (folder / ".git").exists() or str(folder) in listed:
            continue
        if not any(folder.full_match(pattern) for pattern in patterns):
            continue
        name = (
            "fmind/dot"
            if folder == chezmoi
            else (str(folder.relative_to(home)) if folder.is_relative_to(home) else str(folder))
        )
        # agy lists projects in filename order; a slugged ID keeps local repositories alphabetical.
        slug = re.sub(r"[^a-z0-9-.:]+", "-", name.casefold()).strip("-.:")
        project_id = (
            f"local-{slug}" if slug else "local-" + hashlib.sha256(str(folder).encode("utf-8")).hexdigest()[:24]
        )
        target = registry / f"{project_id}.json"
        if _lstat_regular(target) is not None:
            continue
        if not dry_run:
            project = {
                "id": project_id,
                "name": name,
                "projectResources": {"resources": [{"folderUri": folder.as_uri()}]},
            }
            _write(target, json.dumps(project, indent=2) + "\n")
        added.append(folder)
    return added


_GIT_SECTION_HEADER = re.compile(r'^\[(?P<name>[A-Za-z0-9-]+)(?:\s+"(?P<sub>[^"\\]*)")?\](?:\s*[#;].*)?$')
_GIT_INSTEAD_OF = re.compile(r"(?mi)^\s*insteadof\s*(?:=|$)")
_MAX_GIT_CONFIG_BYTES = 262_144


def github_owner(origin: str) -> str | None:
    """Return the owner of a github.com origin URL, or None for any other remote."""
    match = _GITHUB_ORIGIN.fullmatch(origin.strip())
    return match.group("owner") if match else None


def _has_global_url_insteadof(home: Path) -> bool:
    """Return True when global/system Git configuration may rewrite remote fetch URLs."""
    if os.environ.get("GIT_CONFIG_COUNT"):
        return True
    candidates: list[Path] = []
    if not os.environ.get("GIT_CONFIG_NOSYSTEM"):
        candidates.append(Path(os.environ.get("GIT_CONFIG_SYSTEM", "/etc/gitconfig")))
    if global_override := os.environ.get("GIT_CONFIG_GLOBAL"):
        candidates.append(Path(global_override))
    else:
        xdg = Path(os.environ.get("XDG_CONFIG_HOME") or (home / ".config"))
        candidates.extend((xdg / "git/config", home / ".gitconfig"))
        git_dir = xdg / "git"
        try:
            candidates.extend(sorted(git_dir.iterdir()))
        except FileNotFoundError:
            pass
        except OSError:
            return True
    for candidate in candidates:
        if candidate == Path(os.devnull):
            continue
        try:
            info = candidate.stat()
        except FileNotFoundError:
            continue
        except OSError:
            return True
        if not stat.S_ISREG(info.st_mode):
            continue
        try:
            if _GIT_INSTEAD_OF.search(candidate.read_text(encoding="utf-8")):
                return True
        except OSError, UnicodeDecodeError:
            return True
    return False


def _local_origin_url(repository: Path) -> str | None:
    """Read remote.origin.url directly from a standard .git/config, or return None to ask git."""
    metadata = resolve_git_metadata_dir(repository)
    if metadata is None or (metadata / "config.worktree").exists():
        return None
    commondir_file = metadata / "commondir"
    common_dir = metadata
    try:
        commondir_info = commondir_file.lstat()
    except FileNotFoundError:
        commondir_info = None
    except OSError:
        return None
    if commondir_info is not None:
        if not stat.S_ISREG(commondir_info.st_mode) or commondir_info.st_size > 4096:
            return None
        try:
            rel = commondir_file.read_text(encoding="utf-8").strip()
        except OSError, UnicodeDecodeError:
            return None
        if not rel or "\n" in rel or "\r" in rel:
            return None
        common_dir = (metadata / rel).resolve()
    config_path = common_dir / "config"
    try:
        info = config_path.lstat()
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_GIT_CONFIG_BYTES:
        return None
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return None
    section: tuple[str, str] | None = None
    urls: list[str] = []
    for raw_line in text.splitlines():
        if raw_line.endswith("\\"):
            return None
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("["):
            header = _GIT_SECTION_HEADER.match(stripped)
            if header is None:
                return None
            kind = header.group("name").lower()
            if kind in {"include", "includeif", "url"}:
                return None
            section = (kind, header.group("sub") or "")
            continue
        if "=" not in stripped:
            continue
        key, _, raw_value = stripped.partition("=")
        key_name = key.strip().lower()
        if section == ("extensions", "") and key_name == "worktreeconfig":
            return None
        if section == ("remote", "origin") and key_name == "url":
            value = raw_value.strip()
            if any(ch in value for ch in ('"', "\\", "#", ";")):
                return None
            urls.append(value)
    if len(urls) > 1:
        return None
    return urls[0] if urls else ""


def _allowed_origin(state: State, repository: Path, *, fast_origin: bool = False) -> bool:
    """Only an origin under a configured GitHub owner is trusted; unknown or unreadable remotes fail closed."""
    origin = _local_origin_url(repository) if fast_origin else None
    if origin is None:
        try:
            result = state.runner.run(
                ["git", "remote", "get-url", "origin"], cwd=repository, timeout=_ORIGIN_TIMEOUT_SECONDS, check=False
            )
        except DotError, OSError:
            return False
        origin = result.stdout if result.returncode == 0 else ""
    owner = github_owner(origin) if origin else None
    allowed = {name.casefold() for name in state.config.trust.github_owners}
    return owner is not None and owner.casefold() in allowed


def _target_folders(state: State, target: str) -> tuple[list[Path], list[Path]]:
    """Return the folders to trust and the workspace repositories skipped by the owner allowlist."""
    home = Path.home().resolve()
    forbidden = {home, *home.parents}
    if target != "all":
        path = expand_path(target).resolve()
        if not path.is_dir():
            raise DotError(f"{path} is not a directory")
        if path in forbidden:
            raise DotError(f"refusing to trust {path}: it contains the home directory")
        try:
            folders = find_git_repositories(state, [path])
        except NotGitWorkTreeError:
            folders = [path]
        skipped: list[Path] = []
    else:
        # Configured workspaces themselves cover their non-repository subfolders in Claude
        # and every path below them in Copilot; each repository needs its own entry.
        roots = [expand_path(directory).resolve() for directory in state.config.pull.directories]
        trusted = {root for root in roots if root.is_dir()}
        candidates = [repository for repository in find_git_repositories(state) if repository not in trusted]
        fast_origin = not _has_global_url_insteadof(home)
        allowed = run_parallel(
            state.runner,
            lambda repository: _allowed_origin(state, repository, fast_origin=fast_origin),
            candidates,
            _ORIGIN_CONCURRENCY,
        )
        skipped = []
        for repository, is_allowed in zip(candidates, allowed, strict=True):
            if is_allowed:
                trusted.add(repository)
            else:
                skipped.append(repository)
        folders = sorted(trusted)
    # Copilot trusts every descendant of a folder: trusting home or an ancestor would
    # bypass the trust.github_owners allowlist for every repository below it.
    for folder in folders:
        if folder in forbidden:
            raise DotError(f"refusing to trust {folder}: it contains the home directory")
    return folders, skipped


def run_trust(state: State, targets: Sequence[str] = (".",), *, dry_run: bool = False, as_json: bool = False) -> None:
    # One invocation covers every target, so the apply hook pays the CLI startup once.
    home = Path.home().resolve()
    forbidden = {home, *home.parents}
    selected: set[Path] = set()
    excluded: set[Path] = set()
    for target in targets:
        found, skipped_here = _target_folders(state, target)
        selected.update(found)
        excluded.update(skipped_here)
    folders = sorted(selected)
    skipped = sorted(excluded - selected)
    claude_roots = (
        [*[expand_path(directory).resolve() for directory in state.config.pull.directories], *folders]
        if "all" in targets
        else folders
    )
    for root in claude_roots:
        if root in forbidden:
            raise DotError(f"refusing to trust {root}: it contains the home directory")
    harnesses = installed_harnesses()
    # Projects go first: a malformed agy project file then stops the run before any trust write.
    include = state.config.trust.agy_projects
    projects = register_agy_projects(folders, include, dry_run=dry_run) if "agy" in harnesses else []
    claude_directories = register_claude_directories(claude_roots, dry_run=dry_run) if "claude" in harnesses else []
    changes = trust_folders(folders, dry_run=dry_run) if harnesses else {}
    if as_json:
        document = {
            "schema": "dot.trust/v1",
            "dry_run": dry_run,
            "harnesses": harnesses,
            "folders": [{"path": str(folder), "changed": changes.get(folder, [])} for folder in folders],
            "skipped": [str(folder) for folder in skipped],
            "agy_projects": [str(folder) for folder in projects],
            "claude_directories": [str(folder) for folder in claude_directories],
        }
        write_json(state.stdout, document)
        return
    if not harnesses:
        # Apply runs this hook before any harness has started; that is not a failure.
        state.stdout.write("○ No agent harness state found; nothing to trust yet.\n")
        return
    for folder in folders:
        changed = changes[folder]
        verb = "would trust" if dry_run else "trusted"
        detail = f"{verb} in {', '.join(changed)}" if changed else "already trusted"
        state.stdout.write(f"{'✓' if not changed else '+'} {folder}: {detail}\n")
    for folder in claude_directories:
        verb = "would add" if dry_run else "added"
        state.stdout.write(f"+ {folder}: {verb} to Claude additionalDirectories\n")
    for folder in projects:
        verb = "would add" if dry_run else "added"
        state.stdout.write(f"+ {folder}: {verb} to agy Remote Control projects\n")
    for folder in skipped:
        # Skipped repositories sit inside a trusted workspace, which Copilot applies to descendants.
        state.stdout.write(
            f"- {folder}: skipped (origin is not a github.com repository of trust.github_owners; "
            "Copilot still inherits workspace trust)\n"
        )


def _trust(state: State, args: argparse.Namespace) -> None:
    run_trust(state, args.targets or ["."], dry_run=args.dry_run, as_json=args.as_json)


def register(commands: Parser) -> None:
    trust = commands.command(
        "trust",
        "Pre-accept folder trust in Claude, agy, Copilot, and Pi, and add trusted repositories to agy Remote Control projects",
        _trust,
        epilog="The target 'all' covers pull.directories and their trust.github_owners repositories.",
    )
    trust.add_argument(
        "targets",
        nargs="*",
        help="Folders or repositories to trust, or 'all' for the configured workspaces [default: .]",
    )
    trust.add_argument("--dry-run", action="store_true", help="Report trust changes without writing harness files")
    add_json(trust)
