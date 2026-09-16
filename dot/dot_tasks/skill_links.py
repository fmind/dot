"""Preview or back up the exact skill links retired after v6.1.0."""

from __future__ import annotations

import argparse
import stat
import sys
import tempfile
from pathlib import Path

from fmind_dot.errors import DotError

# Frozen migration inventory; never infer retired ownership from arbitrary links.
RETIRED_SKILLS = (
    "a2a-python-sdk",
    "agent-mcp",
    "agent-prompt",
    "agents-cli",
    "antigravity-sdk",
    "claude",
    "cli-contracts",
    "codex",
    "conventional-commit",
    "cookiecutter",
    "copier",
    "copilot",
    "cosign",
    "cursor",
    "d2",
    "dependabot",
    "django",
    "fastapi",
    "git-add-commit-push",
    "github-agentic-workflow",
    "gitleaks",
    "google-adk",
    "gradio",
    "grok",
    "jules",
    "langchain",
    "langextract",
    "langgraph",
    "lefthook",
    "litestar",
    "locust",
    "loop-engineering",
    "marimo",
    "mcp-server",
    "mermaid",
    "modern-web",
    "new-project",
    "nicegui",
    "opencode",
    "project-health",
    "project-license",
    "pydantic",
    "python-async",
    "release",
    "ruff",
    "secure",
    "sherlock",
    "terraform",
    "test-driven-development",
    "trivy",
    "ty",
    "typer",
    "uv",
    "zensical",
    "zizmor",
)


def migration_plan(source: Path, home: Path) -> tuple[list[Path], list[str]]:
    """Select only known links still owned by this checkout; preserve replacements."""
    catalog = home / ".agents/skills"
    for directory in (home / ".agents", catalog):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise DotError(f"skill catalog must use real directories: {directory}")
    selected: list[Path] = []
    preserved: list[str] = []
    for name in RETIRED_SKILLS:
        path = catalog / name
        if (source / "dot_agents/skills" / f"symlink_{name}.tmpl").exists():
            continue
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) and path.readlink() == source / "skills" / name:
            selected.append(path)
        else:
            preserved.append(name)
    return selected, preserved


def migrate_links(source: Path, home: Path, *, apply: bool = False) -> Path | None:
    """Default to preview; explicit apply keeps recoverable links outside discovery."""
    source, home = source.resolve(), home.resolve()
    selected, preserved = migration_plan(source, home)
    for path in selected:
        sys.stdout.write(f"{'Back up' if apply else 'Would back up'}: {path.name}\n")
    for name in preserved:
        sys.stdout.write(f"Preserved another owner: {name}\n")
    if not selected:
        sys.stdout.write("No retired repository skill links need migration.\n")
        return None
    if not apply:
        sys.stdout.write(f"Preview: {len(selected)} links; rerun with --apply to create a recoverable backup.\n")
        return None
    # Keep backups on the catalog filesystem so each move is atomic, and outside
    # skills/ so no host discovers retired entrypoints through their links.
    parent = home / ".agents/retired-skill-links"
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
        raise DotError(f"backup parent must be a real directory: {parent}")
    parent.mkdir(mode=0o700, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="v6.1.0-", dir=parent))
    try:
        for path in selected:
            # Recheck ownership after preview/planning and before every move.
            current, _ = migration_plan(source, home)
            if path not in current:
                raise DotError(f"skill link changed during migration: {path.name}")
            path.rename(backup / path.name)
    except (OSError, DotError) as error:
        raise DotError(f"migration interrupted; completed moves remain recoverable at {backup}: {error}") from error
    sys.stdout.write(f"Backed up {len(selected)} links to {backup}\n")
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Back up confirmed retired links (default: preview)")
    args = parser.parse_args()
    try:
        migrate_links(Path(__file__).resolve().parents[2], Path.home(), apply=args.apply)
    except (DotError, OSError) as error:
        sys.stderr.write(f"skill migration: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
