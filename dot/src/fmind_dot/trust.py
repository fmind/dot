"""Pre-accept coding-harness folder trust for repositories the owner works in."""

import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.repository import find_git_repositories
from fmind_dot.state import State, state_from
from fmind_dot.workstation import DryRun

# Each harness stores trust in a file it also writes itself; an edit only adds entries.
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


def _write(path: Path, text: str) -> None:
    """Replace the file atomically, keeping its permissions (new files are owner-only)."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    write_atomic_file(path, text.encode("utf-8"), mode=mode)


def _load_json(path: Path, text: str) -> dict[str, Any]:
    try:
        value = json.loads(text) if text.strip() else {}
    except ValueError as error:
        raise DotError(f"{path} is not valid JSON; repair it before trusting folders") from error
    if not isinstance(value, dict):
        raise DotError(f"{path} must contain a JSON object")
    return value


def _json_list(path: Path, key: str, folder: str, *, dry_run: bool) -> bool:
    """Append a folder to a top-level JSON array (agy trustedWorkspaces, Copilot trustedFolders)."""
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    # Copilot prefixes // comment lines that strict JSON rejects; keep them in place.
    lines = raw.splitlines(keepends=True)
    header = "".join(line for line in lines if _COPILOT_COMMENT.match(line))
    data = _load_json(path, "".join(line for line in lines if not _COPILOT_COMMENT.match(line)))
    folders = data.setdefault(key, [])
    if not isinstance(folders, list):
        raise DotError(f"{path}: {key} must be a JSON array")
    if folder in folders:
        return False
    if not dry_run:
        folders.append(folder)
        _write(path, header + json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def _claude(path: Path, folder: str, *, dry_run: bool) -> bool:
    data = _load_json(path, path.read_text(encoding="utf-8") if path.exists() else "")
    projects = data.setdefault("projects", {})
    if not isinstance(projects, dict):
        raise DotError(f"{path}: projects must be a JSON object")
    project = projects.setdefault(folder, {})
    if not isinstance(project, dict):
        raise DotError(f"{path}: project {folder} must be a JSON object")
    if project.get("hasTrustDialogAccepted") is True:
        return False
    if not dry_run:
        # Claude re-reads and merges this file under its own lock before it writes.
        project["hasTrustDialogAccepted"] = True
        _write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return True


def _toml_table(path: Path, table: str, folder: str, key: str, value: str, *, dry_run: bool) -> bool:
    """Set `[<table>."<folder>"] <key> = <value>` without reformatting the host's TOML."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    try:
        entry = tomllib.loads(text).get(table, {}).get(folder)
    except tomllib.TOMLDecodeError as error:
        raise DotError(f"{path} is not valid TOML; repair it before trusting folders") from error
    wanted = tomllib.loads(f"{key} = {value}")[key]
    if isinstance(entry, dict) and entry.get(key) == wanted:
        return False
    if dry_run:
        return True
    quoted = json.dumps(folder, ensure_ascii=False)
    header = re.compile(rf"(?m)^([ \t]*)\[{re.escape(table)}\.{re.escape(quoted)}\][ \t]*\n")
    match = header.search(text)
    if match is None:
        separator = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        text = f"{text}{separator}[{table}.{quoted}]\n{key} = {value}\n"
    else:
        # Replace the key inside this table, or insert it right after the header.
        body_start = match.end()
        next_table = re.compile(r"(?m)^[ \t]*\[").search(text, body_start)
        body_end = next_table.start() if next_table else len(text)
        body = text[body_start:body_end]
        line = re.compile(rf"(?m)^([ \t]*){re.escape(key)}[ \t]*=.*$")
        if line.search(body):
            body = line.sub(lambda found: f"{found.group(1)}{key} = {value}", body, count=1)
        else:
            body = f"{match.group(1)}{key} = {value}\n{body}"
        text = text[:body_start] + body + text[body_end:]
    tomllib.loads(text)
    _write(path, text)
    return True


def _harnesses(home: Path) -> dict[str, tuple[Path, Callable[[Path, str, bool], bool]]]:
    # Claude keeps trust in ~/.claude.json but its state directory is ~/.claude.
    return {
        "claude": (home / ".claude.json", lambda path, folder, dry: _claude(path, folder, dry_run=dry)),
        "codex": (
            home / ".codex" / "config.toml",
            lambda path, folder, dry: _toml_table(path, "projects", folder, "trust_level", '"trusted"', dry_run=dry),
        ),
        "grok": (
            home / ".grok" / "trusted_folders.toml",
            # Grok refuses to trust the home directory itself.
            lambda path, folder, dry: (
                folder != str(home) and _toml_table(path, "folders", folder, "trusted", "true", dry_run=dry)
            ),
        ),
        "agy": (
            home / ".gemini" / "antigravity-cli" / "settings.json",
            lambda path, folder, dry: _json_list(path, "trustedWorkspaces", folder, dry_run=dry),
        ),
        "copilot": (
            home / ".copilot" / "config.json",
            lambda path, folder, dry: _json_list(path, "trustedFolders", folder, dry_run=dry),
        ),
    }


def trust_folder(folder: Path, *, dry_run: bool = False, home: Path | None = None) -> list[str]:
    """Trust one folder in every installed harness; return the harnesses that changed."""
    home = home or Path.home()
    changed = []
    for name, (path, update) in _harnesses(home).items():
        # A harness that was never started has no state directory to extend.
        state_directory = home / ".claude" if name == "claude" else path.parent
        if state_directory.is_dir() and update(path, str(folder), dry_run):
            changed.append(name)
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


def run_trust(state: State, target: str = ".", *, dry_run: bool = False) -> None:
    folders, skipped = _target_folders(state, target)
    for folder in folders:
        changed = trust_folder(folder, dry_run=dry_run)
        verb = "would trust" if dry_run else "trusted"
        detail = f"{verb} in {', '.join(changed)}" if changed else "already trusted"
        state.stdout.write(f"{'✓' if not changed else '+'} {folder}: {detail}\n")
    for folder in skipped:
        state.stdout.write(f"- {folder}: skipped (origin is not a github.com repository of trust.github_owners)\n")


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
        dry_run: DryRun = False,
    ) -> None:
        run_trust(state_from(context), target, dry_run=dry_run)
