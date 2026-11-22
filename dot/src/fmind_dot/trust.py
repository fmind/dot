"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import hashlib
import json
import os
import re
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from fmind_dot.command import Parser
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError, NotGitWorkTreeError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import run_parallel
from fmind_dot.repository import find_git_repositories
from fmind_dot.state import State

_GITHUB_ORIGIN = re.compile(
    r"^(?:https://(?:[^@/]+@)?github\.com(?::443)?/|ssh://(?:[^@/]+@)?github\.com(?::22)?/|[^@/:]+@github\.com:)"
    r"(?P<owner>[A-Za-z0-9-]+)/[^/]+?/?$",
    re.IGNORECASE,
)
_ORIGIN_TIMEOUT_SECONDS = 10
_ORIGIN_CONCURRENCY = 8
_AGY_SETTINGS_REL = Path(".gemini/antigravity-cli/settings.json")


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


def _reject_symlink_path(path: Path, home: Path | None, label: str) -> None:
    """Refuse symlinks at ``path`` or any intermediate ancestor inside ``home``."""
    if home is not None and path.is_relative_to(home):
        current = home
        for part in path.relative_to(home).parts:
            current = current / part
            if current.is_symlink():
                raise DotError(f"refusing symlinked {label}: {current}")
        return
    if path.is_symlink():
        raise DotError(f"refusing symlinked {label}: {path}")


def _read_text(path: Path) -> str:
    _lstat_regular(path)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except UnicodeDecodeError as error:
        raise DotError(f"{path} is not valid UTF-8") from error
    except OSError as error:
        raise DotError(f"failed to read trust file {path}: {error}") from error


def _write_text(path: Path, text: str, *, home: Path | None = None) -> None:
    _reject_symlink_path(path.parent, home, "trust directory")
    info = _lstat_regular(path)
    try:
        write_atomic_file(path, text.encode("utf-8"), mode=stat.S_IMODE(info.st_mode) if info else 0o600)
    except OSError as error:
        raise DotError(f"failed to write trust file {path}: {error}") from error


def _load_json(path: Path, text: str) -> dict[str, Any]:
    try:
        value = json.loads(text) if text.strip() else {}
    except (ValueError, RecursionError) as error:
        raise DotError(f"{path} is not valid JSON; repair it before trusting folders") from error
    if not isinstance(value, dict):
        raise DotError(f"{path} must contain a JSON object")
    return value


def _dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _update_trusted_workspaces(path: Path, folders: list[str], *, home: Path | None = None) -> list[str]:
    data = _load_json(path, _read_text(path))
    if not isinstance(trusted := data.setdefault("trustedWorkspaces", []), list):
        raise DotError(f"{path}: trustedWorkspaces must be a JSON array")
    changed = [f for f in folders if f not in trusted]
    if changed:
        trusted.extend(changed)
        _write_text(path, _dump_json(data), home=home)
    return changed


def installed_harnesses(home: Path | None = None) -> list[str]:
    resolved_home = (home or Path.home()).resolve()
    state_dir = (resolved_home / _AGY_SETTINGS_REL).parent
    _reject_symlink_path(state_dir, resolved_home, "harness directory")
    return ["agy"] if state_dir.is_dir() else []


def trust_folders(folders: list[Path], *, home: Path | None = None) -> dict[Path, list[str]]:
    resolved_home = (home or Path.home()).resolve()
    selected = {str(f): f for f in folders}
    changed: dict[Path, list[str]] = {f: [] for f in selected.values()}
    if installed_harnesses(resolved_home):
        for folder in _update_trusted_workspaces(resolved_home / _AGY_SETTINGS_REL, list(selected), home=resolved_home):
            changed[selected[folder]].append("agy")
    return changed


def _agy_project_folders(path: Path, text: str) -> set[str]:
    entries = _load_json(path, text).get("projectResources", {})
    resources = entries.get("resources", []) if isinstance(entries, dict) else None
    if not isinstance(resources, list) or not all(isinstance(e, dict) for e in resources):
        raise DotError(f"{path}: projectResources.resources must be a JSON array of objects")
    folders: set[str] = set()
    for entry in resources:
        git_folder = entry.get("gitFolder")
        uri = entry.get("folderUri") or (git_folder.get("folderUri") if isinstance(git_folder, dict) else None)
        if isinstance(uri, str) and uri.startswith("file://"):
            folders.add(unquote(urlparse(uri).path))
    return folders


def register_agy_projects(folders: list[Path], include: Sequence[str], *, home: Path | None = None) -> list[Path]:
    """Add matching trusted repositories to agy's Remote Control project picker."""
    resolved_home = (home or Path.home()).resolve()
    registry = resolved_home / ".gemini/config/projects"
    _reject_symlink_path(registry, resolved_home, "project registry")
    if not registry.is_dir():
        return []
    listed = set().union(*(_agy_project_folders(p, _read_text(p)) for p in sorted(registry.glob("*.json"))))
    patterns = [expand_path(p, home=resolved_home).resolve() for p in include]
    chezmoi = (resolved_home / ".local/share/chezmoi").resolve()
    added: list[Path] = []
    for folder in folders:
        if not (folder / ".git").exists() or str(folder) in listed or not any(folder.full_match(p) for p in patterns):
            continue
        name = (
            "fmind/dot"
            if folder == chezmoi
            else (str(folder.relative_to(resolved_home)) if folder.is_relative_to(resolved_home) else str(folder))
        )
        slug = re.sub(r"[^a-z0-9-.:]+", "-", name.casefold()).strip("-.:")
        project_id = f"local-{slug or hashlib.sha256(str(folder).encode('utf-8')).hexdigest()[:24]}"
        target = registry / f"{project_id}.json"
        if _lstat_regular(target) is not None:
            continue
        payload = {
            "id": project_id,
            "name": name,
            "projectResources": {"resources": [{"folderUri": folder.as_uri()}]},
        }
        _write_text(target, _dump_json(payload), home=resolved_home)
        added.append(folder)
    return added


def github_owner(origin: str) -> str | None:
    match = _GITHUB_ORIGIN.fullmatch(origin.strip())
    return match.group("owner") if match else None


def _allowed_origin(state: State, repository: Path) -> bool:
    try:
        res = state.runner.run(
            ["git", "remote", "get-url", "origin"], cwd=repository, timeout=_ORIGIN_TIMEOUT_SECONDS, check=False
        )
    except DotError, OSError:
        return False
    owner = github_owner(res.stdout.strip()) if res.returncode == 0 and res.stdout.strip() else None
    return owner is not None and owner.casefold() in {n.casefold() for n in state.config.trust.github_owners}


def _target_folders(state: State, target: str, forbidden: set[Path]) -> tuple[list[Path], list[Path]]:
    if target != "all":
        if not (path := expand_path(target).resolve()).is_dir():
            raise DotError(f"{path} is not a directory")
        if path in forbidden:
            raise DotError(f"refusing to trust {path}: it contains the home directory")
        try:
            return find_git_repositories(state, [path]), []
        except NotGitWorkTreeError:
            return [path], []
    candidates = find_git_repositories(state)
    allowed = run_parallel(state.runner, lambda repo: _allowed_origin(state, repo), candidates, _ORIGIN_CONCURRENCY)
    trusted: list[Path] = []
    skipped: list[Path] = []
    for repo, ok in zip(candidates, allowed, strict=True):
        (trusted.append if ok else skipped.append)(repo)
    return sorted(trusted), skipped


def run_trust(state: State, targets: Sequence[str] = (".",)) -> None:
    home = Path.home().resolve()
    forbidden = {home, *home.parents}
    selected: set[Path] = set()
    excluded: set[Path] = set()
    for target in targets:
        found, skipped_here = _target_folders(state, target, forbidden)
        selected.update(found)
        excluded.update(skipped_here)
    folders, skipped = sorted(selected), sorted(excluded - selected)
    for root in folders:
        if root in forbidden:
            raise DotError(f"refusing to trust {root}: it contains the home directory")
    if not installed_harnesses(home):
        state.stdout.write("○ No agent harness state found; nothing to trust yet.\n")
        return
    projects = register_agy_projects(folders, state.config.trust.agy_projects, home=home)
    changes = trust_folders(folders, home=home)
    lines = []
    for folder in folders:
        changed = changes[folder]
        detail = f"trusted in {', '.join(changed)}" if changed else "already trusted"
        lines.append(f"{'✓' if not changed else '+'} {folder}: {detail}\n")
    lines.extend(f"+ {f}: added to agy Remote Control projects\n" for f in projects)
    lines.extend(f"- {f}: skipped (origin is not a github.com repository of trust.github_owners)\n" for f in skipped)
    state.stdout.writelines(lines)


def register(commands: Parser) -> None:
    t = commands.command(
        "trust",
        "Pre-accept folder trust in agy and add trusted repositories to agy Remote Control projects",
        lambda state, args: run_trust(state, args.targets or ["."]),
        epilog=(
            "The target 'all' covers trust.github_owners repositories under pull.directories.\n\n"
            "Examples: dot trust . · dot trust all"
        ),
    )
    t.add_argument(
        "targets",
        nargs="*",
        help="Folders or repositories to trust, or 'all' for the configured workspaces [default: .]",
    )
