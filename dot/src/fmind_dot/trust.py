"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import unquote, urlparse

import typer

from fmind_dot.command_group import JsonOption
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError, NotGitWorkTreeError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import run_parallel
from fmind_dot.reporting import write_json
from fmind_dot.repository import find_git_repositories
from fmind_dot.state import State, state_from

# Each harness stores trust in a file it also writes itself; preserve unrelated state.
# Claude and agy key trust on the repository root, so a trusted parent
# never covers the repositories below it; Copilot trusts every path below an entry.
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


def _write(path: Path, text: str) -> None:
    """Replace the file atomically, keeping its permissions (new files are owner-only)."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    write_atomic_file(path, text.encode("utf-8"), mode=mode)


def _file_state(path: Path) -> tuple[int, int] | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_size, info.st_mtime_ns


def _update(path: Path, edit: _Edit, folders: list[str], *, dry_run: bool) -> list[str]:
    """Apply all folders in one read-modify-write; return the folders that changed.

    Each host also writes its own file. Replace it only if it still matches what was read,
    and re-apply to the host's newer content otherwise, a bounded number of times.
    """
    for _ in range(_WRITE_ATTEMPTS):
        observed = _file_state(path)
        try:
            text = path.read_text(encoding="utf-8")
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
    # agy creates the registry on its first start; until then there is nothing to extend.
    if not registry.is_dir():
        return []
    listed: set[str] = set()
    for path in sorted(registry.glob("*.json")):
        listed |= _agy_project_folders(path, path.read_text(encoding="utf-8"))
    # Folders arrive resolved, so patterns resolve too: a symlinked home would otherwise never match.
    patterns = [
        (home / pattern.removeprefix("~/") if pattern.startswith("~/") else expand_path(pattern)).resolve()
        for pattern in include
    ]
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
        if target.exists():
            continue
        if not dry_run:
            project = {
                "id": project_id,
                "name": name,
                "projectResources": {"resources": [{"folderUri": folder.as_uri()}]},
            }
            write_atomic_file(target, (json.dumps(project, indent=2) + "\n").encode("utf-8"), mode=0o600)
        added.append(folder)
    return added


def github_owner(origin: str) -> str | None:
    """Return the owner of a github.com origin URL, or None for any other remote."""
    match = _GITHUB_ORIGIN.fullmatch(origin.strip())
    return match.group("owner") if match else None


def _allowed_origin(state: State, repository: Path) -> bool:
    """Only an origin under a configured GitHub owner is trusted; unknown or unreadable remotes fail closed."""
    try:
        result = state.runner.run(
            ["git", "remote", "get-url", "origin"], cwd=repository, timeout=_ORIGIN_TIMEOUT_SECONDS, check=False
        )
    except DotError, OSError:
        return False
    owner = github_owner(result.stdout) if result.returncode == 0 else None
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
        allowed = run_parallel(
            state.runner,
            lambda repository: _allowed_origin(state, repository),
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
    selected: set[Path] = set()
    excluded: set[Path] = set()
    for target in targets:
        found, skipped_here = _target_folders(state, target)
        selected.update(found)
        excluded.update(skipped_here)
    folders = sorted(selected)
    skipped = sorted(excluded - selected)
    harnesses = installed_harnesses()
    # Projects go first: a malformed agy project file then stops the run before any trust write.
    include = state.config.trust.agy_projects
    projects = register_agy_projects(folders, include, dry_run=dry_run) if "agy" in harnesses else []
    changes = trust_folders(folders, dry_run=dry_run) if harnesses else {}
    if as_json:
        document = {
            "schema": "dot.trust/v1",
            "dry_run": dry_run,
            "harnesses": harnesses,
            "folders": [{"path": str(folder), "changed": changes.get(folder, [])} for folder in folders],
            "skipped": [str(folder) for folder in skipped],
            "agy_projects": [str(folder) for folder in projects],
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
    for folder in projects:
        verb = "would add" if dry_run else "added"
        state.stdout.write(f"+ {folder}: {verb} to agy Remote Control projects\n")
    for folder in skipped:
        # Skipped repositories sit inside a trusted workspace, which Copilot applies to descendants.
        state.stdout.write(
            f"- {folder}: skipped (origin is not a github.com repository of trust.github_owners; "
            "Copilot still inherits workspace trust)\n"
        )


def register(app: typer.Typer) -> None:
    @app.command(
        "trust",
        help=(
            "Pre-accept folder trust in Claude, agy, and Copilot, and add trusted repositories to "
            "agy Remote Control projects; 'all' covers pull.directories and their trust.github_owners repositories"
        ),
    )
    def trust(
        context: typer.Context,
        targets: Annotated[
            list[str] | None,
            typer.Argument(
                help="Folders or repositories to trust, or 'all' for the configured workspaces [default: .]",
                show_default=False,
            ),
        ] = None,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Report trust changes without writing harness files")
        ] = False,
        json_output: JsonOption = False,
    ) -> None:
        run_trust(state_from(context), targets or ["."], dry_run=dry_run, as_json=json_output)
