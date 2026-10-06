"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import json
import re
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Annotated, Any

import tomlkit
import typer
from tomlkit.exceptions import TOMLKitError

from fmind_dot.command_group import JsonOption
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.reporting import write_json
from fmind_dot.repository import find_git_repositories
from fmind_dot.state import State, state_from

# Each harness stores trust in a file it also writes itself; preserve unrelated state.
# Claude, Codex, Grok, and agy key trust on the repository root, so a trusted parent
# never covers the repositories below it; Copilot trusts every path below an entry.
_COPILOT_COMMENT = re.compile(r"^\s*//")
# github.com origins over HTTPS, ssh:// URLs, or scp-like SSH; the owner is the first path segment.
_GITHUB_ORIGIN = re.compile(
    r"^(?:https://(?:[^@/]+@)?github\.com(?::443)?/|ssh://(?:[^@/]+@)?github\.com(?::22)?/|[^@/:]+@github\.com:)"
    r"(?P<owner>[A-Za-z0-9-]+)/[^/]+?/?$",
    re.IGNORECASE,
)
_ORIGIN_TIMEOUT_SECONDS = 10


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


def _toml_table(
    path: Path, text: str, folders: list[str], table: str, key: str, value: str | bool
) -> tuple[str, list[str]]:
    """Update trust entries while preserving the host's TOML syntax and comments."""
    try:
        document = tomlkit.parse(text)
    except TOMLKitError as error:
        raise DotError(f"{path} is not valid TOML; repair it before trusting folders") from error
    tables = document.setdefault(table, tomlkit.table())
    if not isinstance(tables, MutableMapping):
        raise DotError(f"{path}: {table} must be a TOML table")
    changed = []
    for folder in folders:
        # Let the parent choose an inline or regular table for a new entry.
        entry = tables.setdefault(folder, {})
        if not isinstance(entry, MutableMapping):
            raise DotError(f"{path}: {table} entry must be a TOML table")
        current = entry.get(key)
        if current == value and (not isinstance(value, bool) or isinstance(current, bool)):
            continue
        entry[key] = value
        changed.append(folder)
    return tomlkit.dumps(document), changed


def _harnesses(home: Path) -> dict[str, tuple[Path, _Edit]]:
    # Claude keeps trust in ~/.claude.json but its state directory is ~/.claude.
    return {
        "claude": (home / ".claude.json", _claude),
        "codex": (
            home / ".codex" / "config.toml",
            lambda path, text, folders: _toml_table(path, text, folders, "projects", "trust_level", "trusted"),
        ),
        "grok": (
            home / ".grok" / "trusted_folders.toml",
            # Grok refuses to trust the home directory itself.
            lambda path, text, folders: _toml_table(
                path, text, [folder for folder in folders if folder != str(home)], "folders", "trusted", True
            ),
        ),
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
    if target != "all":
        path = expand_path(target).resolve()
        if not path.is_dir():
            raise DotError(f"{path} is not a directory")
        try:
            return find_git_repositories(state, [path]), []
        except DotError:
            return [path], []
    # Configured workspaces themselves cover their non-repository subfolders in Claude
    # and every path below them in Copilot; each repository needs its own entry.
    roots = [expand_path(directory).resolve() for directory in state.config.pull.directories]
    trusted = {root for root in roots if root.is_dir()}
    skipped = []
    for repository in find_git_repositories(state):
        if repository in trusted or _allowed_origin(state, repository):
            trusted.add(repository)
        else:
            skipped.append(repository)
    return sorted(trusted), skipped


def run_trust(state: State, target: str = ".", *, dry_run: bool = False, as_json: bool = False) -> None:
    folders, skipped = _target_folders(state, target)
    harnesses = installed_harnesses()
    changes = trust_folders(folders, dry_run=dry_run) if harnesses else {}
    if as_json:
        document = {
            "schema": "dot.trust/v1",
            "dry_run": dry_run,
            "harnesses": harnesses,
            "folders": [{"path": str(folder), "changed": changes.get(folder, [])} for folder in folders],
            "skipped": [str(folder) for folder in skipped],
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
            "Pre-accept folder trust in Claude, Codex, Grok, agy, and Copilot; "
            "'all' covers pull.directories and their trust.github_owners repositories"
        ),
    )
    def trust(
        context: typer.Context,
        target: Annotated[
            str, typer.Argument(help="Folder or repository to trust, or 'all' for the configured workspaces")
        ] = ".",
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Report trust changes without writing harness files")
        ] = False,
        json_output: JsonOption = False,
    ) -> None:
        run_trust(state_from(context), target, dry_run=dry_run, as_json=json_output)
