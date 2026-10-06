"""Native workstation commands with one Python-owned CLI and configuration."""

import json
import os
import select
import shlex
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import IO, Annotated, Any, Literal

import typer

from fmind_dot.command_group import JsonOption, help_group
from fmind_dot.errors import CommandTimeoutError, DotError
from fmind_dot.reporting import write_json
from fmind_dot.state import State, require_tools, state_from

CACHE_COMMANDS = {
    "docker": ["docker", "system", "df"],
    "hf": ["hf", "cache", "ls"],
    "uv": ["uv", "cache", "size", "--human", "--preview-features", "cache-size"],
}
# Machine-readable variants for --json: Docker emits JSON lines, hf a JSON array, uv a byte count.
CACHE_JSON_COMMANDS = {
    "docker": ["docker", "system", "df", "--format", "json"],
    "hf": ["hf", "cache", "ls", "--format", "json"],
    "uv": ["uv", "cache", "size", "--preview-features", "cache-size"],
}
_CACHE_TIMEOUT_SECONDS = 120
PRUNE_COMMANDS = {
    "docker": ["docker", "builder", "prune", "--force"],
    "dprint": ["dprint", "clear-cache"],
    "hf": ["hf", "cache", "prune", "--yes"],
    "mise": ["mise", "cache", "clear"],
    "npm": ["npm", "cache", "verify"],
    "trivy": ["trivy", "clean", "--scan-cache"],
    "uv": ["uv", "cache", "prune"],
}
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


def run_cache_json(state: State, names: Sequence[str], *, dry_run: bool = False) -> None:
    commands = [CACHE_JSON_COMMANDS[name] for name in names]
    if dry_run:
        providers = [{"name": name, "command": shlex.join(args)} for name, args in zip(names, commands, strict=True)]
    else:
        require_tools(state, commands)
        providers = [_cache_report(state, name, args) for name, args in zip(names, commands, strict=True)]
    write_json(state.stdout, {"schema": "dot.cache/v1", "dry_run": dry_run, "providers": providers})
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
            print(f"Clean caches for {', '.join(names)}? [y/N]: ", end="", file=state.stdout, flush=True)
            _wait_for_line(state.stdin)
            answer = state.stdin.readline().strip().lower()
        except KeyboardInterrupt, EOFError:
            raise typer.Abort from None
        if answer in {"y", "yes"}:
            return
        if answer in {"", "n", "no"}:
            raise typer.Abort
        print("Error: invalid input", file=state.stdout)


def register(app: typer.Typer) -> None:
    @app.command("cache", help="Inspect native cache usage; defaults to the configured providers")
    def cache(
        context: typer.Context,
        provider: Annotated[
            Literal["all", "docker", "hf", "uv"],
            # Plain help would render the choices as "[provider]:<all|...>"; list them in the help.
            typer.Argument(help="all, docker, hf, or uv; all uses cache.providers", metavar="provider"),
        ] = "all",
        dry_run: DryRun = False,
        json_output: JsonOption = False,
    ) -> None:
        state = state_from(context)
        names = list(dict.fromkeys(state.config.cache.providers if provider == "all" else [provider]))
        if json_output:
            run_cache_json(state, names, dry_run=dry_run)
            return
        commands = [CACHE_COMMANDS[name] for name in names]
        if not dry_run:
            require_tools(state, commands)
        for name, args in zip(names, commands, strict=True):
            # Native reports such as "No results found." or a bare size do not name their provider.
            if len(commands) > 1 and not dry_run:
                print(f"[{name}]", file=state.stdout, flush=True)
            execute(state, args, dry_run=dry_run)

    prune_app = help_group("Clean tool caches after confirmation; all excludes Docker by default")
    app.add_typer(prune_app, name="prune")

    def add_prune(name: str, description: str) -> None:
        @prune_app.command(name, help=description)
        def prune(
            context: typer.Context,
            dry_run: DryRun = False,
            yes: Annotated[bool, typer.Option("--yes", "-y", help="Confirm cleanup without prompting")] = False,
        ) -> None:
            state = state_from(context)
            names = list(dict.fromkeys(state.config.prune.providers if name == "all" else [name]))
            commands = [PRUNE_COMMANDS[provider] for provider in names]
            if not dry_run:
                require_tools(state, commands)
                if not yes:
                    if not state.stdin.isatty():
                        raise DotError("cache cleanup requires confirmation; preview with --dry-run, then pass --yes")
                    _confirm_prune(state, names)
            # Native noninteractive flags follow Dot's aggregate confirmation.
            for args in commands:
                execute(state, args, dry_run=dry_run)

    for name, description in {
        "all": "Clean the configured providers (all except Docker by default)",
        "docker": "Remove unused build cache from the selected Docker builder",
        "dprint": "Clear downloaded dprint plugins and formatting cache",
        "hf": "Remove detached Hugging Face revisions and incomplete downloads",
        "mise": "Clear mise metadata and task caches, retaining installed tools",
        "npm": "Verify npm cache integrity and remove unneeded entries",
        "trivy": "Clear scan results, retaining vulnerability databases and checks",
        "uv": "Prune unused uv package entries and cached environments",
    }.items():
        add_prune(name, description)
