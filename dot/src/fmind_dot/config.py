"""Strict Python-first configuration for the dot CLI."""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Reject misspelled keys and implicit scalar coercion at the YAML boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


# `~`, `~/...`, or absolute: a relative workspace would resolve against the caller's directory.
WorkspacePath = Annotated[str, Field(pattern=r"^(?:~|~/.+|/.*)$")]
# The keys of archive.parsers.AGENT_ADAPTERS (a test keeps them equal); importing the parsers here would cycle.
LIVE_AGENTS = ("agy", "claude", "copilot", "opencode", "pi")


class CompletionConfig(StrictModel):
    # Completion installs prune unmanaged *.fish files here, so a relative path must never resolve to the cwd.
    path: WorkspacePath = "~/.config/fish/completions"


class PullConfig(StrictModel):
    directories: list[WorkspacePath] = Field(default_factory=lambda: ["~/fmind"])


# GitHub account and organization names: alphanumeric runs joined by single hyphens.
GitHubOwner = Annotated[str, Field(pattern=r"^[A-Za-z0-9](?:-?[A-Za-z0-9])*$", max_length=39)]
# Absolute or `~/` glob over a whole repository path: `*` stays within one segment, `**` spans several.
PathPattern = Annotated[str, Field(pattern=r"^(?:~/|/)\S")]


class TrustConfig(StrictModel):
    # `dot trust all` trusts a workspace repository only when its origin is a
    # github.com repository of one of these owners (compared case-insensitively).
    github_owners: list[GitHubOwner] = Field(default_factory=lambda: ["fmind"])
    # Trusted repositories that `dot trust` adds to agy's Remote Control project picker;
    # other repositories are curated per machine in `~/.gemini/config/projects/`.
    agy_projects: list[PathPattern] = Field(default_factory=lambda: ["~/.local/share/chezmoi"])


TokenPrice = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class ModelPrice(StrictModel):
    input: TokenPrice
    output: TokenPrice
    cache_read: TokenPrice | None = None
    # Model-default cache writes (Claude: 5-minute TTL); Claude prices 1-hour writes separately.
    cache_write: TokenPrice | None = None
    cache_write_1h: TokenPrice | None = None


class PricingConfig(StrictModel):
    as_of: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    sources: list[str]
    models: dict[str, ModelPrice]


@functools.cache
def _parsed_default_pricing() -> PricingConfig:
    return PricingConfig.model_validate(
        yaml.safe_load(Path(__file__).with_name("api-prices.yaml").read_text(encoding="utf-8"))
    )


def default_pricing() -> PricingConfig:
    return _parsed_default_pricing().model_copy(deep=True)


class NotifyConfig(StrictModel):
    """Turn notifications: every field defaults on and turns one part off."""

    # Play a short chime: macOS uses a system sound; Linux plays dot's chime with pw-play or paplay.
    sound: bool = True
    # Inside Zellij, name the session and tab that ran the harness.
    tab: bool = True
    # Inside Zellij, show the pane title the harness sets, such as Claude Code's session topic.
    title: bool = True


class AgentConfig(StrictModel):
    sources: dict[str, WorkspacePath] = Field(
        default_factory=lambda: {
            "agy": "~/.gemini/antigravity-cli/brain",
            "claude": "~/.claude/projects",
            "copilot": "~/.copilot/session-store.db",
            "opencode": "~/.local/share/opencode/opencode.db",
            "pi": "~/.pi/agent/sessions",
        }
    )
    pricing: PricingConfig = Field(default_factory=default_pricing)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)

    @field_validator("sources")
    @classmethod
    def _live_agents_only(cls, sources: dict[str, str]) -> dict[str, str]:
        # A retired harness (codex, grok) or a typo would otherwise be ignored silently.
        if unknown := sorted(set(sources) - set(LIVE_AGENTS)):
            msg = f"unknown agent {', '.join(unknown)}; expected one of {', '.join(LIVE_AGENTS)}"
            raise ValueError(msg)
        return sources


class SecretConfig(StrictModel):
    path: WorkspacePath


class DoctorConfig(StrictModel):
    tools: list[str] = Field(
        default_factory=lambda: [
            "age",
            "agy",
            "betterleaks",
            "bf",
            "chezmoi",
            "claude",
            "copilot",
            "dprint",
            "file",
            "gcloud",
            "gh",
            "git",
            "git-cliff",
            "gws",
            "lefthook",
            "mise",
            "nvim",
            "opencode",
            "pgcli",
            "pi",
            "python",
            "ruff",
            "sqlite3",
            "tree-sitter",
            "trivy",
            "ty",
            "uv",
        ]
    )
    # Each secret must exist with owner-only permissions (0600 or stricter).
    secrets: list[SecretConfig] = Field(
        default_factory=lambda: [
            SecretConfig(path="~/.config/chezmoi/key.txt"),
            SecretConfig(path="~/.ssh/id_ed25519_signing"),
        ]
    )


# Policy values are data; native command arguments and safety boundaries stay in code.
Scope = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_:/.-]*$")]
Project = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
CacheProvider = Literal["docker", "hf", "uv"]
LoginProvider = Literal["colab", "gcp", "github", "workspace"]
PruneProvider = Literal["docker", "dprint", "hf", "mise", "npm", "trivy", "uv"]


class GitHubConfig(StrictModel):
    # Keys and packages stay read-only by default; writes (`--grant write:public_key`) are removed
    # on `dot setup github` so a leaked token cannot plant SSH keys or overwrite published images.
    # `gist` stays because `gh` always requests its minimum scopes (repo, read:org, gist).
    scopes: list[Scope] = Field(
        default_factory=lambda: [
            "gist",
            "notifications",
            "project",
            "read:audit_log",
            "read:gpg_key",
            "read:org",
            "read:packages",
            "read:public_key",
            "read:ssh_signing_key",
            "repo",
            "user",
            "workflow",
        ]
    )
    remove_scopes: list[Scope] = Field(
        default_factory=lambda: [
            "admin:gpg_key",
            "admin:org",
            "admin:org_hook",
            "admin:public_key",
            "admin:ssh_signing_key",
            "codespace",
            "delete:packages",
            "delete_repo",
            "write:gpg_key",
            "write:org",
            "write:packages",
            "write:public_key",
            "write:ssh_signing_key",
        ]
    )

    @model_validator(mode="after")
    def distinct_scopes(self) -> GitHubConfig:
        if set(self.scopes) & set(self.remove_scopes):
            raise ValueError("GitHub scopes and remove_scopes must not overlap")
        return self


# Google's consent page hangs after Allow when one request holds more scopes (bisected 2026-10-26).
WORKSPACE_SCOPE_LIMIT = 50


class WorkspaceConfig(StrictModel):
    project: Project | None = None
    # gws replaces its whole grant on login, so this list owns every consumer's scope (daily user
    # writes plus read-only sensor/CLI scopes). Cap defaults at 48 to leave two `--grant` slots
    # below Google's 50-scope consent-page hang (WORKSPACE_SCOPE_LIMIT).
    scopes: list[Scope] = Field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/admin.directory.customer.readonly",
            "https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly",
            "https://www.googleapis.com/auth/admin.directory.device.mobile.readonly",
            "https://www.googleapis.com/auth/admin.directory.domain.readonly",
            "https://www.googleapis.com/auth/admin.directory.group.readonly",
            "https://www.googleapis.com/auth/admin.directory.orgunit.readonly",
            "https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly",
            "https://www.googleapis.com/auth/admin.directory.user.readonly",
            "https://www.googleapis.com/auth/admin.reports.audit.readonly",
            "https://www.googleapis.com/auth/admin.reports.usage.readonly",
            "https://www.googleapis.com/auth/analytics.edit",
            "https://www.googleapis.com/auth/analytics.manage.users",
            "https://www.googleapis.com/auth/analytics.manage.users.readonly",
            "https://www.googleapis.com/auth/analytics.readonly",
            "https://www.googleapis.com/auth/business.manage",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/chat.messages",
            "https://www.googleapis.com/auth/chat.messages.readonly",
            "https://www.googleapis.com/auth/chat.spaces",
            "https://www.googleapis.com/auth/chat.spaces.readonly",
            "https://www.googleapis.com/auth/chrome.management.policy.readonly",
            "https://www.googleapis.com/auth/chrome.management.reports.readonly",
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/contacts.other.readonly",
            "https://www.googleapis.com/auth/contacts.readonly",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/documents.readonly",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/forms.body",
            "https://www.googleapis.com/auth/forms.responses.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.settings.basic",
            "https://www.googleapis.com/auth/meetings.space.readonly",
            "https://www.googleapis.com/auth/postmaster.traffic.readonly",
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/script.projects",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/tasks",
            "https://www.googleapis.com/auth/tasks.readonly",
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
        ],
        min_length=1,
        max_length=WORKSPACE_SCOPE_LIMIT,
    )
    apis: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*\.googleapis\.com$")]] = Field(
        default_factory=lambda: [
            "admin.googleapis.com",
            "analyticsadmin.googleapis.com",
            "analyticsdata.googleapis.com",
            "businessprofileperformance.googleapis.com",
            "calendar-json.googleapis.com",
            "chat.googleapis.com",
            "chromemanagement.googleapis.com",
            "chromepolicy.googleapis.com",
            "cloudsupport.googleapis.com",
            "docs.googleapis.com",
            "drive.googleapis.com",
            "driveactivity.googleapis.com",
            # The brain's Firebase reader calls these through ADC, which bills this quota project.
            "firebase.googleapis.com",
            "firebaseappcheck.googleapis.com",
            "firebasehosting.googleapis.com",
            "firebaserules.googleapis.com",
            "forms.googleapis.com",
            "gmail.googleapis.com",
            "gmailpostmastertools.googleapis.com",
            "meet.googleapis.com",
            "mybusinessaccountmanagement.googleapis.com",
            "mybusinessbusinessinformation.googleapis.com",
            "pagespeedonline.googleapis.com",
            "people.googleapis.com",
            "script.googleapis.com",
            "searchconsole.googleapis.com",
            "sheets.googleapis.com",
            "slides.googleapis.com",
            "tasks.googleapis.com",
            "youtube.googleapis.com",
            "youtubeanalytics.googleapis.com",
        ],
        min_length=1,
    )


class GcpConfig(StrictModel):
    # ADC login replaces its whole grant: keep gcloud defaults, Colab (`dot login colab`), and
    # read-only BigQuery/Logging/Cloud Platform sensor scopes together.
    adc_scopes: list[Scope] = Field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/sqlservice.login",
            "https://www.googleapis.com/auth/colaboratory",
            "https://www.googleapis.com/auth/bigquery.readonly",
            "https://www.googleapis.com/auth/logging.read",
            "https://www.googleapis.com/auth/cloud-platform.read-only",
        ],
        min_length=1,
    )


class AuthConfig(StrictModel):
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    gcp: GcpConfig = Field(default_factory=GcpConfig)
    # Providers that a bare `dot login` reconciles on this machine; credential lifetimes differ per
    # machine and account policy, so each machine lists only the providers it uses.
    login: Annotated[list[LoginProvider], Field(min_length=1)] = ["github", "gcp", "workspace"]


class PrivacyConfig(StrictModel):
    # Already-public names the repository privacy check accepts on this machine; the list stays
    # in this untracked file so the repository never names the host or employer it exempts.
    allowed_tokens: list[str] = Field(default_factory=list)


class CacheConfig(StrictModel):
    providers: Annotated[list[CacheProvider], Field(min_length=1)] = ["docker", "hf", "uv"]


class PruneConfig(StrictModel):
    providers: Annotated[list[PruneProvider], Field(min_length=1)] = ["dprint", "hf", "mise", "npm", "trivy", "uv"]


class Config(StrictModel):
    schema_version: Literal[3] = 3
    auth: AuthConfig = Field(default_factory=AuthConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    prune: PruneConfig = Field(default_factory=PruneConfig)
    completions: CompletionConfig = Field(default_factory=CompletionConfig)
    pull: PullConfig = Field(default_factory=PullConfig)
    trust: TrustConfig = Field(default_factory=TrustConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    doctor: DoctorConfig = Field(default_factory=DoctorConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)


def expand_path(value: str | Path, *, home: Path | None = None) -> Path:
    text = os.fspath(value)
    if text == "~":
        return home or Path.home()
    if text.startswith("~/"):
        return (home or Path.home()) / text[2:]
    return Path(text)


def env_path(name: str, default: Path, *, expand_vars: bool = True) -> Path:
    """Resolve an environment path override, expanding `~/` and optional `$VARS`."""
    if raw := os.environ.get(name):
        return expand_path(os.path.expandvars(raw) if expand_vars else raw)
    return default


def xdg_dir(name: str, default: str | Path) -> Path:
    """Resolve an XDG base-directory override; empty or relative values fall back to `default`."""
    if raw := os.environ.get(name):
        candidate = expand_path(os.path.expandvars(raw))
        if candidate.is_absolute():
            return candidate
    return default if isinstance(default, Path) else Path.home() / default


def config_file_path(path: str | Path | None) -> tuple[Path, bool]:
    if path is None or os.fspath(path) == "":
        return Path.home() / ".config/dot.yaml", True
    return expand_path(path), False


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def yaml_error_location(error: BaseException) -> str:
    mark = getattr(error, "problem_mark", None)
    return f"line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""


def load_config(path: str | Path | None = None) -> Config:
    resolved, implicit = config_file_path(path)
    try:
        with resolved.open(encoding="utf-8") as stream:
            documents = list(yaml.safe_load_all(stream))
    except FileNotFoundError as error:
        if implicit:
            return Config()
        raise FileNotFoundError(f"failed to read config file at {resolved}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"failed to read config file at {resolved}: {error}") from error
    except (yaml.YAMLError, RecursionError) as error:
        where = yaml_error_location(error)
        location = f" at {where}" if where else ""
        # Parser messages and snippets can include credentials from malformed input.
        raise ValueError(f"failed to parse config file at {resolved}: invalid YAML{location}") from error
    if len(documents) > 1:
        raise ValueError(f"config file at {resolved} must contain exactly one YAML document")
    overlay = documents[0] if documents else {}
    if overlay is None:
        overlay = {}
    if not isinstance(overlay, dict):
        raise ValueError(f"config file at {resolved} must contain a YAML mapping")
    if not overlay:
        return Config()
    defaults = Config().model_dump(mode="python")
    try:
        return Config.model_validate(_deep_merge(defaults, overlay))
    except RecursionError as error:
        raise ValueError(f"failed to parse config file at {resolved}: YAML nesting is too deep") from error


def dump_config(config: Config) -> str:
    return yaml.safe_dump(config.model_dump(mode="python"), allow_unicode=True, sort_keys=False)
