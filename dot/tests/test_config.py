from __future__ import annotations

import dataclasses
import os
from pathlib import Path

import pytest

from fmind_dot.config import (
    Config,
    ConfigValidationError,
    WorkspaceConfig,
    config_file_path,
    env_path,
    load_config,
    policy,
    xdg_dir,
)


def test_defaults_and_schema_version_are_python_first() -> None:
    config = Config()
    assert config.schema_version == 3
    assert {f.name for f in dataclasses.fields(Config)} == {"schema_version", "auth", "pull", "trust", "privacy"}
    assert config.trust.github_owners == ["fmind"]
    assert config.trust.agy_projects == ["~/.local/share/chezmoi"]
    assert len(config.auth.workspace.scopes) > 5
    assert "github" in policy()


@pytest.mark.parametrize("pattern", ["fmind/agent-*", "", "~", "~/ x", "./repo"])
def test_agy_projects_must_be_absolute_or_home_paths(tmp_path: Path, pattern: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(f"trust:\n  agy_projects: ['{pattern}']\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError):
        load_config(path)


@pytest.mark.parametrize(("value", "suffix"), [("", ".cache"), ("rel/cache", ".cache"), ("~/xdg", "xdg")])
def test_xdg_dir_and_env_path_and_config_file_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str, suffix: str
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", value)
    assert xdg_dir("XDG_CACHE_HOME", ".cache") == tmp_path / suffix
    monkeypatch.setenv("CUSTOM_DIR", "~/sub")
    assert env_path("CUSTOM_DIR", tmp_path / "fallback") == tmp_path / "sub"
    assert config_file_path(None) == (tmp_path / ".config/dot.yaml", True)
    assert config_file_path("~/explicit.yaml") == (tmp_path / "explicit.yaml", False)


def test_load_config_overlay_and_strict_validation(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(
        "pull:\n  directories: [~/code]\ntrust:\n  github_owners: [acme]\n"
        "privacy:\n  allowed_tokens: [CustomToken]\n"
        "auth:\n  workspace:\n    project: my-proj-1\n    extra_scopes: [youtube.readonly]\n",
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.pull.directories == ["~/code"]
    assert config.trust.agy_projects == ["~/.local/share/chezmoi"]
    assert config.privacy.allowed_tokens == ["CustomToken"]
    assert config.auth.workspace.project == "my-proj-1"
    assert "https://www.googleapis.com/auth/youtube.readonly" in config.auth.workspace.scopes
    assert config.trust is not Config().trust

    for forbidden in (
        "cloud-platform",
        "CLOUD-PLATFORM/",
        "https://mail.google.com/",
        "https://mail.google.com",
        "https://mail.google.com:443/",
        "http://mail.google.com:80/",
        "HTTPS://Mail.Google.Com/",
        "http://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com:443/auth/cloud-platform",
        "https://www.googleapis.com//auth/./cloud-platform/",
        "HTTPS://WWW.GOOGLEAPIS.COM/auth/cloud-platform/",
        "foo/../cloud-platform",
        "gmail.settings.sharing",
    ):
        path.write_text(f"auth:\n  workspace:\n    extra_scopes: ['{forbidden}']\n", encoding="utf-8")
        with pytest.raises(ConfigValidationError, match="forbidden high-risk scope"):
            load_config(path)

    for invalid_scope in (
        "https://www.googleapis.com/auth/",
        "https://www.googleapis.com/AUTH/",
        "https://www.googleapis.com/auth/..",
        "https://www.googleapis.com/bar",
        "https://www.googleapis.com/",
        "https:///",
        "a://",
        "foo/..",
        "foo/../../bar",
    ):
        path.write_text(f"auth:\n  workspace:\n    extra_scopes: ['{invalid_scope}']\n", encoding="utf-8")
        with pytest.raises(ConfigValidationError, match="invalid Google OAuth scope"):
            load_config(path)

    with pytest.raises(ConfigValidationError, match="invalid Google OAuth scope"):
        WorkspaceConfig(extra_scopes=["/drive"])

    excess = ", ".join(f"scope_{i}" for i in range(60))
    path.write_text(f"auth:\n  workspace:\n    extra_scopes: [{excess}]\n", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="workspace scopes cannot exceed"):
        load_config(path)

    for bad_yaml, match in (
        ("schema_version: true\n", r"schema_version: must be 3"),
        ("auth:\n  login: []\n", r"auth\.login: must contain at least one"),
        ("auth:\n  login: [bogus]\n", r"auth\.login\.0: must be one of"),
        ("auth:\n  extra: 1\n", r"auth\.extra: unknown setting"),
    ):
        path.write_text(bad_yaml, encoding="utf-8")
        with pytest.raises(ConfigValidationError, match=match) as caught:
            load_config(path)
        assert "bogus" not in str(caught.value)


@pytest.mark.parametrize(
    ("content", "exc", "match"),
    [
        ("unknown: true\n", ConfigValidationError, "unknown"),
        ("pull:\n  directories: [~/a]\n---\npull:\n  directories: [~/b]\n", ValueError, "exactly one YAML"),
        ("- item\n", ValueError, "YAML mapping"),
        ("pull: [\n", ValueError, r"failed to parse config file at .*line "),
        (b"\xff", ValueError, r"failed to read config file at "),
        ("a: " + "[" * 1000 + "]" * 1000, ValueError, r"failed to parse config file at "),
    ],
)
def test_load_config_rejects_invalid_inputs_safely(
    tmp_path: Path, content: str | bytes, exc: type[Exception], match: str
) -> None:
    path = tmp_path / "bad.yaml"
    path.write_bytes(content) if isinstance(content, bytes) else path.write_text(content, encoding="utf-8")
    with pytest.raises(exc, match=match):
        load_config(path)


def test_load_config_missing_and_unreadable_default_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert load_config(None) == Config()
    with pytest.raises(FileNotFoundError, match="failed to read config file"):
        load_config(tmp_path / "missing.yaml")
    default = tmp_path / ".config/dot.yaml"
    default.parent.mkdir()
    default.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(ValueError, match="failed to read config file"):
        load_config(None)
    if os.geteuid() != 0:
        default.rmdir()
        default.write_text("schema_version: 3\n", encoding="utf-8")
        default.chmod(0o000)
        try:
            with pytest.raises(ValueError, match="failed to read config file"):
                load_config(None)
        finally:
            default.chmod(0o600)
