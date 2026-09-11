"""Native workstation commands with one Python-owned CLI and configuration."""

import shlex
from typing import Annotated, Literal

import typer

from fmind_dot.command_group import help_group
from fmind_dot.errors import DotError
from fmind_dot.state import State, require_tools, state_from

CACHE_COMMANDS = {
    "docker": ["docker", "system", "df"],
    "hf": ["hf", "cache", "ls"],
    "uv": ["uv", "cache", "size", "--preview-features", "cache-size"],
}
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
    bool, typer.Option("--force", help="Run authentication even when already ready or status is unknown")
]


def execute(state: State, args: list[str], *, dry_run: bool = False) -> None:
    """Preserve caller environment, directory, terminal, and native diagnostics."""
    if dry_run:
        print(shlex.join(args), file=state.stdout)
        return
    require_tools(state, [args])
    code = state.runner.interactive(args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr)
    if code != 0:
        raise DotError(f"{shlex.join(args[:3])} failed (exit {code}); resolve the native diagnostic and retry")


def register(app: typer.Typer) -> None:
    @app.command("cache", help="Inspect native cache usage; defaults to the configured providers")
    def cache(
        context: typer.Context,
        provider: Annotated[Literal["all", "docker", "hf", "uv"], typer.Argument()] = "all",
        dry_run: DryRun = False,
    ) -> None:
        state = state_from(context)
        names = state.config.cache.providers if provider == "all" else [provider]
        commands = [CACHE_COMMANDS[name] for name in dict.fromkeys(names)]
        if not dry_run:
            require_tools(state, commands)
        for args in commands:
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
                    typer.confirm(f"Clean caches for {', '.join(names)}?", abort=True)
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
