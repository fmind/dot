"""Provider-owned authentication with bounded readiness probes and explicit setup."""

import contextlib
import json
import os
import sys
import webbrowser
from collections.abc import Callable, Sequence
from pathlib import PurePath
from typing import Annotated, Any

import typer
from pydantic import TypeAdapter, ValidationError

from fmind_dot.command_group import HELP_MARKUP, AlphabeticalGroup, help_group
from fmind_dot.config import LoginProvider, Project
from fmind_dot.errors import DotError
from fmind_dot.process import CommandResult, run_parallel
from fmind_dot.state import State, require_tools, state_from
from fmind_dot.workstation import DryRun, ForceLogin, execute

_LOGIN_EPILOG = "Exit 0 when ready. With --check, exit 1 when a login is needed or the state is unknown."
login_app = typer.Typer(
    cls=AlphabeticalGroup,
    help="Log in where needed to this machine's providers (auth.login), or to one named provider",
    epilog=_LOGIN_EPILOG,
    invoke_without_command=True,
    rich_markup_mode=HELP_MARKUP,
    context_settings={"help_option_names": ["-h", "--help"]},
)
setup_app = help_group("Reconcile provider setup and configured policy")
_COLAB_ADC_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/colaboratory",
)
GITHUB_HOST = "github.com"
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
# Lowercase gcloud stderr fragments that require a fresh login. gcloud ends
# every relogin error with its login command; transport failures never name one. Google rejects a
# token refresh for scopes outside the stored grant, which gcloud reports as an invalid scopes value.
GCLOUD_LOGIN_MARKERS = (
    "invalid scopes value",
    "invalid_grant",
    "expired or revoked",
    "reauthenticat",
    "to obtain new credentials",
    "gcloud auth login",
    "gcloud auth application-default login",
    "not currently have an active account",
    "no credentialed accounts",
    "default credentials were not found",
    "could not automatically determine credentials",
    "credentials not found",
)
GITHUB_KEYRING_REMEDY = "unlock the system keyring, then run gh auth logout and dot setup github"
GCLOUD_CLI_TOKEN = ["gcloud", "auth", "print-access-token"]
GITHUB_STATUS = ["gh", "auth", "status", "--active", "--hostname", GITHUB_HOST, "--json", "hosts"]
WORKSPACE_STATUS = ["gws", "auth", "status"]
COLAB_SESSIONS = ["colab", "--auth=adc", "sessions"]
# Workspace setup lists and enables APIs through gcloud and Colab shares ADC, so GCP precedes both.
LOGIN_ORDER: tuple[LoginProvider, ...] = ("github", "gcp", "workspace", "colab")
# One worker per distinct readiness probe: the five probes are I/O-bound native CLIs.
PROBE_WORKERS = 5
# Native OAuth URLs that dot may open on behalf of a CLI that only prints them.
_GOOGLE_OAUTH_URL = "https://accounts.google.com/"
_GOOGLE_SCOPE_ALIASES = {
    "email": "https://www.googleapis.com/auth/userinfo.email",
    "profile": "https://www.googleapis.com/auth/userinfo.profile",
}


def probe(state: State, args: list[str]) -> CommandResult:
    """Run a readiness probe once per invocation; logins clear the reused results."""
    key = tuple(args)
    if (cached := state.probes.get(key)) is not None:
        return cached
    require_tools(state, [args])
    result = state.runner.run(args, timeout=state.config.auth.probe_timeout_seconds, check=False)
    state.probes[key] = result
    return result


def probe_commands(state: State, provider: LoginProvider) -> list[list[str]]:
    return {
        "github": [GITHUB_STATUS],
        "gcp": [GCLOUD_CLI_TOKEN, adc_probe_command(state)],
        "workspace": [WORKSPACE_STATUS],
        "colab": [adc_probe_command(state), COLAB_SESSIONS],
    }[provider]


def warm_probes(state: State, providers: Sequence[LoginProvider]) -> None:
    """Run every distinct readiness probe concurrently so the sequential steps reuse the results."""
    commands = list({tuple(args): args for provider in providers for args in probe_commands(state, provider)}.values())

    def run(args: list[str]) -> None:
        # The sequential step that reads this probe reports its failure with provider context.
        with contextlib.suppress(DotError):
            probe(state, args)

    run_parallel(state.runner, run, commands, PROBE_WORKERS)


def change(state: State, args: list[str], **options: Any) -> None:
    """Run a native login or setup command; it changes provider state, so earlier probe results are stale."""
    try:
        execute(state, args, **options)
    finally:
        state.probes.clear()


def probe_json(state: State, args: list[str]) -> object:
    result = probe(state, args)
    if result.returncode and args[0] == "gcloud" and any(m in result.stderr.lower() for m in GCLOUD_LOGIN_MARKERS):
        raise DotError("gcloud credentials need a fresh login; run dot login gcp and retry")
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


def workspace_token_valid(status: object) -> bool | None:
    """Classify gws status JSON: True for a valid token, False when unauthenticated, None when unknown."""
    # Native status exits zero even without credentials; only its JSON proves readiness.
    if not isinstance(status, dict):
        return None
    if status.get("auth_method") == "none" or status.get("token_valid") is False:
        return False
    return True if status.get("token_valid") is True else None


def workspace_ready(state: State) -> bool:
    status = probe_json(state, WORKSPACE_STATUS)
    valid = workspace_token_valid(status)
    if valid is False:
        return False
    scopes = status.get("scopes") if valid and isinstance(status, dict) else None
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes):
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
    # gws 0.22.5 prints its OAuth URL on stderr but never launches a browser.
    change(state, args, on_stderr_line=browser_opener(state))
    if not workspace_ready(state):
        raise DotError("Workspace login did not satisfy the configured scopes; inspect gws auth status and retry")


def open_browser(url: str) -> bool:
    """Open a URL in the graphical browser; report False when none is available."""
    # webbrowser honors $BROWSER (garcon-url-handler on Crostini), but without a graphical
    # session it falls back to console browsers that would seize the terminal mid-login.
    if sys.platform != "darwin" and not any(os.environ.get(name) for name in ("BROWSER", "DISPLAY", "WAYLAND_DISPLAY")):
        return False
    try:
        return webbrowser.open(url)
    except webbrowser.Error:
        return False


def browser_opener(state: State) -> Callable[[str], None]:
    """Open the first Google OAuth URL a native login prints; the printed URL stays the fallback."""
    opened = False

    def on_line(line: str) -> None:
        nonlocal opened
        url = line.strip()
        if opened or not url.startswith(_GOOGLE_OAUTH_URL) or any(char.isspace() for char in url):
            return
        opened = True
        if open_browser(url):
            print("Opened the sign-in page in your browser.", file=state.stderr, flush=True)

    return on_line


def github_status(state: State) -> dict[str, Any] | None:
    return github_entry(probe_json(state, GITHUB_STATUS))


def github_entry(status: object) -> dict[str, Any] | None:
    """Select the active account from gh status JSON: None when unauthenticated; raises when unknown."""
    if not isinstance(status, dict) or not isinstance(status.get("hosts"), dict):
        raise unknown("github")
    entries = status["hosts"].get(GITHUB_HOST, [])
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
    # JSON status exits zero on invalid tokens and network errors alike; gh 2.102 reports a rejected
    # token as "non-200 OK status code: 401 Unauthorized".
    if entry.get("state") == "error" and any(
        marker in str(entry.get("error", "")).lower()
        for marker in ("token is invalid", "(http 401)", "401 unauthorized")
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


def login_github(state: State, *, reconcile: bool = False, force: bool = False, dry_run: bool = False) -> None:
    policy = state.config.auth.github
    args = ["gh", "auth", "login", "--hostname", GITHUB_HOST, "--scopes", ",".join(policy.scopes)]
    refresh = ["gh", "auth", "refresh", *args[3:]]
    if reconcile and policy.remove_scopes:
        refresh.extend(["--remove-scopes", ",".join(policy.remove_scopes)])
    # --web skips the authentication-method prompt; the Git protocol is resolved from gh's
    # configuration at run time, and the SSH key prompt remains a deliberate per-machine choice.
    web = [*args, "--web"]
    if dry_run:
        execute(state, web, dry_run=True)
        if reconcile:
            execute(state, refresh, dry_run=True)
        return
    entry = None if force else github_status(state)
    if not force and github_ready(state, entry, reconcile=reconcile):
        print("GitHub is already authenticated with the requested scope policy.", file=state.stderr)
        warn_plaintext_github_token(state, entry)
        return
    if any(os.environ.get(name) for name in ("GH_TOKEN", "GITHUB_TOKEN")):
        raise DotError(
            "an environment token controls GitHub authentication; update or unset it before changing OAuth scopes"
        )
    env = github_login_env()
    if entry is not None:
        change(state, refresh, env=env)
    else:
        change(state, [*web, *github_git_protocol(state)], env=env)
        # A fresh login cannot remove grants retained from an earlier authorization.
        if reconcile and policy.remove_scopes:
            change(state, refresh, env=env)
    entry = github_status(state)
    if not github_ready(state, entry, reconcile=reconcile):
        raise DotError(
            "GitHub authentication did not satisfy the configured scope policy; inspect gh auth status and retry"
        )
    warn_plaintext_github_token(state, entry)


def github_git_protocol(state: State) -> list[str]:
    """Pass gh's configured Git protocol so login skips its prompt; unknown values keep the prompt."""
    result = probe(state, ["gh", "config", "get", "git_protocol", "--host", GITHUB_HOST])
    value = result.stdout.strip()
    return ["--git-protocol", value] if result.returncode == 0 and value in {"https", "ssh"} else []


def github_login_env() -> dict[str, str] | None:
    """Route gh's one-time code copy through X11 on ChromeOS Crostini."""
    # gh copies the device code by default; under Sommelier wl-copy never learns it owns the
    # selection, so it never forks and gh waits forever. X11 syncs with ChromeOS (clipboard skill).
    if os.environ.get("SOMMELIER_VERSION") and os.environ.get("DISPLAY"):
        return {"WAYLAND_DISPLAY": ""}
    return None


def github_token_plaintext(entry: dict[str, Any] | None) -> bool:
    """Report whether gh stored the token in plaintext hosts.yml because no keyring accepted it."""
    # gh reports "keyring", an environment variable name, or the config file path as tokenSource;
    # it falls back to plaintext hosts.yml silently when the system keyring is unavailable.
    source = entry.get("tokenSource") if entry else None
    return isinstance(source, str) and PurePath(source).name == "hosts.yml"


def warn_plaintext_github_token(state: State, entry: dict[str, Any] | None) -> None:
    if github_token_plaintext(entry):
        print(
            f"Warning: the GitHub token is stored in plaintext hosts.yml; {GITHUB_KEYRING_REMEDY} "
            "to move it to the keyring.",
            file=state.stderr,
        )


def gcloud_ready(state: State, args: list[str], provider: str = "gcp") -> bool:
    result = probe(state, args)
    if result.returncode == 0 and result.stdout.strip():
        return True
    # Never render access tokens or raw provider diagnostics.
    if result.returncode and any(marker in result.stderr.lower() for marker in GCLOUD_LOGIN_MARKERS):
        return False
    raise unknown(provider)


def adc_probe_command(state: State) -> list[str]:
    scopes = ",".join(state.config.auth.gcp.adc_scopes)
    return ["gcloud", "auth", "application-default", "print-access-token", f"--scopes={scopes}"]


def adc_ready(state: State, provider: str = "gcp") -> bool:
    """Refresh ADC for the configured scopes; Google rejects scopes outside the stored grant."""
    return gcloud_ready(state, adc_probe_command(state), provider)


def adc_login_command(state: State) -> list[str]:
    return ["gcloud", "auth", "application-default", "login", f"--scopes={','.join(state.config.auth.gcp.adc_scopes)}"]


def login_gcp(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    # Separate logins keep the configured ADC grant: `gcloud auth login --update-adc` would replace
    # it with gcloud's defaults and silently drop scopes such as Colab's.
    cli = ["gcloud", "auth", "login"]
    adc = adc_login_command(state)
    if dry_run:
        execute(state, cli, dry_run=True)
        execute(state, adc, dry_run=True)
        return
    cli_ready = not force and gcloud_ready(state, GCLOUD_CLI_TOKEN)
    adc_current = not force and adc_ready(state)
    if cli_ready and adc_current:
        print("Google Cloud CLI and ADC already provide usable credentials.", file=state.stderr)
        return
    if (
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or os.environ.get("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE")
        or os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN")
    ):
        raise DotError(
            "external credentials override Google Cloud or ADC; repair or unset the override before OAuth login"
        )
    if not cli_ready:
        change(state, cli)
    if not adc_current:
        change(state, adc)
    if not (gcloud_ready(state, GCLOUD_CLI_TOKEN) and adc_ready(state)):
        raise DotError(
            "Google Cloud login did not provide usable CLI and ADC credentials; inspect gcloud auth and retry"
        )


def colab_ready(state: State) -> bool:
    result = probe(state, COLAB_SESSIONS)
    diagnostic = f"{result.stdout}\n{result.stderr}".lower()
    # Colab 0.7.4 catches an ADC SystemExit and can report an empty listing
    # with exit 0. Authentication diagnostics take precedence over that listing.
    if any(
        marker in diagnostic
        for marker in (
            "no valid default credentials found",
            "defaultcredentialserror",
            "invalid_grant",
            "access_token_scope_insufficient",
            "insufficient authentication scopes",
        )
    ):
        return False
    if result.returncode == 0 and result.stdout.strip():
        return True
    raise DotError(
        "Colab session access could not be verified; inspect colab --auth=adc sessions and retry dot login colab"
    )


def login_colab(state: State, *, force: bool = False, dry_run: bool = False) -> None:
    missing = [scope for scope in _COLAB_ADC_SCOPES if scope not in state.config.auth.gcp.adc_scopes]
    if missing:
        raise DotError(f"auth.gcp.adc_scopes must include the Colab scopes: {', '.join(missing)}")
    args = adc_login_command(state)
    if dry_run:
        execute(state, args, dry_run=True)
        execute(state, COLAB_SESSIONS, dry_run=True)
        return
    require_tools(state, [args, COLAB_SESSIONS])
    # The session backend can accept a token without the RuntimeService scope, so the
    # scoped ADC refresh, not session access, decides whether to skip authorization.
    if not force and adc_ready(state, "colab"):
        print("ADC already grants the configured scopes.", file=state.stderr)
    else:
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            raise DotError(
                "external credentials override Colab ADC; repair or unset GOOGLE_APPLICATION_CREDENTIALS before OAuth login"
            )
        change(state, args)
    if not colab_ready(state):
        raise DotError(
            "Colab login did not provide usable ADC with the required scopes; inspect colab --auth=adc sessions and retry dot login colab --force"
        )
    print("Colab accepts ADC credentials.", file=state.stderr)


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


def workspace_client(state: State, project: str) -> tuple[bool, set[str] | None]:
    """Report whether the OAuth client targets the project, plus its enabled APIs when gws listed them."""
    status = probe_json(state, WORKSPACE_STATUS)
    if not isinstance(status, dict) or type(status.get("client_config_exists")) is not bool:
        raise DotError("Workspace client configuration state is unknown; inspect gws auth status before setup")
    same_project = status.get("project_id") == project
    configured = status["client_config_exists"] and same_project and not status.get("client_config_error")
    # gws queries gcloud live for its own project, which saves a separate services listing.
    apis = status.get("enabled_apis")
    listed = same_project and isinstance(apis, list) and all(isinstance(api, str) for api in apis)
    return configured, set(apis) if listed else None


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
    configured, enabled = workspace_client(state, selected)
    missing = sorted(set(apis) - (enabled if enabled is not None else workspace_apis(state, selected)))
    if missing:
        change(state, ["gcloud", "services", "enable", *missing, "--project", selected, "--quiet"])
        if set(apis) - workspace_apis(state, selected):
            raise DotError("Workspace APIs remain missing after enablement; inspect gcloud services list and retry")
    if not configured:
        change(state, setup)
        if not workspace_client(state, selected)[0]:
            raise DotError("Workspace OAuth client setup is incomplete; inspect gws auth status and retry")
    print(
        "Workspace setup is complete."
        if missing or not configured
        else "Workspace APIs and OAuth client are already configured.",
        file=state.stderr,
    )


CheckLogin = Annotated[
    bool,
    typer.Option("--check", help="Only probe readiness and exit 1 when a login is needed; never opens a login flow"),
]


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
    """Print one readiness line per provider without authenticating; any provider not ready exits 1."""
    if force or dry_run:
        raise typer.BadParameter("--check cannot be combined with --force or --dry-run", param_hint="--check")
    warm_probes(state, providers)
    ready = True
    for provider in providers:
        try:
            verdict = "ready" if provider_ready(state, provider, reconcile=reconcile) else "login needed"
        except DotError as error:
            verdict = f"unknown ({error})"
        ready = ready and verdict == "ready"
        print(f"{provider}: {verdict}", file=state.stdout)
    if not ready:
        print(f"Run {remedy} in a terminal to authenticate.", file=state.stderr)
        raise typer.Exit(1)


def login_machine(state: State, *, force: bool, dry_run: bool, check: bool) -> None:
    """Reconcile the providers auth.login selects, in dependency order, skipping those already ready."""
    providers = [provider for provider in LOGIN_ORDER if provider in state.config.auth.login]
    if check:
        check_logins(state, providers, "dot login", force=force, dry_run=dry_run, reconcile=True)
        return
    project = None
    if "workspace" in providers:
        project = os.environ.get("GWS_PROJECT") or state.config.auth.workspace.project
    # Validate before the browser logins so a bad project ID cannot fail the run at its last step.
    if project:
        try:
            TypeAdapter(Project).validate_python(project)
        except ValidationError as error:
            raise DotError("invalid Workspace project ID; fix GWS_PROJECT or auth.workspace.project") from error
    if not dry_run:
        tools = {"github": ["gh"], "gcp": ["gcloud"], "workspace": ["gws"], "colab": ["gcloud", "colab"]}
        require_tools(state, [[tool] for provider in providers for tool in tools[provider]])
        if not force:
            warm_probes(state, providers)
    for provider in providers:
        if provider == "github":
            login_github(state, reconcile=True, force=force, dry_run=dry_run)
        elif provider == "gcp":
            login_gcp(state, force=force, dry_run=dry_run)
        elif provider == "workspace":
            if project:
                setup_workspace(state, project, dry_run=dry_run)
            else:
                print("Skipping Workspace setup: set GWS_PROJECT or auth.workspace.project.", file=state.stderr)
            login_workspace(state, force=force, dry_run=dry_run)
        else:
            login_colab(state, force=force, dry_run=dry_run)


@login_app.callback()
def login_default(
    context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False
) -> None:
    if context.invoked_subcommand is None:
        login_machine(state_from(context), force=force, dry_run=dry_run, check=check)
    elif force or dry_run or check:
        raise typer.BadParameter("place options after the provider, as in dot login gcp --check")


@login_app.command(
    "workspace",
    help="Authenticate Workspace only when credentials or requested scopes are missing",
    epilog=_LOGIN_EPILOG,
)
def workspace(
    context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False
) -> None:
    state = state_from(context)
    if check:
        check_logins(state, ["workspace"], "dot login workspace", force=force, dry_run=dry_run)
        return
    login_workspace(state, force=force, dry_run=dry_run)


@login_app.command("github", help="Ensure GitHub OAuth authentication and requested scopes", epilog=_LOGIN_EPILOG)
def github(
    context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False
) -> None:
    state = state_from(context)
    if check:
        check_logins(state, ["github"], "dot login github", force=force, dry_run=dry_run)
        return
    login_github(state, force=force, dry_run=dry_run)


@login_app.command("gcp", help="Ensure Google Cloud and ADC both have usable credentials", epilog=_LOGIN_EPILOG)
def gcp(context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False) -> None:
    state = state_from(context)
    if check:
        check_logins(state, ["gcp"], "dot login gcp", force=force, dry_run=dry_run)
        return
    login_gcp(state, force=force, dry_run=dry_run)


@login_app.command("colab", help="Ensure ADC grants the Colab scopes and verify session access", epilog=_LOGIN_EPILOG)
def colab(
    context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False
) -> None:
    state = state_from(context)
    if check:
        check_logins(state, ["colab"], "dot login colab", force=force, dry_run=dry_run)
        return
    login_colab(state, force=force, dry_run=dry_run)


# Kept for existing scripts and habits; a bare `dot login` is the documented form.
@login_app.command("all", hidden=True, help="Same as dot login", epilog=_LOGIN_EPILOG)
def login_all(
    context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False, check: CheckLogin = False
) -> None:
    login_machine(state_from(context), force=force, dry_run=dry_run, check=check)


@setup_app.command("github", help="Ensure requested GitHub scopes and remove configured excluded grants")
def github_setup(context: typer.Context, force: ForceLogin = False, dry_run: DryRun = False) -> None:
    login_github(state_from(context), reconcile=True, force=force, dry_run=dry_run)


@setup_app.command("workspace", help="Enable missing Workspace APIs and configure OAuth for an explicit project")
def workspace_setup(
    context: typer.Context,
    project: Annotated[
        str | None, typer.Argument(envvar="GWS_PROJECT", help="Project ID; overrides auth.workspace.project")
    ] = None,
    dry_run: DryRun = False,
) -> None:
    setup_workspace(state_from(context), project, dry_run=dry_run)
