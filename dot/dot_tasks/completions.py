"""Generate and validate Fish completion scripts for installed CLI tools."""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from fmind_dot.command import FISH_COMPLETION
from fmind_dot.config import expand_path, policy, xdg_dir
from fmind_dot.errors import DotError
from fmind_dot.private_files import private_directory, write_atomic_file
from fmind_dot.process import run_parallel
from fmind_dot.state import State, require_tools

_COMPLETION_TIMEOUT_SECONDS = 60.0
_PROBE_CONCURRENCY = 8
COMPLETIONS_PATH = "~/.config/fish/completions"

_comp = policy()["completions"]
_COMPLETION_PACKAGES: dict[str, str] = dict(_comp["packages"])
_COMPLETION_ENV: dict[str, str] = dict(_comp["env"])
_cmds = _comp["commands"]
_COMPLETION_COMMANDS: dict[str, tuple[str, ...]] = (
    {t: (t, "completions", "fish") for t in _cmds["completions_fish"]}
    | {t: (t, "generate-shell-completion", "fish") for t in _cmds["generate_shell_completion_fish"]}
    | {t: (t, "--generate", "complete-fish") for t in _cmds["generate_complete_fish"]}
    | {k: tuple(v) for k, v in _cmds["custom"].items()}
)
COMPLETION_TOOLS: frozenset[str] = (
    frozenset(_comp["plain"]) | _COMPLETION_PACKAGES.keys() | _COMPLETION_ENV.keys() | _COMPLETION_COMMANDS.keys()
)
MANAGED_COMPLETIONS: frozenset[str] = frozenset({"agy.fish"})


def _write_validated_fish(state: State, path: Path, content: str, mode: int) -> None:
    if not content.strip():
        raise DotError(f"generated Fish script is empty: {path.name}")
    require_tools(state, [["fish"]])
    try:
        state.runner.run(
            ["fish", "--no-config", "--no-execute"], input_text=content, timeout=_COMPLETION_TIMEOUT_SECONDS
        )
    except (DotError, OSError) as error:
        raise DotError(f"generated Fish script failed syntax validation: {path.name}") from error
    try:
        write_atomic_file(path, content.encode("utf-8"), mode=mode)
    except OSError as error:
        raise DotError(f"failed to publish Fish script: {path.name}") from error


def _completion_available(state: State, tool: str) -> bool:
    if (executable := state.runner.which(tool)) is None:
        return False
    mise = state.runner.which("mise")
    if tool != "mise" and mise is not None and executable.resolve() == mise.resolve():
        result = state.runner.run(["mise", "which", tool], timeout=_COMPLETION_TIMEOUT_SECONDS, check=False)
        if result.returncode:
            if "not currently active" in result.stderr or "No version is set" in result.stderr:
                return False
            raise DotError(f"failed to resolve mise completion executable for {tool}")
    return True


def _generate_completion(state: State, tool: str, workdir: Path) -> str:
    if tool == "dot":
        return FISH_COMPLETION
    if not _completion_available(state, tool):
        raise FileNotFoundError(tool)
    if package := _COMPLETION_PACKAGES.get(tool):
        require_tools(state, [["mise"]])
        root = state.runner.run(["mise", "where", "--", package], timeout=_COMPLETION_TIMEOUT_SECONDS).stdout.strip()
        if not root or not Path(root).is_absolute() or not Path(root).is_dir():
            raise DotError(f"mise returned an invalid completion package directory for {tool}")
        if len(matches := list(Path(root).rglob(f"{tool}.fish"))) != 1:
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
        result = state.runner.run(cmd, cwd=cwd, timeout=_COMPLETION_TIMEOUT_SECONDS)
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


def _run_completion(state: State, directory: Path, cache: Path) -> list[str]:
    try:
        directory.mkdir(mode=0o755, parents=True, exist_ok=True)
    except OSError as error:
        raise DotError("failed to create completions directory") from error
    failures: list[str] = []
    _prune_fish(directory, "*.fish", {f"{t}.fish" for t in COMPLETION_TOOLS}.union(MANAGED_COMPLETIONS), failures)
    print(
        f"=> Generating Fish autocompletions for {len(COMPLETION_TOOLS)} tools in {directory}...\n", file=state.stdout
    )
    with tempfile.TemporaryDirectory(prefix="dot-completion-") as temp_dir:
        workdir = Path(temp_dir)

        def complete(tool: str) -> tuple[str, str | None]:
            try:
                _write_validated_fish(
                    state, directory / f"{tool}.fish", _generate_completion(state, tool, workdir), 0o644
                )
                return f"  ✓ Generated completions for {tool}", None
            except FileNotFoundError:
                return f"  ○ {tool} is not installed or active, skipping", None
            except (DotError, OSError) as error:
                return f"  ✗ Failed to generate completions for {tool}", f"{tool}: {error}"

        for line, failure in run_parallel(state.runner, complete, sorted(COMPLETION_TOOLS), _PROBE_CONCURRENCY):
            print(line, file=state.stdout)
            if failure is not None:
                failures.append(failure)
    try:
        private_directory(cache)
    except OSError:
        failures.append("fish cache directory: failed to create")
        print("  ✗ Failed to create fish cache directory", file=state.stdout)
        return failures
    _prune_fish(cache, "*-init.fish", {"atuin-init.fish"}, failures)
    try:
        if _completion_available(state, "atuin"):
            out = state.runner.run(
                ["atuin", "init", "fish", "--disable-ai"], timeout=_COMPLETION_TIMEOUT_SECONDS
            ).stdout
            _write_validated_fish(state, cache / "atuin-init.fish", out, 0o600)
            print("  ✓ Generated atuin-init.fish", file=state.stdout)
    except (DotError, OSError) as error:
        failures.append(f"atuin-init.fish: {error}")
        print("  ✗ Failed to generate atuin-init.fish", file=state.stdout)
    return failures


def run_completion(state: State, *, check_only: bool = False) -> None:
    if check_only:
        with tempfile.TemporaryDirectory(prefix="dot-completion-check-") as temp:
            failures = _run_completion(state, Path(temp) / "completions", Path(temp) / "cache")
        success = "Completion check passed; installed scripts were not changed."
    else:
        directory = expand_path(COMPLETIONS_PATH)
        failures = _run_completion(state, directory, xdg_dir("XDG_CACHE_HOME", ".cache") / "fish")
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
