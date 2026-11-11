"""Native workstation commands with one Python-owned CLI and configuration."""

import argparse
import json
import os
import select
import shlex
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, get_args

from fmind_dot.command import Parser, add_json
from fmind_dot.config import CacheProvider, PruneProvider, env_path, xdg_dir
from fmind_dot.errors import CancelledError, CommandTimeoutError, DotError
from fmind_dot.process import run_parallel
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools


@dataclass(frozen=True)
class CacheTool:
    """One provider's native cache commands; `inspect_json` is the machine-readable variant.

    `prune` removes only stale or unused entries (None: nothing is safe without --aggressive);
    `aggressive` empties the whole rebuildable cache (None: reuse `prune`, since anything deeper is data).
    """

    prune: list[str] | None
    aggressive: list[str] | None = None
    inspect: list[str] | None = None
    inspect_json: list[str] | None = None

    def cleanup(self, *, aggressive: bool) -> list[str] | None:
        return (self.aggressive or self.prune) if aggressive else self.prune


# Single registry for `dot cache` and `dot prune` (keys match CacheProvider / PruneProvider).
# Cleanup never touches repos, active tool installs, models in use, or Docker images/containers/volumes.
CACHE_TOOLS = {
    "docker": CacheTool(
        ["docker", "builder", "prune", "--force"],
        ["docker", "builder", "prune", "--all", "--force"],
        ["docker", "system", "df"],
        ["docker", "system", "df", "--format", "json"],
    ),
    "dprint": CacheTool(None, ["dprint", "clear-cache"]),
    "hf": CacheTool(
        ["hf", "cache", "prune", "--yes"], None, ["hf", "cache", "ls"], ["hf", "cache", "ls", "--format", "json"]
    ),
    # `mise prune` would uninstall tool versions that virtualenvs still link to.
    "mise": CacheTool(["mise", "cache", "prune"], ["mise", "cache", "clear"]),
    "npm": CacheTool(["npm", "cache", "verify"], ["npm", "cache", "clean", "--force"]),
    "trivy": CacheTool(["trivy", "clean", "--scan-cache"], ["trivy", "clean", "--all"]),
    "uv": CacheTool(
        ["uv", "cache", "prune"],
        ["uv", "cache", "clean"],
        ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
        ["uv", "cache", "size", "--preview-features", "cache-size"],
    ),
}
# Long-running `uv run` processes (services, agent loops) hold the cache lock: fail fast instead of
# waiting, and never pass --force, which would delete files those processes are using.
_UV_LOCK_TIMEOUT_SECONDS = "10"
# Typed choices give Fish completion and --help the provider names, and the parser rejects others.
_CACHE_TARGETS = ("all", *get_args(CacheProvider))
_PRUNE_TARGETS = ("all", *get_args(PruneProvider))
_CACHE_TIMEOUT_SECONDS = 120
# A stopped engine answers at once; a hung one must not stall every other provider.
_ENGINE_PROBE_TIMEOUT_SECONDS = 15
CACHE_WORKERS = len(CACHE_TOOLS)


def add_dry_run(parser: Parser) -> None:
    parser.add_argument(
        "--dry-run", action="store_true", help="Show possible commands without running probes or making changes"
    )


def _ensure_hf_cache_dir() -> None:
    # Match huggingface_hub's precedence and expansion before the native CLI runs.
    hf_home = env_path("HF_HOME", xdg_dir("XDG_CACHE_HOME", ".cache") / "huggingface")
    legacy = env_path("HUGGINGFACE_HUB_CACHE", hf_home / "hub")
    env_path("HF_HUB_CACHE", legacy).mkdir(parents=True, exist_ok=True)


def _mise_tracked_configs_dir() -> Path:
    return xdg_dir("MISE_STATE_DIR", xdg_dir("XDG_STATE_HOME", ".local/state") / "mise") / "tracked-configs"


def _prune_mise_tracked_configs() -> None:
    # Scratch checkouts (/tmp, /var/tmp) and deleted directories leave tracked-config symlinks
    # that keep obsolete tool versions from appearing in `mise prune`.
    tracked_dir = _mise_tracked_configs_dir()
    if not tracked_dir.is_dir():
        return
    home = Path.home()
    resolved_home = home.resolve()
    temp_dir = Path(tempfile.gettempdir())
    temp_roots = (
        Path("/tmp"),  # noqa: S108
        Path("/var/tmp"),  # noqa: S108
        Path("/private/tmp"),
        Path("/private/var/tmp"),
        temp_dir,
        temp_dir.resolve(),
    )
    for entry in tracked_dir.iterdir():
        if not entry.is_symlink():
            continue
        try:
            exists = entry.exists()
            raw = entry.readlink()
            resolved = entry.resolve()
        except OSError:
            exists = False
        if not exists:
            entry.unlink(missing_ok=True)
            continue
        target = raw if raw.is_absolute() else tracked_dir / raw
        if target.is_relative_to(home) or resolved.is_relative_to(resolved_home):
            continue
        if any(path.is_relative_to(root) for path in (target, resolved) for root in temp_roots):
            entry.unlink(missing_ok=True)


def execute(
    state: State,
    args: list[str],
    *,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    on_stderr_line: Callable[[str], None] | None = None,
) -> None:
    """Preserve caller environment, directory, terminal, and native diagnostics."""
    if dry_run:
        print(shlex.join(args), file=state.stdout)
        return
    require_tools(state, [args])
    if args[:2] == ["hf", "cache"]:
        _ensure_hf_cache_dir()
    if args[:2] == ["mise", "cache"]:
        _prune_mise_tracked_configs()
    if args[:2] == ["uv", "cache"]:
        env = {"UV_LOCK_TIMEOUT": os.environ.get("UV_LOCK_TIMEOUT", _UV_LOCK_TIMEOUT_SECONDS)} | (env or {})
    code = state.runner.interactive(
        args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr, env=env, on_stderr_line=on_stderr_line
    )
    if code != 0:
        if args[:2] == ["uv", "cache"]:
            raise DotError(
                f"{shlex.join(args[:3])} failed (exit {code}); if a running `uv run` process holds the cache "
                "(a service or agent loop), stop it and retry"
            )
        raise DotError(f"{shlex.join(args[:3])} failed (exit {code}); resolve the native diagnostic and retry")


def _inspect_command(name: str, *, as_json: bool) -> list[str]:
    tool = CACHE_TOOLS[name]
    args = tool.inspect_json if as_json else tool.inspect
    if args is None:
        raise DotError(f"{name} has no cache inspection command")
    return args


def _cache_report(state: State, name: str, args: list[str]) -> dict[str, Any]:
    """Capture one provider's native report; stderr stays out because it can carry provider payloads."""
    entry: dict[str, Any] = {"name": name, "command": shlex.join(args)}
    try:
        if name == "hf":
            _ensure_hf_cache_dir()
        result = state.runner.run(args, timeout=_CACHE_TIMEOUT_SECONDS, check=False)
    except CommandTimeoutError:
        # One slow provider must not discard the other providers' reports.
        return entry | {"error": f"timed out after {_CACHE_TIMEOUT_SECONDS}s; run {shlex.join(args)} directly"}
    except OSError:
        return entry | {"error": f"could not start cache inspection; run {shlex.join(args)} for the native diagnostic"}
    if result.returncode != 0:
        return entry | {"error": f"exit {result.returncode}; run {shlex.join(args)} for the native diagnostic"}
    try:
        if name == "docker":
            report: Any = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        elif name == "uv":
            report = {"bytes": int(result.stdout.strip())}
        else:
            report = json.loads(result.stdout)
    except ValueError:
        return entry | {"error": "unparsable native output"}
    return entry | {"report": report}


def _docker_engine_running(state: State) -> bool:
    """Probe the engine like `dot doctor`; a probe that cannot run leaves the diagnostic to the inspection."""
    try:
        probe = state.runner.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"], timeout=_ENGINE_PROBE_TIMEOUT_SECONDS, check=False
        )
    except CommandTimeoutError, OSError:
        return True
    return probe.returncode == 0


def _skip_reasons(state: State, commands: dict[str, list[str]], *, optional: bool) -> dict[str, str]:
    """Name the providers to skip: missing tools, and under `optional` a stopped Docker engine (as doctor warns)."""
    reasons: dict[str, str] = {}
    for name, args in commands.items():
        if state.runner.which(args[0]) is None:
            reasons[name] = f"{args[0]} not installed"
        elif optional and name == "docker" and not _docker_engine_running(state):
            reasons[name] = "docker engine not running"
    return reasons


def run_cache(
    state: State, names: Sequence[str], *, as_json: bool = False, dry_run: bool = False, optional: bool = False
) -> None:
    """Inspect each provider, continuing past failures; `optional` skips missing tools and a stopped engine."""
    commands = {name: _inspect_command(name, as_json=as_json) for name in names}
    if dry_run:
        providers = [{"name": name, "command": shlex.join(args)} for name, args in commands.items()]
    else:
        if not optional:
            require_tools(state, list(commands.values()))
        # Probe sequentially before the parallel inspections so each provider runs at most once.
        skipped = _skip_reasons(state, commands, optional=optional)
        if as_json:

            def inspect(item: tuple[str, list[str]]) -> dict[str, Any]:
                name, args = item
                if name in skipped:
                    return {"name": name, "command": shlex.join(args), "skipped": skipped[name]}
                return _cache_report(state, name, args)

            providers = run_parallel(state.runner, inspect, list(commands.items()), CACHE_WORKERS)
        else:
            providers = []
            for name, args in commands.items():
                entry: dict[str, Any] = {"name": name, "command": shlex.join(args)}
                if name in skipped:
                    providers.append(entry | {"skipped": skipped[name]})
                    print(f"[{name}] skipped: {skipped[name]}", file=state.stdout, flush=True)
                else:
                    # Native human reports keep their tables and units; they rarely name their provider.
                    if len(commands) > 1:
                        print(f"[{name}]", file=state.stdout, flush=True)
                    try:
                        execute(state, args)
                    except OSError:
                        message = f"could not start cache inspection; run {shlex.join(args)} for the native diagnostic"
                        providers.append(entry | {"error": message})
                        print(f"✗ {message}", file=state.stderr, flush=True)
                        continue
                    except DotError as error:
                        providers.append(entry | {"error": str(error)})
                        print(f"✗ {error}", file=state.stderr, flush=True)
                        continue
                    providers.append(entry)
    if as_json:
        write_json(state.stdout, {"schema": "dot.cache/v1", "dry_run": dry_run, "providers": providers})
    elif dry_run:
        for entry in providers:
            print(entry["command"], file=state.stdout)
    if failed := [entry["name"] for entry in providers if "error" in entry]:
        raise DotError(f"cache inspection failed for {', '.join(failed)}")


def _wait_for_line(stream: IO[str]) -> None:
    # A SIGINT that lands after Python's last signal check but before read() blocks
    # never interrupts that read, and the terminal discards the typed ^C. Polling
    # with a timeout returns to Python often enough to raise KeyboardInterrupt.
    # Canonical terminals return one line per read(), so no answer waits in the buffer.
    try:
        descriptor = stream.fileno()
    except OSError, ValueError:
        return
    while not select.select([descriptor], [], [], 0.1)[0]:
        pass


def _confirm_prune(state: State, names: list[str]) -> None:
    while True:
        try:
            # Prompts go to stderr so stdout stays the command's report.
            question = f"Empty the whole caches for {', '.join(names)} (they rebuild on next use)? [y/N]: "
            print(question, end="", file=state.stderr, flush=True)
            _wait_for_line(state.stdin)
            answer = state.stdin.readline().strip().lower()
        except EOFError:
            raise CancelledError from None
        if answer in {"y", "yes"}:
            return
        if answer in {"", "n", "no"}:
            raise CancelledError
        print("Error: invalid input", file=state.stderr)


def run_prune(
    state: State, names: Sequence[str], *, aggressive: bool = False, dry_run: bool = False, yes: bool = False
) -> None:
    """Clean each provider, continuing past failures so one busy cache never blocks the others."""
    plan = {name: CACHE_TOOLS[name].cleanup(aggressive=aggressive) for name in names}
    commands = {name: args for name, args in plan.items() if args is not None}
    if not dry_run:
        require_tools(state, list(commands.values()))
        # The default tier only drops stale entries, so it runs unattended; emptying caches asks first.
        # Providers without an aggressive step (hf) run their default cleanup unasked.
        emptied = [name for name in commands if CACHE_TOOLS[name].aggressive] if aggressive else []
        if emptied and not yes:
            if not state.stdin.isatty():
                raise DotError("aggressive cleanup requires confirmation; preview with --dry-run, then pass --yes")
            _confirm_prune(state, emptied)
    for name, args in plan.items():
        if args is None:
            print(f"[{name}] skipped: only --aggressive clears it", file=state.stdout, flush=True)
    failed = []
    for name, args in commands.items():
        if len(commands) > 1 and not dry_run:
            print(f"[{name}]", file=state.stdout, flush=True)
        try:
            execute(state, args, dry_run=dry_run)
        except (DotError, OSError) as error:
            failed.append(name)
            print(f"✗ {error}", file=state.stderr, flush=True)
    if failed:
        raise DotError(f"cache cleanup failed for {', '.join(failed)}; the other providers were cleaned")


def _cache(state: State, args: argparse.Namespace) -> None:
    selected = state.config.cache.providers if args.provider == "all" else [args.provider]
    names = list(dict.fromkeys(selected))
    run_cache(state, names, as_json=args.as_json, dry_run=args.dry_run, optional=args.provider == "all")


def _prune(state: State, args: argparse.Namespace) -> None:
    names = list(dict.fromkeys(state.config.prune.providers if args.provider == "all" else [args.provider]))
    run_prune(state, names, aggressive=args.aggressive, dry_run=args.dry_run, yes=args.yes)


def register_cache(commands: Parser) -> None:
    cache = commands.command(
        "cache",
        "Show how much disk tool caches use (read-only); defaults to the configured providers",
        _cache,
        epilog="With all, providers that are not installed and a stopped Docker engine are skipped. "
        "Exit 1 when any inspection fails; "
        "the other providers still report.",
    )
    cache.add_argument("provider", nargs="?", choices=_CACHE_TARGETS, default="all", help="all uses cache.providers")
    add_dry_run(cache)
    add_json(cache)


def register_prune(commands: Parser) -> None:
    prune = commands.command(
        "prune",
        "Clean tool caches: stale entries by default, whole rebuildable caches with --aggressive",
        _prune,
        epilog=(
            "Never touches repositories, installed tool versions, current models, Docker images, containers, "
            "or volumes. all uses prune.providers (every provider but Docker by default). --aggressive asks "
            "first; without a terminal, preview with --dry-run, then pass --yes. Every provider runs; "
            "exit 1 when any fails, such as uv while a `uv run` process holds its cache."
        ),
    )
    prune.add_argument("provider", nargs="?", choices=_PRUNE_TARGETS, default="all", help="all uses prune.providers")
    prune.add_argument(
        "--aggressive", action="store_true", help="Empty whole caches; they download or rebuild on next use"
    )
    add_dry_run(prune)
    prune.add_argument("-y", "--yes", action="store_true", help="Confirm --aggressive without prompting")
