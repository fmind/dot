"""Provider-owned authentication with bounded readiness probes and integrated setup."""

import argparse
import itertools
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fmind_dot.auth_probes import (
    GCLOUD_CLI_TOKEN,
    GITHUB_HOST,
    WORKSPACE_STATUS,
    adc_ready,
    gcloud_ready,
    github_ready,
    github_status,
    is_headless_ssh,
    one_off_scopes,
    probe_json,
    workspace_ready,
)
from fmind_dot.auth_probes import adc_cmd as _adc_cmd
from fmind_dot.auth_probes import dry_run_cmds as _dry_run
from fmind_dot.auth_probes import execute as _execute
from fmind_dot.auth_probes import reject_env as _reject_env
from fmind_dot.auth_probes import require_tty as _require_tty
from fmind_dot.auth_probes import warn_plaintext as _warn_plaintext
from fmind_dot.config import (
    GITHUB_FORBIDDEN_SCOPES,
    GITHUB_REMOVE_SCOPES,
    GITHUB_SCOPES,
    PROJECT_RE,
    WORKSPACE_APIS,
    WORKSPACE_FORBIDDEN_SCOPES,
    WORKSPACE_SCOPE_LIMIT,
    LoginProvider,
    env_path,
    expand_google_scope,
    is_valid_google_scope,
)
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import run_parallel
from fmind_dot.state import State, require_tools

LOGIN_ORDER: tuple[LoginProvider, ...] = ("github", "gcp", "workspace")
_GOOGLE_OAUTH_URL_RE = re.compile(r"https://accounts\.google\.com/o/oauth2/[^\s<>\"'`()\[\]{}\x00-\x1f\x7f]+")


def _has_env_workspace_client() -> bool:
    return bool(
        os.environ.get("GOOGLE_WORKSPACE_CLI_CLIENT_ID") and os.environ.get("GOOGLE_WORKSPACE_CLI_CLIENT_SECRET")
    )


def _workspace_mismatch_error(existing: object, project: str) -> DotError:
    has_dir = bool(os.environ.get("GOOGLE_WORKSPACE_CLI_CONFIG_DIR"))
    has_existing = isinstance(existing, str) and bool(existing)
    valid_existing = has_existing and PROJECT_RE.fullmatch(existing) is not None
    subject = (
        f"Workspace OAuth client is configured for project {existing!r}, not {project!r}"
        if has_existing
        else f"Workspace OAuth client has an unknown project, not {project!r}"
    )
    env_note = " (GOOGLE_WORKSPACE_CLI_CONFIG_DIR is set)" if has_dir else ""
    if has_dir:
        actions = ["unset GOOGLE_WORKSPACE_CLI_CONFIG_DIR"]
        if valid_existing:
            actions.append(f"run dot login workspace --project {existing}")
        actions.append("run dot login workspace --setup to reconfigure")
    else:
        actions = [
            f"run dot login workspace --project {existing}" if valid_existing else "update the project setting",
            "run dot login workspace --setup to reconfigure",
        ]
    remedy = f"{actions[0]}, {actions[1]}, or {actions[2]}" if len(actions) == 3 else f"{actions[0]} or {actions[1]}"
    return DotError(f"{subject}{env_note}; {remedy}")


def _workspace_client(
    state: State, project: str, *, allow_project_mismatch: bool = False
) -> tuple[bool, set[str] | None]:
    status = probe_json(state, WORKSPACE_STATUS)
    if not isinstance(status, dict) or type(status.get("client_config_exists")) is not bool:
        raise DotError("Workspace client configuration state is unknown; inspect gws auth status before setup")
    existing = status.get("project_id")
    same_project = existing == project
    has_valid_client = status["client_config_exists"] and not status.get("client_config_error")
    if has_valid_client and not same_project and not allow_project_mismatch:
        raise _workspace_mismatch_error(existing, project)
    configured = has_valid_client and same_project
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
    configured, enabled = _workspace_client(state, project, allow_project_mismatch=True)
    if not configured:
        _require_tty(state, setup[0])
    missing = list(WORKSPACE_APIS) if enabled is None else [a for a in WORKSPACE_APIS if a not in enabled]
    enabled_missing = bool(missing) and _enable_workspace_apis(
        state, missing, project, allow_permission_denied=configured or bool(enabled)
    )
    if not configured:
        _execute(state, setup)
        if not _workspace_client(state, project, allow_project_mismatch=True)[0]:
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
    state: State,
    *,
    force: bool = False,
    dry_run: bool = False,
    grants: Sequence[str] = (),
    project: str | None = None,
    setup: bool = False,
) -> None:
    configured = state.config.auth.workspace.scopes
    extra = one_off_scopes(
        grants,
        configured,
        expand=expand_google_scope,
        validate=is_valid_google_scope,
        forbidden=WORKSPACE_FORBIDDEN_SCOPES,
    )
    if len(configured) + len(extra) > WORKSPACE_SCOPE_LIMIT:
        raise DotError(
            f"Workspace login would request {len(configured) + len(extra)} scopes, exceeding the {WORKSPACE_SCOPE_LIMIT}-scope limit"
        )
    selected = _resolve_workspace_project(state, project)
    if setup and not selected:
        raise UsageError("--setup requires a project ID through --project, GWS_PROJECT, or auth.workspace.project")
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
    client_ready = bool(selected) and _workspace_client(state, selected, allow_project_mismatch=setup)[0]
    if not force and not setup and (not selected or client_ready) and workspace_ready(state, extra):
        print("Workspace is already authenticated with the requested scopes.", file=state.stderr)
        return
    if selected and (setup or not client_ready):
        if client_ready and (force or not workspace_ready(state, extra)):
            _require_tty(state, args[0])
        setup_workspace(state, selected)
    elif not selected and not _has_env_workspace_client():
        print("Skipping Workspace setup: set --project, GWS_PROJECT, or auth.workspace.project.", file=state.stderr)
    if not force and workspace_ready(state, extra):
        print("Workspace is already authenticated with the requested scopes.", file=state.stderr)
        return
    require_tools(state, [args])
    _require_tty(state, args[0])
    headless = is_headless_ssh()
    if headless:
        print(
            "Headless SSH detected: if OAuth redirects to localhost:<PORT>, run `curl -fsS '<URL>'` on this host.",
            file=state.stderr,
        )
    _execute(state, args, open_url=None if headless else _GOOGLE_OAUTH_URL_RE)
    config_dir = env_path("GOOGLE_WORKSPACE_CLI_CONFIG_DIR", Path.home() / ".config" / "gws")
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
    extra = [] if reconcile_scopes else one_off_scopes(grants, GITHUB_SCOPES, forbidden=GITHUB_FORBIDDEN_SCOPES)
    args = ["gh", "auth", "login", "--hostname", GITHUB_HOST, "--scopes", ",".join([*GITHUB_SCOPES, *extra])]
    remove_list = GITHUB_REMOVE_SCOPES if reconcile_scopes else tuple(sorted(GITHUB_FORBIDDEN_SCOPES))
    remove = ["--remove-scopes", ",".join(remove_list)]
    refresh, web = ["gh", "auth", "refresh", *args[3:], "--clipboard", *remove], [*args, "--web", "--clipboard"]
    if dry_run:
        _dry_run(state, web, refresh)
        return
    entry = None if force else github_status(state)
    if not force and github_ready(entry, reconcile=reconcile_scopes, grants=extra):
        print("GitHub is already authenticated with the requested scope policy.", file=state.stderr)
        _warn_plaintext(state, entry)
        return
    _reject_env(
        ("GH_TOKEN", "GITHUB_TOKEN"), "an environment token controls GitHub authentication; update or unset it first"
    )
    if entry is None:
        _execute(state, web)
        entry = github_status(state)
    if not github_ready(entry, reconcile=reconcile_scopes, grants=extra):
        _execute(state, refresh)
        entry = github_status(state)
    if not github_ready(entry, reconcile=reconcile_scopes, grants=extra):
        msg = "GitHub authentication did not satisfy the requested scope policy; inspect gh auth status and retry"
        raise DotError(msg)
    _warn_plaintext(state, entry)
    if extra:
        msg = f"One-off GitHub scopes granted: {', '.join(extra)}; run dot login github to restore defaults."
        print(msg, file=state.stderr)


def login_gcp(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    browser_flag = ["--no-launch-browser"] if is_headless_ssh() else []
    cli, adc = ["gcloud", "auth", "login", *browser_flag], [*_adc_cmd("login"), *browser_flag]
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


def provider_ready(state: State, provider: LoginProvider, *, reconcile: bool = False) -> bool:
    if provider == "github":
        return github_ready(github_status(state), reconcile=reconcile)
    if provider == "gcp":
        return gcloud_ready(state, GCLOUD_CLI_TOKEN) and adc_ready(state)
    if selected := _resolve_workspace_project(state, None):
        return _workspace_client(state, selected)[0] and workspace_ready(state)
    return workspace_ready(state)


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
        login_workspace(
            state,
            force=force,
            dry_run=dry_run,
            grants=kw.get("grants", ()),
            project=kw.get("project"),
            setup=bool(kw.get("setup", False)),
        )
    else:
        login_gcp(state, force=force, dry_run=dry_run)


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
            "workspace": ["gws"],
        }
        require_tools(state, [[tool] for p in providers for tool in tools[p]])
    for provider in providers:
        kw = {"project": project} if provider == "workspace" else {"reconcile": True} if provider == "github" else {}
        _run_provider(state, provider, force=force, dry_run=dry_run, **kw)


def _login_all(state: State, args: argparse.Namespace) -> None:
    login_machine(state, force=args.all_force, dry_run=args.all_dry_run, check=args.all_check)


def _login_provider(state: State, args: argparse.Namespace) -> None:
    provider: LoginProvider = args.provider
    force = args.force or args.all_force
    dry_run = args.dry_run or args.all_dry_run
    check = args.check or args.all_check
    grants = getattr(args, "grant", [])
    project = getattr(args, "project", None)
    setup = getattr(args, "setup", False)
    if check:
        if grants or project is not None or setup:
            raise UsageError("--check cannot be combined with --grant, --project, or --setup")
        check_logins(state, [provider], f"dot login {provider}", force=force, dry_run=dry_run, reconcile=True)
        return
    _run_provider(
        state,
        provider,
        force=force,
        dry_run=dry_run,
        grants=grants,
        project=project,
        setup=setup,
    )
