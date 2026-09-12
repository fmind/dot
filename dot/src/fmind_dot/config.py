"""Strict Python-first configuration for the dot CLI."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Seconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    """Reject misspelled keys and implicit scalar coercion at the YAML boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ToolConfig(StrictModel):
    binary: str = ""
    args: list[str] = Field(default_factory=list)
    package: str = ""

    @model_validator(mode="after")
    def one_completion_source(self) -> ToolConfig:
        if self.package and (self.binary or self.args):
            raise ValueError("choose either a bundled package or a completion command")
        return self


def _default_custom_completions() -> dict[str, ToolConfig]:
    return {
        "a2a": ToolConfig(),
        "acli": ToolConfig(),
        "ast-grep": ToolConfig(args=["completions", "fish"]),
        "atuin": ToolConfig(args=["gen-completions", "--shell", "fish"]),
        "bat": ToolConfig(args=["--completion", "fish"]),
        "btm": ToolConfig(package="bottom"),
        "carapace": ToolConfig(args=["carapace", "fish"]),
        "chezmoi": ToolConfig(),
        "codex": ToolConfig(args=["completion", "fish"]),
        "colab": ToolConfig(binary="env", args=["_COLAB_COMPLETE=source_fish", "colab"]),
        "copilot": ToolConfig(),
        "cosign": ToolConfig(),
        "delta": ToolConfig(args=["--generate-completion", "fish"]),
        "doggo": ToolConfig(args=["completions", "fish"]),
        "dot": ToolConfig(binary="env", args=["_DOT_COMPLETE=source_fish", "dot"]),
        "dprint": ToolConfig(args=["completions", "fish"]),
        "dyff": ToolConfig(),
        "fastfetch": ToolConfig(package="fastfetch"),
        "fd": ToolConfig(args=["--gen-completions", "fish"]),
        "fkf": ToolConfig(binary="env", args=["_FKF_COMPLETE=source_fish", "fkf"]),
        "gh": ToolConfig(args=["completion", "-s", "fish"]),
        "git-cliff": ToolConfig(package="git-cliff"),
        "git-lfs": ToolConfig(binary="git", args=["lfs", "completion", "fish"]),
        "gitleaks": ToolConfig(),
        "grok": ToolConfig(args=["completions", "fish"]),
        "hf": ToolConfig(binary="env", args=["_HF_COMPLETE=fish_source", "hf"]),
        "hyperfine": ToolConfig(package="hyperfine"),
        "jules": ToolConfig(),
        "lazygit": ToolConfig(args=["completion", "fish"]),
        "lefthook": ToolConfig(),
        "lsd": ToolConfig(package="lsd"),
        "lychee": ToolConfig(args=["--generate", "complete-fish"]),
        "marimo": ToolConfig(binary="env", args=["_MARIMO_COMPLETE=fish_source", "marimo"]),
        "mise": ToolConfig(),
        "rg": ToolConfig(args=["--generate", "complete-fish"]),
        "ruff": ToolConfig(args=["generate-shell-completion", "fish"]),
        "rustup": ToolConfig(args=["completions", "fish"]),
        "starship": ToolConfig(args=["completions", "fish"]),
        "terraform-docs": ToolConfig(),
        "tree-sitter": ToolConfig(args=["complete", "--shell", "fish"]),
        "trivy": ToolConfig(),
        "ty": ToolConfig(args=["generate-shell-completion", "fish"]),
        "usage": ToolConfig(args=["--completions", "fish"]),
        "uv": ToolConfig(args=["generate-shell-completion", "fish"]),
        "uvx": ToolConfig(args=["--generate-shell-completion", "fish"]),
        "vhs": ToolConfig(package="vhs"),
        "watchexec": ToolConfig(args=["--completions", "fish"]),
        "xh": ToolConfig(args=["--generate", "complete-fish"]),
        "ya": ToolConfig(package="github:sxyazi/yazi"),
        "yazi": ToolConfig(package="github:sxyazi/yazi"),
        "yq": ToolConfig(args=["shell-completion", "fish"]),
        "zellij": ToolConfig(args=["setup", "--generate-completion", "fish"]),
        "zizmor": ToolConfig(args=["--completions", "fish"]),
        "zoxide": ToolConfig(package="zoxide"),
    }


class CompletionConfig(StrictModel):
    path: str = "~/.config/fish/completions"
    custom_commands: dict[str, ToolConfig] = Field(default_factory=_default_custom_completions)
    tools: list[str] = Field(default_factory=lambda: sorted(_default_custom_completions()))
    timeout_seconds: Seconds = 60.0


class PullConfig(StrictModel):
    directories: list[str] = Field(default_factory=lambda: ["~/fmind", "~/fmind-ai", "~/mlops-courses"])
    timeout_seconds: Seconds = 120.0
    concurrency: int = Field(default=8, gt=0)


class AgentDoctorConfig(StrictModel):
    stale_lag_seconds: Seconds = 86400.0
    scan_limit: int = Field(default=16384, gt=0)
    example_limit: int = Field(default=5, ge=0, le=100)


class HookFailureConfig(StrictModel):
    limit: int = Field(default=100, gt=0)
    detail_limit: int = Field(default=512, gt=0)


TokenPrice = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class ModelPrice(StrictModel):
    input: TokenPrice
    output: TokenPrice
    cache_read: TokenPrice | None = None
    cache_write: TokenPrice | None = None


class PricingConfig(StrictModel):
    as_of: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    sources: list[str]
    models: dict[str, ModelPrice]


def default_pricing() -> PricingConfig:
    return PricingConfig.model_validate(yaml.safe_load(Path(__file__).with_name("api-prices.yaml").read_text()))


class SubscriptionConfig(StrictModel):
    renewal_day: int = Field(ge=1, le=31)
    timezone: str = "UTC"
    monthly_usd: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def valid_timezone(self) -> SubscriptionConfig:
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError("subscription timezone must be an IANA timezone such as Europe/Paris") from error
        return self


class AgentConfig(StrictModel):
    sources: dict[str, str] = Field(
        default_factory=lambda: {
            "agy": "~/.gemini/antigravity-cli/brain",
            "claude": "~/.claude/projects",
            "codex": "~/.codex/sessions",
            "copilot": "~/.copilot/session-store.db",
            "grok": "~/.grok/sessions",
        }
    )
    pricing: PricingConfig = Field(default_factory=default_pricing)
    subscriptions: dict[str, SubscriptionConfig] = Field(default_factory=dict)
    doctor: AgentDoctorConfig = Field(default_factory=AgentDoctorConfig)
    hook_failures: HookFailureConfig = Field(default_factory=HookFailureConfig)


class EnvVarsConfig(StrictModel):
    required: list[str] = Field(default_factory=lambda: ["JULES_API_KEY", "STITCH_ACCESS_TOKEN"])
    optional: list[str] = Field(
        default_factory=lambda: [
            "STUDIO_API_KEY",
            "KAGGLE_API_TOKEN",
            "HUGGINGFACE_API_TOKEN",
            "GWS_PROJECT",
            "ANTIGRAVITY_CLOUD_PROJECT",
            "ANTIGRAVITY_CLOUD_LOCATION",
            "ANTIGRAVITY_SDK_API_KEY",
            "GEMINI_API_KEY",
        ]
    )


class SecretConfig(StrictModel):
    path: str
    required_perms: int = 0o600


class DoctorConfig(StrictModel):
    github_host: str = "github.com"
    env_vars: EnvVarsConfig = Field(default_factory=EnvVarsConfig)
    tools: list[str] = Field(
        default_factory=lambda: [
            "age",
            "agy",
            "chezmoi",
            "claude",
            "codex",
            "copilot",
            "cursor-agent",
            "docker",
            "dprint",
            "fkf",
            "gcloud",
            "gh",
            "git",
            "git-cliff",
            "gitleaks",
            "grok",
            "gws",
            "jules",
            "lefthook",
            "marimo",
            "mise",
            "nvim",
            "opencode",
            "python",
            "ruff",
            "sqlite3",
            "tree-sitter",
            "trivy",
            "ty",
            "uv",
        ]
    )
    secrets: list[SecretConfig] = Field(default_factory=lambda: [SecretConfig(path="~/.config/chezmoi/key.txt")])
    probe_timeout_seconds: Seconds = 45.0
    probe_concurrency: int = Field(default=8, gt=0)


# Policy values are data; native command arguments and safety boundaries stay in code.
Scope = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_:/.-]*$")]
Host = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.-]*$")]
Project = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
CacheProvider = Literal["docker", "hf", "uv"]
PruneProvider = Literal["docker", "dprint", "hf", "mise", "npm", "trivy", "uv"]


class GitHubConfig(StrictModel):
    host: Host = "github.com"
    scopes: list[Scope] = Field(
        default_factory=lambda: [
            "gist",
            "notifications",
            "project",
            "read:org",
            "read:packages",
            "read:user",
            "repo",
            "user:email",
            "workflow",
            "write:packages",
            "write:public_key",
        ]
    )
    remove_scopes: list[Scope] = Field(
        default_factory=lambda: ["admin:public_key", "delete:packages", "delete_repo", "user"]
    )

    @model_validator(mode="after")
    def distinct_scopes(self) -> GitHubConfig:
        if set(self.scopes) & set(self.remove_scopes):
            raise ValueError("GitHub scopes and remove_scopes must not overlap")
        return self


class WorkspaceConfig(StrictModel):
    project: Project | None = None
    scopes: list[Scope] = Field(
        default_factory=lambda: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/contacts",
            "https://www.googleapis.com/auth/contacts.other.readonly",
            "https://www.googleapis.com/auth/directory.readonly",
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/forms.body",
            "https://www.googleapis.com/auth/forms.responses.readonly",
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.settings.basic",
            "https://www.googleapis.com/auth/meetings.space.created",
            "https://www.googleapis.com/auth/meetings.space.readonly",
            "https://www.googleapis.com/auth/meetings.space.settings",
            "https://www.googleapis.com/auth/tasks",
            "https://www.googleapis.com/auth/chat.spaces",
            "https://www.googleapis.com/auth/chat.messages",
            "https://www.googleapis.com/auth/chat.memberships",
            "https://www.googleapis.com/auth/chat.users.readstate",
            "https://www.googleapis.com/auth/script.projects",
            "https://www.googleapis.com/auth/script.deployments",
            "https://www.googleapis.com/auth/script.processes",
        ],
        min_length=1,
    )
    apis: list[Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*\.googleapis\.com$")]] = Field(
        default_factory=lambda: [
            "calendar-json.googleapis.com",
            "chat.googleapis.com",
            "docs.googleapis.com",
            "drive.googleapis.com",
            "forms.googleapis.com",
            "gmail.googleapis.com",
            "meet.googleapis.com",
            "people.googleapis.com",
            "script.googleapis.com",
            "sheets.googleapis.com",
            "slides.googleapis.com",
            "tasks.googleapis.com",
        ],
        min_length=1,
    )


class AuthConfig(StrictModel):
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    probe_timeout_seconds: Seconds = 45.0


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
    agent: AgentConfig = Field(default_factory=AgentConfig)
    doctor: DoctorConfig = Field(default_factory=DoctorConfig)


def expand_path(value: str | Path) -> Path:
    text = os.fspath(value)
    if text == "~":
        return Path.home()
    if text.startswith(("~/", "~\\")):
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
    if not resolved.exists():
        if implicit:
            return Config()
        raise FileNotFoundError(f"failed to read config file at {resolved}")
    try:
        with resolved.open(encoding="utf-8") as stream:
            documents = list(yaml.safe_load_all(stream))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"failed to read config file at {resolved}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"failed to read config file at {resolved}: {error}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"failed to parse config file at {resolved}: {error}") from error
    if len(documents) > 1:
        raise ValueError(f"config file at {resolved} must contain exactly one YAML document")
    overlay = documents[0] if documents else {}
    if overlay is None:
        overlay = {}
    if not isinstance(overlay, dict):
        raise ValueError(f"config file at {resolved} must contain a YAML mapping")
    defaults = Config().model_dump(mode="python")
    return Config.model_validate(_deep_merge(defaults, overlay))


def dump_config(config: Config) -> str:
    return yaml.safe_dump(config.model_dump(mode="python"), allow_unicode=True, sort_keys=False)
