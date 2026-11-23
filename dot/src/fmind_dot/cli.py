"""Command tree and entry point for dot."""

from __future__ import annotations

import argparse
import importlib
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fmind_dot.command import COMPLETE_VARIABLE, Handler, Parser, add_json, add_quiet, candidates
from fmind_dot.errors import DotError, UsageError, flush_stdout_on_error, suppress_broken_pipe_stdout

if TYPE_CHECKING:
    from fmind_dot.state import State

_EPILOG = (
    "Exit codes: 0 success; 1 failure or unhealthy result; 2 usage error; 130 interrupted. "
    "Reports go to stdout; prompts and errors go to stderr.\n\n"
    "Reports accept --json (-j) and print one JSON document with a versioned schema field. "
    "login accepts --dry-run and --check. Run dot COMMAND --help for examples."
)
_LOGIN_EPILOG = (
    "Exit 0 when ready; 1 with --check when a login is needed or the state is unknown, or on failure; 2 on conflicting flags.\n\n"
    "Examples: dot login --check · dot login gcp --dry-run · dot login workspace --grant analytics.readonly"
)


class _VersionAction(argparse.Action):
    """Resolve package metadata only when -V/--version is requested."""

    def __init__(self, option_strings: Sequence[str], dest: str = argparse.SUPPRESS, **kwargs: Any) -> None:
        super().__init__(option_strings=option_strings, dest=dest, default=argparse.SUPPRESS, nargs=0, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        del namespace, values, option_string
        from fmind_dot import __version__

        formatter = parser._get_formatter()  # noqa: SLF001 - mirrors argparse._VersionAction
        formatter.add_text(f"dot version {__version__}")
        parser._print_message(formatter.format_help(), sys.stdout)  # noqa: SLF001
        parser.exit()


def _lazy(module: str, attr: str) -> Handler:
    """Defer command-module imports until that command executes."""

    def dispatch(state: State, args: argparse.Namespace) -> Any:
        return getattr(importlib.import_module(f"fmind_dot.{module}"), attr)(state, args)

    return dispatch


def _add_login_options(parser: Parser, prefix: str = "") -> None:
    chk = "Only probe readiness and exit 1 when a login is needed; never opens a login flow"
    opts = (
        (("-f", "--force"), f"{prefix}force", "Run authentication even when already ready or status is unknown"),
        (("--dry-run",), f"{prefix}dry_run", "Show possible commands without running probes or making changes"),
        (("--check",), f"{prefix}check", chk),
    )
    for flags, dest, help_text in opts:
        parser.add_argument(*flags, dest=dest, action="store_true", help=help_text)


def _register_context(commands: Parser) -> None:
    desc = (
        "Measure global, project, and combined AGENTS.md, skill, and subagent discovery costs; report duplicate names"
    )
    epilog = (
        "Exit codes: 0 report or passing --check; 1 failed --check or invalid/unreadable input; "
        "2 usage error (including --quiet with --details).\n\n"
        "Examples: dot context --check · dot context --source . --project . --details · dot context --check --json"
    )
    c = commands.command("context", desc, _lazy("context_budget", "_context"), config=False, epilog=epilog)
    proj_help = "Project root (only its own instructions, skills, and subagents) [default: .]"
    c.add_argument("-p", "--project", type=Path, default=Path(), metavar="PATH", help=proj_help)
    src_help = "Measure a dot source checkout instead of installed global files"
    c.add_argument("--source", type=Path, metavar="PATH", help=src_help)
    chk_help = "Exit 1 at 5,000 instruction + skill or 2,000 subagent tokens per scope, or on duplicate names"
    c.add_argument("--check", action="store_true", help=chk_help)
    det_help = "Include source paths, on-demand file costs, and coverage in text output"
    c.add_argument("--details", action="store_true", help=det_help)
    add_json(c)
    add_quiet(c)


def _register_doctor(commands: Parser) -> None:
    epilog = (
        "Exit 1 on any failed check, including disk below 10 GiB free (warns below 20). "
        "--headroom also fails below 1 GiB available memory; exit 2 when --headroom is combined with --fix or --deep.\n\n"
        "Examples: dot doctor --deep · dot doctor --headroom · dot doctor -q --json"
    )
    summary = "Check local workstation health; --deep also probes provider authentication"
    d = commands.command("doctor", summary, _lazy("system", "_doctor"), config=False, epilog=epilog)
    add_json(d)
    add_quiet(d)
    d.add_argument("--fix", action="store_true", help="Repair local secret-file permissions")
    d.add_argument("--deep", action="store_true", help="Also probe provider authentication")
    headroom_help = (
        "Only check disk (≥10 GiB) and memory (≥1 GiB) headroom before large downloads or builds; prints one line"
    )
    d.add_argument("--headroom", action="store_true", help=headroom_help)


def _register_login(commands: Parser) -> None:
    desc = "Log in where needed to this machine's providers (auth.login), or to one named provider"
    group = commands.group(
        "login",
        desc,
        handler=_lazy("auth", "_login_all"),
        config=True,
        epilog=_LOGIN_EPILOG,
    )
    _add_login_options(group, prefix="all_")
    grant_epilogs = {
        "workspace": "A --grant scope lasts until dot login workspace --force restores defaults.",
        "github": "A --grant scope skips --remove-scopes removal for that run; dot login github reconciles defaults again.",
    }
    summaries = {
        "gcp": "Ensure Google Cloud and ADC both have usable credentials",
        "github": "Ensure GitHub OAuth authentication and requested scopes",
        "workspace": "Authenticate Workspace OAuth and configure project APIs/OAuth when needed",
    }
    provider_handler = _lazy("auth", "_login_provider")
    for provider, summary in summaries.items():
        ep = grant_epilogs.get(provider)
        cmd = group.command(
            provider, summary, provider_handler, epilog=f"{ep} {_LOGIN_EPILOG}" if ep else _LOGIN_EPILOG
        )
        cmd.set_defaults(provider=provider)
        _add_login_options(cmd)
        if ep:
            h = "Also request this one-off scope; repeat for several"
            cmd.add_argument("--grant", action="append", default=[], metavar="SCOPE", help=h)
        if provider == "workspace":
            h = "Google Cloud project ID for API/OAuth setup [env: GWS_PROJECT]"
            cmd.add_argument("-p", "--project", default=None, metavar="ID", help=h)
            s = "Enable Workspace APIs and reconcile OAuth client configuration on the target project"
            cmd.add_argument("-s", "--setup", action="store_true", help=s)


def _register_privacy(commands: Parser) -> None:
    desc = "Scan directories and Git history for unapproved emails, SSH comments, and local workstation identifiers"
    epilog = (
        "Reads untracked ~/.config/dot*.yaml and ~/.config/git/config.* to catch private tokens before publishing. "
        "Exit 0 when clean; 1 when any finding or missing directory is reported.\n\n"
        "Examples: dot privacy · dot privacy --staged -q · dot privacy ~/fmind/www --json"
    )
    p = commands.command("privacy", desc, _lazy("privacy", "_privacy"), config=False, epilog=epilog)
    p.add_argument("paths", nargs="*", type=Path, help="Directories or repositories to scan [default: .]")
    p.add_argument("--staged", action="store_true", help="Scan staged Git index blobs instead of working-tree files")
    add_json(p)
    add_quiet(p)


def _register_pull(commands: Parser) -> None:
    msg = (
        "Skips dirty worktrees and branches without an upstream, and reports diverged branches without changing them. "
        "Exit 1 when any repository fails or diverged.\n\n"
        "Examples: dot pull · dot pull ~/fmind/dot --json"
    )
    p = commands.command(
        "pull",
        "Fast-forward configured repositories; never merges, rebases, or touches dirty checkouts",
        _lazy("repository", "_pull"),
        epilog=msg,
    )
    p.add_argument("paths", nargs="*", type=Path, help="Repositories to update; defaults to configured workspaces")
    add_json(p)


def _register_status(commands: Parser) -> None:
    s = commands.command(
        "status",
        "Show repository status using cached upstream refs (--fetch refreshes them)",
        _lazy("repository", "_status"),
        epilog=(
            "Exit 1 when any repository cannot be inspected; --json still prints every result.\n\n"
            "Examples: dot status --needs-attention · dot status --fetch --json"
        ),
    )
    s.add_argument("paths", nargs="*", type=Path, help="Repositories to inspect; defaults to configured workspaces")
    add_json(s)
    s.add_argument("--needs-attention", action="store_true", help="Only report repositories needing attention")
    s.add_argument("-f", "--fetch", action="store_true", help="Fetch remotes first so ahead/behind are current")


def _register_trust(commands: Parser) -> None:
    t = commands.command(
        "trust",
        "Pre-accept folder trust in agy and add trusted repositories to agy Remote Control projects",
        _lazy("trust", "_trust"),
        epilog=(
            "The target 'all' covers trust.github_owners repositories under pull.directories.\n\n"
            "Examples: dot trust . · dot trust all"
        ),
    )
    t.add_argument(
        "targets",
        nargs="*",
        help="Folders or repositories to trust, or 'all' for the configured workspaces [default: .]",
    )


def build_parser() -> Parser:
    """Build the command tree; help lists commands in registration order."""
    root = Parser(prog="dot", summary="Manage workstation tools, repositories, and agent setup", epilog=_EPILOG)
    root.add_argument(
        "-c",
        "--config",
        type=Path,
        metavar="PATH",
        default=os.environ.get("DOT_CONFIG_PATH") or None,
        help="Path to the configuration file [env: DOT_CONFIG_PATH]",
    )
    root.add_argument("-V", "--version", action=_VersionAction, help="Print the version and exit")
    root.set_defaults(handler=root.show_help, needs_config=False, parser=root)
    _register_context(root)
    _register_doctor(root)
    _register_login(root)
    _register_privacy(root)
    _register_pull(root)
    _register_status(root)
    _register_trust(root)
    return root


def app(arguments: Sequence[str] | None = None) -> None:
    """Parse and run one command; usage errors exit 2 through argparse, failures raise."""
    from fmind_dot.state import State

    args = build_parser().parse_args(arguments)
    state = State(config_argument=args.config)
    if args.needs_config:
        _ = state.config
    try:
        args.handler(state, args)
    except UsageError as error:
        args.parser.error(str(error))


def _interrupt_on_sigterm(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def main() -> None:
    previous_sigterm = signal.signal(signal.SIGTERM, _interrupt_on_sigterm)
    try:
        try:
            if (current := os.environ.get(COMPLETE_VARIABLE)) is not None:
                for value, description in candidates(build_parser(), [*sys.argv[1:], current]):
                    sys.stdout.write(f"{value}\t{description}\n" if description else f"{value}\n")
            else:
                app()
        except SystemExit:
            sys.stdout.flush()
            raise
        sys.stdout.flush()
    except BrokenPipeError:
        suppress_broken_pipe_stdout()
    except KeyboardInterrupt:
        flush_stdout_on_error()
        sys.stderr.write("Cancelled.\n")
        raise SystemExit(130) from None
    except (DotError, OSError, ValueError) as error:
        flush_stdout_on_error()
        sys.stderr.write(f"dot: {error}\n")
        raise SystemExit(1) from error
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
