"""Strict Python-first configuration and policy catalogs for the dot CLI."""

from __future__ import annotations

import functools
import os
import posixpath
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
LoginProvider = Literal["gcp", "github", "workspace"]
LOGIN_PROVIDERS: tuple[LoginProvider, ...] = ("gcp", "github", "workspace")

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
        scheme = parts.scheme.lower()
        host = (parts.hostname or "").lower()
        if not host:
            return scope.lower()
        is_google_host = host in {"mail.google.com", "www.googleapis.com"}
        if is_google_host and scheme in {"http", "https"}:
            scheme = "https"
        netloc = host if is_google_host else parts.netloc.lower()
        collapsed = re.sub(r"/+", "/", parts.path)
        norm_path = posixpath.normpath(collapsed) if collapsed else ""
        if norm_path in {".", "/"}:
            norm_path = ""
        if scheme == "https" and host == "mail.google.com" and not norm_path:
            return "https://mail.google.com/"
        return urllib.parse.urlunsplit((scheme, netloc, norm_path.rstrip("/"), parts.query, parts.fragment))
    suffix = scope.rstrip("/")
    if not suffix:
        return ""
    if (alias := _GOOGLE_ALIASES.get(suffix.lower())) is not None:
        return alias
    return expand_google_scope(f"{_GWS_AUTH}{suffix}")


def is_valid_google_scope(scope: str) -> bool:
    """Return True when an expanded Google OAuth scope is non-empty and under /auth/<name> for googleapis."""
    if not SCOPE_RE.fullmatch(scope) or scope.rstrip("/").lower() == "https://www.googleapis.com/auth":
        return False
    if "://" in scope:
        parts = urllib.parse.urlsplit(scope)
        host = (parts.hostname or "").lower()
        if parts.scheme not in {"http", "https"} or not host:
            return False
        if host == "www.googleapis.com":
            path = parts.path.lower()
            if not path.startswith("/auth/") or not path.removeprefix("/auth/").strip("/"):
                return False
    return True


class ConfigValidationError(ValueError):
    """Strict config validation error that never echoes invalid input values."""

    def __init__(self, path: tuple[object, ...], reason: str) -> None:
        self.path = path
        self.reason = reason
        dotted = ".".join(str(part) for part in path) or "<root>"
        super().__init__(f"{dotted}: {reason}")


@functools.cache
def policy() -> dict[str, Any]:
    """Return the bundled static tool, scope, and API catalogs."""
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


def _parse_provider(raw: object, path: tuple[object, ...]) -> LoginProvider:
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
class WorkspaceConfig:
    project: str | None = None
    extra_scopes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if any(not SCOPE_RE.fullmatch(s) for s in self.extra_scopes):
            raise ConfigValidationError(("auth", "workspace", "extra_scopes"), "contains an invalid Google OAuth scope")
        expanded = [expand_google_scope(s) for s in self.extra_scopes]
        if any(not is_valid_google_scope(s) for s in expanded):
            raise ConfigValidationError(("auth", "workspace", "extra_scopes"), "contains an invalid Google OAuth scope")
        if {s.lower() for s in expanded} & WORKSPACE_FORBIDDEN_SCOPES:
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


def env_path(name: str, default: Path) -> Path:
    """Resolve an environment path override, expanding `~/`."""
    if raw := os.environ.get(name):
        return expand_path(raw)
    return default


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
