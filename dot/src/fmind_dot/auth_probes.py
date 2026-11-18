"""Readiness probes and status parsing across GitHub, Google Cloud, Workspace, and Colab."""

from __future__ import annotations

import json
import os
import re
import shlex
from collections.abc import Callable, Collection, Iterable, Sequence
from pathlib import PurePath
from typing import Any

from fmind_dot.config import (
    GCP_ADC_SCOPES,
    GITHUB_FORBIDDEN_SCOPES,
    GITHUB_REMOVE_SCOPES,
    GITHUB_SCOPES,
    SCOPE_RE,
    WORKSPACE_FORBIDDEN_SCOPES,
    expand_google_scope,
    policy,
)
from fmind_dot.errors import DotError, UsageError
from fmind_dot.process import CommandResult
from fmind_dot.state import State, require_tools

GITHUB_HOST = "github.com"
GCLOUD_CLI_TOKEN = ["gcloud", "auth", "print-access-token"]
GITHUB_STATUS = ["gh", "auth", "status", "--active", "--hostname", GITHUB_HOST, "--json", "hosts"]
WORKSPACE_STATUS = ["gws", "auth", "status"]
COLAB_SESSIONS = ["colab", "--auth=adc", "sessions"]
PROBE_TIMEOUT_SECONDS = 45.0
_COLAB_MARKERS = (
    "no valid default credentials found",
    "defaultcredentialserror",
    "invalid_grant",
    "access_token_scope_insufficient",
    "insufficient authentication scopes",
)


def adc_cmd(verb: str) -> list[str]:
    """Return the gcloud application-default command with configured ADC scopes."""
    return ["gcloud", "auth", "application-default", verb, f"--scopes={','.join(GCP_ADC_SCOPES)}"]


def execute(state: State, args: Sequence[str], *, open_url: re.Pattern[str] | None = None) -> None:
    """Run an interactive auth command and invalidate cached readiness probes."""
    require_tools(state, [list(args)])
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
    markers: Sequence[str] = policy()["gcp"]["login_markers"]
    if result.returncode and args[0] == "gcloud" and any(m in result.stderr.lower() for m in markers):
        raise DotError("gcloud credentials need a fresh login; run dot login gcp and retry")
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
    forbidden: Collection[str] = (),
) -> list[str]:
    """Validate and deduplicate one-off `--grant` scopes against configured defaults."""
    forbidden_lower = {f.lower() for f in forbidden}
    scopes: list[str] = []
    for grant in grants:
        scope = expand(grant) if expand else grant
        if not SCOPE_RE.fullmatch(scope):
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


def github_ready(state: State, entry: dict[str, Any] | None, *, reconcile: bool, grants: Sequence[str] = ()) -> bool:
    """Return True when GitHub CLI scopes satisfy policy defaults and optional grants."""
    del state
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


def warn_plaintext(state: State, entry: dict[str, Any] | None) -> None:
    """Warn on stderr if GitHub CLI stores its token in plaintext hosts.yml."""
    if github_token_plaintext(entry):
        msg = "Warning: the GitHub token is stored in plaintext hosts.yml; unlock the system keyring, then run gh auth logout and dot login github to move it to the keyring."
        print(msg, file=state.stderr)


def gcloud_ready(state: State, args: list[str], provider: str = "gcp") -> bool:
    """Return True when a gcloud access-token probe succeeds with non-empty stdout."""
    result = probe(state, args)
    if result.returncode == 0 and result.stdout.strip():
        return True
    if result.returncode and any(m in result.stderr.lower() for m in policy()["gcp"]["login_markers"]):
        return False
    raise unknown_provider(provider)


def adc_ready(state: State, provider: str = "gcp") -> bool:
    """Return True when Application Default Credentials hold configured GCP scopes."""
    return gcloud_ready(state, adc_cmd("print-access-token"), provider)


def colab_ready(state: State) -> bool:
    """Verify Google Colab CLI can open sessions via ADC."""
    result = probe(state, COLAB_SESSIONS)
    if any(m in f"{result.stdout}\n{result.stderr}".lower() for m in _COLAB_MARKERS):
        return False
    if result.returncode == 0 and result.stdout.strip():
        return True
    msg = "Colab session access could not be verified; inspect colab --auth=adc sessions and retry dot login colab"
    raise DotError(msg)
