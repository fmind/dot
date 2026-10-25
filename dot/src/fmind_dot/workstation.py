"""Native workstation commands with one Python-owned CLI and configuration."""

import json
import os
import select
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Annotated, Any, Literal

import typer

from fmind_dot.command_group import JsonOption
from fmind_dot.config import CacheProvider, PruneProvider
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools, state_from


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


# The single registry for `dot cache` and `dot prune`; config.CacheProvider/PruneProvider name its keys.
# Cleanup never touches repositories, installed tool versions (virtualenvs link to them), models in
# use, Docker images, containers, or volumes. Machine-readable inspection: Docker emits JSON lines,
# hf a JSON array, uv a byte count.
CACHE_TOOLS = {
    # Dangling build cache by default; every unused build-cache layer with --aggressive.
    "docker": CacheTool(
        ["docker", "builder", "prune", "--force"],
        ["docker", "builder", "prune", "--all", "--force"],
        ["docker", "system", "df"],
        ["docker", "system", "df", "--format", "json"],
    ),
    # Downloaded plugins only: offline formatting (and commit hooks) fail until they download again.
    "dprint": CacheTool(None, ["dprint", "clear-cache"]),
    # Detached revisions and incomplete downloads; current model revisions are data, never cache.
    "hf": CacheTool(
        ["hf", "cache", "prune", "--yes"], None, ["hf", "cache", "ls"], ["hf", "cache", "ls", "--format", "json"]
    ),
    # Metadata and download caches; `mise prune` would uninstall versions that virtualenvs still use.
    "mise": CacheTool(["mise", "cache", "clear"]),
    # Garbage-collect unreachable entries; --aggressive empties the cache.
    "npm": CacheTool(["npm", "cache", "verify"], ["npm", "cache", "clean", "--force"]),
    # Scan results; --aggressive also drops the vulnerability databases, which the next scan downloads.
    "trivy": CacheTool(["trivy", "clean", "--scan-cache"], ["trivy", "clean", "--all"]),
    # Unused entries; --aggressive empties the cache (hardlinked virtualenvs keep their files).
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
# Typed choices give Fish completion and --help the provider names, and Typer rejects others.
CacheTarget = Literal["all", CacheProvider]
PruneTarget = Literal["all", PruneProvider]
_CACHE_TIMEOUT_SECONDS = 120
DryRun = Annotated[
    bool, typer.Option("--dry-run", help="Show possible commands without running probes or making changes")
]


def _ensure_hf_cache_dir() -> None:
    # Match huggingface_hub's precedence and expansion before the native CLI runs.
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")) / "huggingface"
    hf_home = os.path.expandvars(str(Path(os.environ.get("HF_HOME", str(cache_root))).expanduser()))
    legacy = os.environ.get("HUGGINGFACE_HUB_CACHE", str(Path(hf_home) / "hub"))
    selected = Path(os.environ.get("HF_HUB_CACHE", legacy)).expanduser()
    Path(os.path.expandvars(str(selected))).mkdir(parents=True, exist_ok=True)


def execute(
    state: State,
    args: list[str],
    *,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    """Preserve caller environment, directory, terminal, and native diagnostics."""
    if dry_run:
        print(shlex.join(args), file=state.stdout)
        return
    require_tools(state, [args])
    if args[:2] == ["hf", "cache"]:
        _ensure_hf_cache_dir()
    if args[:2] == ["uv", "cache"]:
        env = {"UV_LOCK_TIMEOUT": os.environ.get("UV_LOCK_TIMEOUT", _UV_LOCK_TIMEOUT_SECONDS)} | (env or {})
    code = state.runner.interactive(args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr, env=env)
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
        return entry | {"error": "unparseable native output"}
    return entry | {"report": report}


def run_cache(
    state: State, names: Sequence[str], *, as_json: bool = False, dry_run: bool = False, optional: bool = False
) -> None:
    """Inspect each provider, continuing past failures; `optional` skips providers that are not installed."""
    commands = {name: _inspect_command(name, as_json=as_json) for name in names}
    if dry_run:
        providers = [{"name": name, "command": shlex.join(args)} for name, args in commands.items()]
    else:
        if not optional:
            require_tools(state, list(commands.values()))
        providers = []
        for name, args in commands.items():
            entry: dict[str, Any] = {"name": name, "command": shlex.join(args)}
            if state.runner.which(args[0]) is None:
                providers.append(entry | {"skipped": f"{args[0]} not installed"})
                if not as_json:
                    print(f"[{name}] skipped: {args[0]} not installed", file=state.stdout, flush=True)
            elif as_json:
                providers.append(_cache_report(state, name, args))
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
        except KeyboardInterrupt, EOFError:
            raise typer.Abort from None
        if answer in {"y", "yes"}:
            return
        if answer in {"", "n", "no"}:
            raise typer.Abort
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
        # Providers without an aggressive step (hf, mise) run their default cleanup unasked.
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


def register(app: typer.Typer) -> None:
    @app.command(
        "cache",
        help="Show how much disk tool caches use (read-only); defaults to the configured providers",
        epilog="With all, providers that are not installed are skipped. Exit 1 when any inspection fails; "
        "the other providers still report.",
    )
    def cache(
        context: typer.Context,
        provider: Annotated[CacheTarget, typer.Argument(help="all uses cache.providers")] = "all",
        dry_run: DryRun = False,
        json_output: JsonOption = False,
    ) -> None:
        state = state_from(context)
        selected = state.config.cache.providers if provider == "all" else [provider]
        names = list(dict.fromkeys(selected))
        run_cache(state, names, as_json=json_output, dry_run=dry_run, optional=provider == "all")

    @app.command(
        "prune",
        help="Clean tool caches: stale entries by default, whole rebuildable caches with --aggressive",
        epilog=(
            "Never touches repositories, installed tool versions, current models, Docker images, containers, "
            "or volumes. all uses prune.providers (every provider but Docker by default). --aggressive asks "
            "first; without a terminal, preview with --dry-run, then pass --yes. Every provider runs; "
            "exit 1 when any fails, such as uv while a `uv run` process holds its cache."
        ),
    )
    def prune(
        context: typer.Context,
        provider: Annotated[PruneTarget, typer.Argument(help="all uses prune.providers")] = "all",
        aggressive: Annotated[
            bool, typer.Option("--aggressive", help="Empty whole caches; they download or rebuild on next use")
        ] = False,
        dry_run: DryRun = False,
        yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm --aggressive without prompting")] = False,
    ) -> None:
        state = state_from(context)
        names = list(dict.fromkeys(state.config.prune.providers if provider == "all" else [provider]))
        run_prune(state, names, aggressive=aggressive, dry_run=dry_run, yes=yes)
