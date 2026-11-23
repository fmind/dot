"""Readiness probes and status parsing across GitHub, Google Cloud, and Workspace."""

from __future__ import annotations

import json
import os
import re
import shlex
import stat
import sys
from collections.abc import Callable, Collection, Iterable, Sequence
from pathlib import Path, PurePath
from typing import Any

from fmind_dot.config import (
    GCP_ADC_SCOPES,
    GITHUB_FORBIDDEN_SCOPES,
    GITHUB_REMOVE_SCOPES,
    GITHUB_SCOPES,
    SCOPE_RE,
    WORKSPACE_FORBIDDEN_SCOPES,
    env_path,
    expand_google_scope,
    policy,
)
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import CommandResult
from fmind_dot.state import State, require_tools

GITHUB_HOST = "github.com"
GCLOUD_CLI_TOKEN = ["gcloud", "auth", "print-access-token"]
GCLOUD_ACTIVE_ACCOUNT = ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]
GCE_DMI_PRODUCT_PATH = Path("/sys/class/dmi/id/product_name")
GITHUB_STATUS = ["gh", "auth", "status", "--active", "--hostname", GITHUB_HOST, "--json", "hosts"]
WORKSPACE_STATUS = ["gws", "auth", "status"]
PROBE_TIMEOUT_SECONDS = 45.0


def adc_cmd(verb: str) -> list[str]:
    """Return the gcloud application-default command with configured ADC scopes."""
    return ["gcloud", "auth", "application-default", verb, f"--scopes={','.join(GCP_ADC_SCOPES)}"]


def _stream_isatty(stream: object) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError, ValueError:
        return False


def require_tty(state: State, tool: str) -> None:
    """Fail closed before mutating state when interactive authentication lacks a terminal."""
    if state.runner.requires_tty and not (_stream_isatty(state.stdin) and _stream_isatty(state.stdout)):
        raise DotError(
            f"interactive authentication for {tool} requires a terminal (TTY); run in a terminal or use --check / --dry-run"
        )


def execute(state: State, args: Sequence[str], *, open_url: re.Pattern[str] | None = None) -> None:
    """Run an interactive auth command and invalidate cached readiness probes."""
    require_tools(state, [list(args)])
    require_tty(state, args[0])
    try:
        code = state.runner.interactive(
            args, stdin=state.stdin, stdout=state.stdout, stderr=state.stderr, open_url=open_url
        )
        if code != 0:
            raise DotError(f"command failed ({code}): {args[0]}")
    finally:
        state.clear_probes()


def dry_run_cmds(state: State, *commands: Sequence[str]) -> None:
    """Print shell-quoted dry-run commands to stdout."""
    for args in commands:
        state.stdout.write(f"$ {shlex.join(args)}\n")


def probe(state: State, args: list[str], timeout: float = PROBE_TIMEOUT_SECONDS) -> CommandResult:
    """Run a readiness probe once per invocation; logins clear the reused results."""
    return state.run_probe(
        tuple(args), lambda: (require_tools(state, [args]), state.runner.run(args, timeout=timeout, check=False))[1]
    )


def probe_json(state: State, args: list[str], timeout: float = PROBE_TIMEOUT_SECONDS) -> object:
    """Run a probe returning JSON output and raise an actionable DotError on failure."""
    result = probe(state, args, timeout)
    if result.returncode:
        raise DotError(f"{args[0]} status failed (exit {result.returncode}); inspect the provider directly and retry")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise DotError(f"{args[0]} returned invalid status JSON; inspect the provider directly and retry") from error


def unknown_provider(provider: str) -> DotError:
    """Return a consistent unknown-authentication error for a provider."""
    return DotError(
        f"{provider} authentication state is unknown; inspect native auth status or use dot login {provider} --force"
    )


def reject_env(names: Sequence[str], message: str) -> None:
    """Fail when an overriding credential environment variable is active."""
    if any(os.environ.get(n) for n in names):
        raise DotError(message)


def workspace_token_valid(status: object) -> bool | None:
    """Return whether parsed `gws auth status` JSON reports a valid token."""
    if not isinstance(status, dict):
        return None
    if status.get("auth_method") == "none" or status.get("token_valid") is False:
        return False
    return True if status.get("token_valid") is True else None


def one_off_scopes(
    grants: Sequence[str],
    configured: Sequence[str],
    *,
    expand: Callable[[str], str] | None = None,
    validate: Callable[[str], bool] | None = None,
    forbidden: Collection[str] = (),
) -> list[str]:
    """Validate and deduplicate one-off `--grant` scopes against configured defaults."""
    forbidden_lower = {f.lower() for f in forbidden}
    scopes: list[str] = []
    for grant in grants:
        if not SCOPE_RE.fullmatch(grant):
            raise UsageError(f"--grant: invalid scope {grant!r}")
        scope = expand(grant) if expand else grant
        valid = validate(scope) if validate else bool(SCOPE_RE.fullmatch(scope))
        if not valid:
            raise UsageError(f"--grant: invalid scope {grant!r}")
        if scope.lower() in forbidden_lower:
            raise UsageError(f"--grant: scope {grant!r} is forbidden by security policy")
        if scope not in configured and scope not in scopes:
            scopes.append(scope)
    return scopes


def norm_google(scopes: Iterable[str]) -> set[str]:
    """Normalize Google OAuth short alias names and URLs to canonical identifiers."""
    return {expand_google_scope(s) for s in scopes}


def workspace_granted(state: State) -> set[str] | None:
    """Return granted Google Workspace OAuth scopes or None when logged out."""
    status = probe_json(state, WORKSPACE_STATUS)
    if workspace_token_valid(status) is False:
        return None
    scopes = status.get("scopes") if workspace_token_valid(status) and isinstance(status, dict) else None
    if not isinstance(scopes, list) or not all(isinstance(s, str) for s in scopes):
        raise unknown_provider("workspace")
    return norm_google(scopes)


def workspace_ready(state: State, grants: Sequence[str] = ()) -> bool:
    """Return True when Workspace auth holds all configured plus requested scopes and no forbidden scopes."""
    granted = workspace_granted(state)
    return (
        granted is not None
        and not ({s.lower() for s in granted} & WORKSPACE_FORBIDDEN_SCOPES)
        and norm_google([*state.config.auth.workspace.scopes, *grants]) <= granted
    )


def github_entry(status: object) -> dict[str, Any] | None:
    """Extract the active GitHub CLI auth entry from `gh auth status --json` output."""
    if not isinstance(status, dict) or not isinstance(status.get("hosts"), dict):
        raise unknown_provider("github")
    entries = status["hosts"].get(GITHUB_HOST, [])
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise unknown_provider("github")
    if not entries:
        return None
    active = [e for e in entries if e.get("active") is True]
    if len(active) != 1:
        raise unknown_provider("github")
    entry = active[0]
    if entry.get("state") == "success":
        return entry
    if entry.get("state") == "error" and any(
        m in str(entry.get("error", "")).lower() for m in ("token is invalid", "(http 401)", "401 unauthorized")
    ):
        return None
    raise unknown_provider("github")


def github_status(state: State) -> dict[str, Any] | None:
    """Probe and return the active GitHub host auth record."""
    return github_entry(probe_json(state, GITHUB_STATUS))


def github_ready(entry: dict[str, Any] | None, *, reconcile: bool, grants: Sequence[str] = ()) -> bool:
    """Return True when GitHub CLI scopes satisfy policy defaults and optional grants."""
    if entry is None:
        return False
    if not isinstance(raw := entry.get("scopes"), str) or not raw:
        raise DotError("GitHub did not report OAuth scopes; inspect gh auth status before changing authentication")
    implied = {k: set(v) for k, v in policy()["github"]["implied"].items()}
    scopes = {s.strip() for s in raw.split(",")}
    granted = scopes | set().union(*(implied.get(s, set()) for s in scopes))
    return (
        {*GITHUB_SCOPES, *grants} <= granted
        and not (GITHUB_FORBIDDEN_SCOPES & granted)
        and (not reconcile or not set(GITHUB_REMOVE_SCOPES) & scopes)
    )


def github_token_plaintext(entry: dict[str, Any] | None) -> bool:
    """Return True when `gh` reports storing the active token in plaintext hosts.yml."""
    source = entry.get("tokenSource") if entry else None
    return isinstance(source, str) and PurePath(source).name == "hosts.yml"


def github_plaintext_headless_ok(entry: dict[str, Any] | None) -> bool:
    """Return True on a headless GCE VM when gh hosts.yml is a regular 0600 file (no Secret Service keyring)."""
    if not (is_gce_vm() and is_headless_ssh()) or not entry:
        return False
    source = entry.get("tokenSource")
    if not isinstance(source, str):
        return False
    try:
        info = Path(source).lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and (stat.S_IMODE(info.st_mode) & ~0o600 == 0)


def warn_plaintext(state: State, entry: dict[str, Any] | None) -> None:
    """Warn on stderr if GitHub CLI stores its token in plaintext hosts.yml."""
    if github_token_plaintext(entry) and not github_plaintext_headless_ok(entry):
        msg = "Warning: the GitHub token is stored in plaintext hosts.yml; unlock the system keyring, then run gh auth logout and dot login github to move it to the keyring."
        print(msg, file=state.stderr)


def is_gce_vm() -> bool:
    """Return True when running inside a Google Compute Engine VM."""
    try:
        return b"google compute engine" in GCE_DMI_PRODUCT_PATH.read_bytes().strip().lower()
    except OSError:
        return False


def is_headless_ssh() -> bool:
    """Return True when no desktop browser can receive OAuth callbacks (SSH or headless Linux)."""
    if os.environ.get("SSH_TTY") or os.environ.get("SSH_CONNECTION"):
        return True
    return sys.platform == "linux" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _active_gcloud_is_service_account(state: State, provider: str = "gcp") -> bool:
    """Return True when gcloud's active account is a GCE metadata service account rather than a user login."""
    if (
        not is_gce_vm()
        or os.environ.get("CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE")
        or os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN")
    ):
        return False
    result = probe(state, GCLOUD_ACTIVE_ACCOUNT)
    if result.returncode != 0:
        raise unknown_provider(provider)
    account = result.stdout.strip().lower()
    return bool(account) and account.endswith(".gserviceaccount.com")


def gcloud_ready(state: State, args: list[str], provider: str = "gcp") -> bool:
    """Return True when a gcloud access-token probe succeeds for a non-metadata user account."""
    result = probe(state, args)
    if result.returncode == 0 and result.stdout.strip():
        return not (args == GCLOUD_CLI_TOKEN and _active_gcloud_is_service_account(state, provider))
    if result.returncode and any(m in result.stderr.lower() for m in policy()["gcp"]["login_markers"]):
        return False
    raise unknown_provider(provider)


def adc_ready(state: State, provider: str = "gcp") -> bool:
    """Return True when Application Default Credentials hold configured GCP scopes (ignoring GCE metadata SA fallback)."""
    if is_gce_vm() and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        gcloud_dir = env_path("CLOUDSDK_CONFIG", Path.home() / ".config" / "gcloud")
        adc_file = gcloud_dir / "application_default_credentials.json"
        if not adc_file.is_file():
            return False
    return gcloud_ready(state, adc_cmd("print-access-token"), provider)
