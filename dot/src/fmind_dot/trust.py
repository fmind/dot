"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Sequence
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
_Edit = Callable[[Path, str, list[str]], tuple[str, list[str]]]


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


def _update(path: Path, edit: _Edit, folders: list[str], *, home: Path | None = None) -> list[str]:
    updated, changed = edit(path, _read_text(path), folders)
    if changed:
        _write_text(path, updated, home=home)
    return changed


def _json_list(path: Path, raw: str, folders: list[str], key: str) -> tuple[str, list[str]]:
    data = _load_json(path, raw)
    if not isinstance(trusted := data.setdefault(key, []), list):
        raise DotError(f"{path}: {key} must be a JSON array")
    changed = [f for f in folders if f not in trusted]
    trusted.extend(changed)
    return _dump_json(data), changed


def _claude(path: Path, text: str, folders: list[str]) -> tuple[str, list[str]]:
    data = _load_json(path, text)
    if not isinstance(projects := data.setdefault("projects", {}), dict):
        raise DotError(f"{path}: projects must be a JSON object")
    changed: list[str] = []
    for folder in folders:
        if not isinstance(project := projects.setdefault(folder, {}), dict):
            raise DotError(f"{path}: project {folder} must be a JSON object")
        if project.get("hasTrustDialogAccepted") is not True:
            project["hasTrustDialogAccepted"] = True
            changed.append(folder)
    return _dump_json(data), changed


def _claude_settings(path: Path, text: str, folders: list[str], *, home: Path) -> tuple[str, list[str]]:
    data = _load_json(path, text)
    if not isinstance(perms := data.setdefault("permissions", {}), dict):
        raise DotError(f"{path}: permissions must be a JSON object")
    dirs = perms.setdefault("additionalDirectories", [])
    if not isinstance(dirs, list) or not all(isinstance(i, str) for i in dirs):
        raise DotError(f"{path}: permissions.additionalDirectories must be a JSON array of strings")
    expanded = [expand_path(i, home=home) for i in dirs]
    covered = {i.resolve() for i in expanded} | set(expanded)
    changed: list[str] = []
    for raw in folders:
        folder, resolved = Path(raw), Path(raw).resolve()
        if not any(resolved.is_relative_to(p) or folder.is_relative_to(p) for p in covered):
            dirs.append(raw)
            covered.update((folder, resolved))
            changed.append(raw)
    return _dump_json(data), changed


def register_claude_directories(folders: Sequence[Path], *, home: Path | None = None) -> list[Path]:
    """Extend Claude's permissions.additionalDirectories with ~/.agents and uncovered roots."""
    resolved_home = (home or Path.home()).resolve()
    claude_dir = resolved_home / ".claude"
    _reject_symlink_path(claude_dir, resolved_home, "harness directory")
    if not claude_dir.is_dir():
        return []
    ordered = [resolved_home / ".agents", *sorted(set(folders), key=lambda i: (len(i.parts), str(i)))]
    selected = {str(folder): folder for folder in ordered}
    added = _update(
        claude_dir / "settings.json",
        lambda p, t, items: _claude_settings(p, t, items, home=resolved_home),
        list(selected),
        home=resolved_home,
    )
    return [selected[raw] for raw in added]


def _pi(path: Path, text: str, folders: list[str]) -> tuple[str, list[str]]:
    data = _load_json(path, text)
    changed = [f for f in folders if data.get(f) is not True and (Path(f) / ".git").exists()]
    data.update(dict.fromkeys(changed, True))
    return _dump_json(data), changed


def _harnesses(home: Path) -> dict[str, tuple[Path, _Edit]]:
    return {
        "claude": (home / ".claude.json", _claude),
        "agy": (
            home / ".gemini/antigravity-cli/settings.json",
            lambda p, t, f: _json_list(p, t, f, "trustedWorkspaces"),
        ),
        "pi": (home / ".pi/agent/trust.json", _pi),
    }


def installed_harnesses(home: Path | None = None) -> list[str]:
    resolved_home = (home or Path.home()).resolve()
    installed: list[str] = []
    for name, (path, _) in _harnesses(resolved_home).items():
        state_dir = resolved_home / ".claude" if name == "claude" else path.parent
        _reject_symlink_path(state_dir, resolved_home, "harness directory")
        if state_dir.is_dir():
            installed.append(name)
    return installed


def trust_folders(folders: list[Path], *, home: Path | None = None) -> dict[Path, list[str]]:
    resolved_home = (home or Path.home()).resolve()
    selected = {str(f): f for f in folders}
    changed: dict[Path, list[str]] = {f: [] for f in selected.values()}
    harnesses = _harnesses(resolved_home)
    for name in installed_harnesses(resolved_home):
        for folder in _update(harnesses[name][0], harnesses[name][1], list(selected), home=resolved_home):
            changed[selected[folder]].append(name)
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
    trusted = {root for d in state.config.pull.directories if (root := expand_path(d).resolve()).is_dir()}
    candidates = [repo for repo in find_git_repositories(state) if repo not in trusted]
    allowed = run_parallel(state.runner, lambda repo: _allowed_origin(state, repo), candidates, _ORIGIN_CONCURRENCY)
    skipped: list[Path] = []
    for repo, ok in zip(candidates, allowed, strict=True):
        (trusted.add if ok else skipped.append)(repo)
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
    claude_roots = (
        [*[expand_path(d).resolve() for d in state.config.pull.directories], *folders] if "all" in targets else folders
    )
    for root in [*folders, *claude_roots]:
        if root in forbidden:
            raise DotError(f"refusing to trust {root}: it contains the home directory")
    harnesses = installed_harnesses(home)
    if not harnesses:
        state.stdout.write("○ No agent harness state found; nothing to trust yet.\n")
        return
    projects = register_agy_projects(folders, state.config.trust.agy_projects, home=home) if "agy" in harnesses else []
    claude_dirs = register_claude_directories(claude_roots, home=home) if "claude" in harnesses else []
    changes = trust_folders(folders, home=home)
    lines = []
    for folder in folders:
        changed = changes[folder]
        detail = f"trusted in {', '.join(changed)}" if changed else "already trusted"
        lines.append(f"{'✓' if not changed else '+'} {folder}: {detail}\n")
    lines.extend(f"+ {f}: added to Claude additionalDirectories\n" for f in claude_dirs)
    lines.extend(f"+ {f}: added to agy Remote Control projects\n" for f in projects)
    lines.extend(f"- {f}: skipped (origin is not a github.com repository of trust.github_owners)\n" for f in skipped)
    state.stdout.writelines(lines)


def register(commands: Parser) -> None:
    t = commands.command(
        "trust",
        "Pre-accept folder trust in Claude, agy, and Pi, and add trusted repositories to agy Remote Control projects",
        lambda state, args: run_trust(state, args.targets or ["."]),
        epilog="The target 'all' covers pull.directories and their trust.github_owners repositories.",
    )
    t.add_argument(
        "targets",
        nargs="*",
        help="Folders or repositories to trust, or 'all' for the configured workspaces [default: .]",
    )
