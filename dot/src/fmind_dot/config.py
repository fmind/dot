"""Strict Python-first configuration and policy catalogs for the dot CLI."""

from __future__ import annotations

import copy
import functools
import math
import os
import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# `~`, `~/...`, or absolute: a relative workspace would resolve against the caller's directory.
WORKSPACE_PATH_RE = re.compile(r"^(?:~|~/.+|/.*)$")
GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:-?[A-Za-z0-9])*$")
PATH_PATTERN_RE = re.compile(r"^(?:~/|/)\S[^\r\n]*$")
SCOPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_:/.-]*$")
PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
LoginProvider = Literal["colab", "gcp", "github", "workspace"]
LOGIN_PROVIDERS: tuple[LoginProvider, ...] = ("colab", "gcp", "github", "workspace")

# Google's consent page hangs after Allow when one request holds more than 50 scopes (bisected 2026-10-26).
WORKSPACE_SCOPE_LIMIT = 50
_GWS_AUTH = "https://www.googleapis.com/auth/"
_GOOGLE_ALIASES = {"email": f"{_GWS_AUTH}userinfo.email", "profile": f"{_GWS_AUTH}userinfo.profile"}


def expand_google_scope(scope: str) -> str:
    """Expand a bare Google OAuth scope suffix or alias to its canonical identifier."""
    if scope == "openid":
        return scope
    if "://" in scope:
        parts = urllib.parse.urlsplit(scope)
        scheme, netloc, path = parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/")
        if scheme in {"http", "https"} and netloc == "mail.google.com" and not path:
            return "https://mail.google.com/"
        return urllib.parse.urlunsplit((scheme, netloc, path, parts.query, parts.fragment))
    suffix = scope.rstrip("/")
    return _GOOGLE_ALIASES.get(suffix.lower(), f"{_GWS_AUTH}{suffix}")


class ConfigValidationError(ValueError):
    """Strict config or pricing validation error that never echoes invalid input values."""

    def __init__(self, path: tuple[object, ...], reason: str) -> None:
        self.path = path
        self.reason = reason
        dotted = ".".join(str(part) for part in path) or "<root>"
        super().__init__(f"{dotted}: {reason}")


@functools.cache
def policy() -> dict[str, Any]:
    """Return the bundled static tool, scope, API, and completion catalogs."""
    loaded = yaml.safe_load(Path(__file__).with_name("policy.yaml").read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("invalid bundled policy catalog")
    return loaded


_policy = policy()
GITHUB_SCOPES: tuple[str, ...] = tuple(_policy["github"]["scopes"])
GITHUB_REMOVE_SCOPES: tuple[str, ...] = tuple(_policy["github"]["remove_scopes"])
GITHUB_FORBIDDEN_SCOPES: frozenset[str] = frozenset(_policy["github"]["forbidden_scopes"])
WORKSPACE_SCOPES: tuple[str, ...] = ("openid", *(f"{_GWS_AUTH}{s}" for s in _policy["workspace"]["scope_suffixes"]))
WORKSPACE_FORBIDDEN_SCOPES: frozenset[str] = frozenset(_policy["workspace"]["forbidden_scopes"])
WORKSPACE_APIS: tuple[str, ...] = tuple(f"{n}.googleapis.com" for n in _policy["workspace"]["api_names"])
GCP_ADC_SCOPES: tuple[str, ...] = ("openid", *(f"{_GWS_AUTH}{s}" for s in _policy["gcp"]["adc_scope_suffixes"]))


def _expect_mapping(raw: object, allowed: frozenset[str], path: tuple[object, ...]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ConfigValidationError(path, "must be a mapping")
    for key in raw:
        if not isinstance(key, str):
            raise ConfigValidationError(path, "keys must be strings")
        if key not in allowed:
            raise ConfigValidationError((*path, key), "unknown setting")
    return raw


def _expect_str(
    raw: object,
    path: tuple[object, ...],
    *,
    non_empty: bool = False,
    pattern: re.Pattern[str] | None = None,
    max_length: int | None = None,
) -> str:
    if type(raw) is not str:
        raise ConfigValidationError(path, "must be a string")
    if non_empty and not raw:
        raise ConfigValidationError(path, "must not be empty")
    if max_length is not None and len(raw) > max_length:
        raise ConfigValidationError(path, f"must be at most {max_length} characters")
    if pattern is not None and pattern.fullmatch(raw) is None:
        raise ConfigValidationError(path, "does not match required format")
    return raw


def _expect_list[T](
    raw: object, path: tuple[object, ...], parse_item: Callable[[object, tuple[object, ...]], T]
) -> list[T]:
    if not isinstance(raw, list):
        raise ConfigValidationError(path, "must be a list")
    return [parse_item(item, (*path, index)) for index, item in enumerate(raw)]


def _expect_price(raw: object, path: tuple[object, ...]) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise ConfigValidationError(path, "must be a number")
    try:
        value = float(raw)
    except OverflowError as error:
        raise ConfigValidationError(path, "must be a finite number") from error
    if not math.isfinite(value) or value < 0:
        raise ConfigValidationError(path, "must be a non-negative finite number")
    return value


def _parse_provider(raw: object, path: tuple[object, ...]) -> LoginProvider:
    if raw == "colab":
        return "colab"
    if raw == "gcp":
        return "gcp"
    if raw == "github":
        return "github"
    if raw == "workspace":
        return "workspace"
    raise ConfigValidationError(path, f"must be one of {', '.join(LOGIN_PROVIDERS)}")


@dataclass
class PullConfig:
    directories: list[str] = field(default_factory=lambda: ["~/fmind"])

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> PullConfig:
        data = _expect_mapping(raw, frozenset({"directories"}), path)
        if "directories" not in data:
            return cls()
        dirs = _expect_list(
            data["directories"],
            (*path, "directories"),
            lambda v, p: _expect_str(v, p, pattern=WORKSPACE_PATH_RE),
        )
        return cls(directories=dirs)


@dataclass
class TrustConfig:
    github_owners: list[str] = field(default_factory=lambda: ["fmind"])
    agy_projects: list[str] = field(default_factory=lambda: ["~/.local/share/chezmoi"])

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> TrustConfig:
        data = _expect_mapping(raw, frozenset({"github_owners", "agy_projects"}), path)
        kwargs: dict[str, Any] = {}
        if "github_owners" in data:
            kwargs["github_owners"] = _expect_list(
                data["github_owners"],
                (*path, "github_owners"),
                lambda v, p: _expect_str(v, p, pattern=GITHUB_OWNER_RE, max_length=39),
            )
        if "agy_projects" in data:
            kwargs["agy_projects"] = _expect_list(
                data["agy_projects"],
                (*path, "agy_projects"),
                lambda v, p: _expect_str(v, p, pattern=PATH_PATTERN_RE),
            )
        return cls(**kwargs)


@dataclass
class ModelPrice:
    input: float
    output: float
    cache_read: float | None = None
    cache_write: float | None = None
    cache_write_1h: float | None = None

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> ModelPrice:
        allowed = frozenset({"input", "output", "cache_read", "cache_write", "cache_write_1h"})
        data = _expect_mapping(raw, allowed, path)
        for req in ("input", "output"):
            if req not in data:
                raise ConfigValidationError((*path, req), "required setting missing")
        kwargs: dict[str, float | None] = {}
        for name in ("input", "output"):
            kwargs[name] = _expect_price(data[name], (*path, name))
        for opt in ("cache_read", "cache_write", "cache_write_1h"):
            if opt in data and data[opt] is not None:
                kwargs[opt] = _expect_price(data[opt], (*path, opt))
        return cls(
            input=float(kwargs["input"] or 0.0),
            output=float(kwargs["output"] or 0.0),
            cache_read=kwargs.get("cache_read"),
            cache_write=kwargs.get("cache_write"),
            cache_write_1h=kwargs.get("cache_write_1h"),
        )


@dataclass
class PricingConfig:
    as_of: str
    basis: str
    sources: list[str]
    models: dict[str, ModelPrice]

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...] = ()) -> PricingConfig:
        data = _expect_mapping(raw, frozenset({"as_of", "basis", "sources", "models"}), path)
        for req in ("as_of", "basis", "sources", "models"):
            if req not in data:
                raise ConfigValidationError((*path, req), "required setting missing")
        as_of = _expect_str(data["as_of"], (*path, "as_of"), non_empty=True)
        basis = _expect_str(data["basis"], (*path, "basis"), non_empty=True)
        sources = _expect_list(data["sources"], (*path, "sources"), lambda v, p: _expect_str(v, p))
        raw_models = data["models"]
        if not isinstance(raw_models, dict):
            raise ConfigValidationError((*path, "models"), "must be a mapping")
        models: dict[str, ModelPrice] = {}
        for key, value in raw_models.items():
            if type(key) is not str or not key:
                raise ConfigValidationError((*path, "models"), "model names must be non-empty strings")
            models[key] = ModelPrice.from_raw(value, (*path, "models", key))
        return cls(as_of=as_of, basis=basis, sources=sources, models=models)


@functools.cache
def _parsed_default_pricing() -> PricingConfig:
    loaded = yaml.safe_load(Path(__file__).with_name("api-prices.yaml").read_text(encoding="utf-8"))
    return PricingConfig.from_raw(loaded)


def default_pricing() -> PricingConfig:
    """Return the bundled API token price table."""
    return copy.deepcopy(_parsed_default_pricing())


@dataclass
class WorkspaceConfig:
    project: str | None = None
    extra_scopes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if {expand_google_scope(s).lower() for s in self.extra_scopes} & WORKSPACE_FORBIDDEN_SCOPES:
            raise ConfigValidationError(
                ("auth", "workspace", "extra_scopes"),
                "contains a forbidden high-risk scope (https://mail.google.com/, gmail.settings.sharing, or cloud-platform)",
            )
        if len(self.scopes) > WORKSPACE_SCOPE_LIMIT:
            raise ConfigValidationError(
                ("auth", "workspace", "extra_scopes"),
                f"workspace scopes cannot exceed {WORKSPACE_SCOPE_LIMIT} entries ({len(self.scopes)})",
            )

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> WorkspaceConfig:
        data = _expect_mapping(raw, frozenset({"project", "extra_scopes"}), path)
        project: str | None = None
        if "project" in data and data["project"] is not None:
            project = _expect_str(data["project"], (*path, "project"), pattern=PROJECT_RE)
        extra_scopes: list[str] = []
        if "extra_scopes" in data:
            extra_scopes = _expect_list(
                data["extra_scopes"],
                (*path, "extra_scopes"),
                lambda v, p: _expect_str(v, p, non_empty=True, pattern=SCOPE_RE),
            )
        return cls(project=project, extra_scopes=extra_scopes)

    @property
    def scopes(self) -> list[str]:
        return list(dict.fromkeys([*WORKSPACE_SCOPES, *(expand_google_scope(s) for s in self.extra_scopes)]))


@dataclass
class AuthConfig:
    login: list[LoginProvider] = field(default_factory=lambda: ["github", "gcp", "workspace"])
    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> AuthConfig:
        data = _expect_mapping(raw, frozenset({"login", "workspace"}), path)
        kwargs: dict[str, Any] = {}
        if "login" in data:
            providers = _expect_list(data["login"], (*path, "login"), _parse_provider)
            if not providers:
                raise ConfigValidationError((*path, "login"), "must contain at least one provider")
            kwargs["login"] = providers
        if "workspace" in data:
            kwargs["workspace"] = WorkspaceConfig.from_raw(data["workspace"], (*path, "workspace"))
        return cls(**kwargs)


@dataclass
class PrivacyConfig:
    allowed_tokens: list[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: object, path: tuple[object, ...]) -> PrivacyConfig:
        data = _expect_mapping(raw, frozenset({"allowed_tokens"}), path)
        if "allowed_tokens" not in data:
            return cls()
        tokens = _expect_list(data["allowed_tokens"], (*path, "allowed_tokens"), lambda v, p: _expect_str(v, p))
        return cls(allowed_tokens=tokens)


@dataclass
class Config:
    schema_version: int = 3
    auth: AuthConfig = field(default_factory=AuthConfig)
    pull: PullConfig = field(default_factory=PullConfig)
    trust: TrustConfig = field(default_factory=TrustConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)

    @classmethod
    def from_raw(cls, raw: object) -> Config:
        data = _expect_mapping(raw, frozenset({"schema_version", "auth", "pull", "trust", "privacy"}), ())
        kwargs: dict[str, Any] = {}
        if "schema_version" in data:
            ver = data["schema_version"]
            if type(ver) is not int or ver != 3:
                raise ConfigValidationError(("schema_version",), "must be 3")
            kwargs["schema_version"] = 3
        if "auth" in data:
            kwargs["auth"] = AuthConfig.from_raw(data["auth"], ("auth",))
        if "pull" in data:
            kwargs["pull"] = PullConfig.from_raw(data["pull"], ("pull",))
        if "trust" in data:
            kwargs["trust"] = TrustConfig.from_raw(data["trust"], ("trust",))
        if "privacy" in data:
            kwargs["privacy"] = PrivacyConfig.from_raw(data["privacy"], ("privacy",))
        return cls(**kwargs)


def expand_path(value: str | Path, *, home: Path | None = None) -> Path:
    text = os.fspath(value)
    if text == "~":
        return home or Path.home()
    return (home or Path.home()) / text[2:] if text.startswith("~/") else Path(text)


def env_path(name: str, default: Path, *, expand_vars: bool = True) -> Path:
    """Resolve an environment path override, expanding `~/` and optional `$VARS`."""
    if raw := os.environ.get(name):
        return expand_path(os.path.expandvars(raw) if expand_vars else raw)
    return default


def xdg_dir(name: str, default: str | Path) -> Path:
    """Resolve an XDG base-directory override; empty or relative values fall back to `default`."""
    if (raw := os.environ.get(name)) and (candidate := expand_path(os.path.expandvars(raw))).is_absolute():
        return candidate
    return default if isinstance(default, Path) else Path.home() / default


def config_file_path(path: str | Path | None) -> tuple[Path, bool]:
    if path is None or os.fspath(path) == "":
        return Path.home() / ".config/dot.yaml", True
    return expand_path(path), False


def yaml_error_location(error: BaseException) -> str:
    mark = getattr(error, "problem_mark", None)
    return f"line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""


def load_config(path: str | Path | None = None) -> Config:
    resolved, implicit = config_file_path(path)
    try:
        documents = list(yaml.safe_load_all(resolved.read_text(encoding="utf-8")))
    except FileNotFoundError as error:
        if implicit:
            return Config()
        raise FileNotFoundError(f"failed to read config file at {resolved}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"failed to read config file at {resolved}: {error}") from error
    except (yaml.YAMLError, RecursionError) as error:
        where = yaml_error_location(error)
        raise ValueError(
            f"failed to parse config file at {resolved}: invalid YAML{f' at {where}' if where else ''}"
        ) from error
    if len(documents) > 1:
        raise ValueError(f"config file at {resolved} must contain exactly one YAML document")
    overlay = documents[0] if documents and documents[0] is not None else {}
    if not isinstance(overlay, dict):
        raise ValueError(f"config file at {resolved} must contain a YAML mapping")
    return Config.from_raw(overlay) if overlay else Config()
