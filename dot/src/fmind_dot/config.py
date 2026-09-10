"""Strict Python-first configuration for the dot CLI."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

Seconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    """Reject misspelled keys and implicit scalar coercion at the YAML boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ToolConfig(StrictModel):
    binary: str = ""
    args: list[str] = Field(default_factory=list)


def _default_custom_completions() -> dict[str, ToolConfig]:
    return {
        "ast-grep": ToolConfig(args=["completions", "fish"]),
        "atlas": ToolConfig(args=["completion", "fish"]),
        "atuin": ToolConfig(args=["gen-completions", "--shell", "fish"]),
        "bat": ToolConfig(args=["--completion", "fish"]),
        "carapace": ToolConfig(args=["_carapace", "fish"]),
        "codex": ToolConfig(args=["completion", "fish"]),
        "delta": ToolConfig(args=["--generate-completion", "fish"]),
        "doggo": ToolConfig(args=["completions", "fish"]),
        "dot": ToolConfig(binary="env", args=["_DOT_COMPLETE=source_fish", "dot"]),
        "dprint": ToolConfig(args=["completions", "fish"]),
        "fd": ToolConfig(args=["--gen-completions", "fish"]),
        "fkf": ToolConfig(binary="env", args=["_FKF_COMPLETE=source_fish", "fkf"]),
        "gh": ToolConfig(args=["completion", "-s", "fish"]),
        "git-lfs": ToolConfig(binary="git", args=["lfs", "completion", "fish"]),
        "lazygit": ToolConfig(args=["completion", "fish"]),
        "marimo": ToolConfig(binary="env", args=["_MARIMO_COMPLETE=fish_source", "marimo"]),
        "rg": ToolConfig(args=["--generate", "complete-fish"]),
        "ruff": ToolConfig(args=["generate-shell-completion", "fish"]),
        "starship": ToolConfig(args=["completions", "fish"]),
        "ty": ToolConfig(args=["generate-shell-completion", "fish"]),
        "uv": ToolConfig(args=["generate-shell-completion", "fish"]),
        "watchexec": ToolConfig(args=["--completions", "fish"]),
        "xh": ToolConfig(args=["--generate", "complete-fish"]),
        "yq": ToolConfig(args=["shell-completion", "fish"]),
        "zellij": ToolConfig(args=["setup", "--generate-completion", "fish"]),
    }


class CompletionConfig(StrictModel):
    path: str = "~/.config/fish/completions"
    custom_commands: dict[str, ToolConfig] = Field(default_factory=_default_custom_completions)
    tools: list[str] = Field(
        default_factory=lambda: [
            "ast-grep",
            "atlas",
            "atuin",
            "bat",
            "carapace",
            "chezmoi",
            "codex",
            "cosign",
            "delta",
            "doggo",
            "dot",
            "dprint",
            "dyff",
            "fd",
            "fkf",
            "gh",
            "git-lfs",
            "gitleaks",
            "jules",
            "lazygit",
            "lefthook",
            "marimo",
            "mise",
            "rg",
            "ruff",
            "starship",
            "terraform-docs",
            "trivy",
            "ty",
            "uv",
            "watchexec",
            "xh",
            "yq",
            "zellij",
        ]
    )
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


class Config(StrictModel):
    schema_version: Literal[3] = 3
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
