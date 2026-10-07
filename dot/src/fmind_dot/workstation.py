"""Native workstation commands with one Python-owned CLI and configuration."""

import json
import os
import select
import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Annotated, Any, get_args

import typer

from fmind_dot.command_group import JsonOption, help_group
from fmind_dot.config import CacheProvider, PruneProvider
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools, state_from


@dataclass(frozen=True)
class CacheTool:
    """One provider's native cache commands; `inspect_json` is the machine-readable variant."""

    prune: list[str]
    prune_help: str
    inspect: list[str] | None = None
    inspect_json: list[str] | None = None


# The single registry for `dot cache` and `dot prune`; config.CacheProvider/PruneProvider name its keys.
# Machine-readable variants: Docker emits JSON lines, hf a JSON array, uv a byte count.
CACHE_TOOLS = {
    "docker": CacheTool(
        ["docker", "builder", "prune", "--force"],
        "Remove unused build cache from the selected Docker builder",
        ["docker", "system", "df"],
        ["docker", "system", "df", "--format", "json"],
    ),
    "dprint": CacheTool(["dprint", "clear-cache"], "Clear downloaded dprint plugins and formatting cache"),
    "hf": CacheTool(
        ["hf", "cache", "prune", "--yes"],
        "Remove detached Hugging Face revisions and incomplete downloads",
        ["hf", "cache", "ls"],
        ["hf", "cache", "ls", "--format", "json"],
    ),
    "mise": CacheTool(["mise", "cache", "clear"], "Clear mise metadata and task caches, retaining installed tools"),
    "npm": CacheTool(["npm", "cache", "verify"], "Verify npm cache integrity and remove unneeded entries"),
    "trivy": CacheTool(
        ["trivy", "clean", "--scan-cache"], "Clear scan results, retaining vulnerability databases and checks"
    ),
    "uv": CacheTool(
        ["uv", "cache", "prune"],
        "Prune unused uv package entries and cached environments",
        ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
        ["uv", "cache", "size", "--preview-features", "cache-size"],
    ),
}
_CACHE_PROVIDERS: tuple[str, ...] = get_args(CacheProvider)
_PRUNE_PROVIDERS: tuple[str, ...] = get_args(PruneProvider)
_CACHE_TIMEOUT_SECONDS = 120
DryRun = Annotated[
    bool, typer.Option("--dry-run", help="Show possible commands without running probes or making changes")
]
ForceLogin = Annotated[
    bool, typer.Option("--force", "-f", help="Run authentication even when already ready or status is unknown")
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
    on_stderr_line: Callable[[str], None] | None = None,
) -> None:
    """Preserve caller environment, directory, terminal, and native diagnostics."""
    if dry_run:
        print(shlex.join(args), file=state.stdout)
        return
    require_tools(state, [args])
    if args[:2] == ["hf", "cache"]:
        _ensure_hf_cache_dir()
    code = state.runner.interactive(
        args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr, env=env, on_stderr_line=on_stderr_line
    )
    if code != 0:
        raise DotError(f"{shlex.join(args[:3])} failed (exit {code}); resolve the native diagnostic and retry")


def _inspect_command(name: str, *, as_json: bool) -> list[str]:
    tool = CACHE_TOOLS[name]
    args = tool.inspect_json if as_json else tool.inspect
    if args is None:
        raise DotError(f"{name} has no cache inspection command")
    return args


def _cache_report(state: State, name: str, args: list[str]) -> dict[str, Any]:
    """Capture one provider's native report; stderr stays out because it can carry provider payloads."""
    if name == "hf":
        _ensure_hf_cache_dir()
    entry: dict[str, Any] = {"name": name, "command": shlex.join(args)}
    try:
        result = state.runner.run(args, timeout=_CACHE_TIMEOUT_SECONDS, check=False)
    except CommandTimeoutError:
        # One slow provider must not discard the other providers' reports.
        return entry | {"error": f"timed out after {_CACHE_TIMEOUT_SECONDS}s; run {shlex.join(args)} directly"}
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
            print(f"Clean caches for {', '.join(names)}? [y/N]: ", end="", file=state.stderr, flush=True)
            _wait_for_line(state.stdin)
            answer = state.stdin.readline().strip().lower()
        except KeyboardInterrupt, EOFError:
            raise typer.Abort from None
        if answer in {"y", "yes"}:
            return
        if answer in {"", "n", "no"}:
            raise typer.Abort
        print("Error: invalid input", file=state.stderr)


def register(app: typer.Typer) -> None:
    cache_choices = ", ".join(_CACHE_PROVIDERS)

    @app.command(
        "cache",
        help="Inspect native cache usage; defaults to the configured providers",
        epilog="With all, providers that are not installed are skipped. Exit 1 when any inspection fails; "
        "the other providers still report.",
    )
    def cache(
        context: typer.Context,
        provider: Annotated[
            str, typer.Argument(help=f"all, {cache_choices}; all uses cache.providers", metavar="provider")
        ] = "all",
        dry_run: DryRun = False,
        json_output: JsonOption = False,
    ) -> None:
        if provider != "all" and provider not in _CACHE_PROVIDERS:
            raise typer.BadParameter(f"choose all, {cache_choices}", param_hint="provider")
        state = state_from(context)
        selected = state.config.cache.providers if provider == "all" else [provider]
        names = list(dict.fromkeys(selected))
        run_cache(state, names, as_json=json_output, dry_run=dry_run, optional=provider == "all")

    prune_app = help_group("Clean tool caches after confirmation; all excludes Docker by default")
    app.add_typer(prune_app, name="prune")

    def add_prune(name: str, description: str) -> None:
        @prune_app.command(
            name,
            help=description,
            epilog="Without a terminal, preview with --dry-run, then pass --yes. Stops at the first native failure.",
        )
        def prune(
            context: typer.Context,
            dry_run: DryRun = False,
            yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm cleanup without prompting")] = False,
        ) -> None:
            state = state_from(context)
            names = list(dict.fromkeys(state.config.prune.providers if name == "all" else [name]))
            commands = [CACHE_TOOLS[provider].prune for provider in names]
            if not dry_run:
                require_tools(state, commands)
                if not yes:
                    if not state.stdin.isatty():
                        raise DotError("cache cleanup requires confirmation; preview with --dry-run, then pass --yes")
                    _confirm_prune(state, names)
            # Native noninteractive flags follow Dot's aggregate confirmation.
            for args in commands:
                execute(state, args, dry_run=dry_run)

    add_prune("all", "Clean the configured providers (all except Docker by default)")
    for name in _PRUNE_PROVIDERS:
        add_prune(name, CACHE_TOOLS[name].prune_help)
