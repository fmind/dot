"""Strict Python-first configuration for the dot CLI."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Reject misspelled keys and implicit scalar coercion at the YAML boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


@dataclass(frozen=True)
class ToolConfig:
    """One Fish completion source: a native generator command or a mise package's bundled script."""

    binary: str = ""
    args: tuple[str, ...] = ()
    package: str = ""


# Every entry is generated; unlisted fields fall back to `<tool> completion fish`.
COMPLETION_SOURCES: dict[str, ToolConfig] = {
    "a2a": ToolConfig(),
    "ast-grep": ToolConfig(args=("completions", "fish")),
    "astro": ToolConfig(),
    "atuin": ToolConfig(args=("gen-completions", "--shell", "fish")),
    "aws-sso-util": ToolConfig(binary="env", args=("_AWS_SSO_UTIL_COMPLETE=fish_source", "aws-sso-util")),
    "bat": ToolConfig(args=("--completion", "fish")),
    "bf": ToolConfig(binary="env", args=("_BF_COMPLETE=source_fish", "bf")),
    "cf": ToolConfig(args=("complete", "fish")),
    "chezmoi": ToolConfig(),
    "colab": ToolConfig(binary="env", args=("_COLAB_COMPLETE=source_fish", "colab")),
    "copilot": ToolConfig(),
    "databricks": ToolConfig(),
    "delta": ToolConfig(args=("--generate-completion", "fish")),
    "doggo": ToolConfig(args=("completions", "fish")),
    # Rendered in-process from Click; the installed dot may be older than this checkout.
    "dot": ToolConfig(),
    "dprint": ToolConfig(args=("completions", "fish")),
    "fastfetch": ToolConfig(package="github:fastfetch-cli/fastfetch"),
    "fd": ToolConfig(args=("--gen-completions", "fish")),
    "gh": ToolConfig(args=("completion", "-s", "fish")),
    "git-cliff": ToolConfig(package="git-cliff"),
    "git-lfs": ToolConfig(binary="git", args=("lfs", "completion", "fish")),
    "gitleaks": ToolConfig(),
    "hf": ToolConfig(binary="env", args=("_HF_COMPLETE=fish_source", "hf")),
    "hyperfine": ToolConfig(package="hyperfine"),
    "lazygit": ToolConfig(args=("completion", "fish")),
    "lefthook": ToolConfig(),
    "lsd": ToolConfig(package="lsd"),
    "lychee": ToolConfig(args=("--generate", "complete-fish")),
    "mise": ToolConfig(),
    "pup": ToolConfig(args=("completions", "fish")),
    "rg": ToolConfig(args=("--generate", "complete-fish")),
    "ruff": ToolConfig(args=("generate-shell-completion", "fish")),
    "starship": ToolConfig(args=("completions", "fish")),
    "tree-sitter": ToolConfig(args=("complete", "--shell", "fish")),
    "trivy": ToolConfig(),
    "ty": ToolConfig(args=("generate-shell-completion", "fish")),
    "usage": ToolConfig(args=("--completions", "fish")),
    "uv": ToolConfig(args=("generate-shell-completion", "fish")),
    "uvx": ToolConfig(args=("--generate-shell-completion", "fish")),
    "xh": ToolConfig(args=("--generate", "complete-fish")),
    "ya": ToolConfig(package="yazi"),
    "yazi": ToolConfig(package="yazi"),
    "yq": ToolConfig(args=("shell-completion", "fish")),
    "zellij": ToolConfig(args=("setup", "--generate-completion", "fish")),
    "zizmor": ToolConfig(args=("--completions", "fish")),
    "zoxide": ToolConfig(package="zoxide"),
}
# Static completion scripts deployed by chezmoi in dot_config/fish/completions/.
MANAGED_COMPLETIONS: frozenset[str] = frozenset({"agy.fish"})


class CompletionConfig(StrictModel):
    path: str = "~/.config/fish/completions"


# `~`, `~/...`, or absolute: a relative workspace would resolve against the caller's directory.
WorkspacePath = Annotated[str, Field(pattern=r"^(?:~|~/.+|/.*)$")]


class PullConfig(StrictModel):
    # dot_claude/modify_private_settings.json repeats this default; test_harness_config keeps them equal.
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


def default_pricing() -> PricingConfig:
    return PricingConfig.model_validate(yaml.safe_load(Path(__file__).with_name("api-prices.yaml").read_text()))


class NotifyConfig(StrictModel):
    """Turn notifications: every field defaults on and turns one part off."""

    # Play a short chime: macOS uses a system sound; Linux plays dot's chime with pw-play or paplay.
    sound: bool = True
    # Inside Zellij, name the session and tab that ran the harness.
    tab: bool = True
    # Inside Zellij, show the pane title the harness sets, such as Claude Code's session topic.
    title: bool = True


class AgentConfig(StrictModel):
    sources: dict[str, str] = Field(
        default_factory=lambda: {
            "agy": "~/.gemini/antigravity-cli/brain",
            "claude": "~/.claude/projects",
            "copilot": "~/.copilot/session-store.db",
            "opencode": "~/.local/share/opencode/opencode.db",
        }
    )
    pricing: PricingConfig = Field(default_factory=default_pricing)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)


class SecretConfig(StrictModel):
    path: str


class DoctorConfig(StrictModel):
    tools: list[str] = Field(
        default_factory=lambda: [
            "age",
            "agy",
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
            "gitleaks",
            "gws",
            "lefthook",
            "mise",
            "nvim",
            "opencode",
            "pgcli",
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
    # Defaults grant everything except key, package, org and enterprise administration and deletion
    # (https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps).
    # Keys and packages stay readable so security reviews can spot planted keys or images; writing
    # them is a one-off grant (`dot login github --grant write:public_key`) that the next
    # `dot setup github` removes, because a stolen token could otherwise add a persistent SSH key
    # or replace a public image that CI publishes with its own token. gh always requests its minimum
    # scopes (repo, read:org, gist) and cannot remove them, so gist stays listed. The
    # dot-cli authentication guide lists the possible and refused one-off grants.
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
    # gws replaces its whole grant on login, so this list is the single owner of every scope
    # borrowed from it: the read-only analytics, Search Console, YouTube, Workspace and audit
    # scopes that brain sensors narrow their tokens to, the read-only Admin and Chrome management
    # scopes the brain's google CLI reads with, and the Analytics, Search Console and Business
    # Profile management scopes it narrows its explicit writes to; dropping one breaks those
    # consumers on the next login. Google's consent page hangs after Allow above 50 scopes (logins
    # of 45, 47 and 50 completed; 52 and more hung, bisected 2026-10-26), and one-off grants share
    # that consent, so defaults stop at 48 to leave two one-off slots. They hold the everyday
    # user-level writes and only the read-only scopes a consumer narrows its token to, since a write
    # scope already allows reads. Everything else is a one-off grant (`dot login workspace --grant
    # SCOPE`) that the dot-cli authentication guide lists
    # (https://developers.google.com/identity/protocols/oauth2/scopes).
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
            "https://www.googleapis.com/auth/postmaster.readonly",
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
    # ADC login replaces its whole grant, so this list owns every ADC consumer's scope: gcloud's
    # default ADC scopes plus Colab's and the read-only scopes the brain's sensors narrow their
    # tokens to (BigQuery for analytics and costs; Logging and read-only Cloud Platform for the
    # error collector's log reads and project listing). `dot login colab` requires the Colab
    # scopes to stay listed.
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


def expand_path(value: str | Path) -> Path:
    text = os.fspath(value)
    if text == "~":
        return Path.home()
    if text.startswith("~/"):
        return Path.home() / text[2:]
    return Path(text)


def config_file_path(path: str | Path | None) -> tuple[Path, bool]:
    if path is None or os.fspath(path) == "":
        return Path.home() / ".config/dot.yaml", True
    return expand_path(path), False


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


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
        mark = getattr(error, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""
        # Parser messages and snippets can include credentials from malformed input.
        raise ValueError(f"failed to parse config file at {resolved}: invalid YAML{location}") from error
    if len(documents) > 1:
        raise ValueError(f"config file at {resolved} must contain exactly one YAML document")
    overlay = documents[0] if documents else {}
    if overlay is None:
        overlay = {}
    if not isinstance(overlay, dict):
        raise ValueError(f"config file at {resolved} must contain a YAML mapping")
    defaults = Config().model_dump(mode="python")
    try:
        return Config.model_validate(_deep_merge(defaults, overlay))
    except RecursionError as error:
        raise ValueError(f"failed to parse config file at {resolved}: YAML nesting is too deep") from error


def dump_config(config: Config) -> str:
    return yaml.safe_dump(config.model_dump(mode="python"), allow_unicode=True, sort_keys=False)
