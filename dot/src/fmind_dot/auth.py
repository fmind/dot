"""Provider-owned authentication with bounded readiness probes and explicit setup."""

import json
import os
from typing import Annotated, Any

import typer
from pydantic import TypeAdapter, ValidationError

from fmind_dot.command_group import help_group
from fmind_dot.config import Host, Project
from fmind_dot.errors import DotError
from fmind_dot.process import PROBE_OUTPUT_LIMIT_BYTES, CommandResult
from fmind_dot.state import State, require_tools, state_from
from fmind_dot.workstation import DryRun, ForceLogin, execute

login_app = help_group("Authenticate a provider; all runs Workspace then GCP")
setup_app = help_group("Reconcile provider setup and configured policy")
HostOption = Annotated[
    str | None, typer.Option("--host", envvar="GH_HOST", help="GitHub host; overrides auth.github.host")
]
# GitHub normalizes grants, dropping scopes implied by broader grants.
# https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps
_GITHUB_IMPLIED = {
    "repo": {
        "repo:status",
        "repo_deployment",
        "public_repo",
        "repo:invite",
        "security_events",
        "admin:repo_hook",
        "write:repo_hook",
        "read:repo_hook",
    },
    "public_repo": {"admin:repo_hook", "write:repo_hook", "read:repo_hook"},
    "admin:repo_hook": {"write:repo_hook", "read:repo_hook"},
    "write:repo_hook": {"read:repo_hook"},
    "admin:org": {"write:org", "read:org"},
    "write:org": {"read:org"},
    "admin:public_key": {"write:public_key", "read:public_key"},
    "write:public_key": {"read:public_key"},
    "admin:gpg_key": {"write:gpg_key", "read:gpg_key"},
    "write:gpg_key": {"read:gpg_key"},
    "user": {"read:user", "user:email", "user:follow"},
    "project": {"read:project"},
    "write:packages": {"read:packages"},
}
_GOOGLE_SCOPE_ALIASES = {
    "email": "https://www.googleapis.com/auth/userinfo.email",
    "profile": "https://www.googleapis.com/auth/userinfo.profile",
}


def probe(state: State, args: list[str]) -> CommandResult:
    require_tools(state, [args])
    result = state.runner.run_bounded(
        args, max_output_bytes=PROBE_OUTPUT_LIMIT_BYTES, timeout=state.config.auth.probe_timeout_seconds, check=False
    )
    if result.output_truncated:
        raise DotError(f"{args[0]} status exceeded the output limit; inspect the provider directly and retry")
    return result


def probe_json(state: State, args: list[str]) -> object:
    result = probe(state, args)
    if result.returncode:
        raise DotError(f"{args[0]} status failed (exit {result.returncode}); inspect the provider directly and retry")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise DotError(f"{args[0]} returned invalid status JSON; inspect the provider directly and retry") from error


def unknown(provider: str) -> DotError:
    return DotError(
        f"{provider} authentication state is unknown; inspect native auth status or use dot login {provider} --force to authenticate explicitly"
    )


def workspace_ready(state: State) -> bool:
    status = probe_json(state, ["gws", "auth", "status"])
    if not isinstance(status, dict):
        raise unknown("workspace")
    if status.get("auth_method") == "none":
        return False
    if status.get("token_valid") is False:
        return False
    scopes = status.get("scopes")
    if (
        status.get("token_valid") is not True
        or not isinstance(scopes, list)
        or not all(isinstance(scope, str) for scope in scopes)
    ):
        raise unknown("workspace")
    granted = {_GOOGLE_SCOPE_ALIASES.get(scope, scope) for scope in scopes}
    requested = {_GOOGLE_SCOPE_ALIASES.get(scope, scope) for scope in state.config.auth.workspace.scopes}
    return requested <= granted


def login_workspace(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    args = ["gws", "auth", "login", "--scopes", ",".join(state.config.auth.workspace.scopes)]
    if dry_run:
        execute(state, args, dry_run=True)
        return
    # gws status reports stored OAuth credentials even when an environment token
    # overrides the credentials actually used by API commands (gws 0.22.5).
    if os.environ.get("GOOGLE_WORKSPACE_CLI_TOKEN") or os.environ.get("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"):
        raise DotError(
            "external Workspace credentials override stored OAuth; unset GOOGLE_WORKSPACE_CLI_TOKEN or GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE before using dot login workspace"
        )
    if not force and workspace_ready(state):
        print("Workspace is already authenticated with the requested scopes.", file=state.stderr)
        return
    execute(state, args)
    if not workspace_ready(state):
        raise DotError("Workspace login did not satisfy the configured scopes; inspect gws auth status and retry")


def github_status(state: State, host: str) -> dict[str, Any] | None:
    status = probe_json(state, ["gh", "auth", "status", "--active", "--hostname", host, "--json", "hosts"])
    if not isinstance(status, dict) or not isinstance(status.get("hosts"), dict):
        raise unknown("github")
    entries = status["hosts"].get(host, [])
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise unknown("github")
    active = [entry for entry in entries if entry.get("active") is True]
    if not entries:
        return None
    if len(active) != 1:
        raise unknown("github")
    entry = active[0]
    if entry.get("state") == "success":
        return entry
    # JSON status exits zero on invalid tokens and network errors alike.
    if entry.get("state") == "error" and any(
        marker in str(entry.get("error", "")).lower() for marker in ("token is invalid", "(http 401)")
    ):
        return None
    raise unknown("github")


def github_ready(state: State, entry: dict[str, Any] | None, *, reconcile: bool) -> bool:
    if entry is None:
        return False
    raw = entry.get("scopes")
    if not isinstance(raw, str) or not raw:
        raise DotError(
            "GitHub did not report OAuth scopes; inspect the active token with gh auth status before changing authentication"
        )
    scopes = {scope.strip() for scope in raw.split(",")}
    granted = scopes | set().union(*(_GITHUB_IMPLIED.get(scope, set()) for scope in scopes))
    policy = state.config.auth.github
    return set(policy.scopes) <= granted and (not reconcile or not set(policy.remove_scopes) & scopes)


def login_github(
    state: State, host: str | None, *, reconcile: bool = False, force: bool = False, dry_run: bool = False
) -> None:
    try:
        selected = TypeAdapter(Host).validate_python(host if host is not None else state.config.auth.github.host)
    except ValidationError as error:
        raise typer.BadParameter("expected a hostname", param_hint="--host") from error
    policy = state.config.auth.github
    args = ["gh", "auth", "login", "--hostname", selected, "--scopes", ",".join(policy.scopes)]
    refresh = ["gh", "auth", "refresh", *args[3:]]
    if reconcile and policy.remove_scopes:
        refresh.extend(["--remove-scopes", ",".join(policy.remove_scopes)])
    if dry_run:
        execute(state, args, dry_run=True)
        if reconcile:
            execute(state, refresh, dry_run=True)
        return
    entry = None if force else github_status(state, selected)
    if not force and github_ready(state, entry, reconcile=reconcile):
        print("GitHub is already authenticated with the requested scope policy.", file=state.stderr)
        return
    env_names = (
        ("GH_TOKEN", "GITHUB_TOKEN")
        if selected == "github.com" or selected.endswith(".ghe.com")
        else ("GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")
    )
    if any(os.environ.get(name) for name in env_names):
        raise DotError(
            "an environment token controls GitHub authentication; update or unset it before changing OAuth scopes"
        )
    if entry is not None:
        execute(state, refresh)
    else:
        execute(state, args)
        # A fresh login cannot remove grants retained from an earlier authorization.
        if reconcile and policy.remove_scopes:
            execute(state, refresh)
    if not github_ready(state, github_status(state, selected), reconcile=reconcile):
        raise DotError(
            "GitHub authentication did not satisfy the configured scope policy; inspect gh auth status and retry"
        )


def gcp_ready(state: State) -> bool:
    ready = True
    for args in (
        ["gcloud", "auth", "print-access-token"],
        ["gcloud", "auth", "application-default", "print-access-token"],
    ):
        result = probe(state, args)
        if result.returncode == 0 and result.stdout.strip():
            continue
        # Never render access tokens or raw provider diagnostics.
        missing = (
            "invalid_grant",
            "expired or revoked",
            "reauthentication failed",
            "not currently have an active account",
            "no credentialed accounts",
            "default credentials were not found",
            "could not automatically determine credentials",
            "credentials not found",
        )
        if result.returncode and any(marker in result.stderr.lower() for marker in missing):
            ready = False
        else:
            raise unknown("gcp")
    return ready


def login_gcp(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    args = ["gcloud", "auth", "login", "--update-adc"]
    if dry_run:
        execute(state, args, dry_run=True)
        return
    if not force and gcp_ready(state):
        print("Google Cloud and ADC already provide usable credentials.", file=state.stderr)
        return
    if (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE")
        or os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN")
    ):
        raise DotError(
            "external credentials override Google Cloud or ADC; repair or unset the override before OAuth login"
        )
    execute(state, args)
    if not gcp_ready(state):
        raise DotError(
            "Google Cloud login did not provide usable CLI and ADC credentials; inspect gcloud auth and retry"
        )


def workspace_apis(state: State, project: str) -> set[str]:
    enabled = probe_json(
        state, ["gcloud", "services", "list", "--enabled", "--project", project, "--format=json(config.name)"]
    )
    if not isinstance(enabled, list) or not all(
        isinstance(row, dict) and isinstance(row.get("config"), dict) and isinstance(row["config"].get("name"), str)
        for row in enabled
    ):
        raise DotError("gcloud returned an invalid enabled API list; inspect the project before setup")
    return {row["config"]["name"] for row in enabled}


def workspace_configured(state: State, project: str) -> bool:
    status = probe_json(state, ["gws", "auth", "status"])
    if not isinstance(status, dict) or type(status.get("client_config_exists")) is not bool:
        raise DotError("Workspace client configuration state is unknown; inspect gws auth status before setup")
    return (
        status["client_config_exists"] and status.get("project_id") == project and not status.get("client_config_error")
    )


def setup_workspace(state: State, project: str | None, *, dry_run: bool = False) -> None:
    try:
        selected = TypeAdapter(Project).validate_python(
            project if project is not None else state.config.auth.workspace.project
        )
    except ValidationError as error:
        raise typer.BadParameter(
            "set a valid project ID through PROJECT, GWS_PROJECT, or auth.workspace.project", param_hint="PROJECT"
        ) from error
    apis = list(dict.fromkeys(state.config.auth.workspace.apis))
    setup = ["gws", "auth", "setup", "--project", selected]
    enable = ["gcloud", "services", "enable", *apis, "--project", selected, "--quiet"]
    if dry_run:
        execute(state, enable, dry_run=True)
        execute(state, setup, dry_run=True)
        return
    require_tools(state, [enable, setup])
    missing = sorted(set(apis) - workspace_apis(state, selected))
    configured = workspace_configured(state, selected)
    if missing:
        execute(state, ["gcloud", "services", "enable", *missing, "--project", selected, "--quiet"])
        if set(apis) - workspace_apis(state, selected):
            raise DotError("Workspace APIs remain missing after enablement; inspect gcloud services list and retry")
    if not configured:
        execute(state, setup)
        if not workspace_configured(state, selected):
            raise DotError("Workspace OAuth client setup is incomplete; inspect gws auth status and retry")
    print(
        "Workspace setup is complete."
        if missing or not configured
        else "Workspace APIs and OAuth client are already configured.",
        file=state.stderr,
    )


@login_app.command("workspace", help="Authenticate Workspace only when credentials or requested scopes are missing")
def workspace(context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False) -> None:
    login_workspace(state_from(context), force=force, dry_run=dry_run)


@login_app.command("github", help="Ensure GitHub OAuth authentication and requested scopes")
def github(context: typer.Context, host: HostOption = None, force: ForceLogin = False, dry_run: DryRun = False) -> None:
    login_github(state_from(context), host, force=force, dry_run=dry_run)


@login_app.command("gcp", help="Ensure Google Cloud and ADC both have usable credentials")
def gcp(context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False) -> None:
    login_gcp(state_from(context), force=force, dry_run=dry_run)


@login_app.command("all", help="Authenticate Workspace, then Google Cloud and ADC; stop on failure (excludes GitHub)")
def all_providers(context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False) -> None:
    state = state_from(context)
    if not dry_run:
        require_tools(state, [["gws"], ["gcloud"]])
    login_workspace(state, force=force, dry_run=dry_run)
    login_gcp(state, force=force, dry_run=dry_run)


@setup_app.command("github", help="Ensure requested GitHub scopes and remove configured excluded grants")
def github_setup(
    context: typer.Context, host: HostOption = None, force: ForceLogin = False, dry_run: DryRun = False
) -> None:
    login_github(state_from(context), host, reconcile=True, force=force, dry_run=dry_run)


@setup_app.command("workspace", help="Enable missing Workspace APIs and configure OAuth for an explicit project")
def workspace_setup(
    context: typer.Context,
    project: Annotated[
        str | None, typer.Argument(envvar="GWS_PROJECT", help="Project ID; overrides auth.workspace.project")
    ] = None,
    dry_run: DryRun = False,
) -> None:
    setup_workspace(state_from(context), project, dry_run=dry_run)
