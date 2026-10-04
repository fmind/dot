"""Count the paths each gitignore-syntax pattern matches in a Git repository.

Reads only: Git attributes every path to the highest-precedence pattern that
decides it, so a pattern with zero hits is unused or shadowed by another one.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SAMPLES = 2
TIMEOUT = 60


def git(root: Path, *args: str, stdin: bytes | None = None, empty_ok: bool = False) -> bytes:
    result = subprocess.run(  # noqa: S603 - fixed git executable; paths travel on stdin
        ["git", "-C", str(root), *args],  # noqa: S607 - git resolves from PATH like every repository task
        input=stdin,
        capture_output=True,
        timeout=TIMEOUT,
        check=False,
    )
    # check-ignore (no match) and config --get (unset) exit 1 with a valid, empty answer.
    if result.returncode and not (empty_ok and result.returncode == 1):
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {args[0]} failed (exit {result.returncode}): {detail}")
    return result.stdout


def split(output: bytes) -> list[str]:
    return [item.decode("utf-8", "surrogateescape") for item in output.split(b"\0") if item]


def candidate_paths(root: Path) -> tuple[list[str], set[str]]:
    """Tracked and untracked files plus ignored entries, collapsing ignored directories."""
    tracked = split(git(root, "ls-files", "-z", "--cached"))
    untracked = split(git(root, "ls-files", "-z", "--others", "--exclude-standard"))
    ignored = split(git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"))
    return sorted({*tracked, *untracked, *ignored}), set(tracked)


def global_excludes(root: Path) -> Path | None:
    configured = git(root, "config", "--path", "--get", "core.excludesFile", empty_ok=True).decode().strip()
    if configured:
        return Path(configured).expanduser()
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "git/ignore"


def patterns(path: Path) -> list[tuple[int, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        (number, line.rstrip())
        for number, line in enumerate(lines, 1)
        if line.strip() and not line.lstrip().startswith("#")
    ]


def attribute(root: Path, paths: list[str], extra: Path | None) -> dict[tuple[str, int], list[str]]:
    """Map (source, line) to the paths whose ignore decision that pattern owns."""
    config = ["-c", f"core.excludesFile={extra}"] if extra else []
    stdin = b"\0".join(item.encode("utf-8", "surrogateescape") for item in paths)
    fields = split(
        git(root, *config, "check-ignore", "--no-index", "--verbose", "--stdin", "-z", stdin=stdin, empty_ok=True)
    )
    hits: dict[tuple[str, int], list[str]] = defaultdict(list)
    for source, line, _pattern, path in zip(*(iter(fields),) * 4, strict=True):
        if source and line:
            hits[str((root / source).resolve()) if not Path(source).is_absolute() else source, int(line)].append(path)
    return hits


def audit(root: Path, files: list[Path]) -> dict[str, Any]:
    root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip())
    paths, tracked = candidate_paths(root)
    global_file = global_excludes(root)
    global_patterns = (
        {line.strip() for _, line in patterns(global_file)} if global_file and global_file.is_file() else set()
    )
    # --exclude-standard skips tool-written .gitignore files inside ignored caches and environments.
    listed = split(git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.gitignore"))
    targets = [path.resolve() for path in files] or [(root / item).resolve() for item in listed]
    reports = []
    for target in targets:
        # Other files such as .ignore are audited as the excludes file, so a
        # .gitignore pattern that already decides a path shadows them. That
        # emulation has two limits: excludes patterns anchor to the repository
        # root, and a negation cannot override .gitignore as it does in search.
        gitignore = target.name == ".gitignore"
        hits = attribute(root, paths, None if gitignore else target)
        warnings = []
        if not gitignore and target.is_relative_to(root) and target.parent != root:
            warnings.append(
                f"nested {target.name}: anchored patterns resolve against the repository root, "
                f"not {target.parent.relative_to(root)}/; verify them with rg or fd"
            )
        seen: dict[str, int] = {}
        entries = []
        for number, pattern in patterns(target):
            matched = hits.get((str(target), number), [])
            notes = []
            if pattern.strip() in seen:
                notes.append(f"duplicate of line {seen[pattern.strip()]}")
            if gitignore and pattern.strip() in global_patterns:
                notes.append("also in global excludes")
            # Never report an unmatched search negation as prunable: it may re-include gitignored paths.
            unmeasured = not gitignore and pattern.lstrip().startswith("!")
            if unmeasured:
                notes.append("negation: re-includes for search; not measurable here")
            seen.setdefault(pattern.strip(), number)
            entries.append(
                {
                    "line": number,
                    "pattern": pattern,
                    "status": "used" if matched else "n/a" if unmeasured else "unused",
                    "notes": notes,
                    "matches": len(matched),
                    "tracked": sum(item in tracked for item in matched),
                    "samples": matched[:SAMPLES],
                }
            )
        name = str(target.relative_to(root)) if target.is_relative_to(root) else str(target)
        reports.append({"file": name, "warnings": warnings, "patterns": entries})
    return {"root": str(root), "global_excludes": str(global_file) if global_file else None, "files": reports}


def render(report: dict[str, Any]) -> str:
    lines = [f"root: {report['root']} · global excludes: {report['global_excludes']}"]
    for item in report["files"]:
        lines.append(f"\n{item['file']}")
        lines.extend(f"  warning: {warning}" for warning in item["warnings"])
        for entry in item["patterns"]:
            count = f"{entry['matches']} ({entry['tracked']} tracked)" if entry["tracked"] else str(entry["matches"])
            notes = f" [{'; '.join(entry['notes'])}]" if entry["notes"] else ""
            sample = f" e.g. {', '.join(entry['samples'])}" if entry["samples"] else ""
            lines.append(f"  {entry['line']:>4} {entry['status']:<6} {count:>14}  {entry['pattern']}{notes}{sample}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path, help="ignore files to audit (default: every .gitignore)")
    parser.add_argument("--root", type=Path, default=Path(), help="any path inside the repository")
    parser.add_argument("--json", action="store_true", help="emit structured JSON")
    args = parser.parse_args(argv)
    try:
        report = audit(args.root, args.files)
    except (RuntimeError, OSError, UnicodeDecodeError, subprocess.TimeoutExpired) as error:
        sys.stderr.write(f"Ignore audit error: {error}\n")
        return 1
    sys.stdout.write((json.dumps(report, indent=2) if args.json else render(report)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
