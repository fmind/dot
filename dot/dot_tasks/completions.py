"""Generate and validate Fish completion scripts for installed CLI tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from fmind_dot.command import FISH_COMPLETION
from fmind_dot.config import expand_path
from fmind_dot.errors import DotError
from fmind_dot.private_files import write_atomic_file
from fmind_dot.process import CommandResult, run_parallel, sigterm_as_keyboard_interrupt
from fmind_dot.state import State, require_tools

_COMPLETION_TIMEOUT_SECONDS = 60.0
_PROBE_CONCURRENCY = 8
COMPLETIONS_PATH = "~/.config/fish/completions"

_PLAIN_COMPLETIONS = (
    "agentsview",
    "betterleaks",
    "chezmoi",
    "copilot",
    "databricks",
    "dot",
    "genie",
    "lazygit",
    "mise",
    "trivy",
)
_COMPLETION_PACKAGES: dict[str, str] = {"lsd": "lsd", "ya": "yazi", "yazi": "yazi", "zoxide": "zoxide"}
_COMPLETION_ENV: dict[str, str] = {"hf": "_HF_COMPLETE=fish_source"}
_COMPLETION_COMMANDS: dict[str, tuple[str, ...]] = (
    {t: (t, "completions", "fish") for t in ("ast-grep", "doggo", "dprint", "starship", "typst")}
    | {t: (t, "generate-shell-completion", "fish") for t in ("ruff", "ty", "uv")}
    | {t: (t, "--generate", "complete-fish") for t in ("rg", "xh")}
    | {
        "atuin": ("atuin", "gen-completions", "--shell", "fish"),
        "bat": ("bat", "--completion", "fish"),
        "delta": ("delta", "--generate-completion", "fish"),
        "fd": ("fd", "--gen-completions", "fish"),
        "gh": ("gh", "completion", "-s", "fish"),
        "git-lfs": ("git", "lfs", "completion", "fish"),
        "openspec": ("openspec", "completion", "generate", "fish"),
        "tree-sitter": ("tree-sitter", "complete", "--shell", "fish"),
        "usage": ("usage", "--completions", "fish"),
        "uvx": ("uvx", "--generate-shell-completion", "fish"),
        "yq": ("yq", "shell-completion", "fish"),
        "zellij": ("zellij", "setup", "--generate-completion", "fish"),
    }
)
COMPLETION_TOOLS: frozenset[str] = (
    frozenset(_PLAIN_COMPLETIONS) | _COMPLETION_PACKAGES.keys() | _COMPLETION_ENV.keys() | _COMPLETION_COMMANDS.keys()
)


def _write_validated_fish(
    state: State, path: Path, content: str, mode: int, *, env: Mapping[str, str] | None = None
) -> None:
    if not content.strip():
        raise DotError(f"generated Fish script is empty: {path.name}")
    require_tools(state, [["fish"]])
    try:
        state.runner.run(
            ["fish", "--no-config", "--no-execute"], input_text=content, env=env, timeout=_COMPLETION_TIMEOUT_SECONDS
        )
    except (DotError, OSError) as error:
        raise DotError(f"generated Fish script failed syntax validation: {path.name}") from error
    try:
        write_atomic_file(path, content.encode("utf-8"), mode=mode)
    except OSError as error:
        raise DotError(f"failed to publish Fish script: {path.name}") from error


def _parse_install_paths(raw: str) -> dict[str, Path]:
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    install_paths: dict[str, Path] = {}
    for pkg, entries in parsed.items():
        if not isinstance(pkg, str) or not isinstance(entries, list):
            continue
        match = next(
            (
                ip
                for entry in entries
                if isinstance(entry, dict)
                and entry.get("active")
                and entry.get("installed")
                and isinstance(ip := entry.get("install_path"), str)
                and ip
            ),
            None,
        )
        if match is not None:
            install_paths[pkg] = Path(match)
    return install_paths


def _mise_context(state: State) -> tuple[dict[str, Path], str | None]:
    if state.runner.which("mise") is None:
        return {}, None

    def probe(cmd: list[str]) -> CommandResult | None:
        try:
            return state.runner.run(cmd, timeout=_COMPLETION_TIMEOUT_SECONDS, check=False)
        except DotError, OSError:
            return None

    ls_res, bp_res = run_parallel(
        state.runner, probe, [["mise", "ls", "--current", "--json"], ["mise", "bin-paths"]], 2
    )
    install_paths = _parse_install_paths(ls_res.stdout) if ls_res is not None and ls_res.returncode == 0 else {}
    mise_bin_path: str | None = None
    if bp_res is not None and bp_res.returncode == 0:
        dirs = [d for line in bp_res.stdout.splitlines() if (d := line.strip())]
        if dirs and all(Path(d).is_absolute() for d in dirs):
            mise_bin_path = os.pathsep.join(dirs)
    return install_paths, mise_bin_path


def _completion_available(state: State, tool: str, *, mise_bin_path: str | None = None) -> bool:
    if (executable := state.runner.which(tool)) is None:
        return False
    mise = state.runner.which("mise")
    if tool != "mise" and mise is not None and executable.resolve() == mise.resolve():
        if mise_bin_path is not None:
            return shutil.which(tool, path=mise_bin_path) is not None
        result = state.runner.run(["mise", "which", tool], timeout=_COMPLETION_TIMEOUT_SECONDS, check=False)
        if result.returncode:
            if "not currently active" in result.stderr or "No version is set" in result.stderr:
                return False
            raise DotError(f"failed to resolve mise completion executable for {tool}")
    return True


def _generate_completion(
    state: State,
    tool: str,
    workdir: Path,
    *,
    install_paths: Mapping[str, Path] | None = None,
    mise_bin_path: str | None = None,
    run_env: Mapping[str, str] | None = None,
) -> str:
    if tool == "dot":
        return FISH_COMPLETION
    if not _completion_available(state, tool, mise_bin_path=mise_bin_path):
        raise FileNotFoundError(tool)
    if package := _COMPLETION_PACKAGES.get(tool):
        if install_paths and (pkg_root := install_paths.get(package)) is not None:
            root_path = pkg_root
        else:
            require_tools(state, [["mise"]])
            root = state.runner.run(
                ["mise", "where", "--", package], timeout=_COMPLETION_TIMEOUT_SECONDS
            ).stdout.strip()
            root_path = Path(root) if root else Path()
        if not root_path.is_absolute() or not root_path.is_dir():
            raise DotError(f"mise returned an invalid completion package directory for {tool}")
        if len(matches := list(root_path.rglob(f"{tool}.fish"))) != 1:
            raise DotError(f"expected one bundled Fish completion for {tool}, found {len(matches)}")
        try:
            return matches[0].read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise DotError(f"bundled Fish completion for {tool} is not UTF-8") from error
    cmd: Sequence[str] = (
        ("env", _COMPLETION_ENV[tool], tool)
        if tool in _COMPLETION_ENV
        else _COMPLETION_COMMANDS.get(tool, (tool, "completion", "fish"))
    )
    if cmd[0] != tool and state.runner.which(cmd[0]) is None:
        raise DotError(f"completion generator for {tool} is not installed: {cmd[0]}")
    cwd = workdir / tool
    cwd.mkdir(exist_ok=True)
    try:
        result = state.runner.run(cmd, cwd=cwd, env=run_env, timeout=_COMPLETION_TIMEOUT_SECONDS)
    except (DotError, OSError) as error:
        raise DotError(f"failed to generate completions for {tool}") from error
    if not result.stdout.strip():
        raise DotError(f"failed to generate completions for {tool}: empty output")
    return result.stdout


def _prune_fish(directory: Path, pattern: str, keep: set[str] | frozenset[str], failures: list[str]) -> None:
    for path in sorted(directory.glob(pattern)):
        if path.name not in keep and not path.is_symlink() and path.is_file():
            try:
                path.unlink()
            except OSError as error:
                failures.append(f"{path.name}: {error}")


def _run_completion(state: State, directory: Path) -> list[str]:
    try:
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError("failed to create completions directory") from error
    failures: list[str] = []
    _prune_fish(directory, "*.fish", {f"{t}.fish" for t in COMPLETION_TOOLS}, failures)
    install_paths, mise_bin_path = _mise_context(state)
    run_env = (
        {"PATH": f"{mise_bin_path}{os.pathsep}{os.environ.get('PATH', '')}".rstrip(os.pathsep)}
        if mise_bin_path
        else None
    )
    print(
        f"=> Generating Fish autocompletions for {len(COMPLETION_TOOLS)} tools in {directory}...\n", file=state.stdout
    )
    with tempfile.TemporaryDirectory(prefix="dot-completion-") as temp_dir:
        workdir = Path(temp_dir)

        def complete(tool: str) -> tuple[str, str | None]:
            try:
                script = _generate_completion(
                    state,
                    tool,
                    workdir,
                    install_paths=install_paths,
                    mise_bin_path=mise_bin_path,
                    run_env=run_env,
                )
                _write_validated_fish(state, directory / f"{tool}.fish", script, 0o644, env=run_env)
                return f"  ✓ Generated completions for {tool}", None
            except FileNotFoundError:
                return f"  ○ {tool} is not installed or active, skipping", None
            except (DotError, OSError) as error:
                return f"  ✗ Failed to generate completions for {tool}", f"{tool}: {error}"

        for line, failure in run_parallel(state.runner, complete, sorted(COMPLETION_TOOLS), _PROBE_CONCURRENCY):
            print(line, file=state.stdout)
            if failure is not None:
                failures.append(failure)
    return failures


def run_completion(state: State, *, check_only: bool = False) -> None:
    if check_only:
        with tempfile.TemporaryDirectory(prefix="dot-completion-check-") as temp:
            failures = _run_completion(state, Path(temp) / "completions")
        success = "Completion check passed; installed scripts were not changed."
    else:
        directory = expand_path(COMPLETIONS_PATH)
        failures = _run_completion(state, directory)
        success = f"\n✓ Completions updated in {directory}"
    if failures:
        raise DotError("completion generation failed: " + "; ".join(failures))
    print(success, file=state.stdout)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument(
        "--check",
        dest="check_only",
        action="store_true",
        help="Validate generators in a temporary directory without installing scripts",
    )
    args = parser.parse_args(argv)
    with sigterm_as_keyboard_interrupt():
        try:
            run_completion(State(), check_only=args.check_only)
        except KeyboardInterrupt:
            return 130
        except (DotError, OSError) as error:
            sys.stderr.write(f"completions: {error}\n")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
