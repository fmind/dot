"""Provider-owned authentication with bounded readiness probes and integrated setup."""

import argparse
import itertools
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fmind_dot.auth_probes import (
    COLAB_SESSIONS as COLAB_SESSIONS,
)
from fmind_dot.auth_probes import (
    GCLOUD_CLI_TOKEN as GCLOUD_CLI_TOKEN,
)
from fmind_dot.auth_probes import (
    GITHUB_HOST as GITHUB_HOST,
)
from fmind_dot.auth_probes import (
    GOOGLE_ALIASES as _GOOGLE_ALIASES,
)
from fmind_dot.auth_probes import (
    GOOGLE_PREFIX as _GOOGLE_PREFIX,
)
from fmind_dot.auth_probes import (
    PROBE_TIMEOUT_SECONDS as PROBE_TIMEOUT_SECONDS,
)
from fmind_dot.auth_probes import (
    WORKSPACE_STATUS as WORKSPACE_STATUS,
)
from fmind_dot.auth_probes import (
    adc_cmd as _adc_cmd,
)
from fmind_dot.auth_probes import (
    adc_ready as adc_ready,
)
from fmind_dot.auth_probes import (
    colab_ready as colab_ready,
)
from fmind_dot.auth_probes import (
    dry_run_cmds as _dry_run,
)
from fmind_dot.auth_probes import (
    execute as _execute,
)
from fmind_dot.auth_probes import (
    gcloud_ready as gcloud_ready,
)
from fmind_dot.auth_probes import (
    github_entry as github_entry,
)
from fmind_dot.auth_probes import (
    github_ready as github_ready,
)
from fmind_dot.auth_probes import (
    github_status as github_status,
)
from fmind_dot.auth_probes import (
    github_token_plaintext as github_token_plaintext,
)
from fmind_dot.auth_probes import (
    norm_google as _norm_google,
)
from fmind_dot.auth_probes import (
    one_off_scopes as one_off_scopes,
)
from fmind_dot.auth_probes import (
    probe_json as probe_json,
)
from fmind_dot.auth_probes import (
    reject_env as _reject_env,
)
from fmind_dot.auth_probes import (
    warn_plaintext as _warn_plaintext,
)
from fmind_dot.auth_probes import (
    workspace_granted as workspace_granted,
)
from fmind_dot.auth_probes import (
    workspace_ready as workspace_ready,
)
from fmind_dot.command import Parser
from fmind_dot.config import (
    GITHUB_REMOVE_SCOPES,
    GITHUB_SCOPES,
    PROJECT_RE,
    WORKSPACE_APIS,
    WORKSPACE_SCOPE_LIMIT,
    LoginProvider,
    env_path,
)
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import run_parallel
from fmind_dot.state import State, require_tools

_LOGIN_EPILOG = "Exit 0 when ready. With --check, exit 1 when a login is needed or the state is unknown."
LOGIN_ORDER: tuple[LoginProvider, ...] = ("github", "gcp", "workspace", "colab")


def _workspace_client(state: State, project: str) -> tuple[bool, set[str] | None]:
    status = probe_json(state, WORKSPACE_STATUS)
    if not isinstance(status, dict) or type(status.get("client_config_exists")) is not bool:
        raise DotError("Workspace client configuration state is unknown; inspect gws auth status before setup")
    same_project = status.get("project_id") == project
    configured = status["client_config_exists"] and same_project and not status.get("client_config_error")
    apis = status.get("enabled_apis")
    return configured, set(apis) if same_project and isinstance(apis, list) and all(
        isinstance(a, str) for a in apis
    ) else None


# Service Usage (serviceusage.googleapis.com) caps gcloud services enable at 20 services per call.
_SERVICE_ENABLE_BATCH_SIZE = 20
_SERVICE_ENABLE_TIMEOUT_SECONDS = 120.0
_SERVICE_PERMISSION_MARKERS = (
    "AUTH_PERMISSION_DENIED",
    "serviceusage.services.enable",
    "Permission denied to enable service",
)


def _enable_commands(apis: Sequence[str], project: str) -> list[list[str]]:
    return [
        ["gcloud", "services", "enable", *batch, "--project", project, "--quiet"]
        for batch in itertools.batched(apis, _SERVICE_ENABLE_BATCH_SIZE, strict=False)
    ]


def _enable_workspace_apis(state: State, apis: Sequence[str], project: str, *, allow_permission_denied: bool) -> bool:
    for cmd in _enable_commands(apis, project):
        try:
            result = state.runner.run(cmd, timeout=_SERVICE_ENABLE_TIMEOUT_SECONDS, check=False)
        finally:
            state.clear_probes()
        if result.returncode == 0:
            continue
        if allow_permission_denied and any(m in result.stderr for m in _SERVICE_PERMISSION_MARKERS):
            print(
                f"Warning: cannot enable remaining Workspace APIs on {project} (missing serviceusage.services.enable); using pre-enabled APIs.",
                file=state.stderr,
            )
            return False
        if result.stderr:
            state.stderr.write(result.stderr)
        raise DotError(f"command failed ({result.returncode}): {cmd[0]}")
    return True


def setup_workspace(state: State, project: str, *, dry_run: bool = False) -> None:
    """Enable required Workspace APIs and configure the gws OAuth client for ``project``."""
    setup = ["gws", "auth", "setup", "--project", project]
    if dry_run:
        _dry_run(state, *_enable_commands(WORKSPACE_APIS, project), setup)
        return
    require_tools(state, [*_enable_commands(WORKSPACE_APIS, project), setup])
    configured, enabled = _workspace_client(state, project)
    missing = list(WORKSPACE_APIS) if enabled is None else [a for a in WORKSPACE_APIS if a not in enabled]
    enabled_missing = bool(missing) and _enable_workspace_apis(
        state, missing, project, allow_permission_denied=configured or bool(enabled)
    )
    if not configured:
        _execute(state, setup)
        if not _workspace_client(state, project)[0]:
            raise DotError("Workspace OAuth client setup is incomplete; inspect gws auth status and retry")
    if enabled_missing or not configured:
        print("Workspace setup is complete.", file=state.stderr)


def _resolve_workspace_project(state: State, project: str | None) -> str | None:
    if not (raw := project or os.environ.get("GWS_PROJECT") or state.config.auth.workspace.project):
        return None
    if PROJECT_RE.fullmatch(raw) is None:
        raise UsageError("PROJECT: set a valid project ID through --project, GWS_PROJECT, or auth.workspace.project")
    return raw


def login_workspace(
    state: State, *, force: bool = False, dry_run: bool = False, grants: Sequence[str] = (), project: str | None = None
) -> None:
    configured = state.config.auth.workspace.scopes
    extra = one_off_scopes(
        grants,
        configured,
        expand=lambda n: n if "://" in n or n == "openid" else _GOOGLE_ALIASES.get(n, f"{_GOOGLE_PREFIX}{n}"),
    )
    if len(configured) + len(extra) > WORKSPACE_SCOPE_LIMIT:
        raise DotError(
            f"Workspace login would request {len(configured) + len(extra)} scopes, exceeding the {WORKSPACE_SCOPE_LIMIT}-scope limit"
        )
    selected = _resolve_workspace_project(state, project)
    args = ["gws", "auth", "login", "--scopes", ",".join([*configured, *extra])]
    if dry_run:
        if selected:
            setup_workspace(state, selected, dry_run=True)
        _dry_run(state, args)
        return
    _reject_env(
        ("GOOGLE_WORKSPACE_CLI_TOKEN", "GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"),
        "external Workspace credentials override stored OAuth; unset GOOGLE_WORKSPACE_CLI_TOKEN or GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE before using dot login workspace",
    )
    if not force and (not selected or _workspace_client(state, selected)[0]):
        granted = workspace_granted(state)
        if granted is not None and _norm_google([*configured, *extra]) <= granted:
            print("Workspace is already authenticated with the requested scopes.", file=state.stderr)
            return
    if selected:
        setup_workspace(state, selected)
    else:
        print("Skipping Workspace setup: set --project, GWS_PROJECT, or auth.workspace.project.", file=state.stderr)
    granted = None if force else workspace_granted(state)
    if granted is not None and _norm_google([*configured, *extra]) <= granted:
        print("Workspace is already authenticated with the requested scopes.", file=state.stderr)
        return
    _execute(state, args)
    config_dir = env_path("GOOGLE_WORKSPACE_CLI_CONFIG_DIR", Path.home() / ".config" / "gws", expand_vars=False)
    for name in ("token_cache.json", "sa_token_cache.json"):
        (config_dir / name).unlink(missing_ok=True)
    if not workspace_ready(state, extra):
        raise DotError("Workspace login did not satisfy the requested scopes; inspect gws auth status and retry")
    if extra:
        print(
            f"One-off Workspace scopes granted: {', '.join(extra)}. Run dot login workspace --force to reset.",
            file=state.stderr,
        )


def login_github(
    state: State,
    *,
    force: bool = False,
    dry_run: bool = False,
    grants: Sequence[str] = (),
    reconcile: bool | None = None,
) -> None:
    reconcile_scopes = not grants if reconcile is None else reconcile
    extra = [] if reconcile_scopes else one_off_scopes(grants, GITHUB_SCOPES)
    args = ["gh", "auth", "login", "--hostname", GITHUB_HOST, "--scopes", ",".join([*GITHUB_SCOPES, *extra])]
    remove = ["--remove-scopes", ",".join(GITHUB_REMOVE_SCOPES)] if reconcile_scopes else []
    refresh, web = ["gh", "auth", "refresh", *args[3:], *remove], [*args, "--web"]
    if dry_run:
        _dry_run(state, *(web, refresh) if reconcile_scopes else (web,))
        return
    entry = None if force else github_status(state)
    if not force and github_ready(state, entry, reconcile=reconcile_scopes, grants=extra):
        print("GitHub is already authenticated with the requested scope policy.", file=state.stderr)
        _warn_plaintext(state, entry)
        return
    _reject_env(
        ("GH_TOKEN", "GITHUB_TOKEN"), "an environment token controls GitHub authentication; update or unset it first"
    )
    if entry is None:
        _execute(state, web)
    if entry is not None or reconcile_scopes:
        _execute(state, refresh)
    entry = github_status(state)
    if not github_ready(state, entry, reconcile=reconcile_scopes, grants=extra):
        msg = "GitHub authentication did not satisfy the requested scope policy; inspect gh auth status and retry"
        raise DotError(msg)
    _warn_plaintext(state, entry)
    if extra:
        msg = f"One-off GitHub scopes granted: {', '.join(extra)}; run dot login github to restore defaults."
        print(msg, file=state.stderr)


def login_gcp(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    cli, adc = ["gcloud", "auth", "login"], _adc_cmd("login")
    if dry_run:
        _dry_run(state, cli, adc)
        return
    cli_ok, adc_ok = not force and gcloud_ready(state, GCLOUD_CLI_TOKEN), not force and adc_ready(state)
    if cli_ok and adc_ok:
        print("Google Cloud CLI and ADC already provide usable credentials.", file=state.stderr)
        return
    _reject_env(
        ("GOOGLE_APPLICATION_CREDENTIALS", "CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE", "CLOUDSDK_AUTH_ACCESS_TOKEN"),
        "external credentials override Google Cloud or ADC; repair or unset the override before OAuth login",
    )
    if not cli_ok:
        _execute(state, cli)
    if not adc_ok:
        _execute(state, adc)
    if not (gcloud_ready(state, GCLOUD_CLI_TOKEN) and adc_ready(state)):
        msg = "Google Cloud login did not provide usable CLI and ADC credentials; inspect gcloud auth and retry"
        raise DotError(msg)


def login_colab(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    args = _adc_cmd("login")
    if dry_run:
        _dry_run(state, args, COLAB_SESSIONS)
        return
    require_tools(state, [args, COLAB_SESSIONS])
    if not force and adc_ready(state, "colab"):
        print("ADC already grants the configured scopes.", file=state.stderr)
    else:
        msg = (
            "external credentials override Colab ADC; repair or unset GOOGLE_APPLICATION_CREDENTIALS before OAuth login"
        )
        _reject_env(("GOOGLE_APPLICATION_CREDENTIALS",), msg)
        _execute(state, args)
    if not colab_ready(state):
        msg = "Colab login did not provide usable ADC; inspect colab --auth=adc sessions and retry dot login colab --force"
        raise DotError(msg)
    print("Colab accepts ADC credentials.", file=state.stderr)


def provider_ready(state: State, provider: LoginProvider, *, reconcile: bool = False) -> bool:
    if provider == "github":
        return github_ready(state, github_status(state), reconcile=reconcile)
    if provider == "gcp":
        return gcloud_ready(state, GCLOUD_CLI_TOKEN) and adc_ready(state)
    if provider == "workspace":
        return workspace_ready(state)
    return adc_ready(state, "colab") and colab_ready(state)


def check_logins(
    state: State,
    providers: Sequence[LoginProvider],
    remedy: str,
    *,
    force: bool,
    dry_run: bool,
    reconcile: bool = False,
) -> None:
    if force or dry_run:
        raise UsageError("--check cannot be combined with --force or --dry-run")

    def inspect(provider: LoginProvider) -> str:
        try:
            return "ready" if provider_ready(state, provider, reconcile=reconcile) else "login needed"
        except DotError as error:
            return f"unknown ({error})"

    verdicts = run_parallel(state.runner, inspect, list(providers), max(1, len(providers)))
    for provider, verdict in zip(providers, verdicts, strict=True):
        print(f"{provider}: {verdict}", file=state.stdout)
    if not all(v == "ready" for v in verdicts):
        print(f"Run {remedy} in a terminal to authenticate.", file=state.stderr)
        raise SystemExit(1)


def _run_provider(state: State, provider: LoginProvider, **kw: Any) -> None:
    force, dry_run = kw["force"], kw["dry_run"]
    if provider == "github":
        login_github(state, force=force, dry_run=dry_run, grants=kw.get("grants", ()), reconcile=kw.get("reconcile"))
    elif provider == "workspace":
        login_workspace(state, force=force, dry_run=dry_run, grants=kw.get("grants", ()), project=kw.get("project"))
    elif provider == "gcp":
        login_gcp(state, force=force, dry_run=dry_run)
    else:
        login_colab(state, force=force, dry_run=dry_run)


def login_machine(state: State, *, force: bool, dry_run: bool, check: bool) -> None:
    providers = [p for p in LOGIN_ORDER if p in state.config.auth.login]
    if check:
        check_logins(state, providers, "dot login", force=force, dry_run=dry_run, reconcile=True)
        return
    project = _resolve_workspace_project(state, None) if "workspace" in providers else None
    if not dry_run:
        tools = {
            "github": ["gh"],
            "gcp": ["gcloud"],
            "workspace": ["gws", "gcloud"] if project else ["gws"],
            "colab": ["gcloud", "colab"],
        }
        require_tools(state, [[tool] for p in providers for tool in tools[p]])
    for provider in providers:
        f = force and not (provider == "colab" and "gcp" in providers)
        kw = {"project": project} if provider == "workspace" else {"reconcile": True} if provider == "github" else {}
        _run_provider(state, provider, force=f, dry_run=dry_run, **kw)


def _add_login_options(parser: Parser, prefix: str = "") -> None:
    chk = "Only probe readiness and exit 1 when a login is needed; never opens a login flow"
    opts = (
        (("-f", "--force"), f"{prefix}force", "Run authentication even when already ready or status is unknown"),
        (("--dry-run",), f"{prefix}dry_run", "Show possible commands without running probes or making changes"),
        (("--check",), f"{prefix}check", chk),
    )
    for flags, dest, help_text in opts:
        parser.add_argument(*flags, dest=dest, action="store_true", help=help_text)


def _login_provider(state: State, args: argparse.Namespace) -> None:
    provider: LoginProvider = args.provider
    if args.all_force or args.all_dry_run or args.all_check:
        raise UsageError("place options after the provider, as in dot login gcp --check")
    grants = getattr(args, "grant", [])
    if args.check:
        if grants:
            raise UsageError("--check cannot be combined with --grant")
        check_logins(state, [provider], f"dot login {provider}", force=args.force, dry_run=args.dry_run, reconcile=True)
        return
    _run_provider(
        state, provider, force=args.force, dry_run=args.dry_run, grants=grants, project=getattr(args, "project", None)
    )


def register_login(commands: Parser) -> None:
    desc = "Log in where needed to this machine's providers (auth.login), or to one named provider"
    group = commands.group(
        "login",
        desc,
        handler=lambda s, a: login_machine(s, force=a.all_force, dry_run=a.all_dry_run, check=a.all_check),
        config=True,
        epilog=_LOGIN_EPILOG,
    )
    _add_login_options(group, prefix="all_")
    grant_epilogs = {
        "workspace": "A --grant scope lasts until dot login workspace --force restores defaults.",
        "github": "A --grant scope skips --remove-scopes removal for that run; dot login github reconciles defaults again.",
    }
    summaries = {
        "colab": "Ensure ADC grants the Colab scopes and verify session access",
        "gcp": "Ensure Google Cloud and ADC both have usable credentials",
        "github": "Ensure GitHub OAuth authentication and requested scopes",
        "workspace": "Setup APIs/OAuth when a project is configured and authenticate Workspace",
    }
    for provider, summary in summaries.items():
        ep = grant_epilogs.get(provider)
        cmd = group.command(provider, summary, _login_provider, epilog=f"{ep} {_LOGIN_EPILOG}" if ep else _LOGIN_EPILOG)
        cmd.set_defaults(provider=provider)
        _add_login_options(cmd)
        if ep:
            h = "Also request this one-off scope; repeat for several"
            cmd.add_argument("--grant", action="append", default=[], metavar="SCOPE", help=h)
        if provider == "workspace":
            h = "Google Cloud project ID for API/OAuth setup [env: GWS_PROJECT]"
            cmd.add_argument("-p", "--project", default=None, metavar="ID", help=h)
