from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from fmind_dot.config import COMPLETION_SOURCES, Config, ToolConfig, config_file_path, expand_path, load_config


def test_python_first_defaults_replace_retired_stacks() -> None:
    config = Config()

    assert config.schema_version == 3
    assert set(Config.model_fields) == {
        "schema_version",
        "agent",
        "doctor",
        "completions",
        "pull",
        "trust",
        "auth",
        "cache",
        "prune",
    }
    assert config.trust.github_owners == ["fmind", "fmind-ai", "mlops-courses"]
    assert config.trust.agy_projects_exclude == [
        "~/fmind/agent-*",
        "~/fmind/fgraph",
        "~/fmind/mcp-context-benchmark",
    ]


@pytest.mark.parametrize("pattern", ["fmind/agent-*", "", "~", "~/ x", "./repo"])
def test_agy_project_exclusions_must_name_absolute_or_home_paths(tmp_path: Path, pattern: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(f"trust:\n  agy_projects_exclude: ['{pattern}']\n", encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


def test_verify_inventory_covers_managed_harnesses_and_core_workflows() -> None:
    config = Config()
    expected = {*config.agent.sources, "opencode", "bf"}
    assert expected <= set(config.doctor.tools)


def test_retired_tools_are_not_workstation_requirements() -> None:
    config = Config()
    retired = {"cursor-agent", "jules", "marimo", "pyrit"}
    assert not retired.intersection(config.doctor.tools)
    assert not retired.intersection(COMPLETION_SOURCES)


def test_cloud_and_k8s_tools_are_included_in_default_completions() -> None:
    assert {"astro", "aws-sso-util", "cf", "databricks", "pup"} <= set(COMPLETION_SOURCES)


@pytest.mark.parametrize("source", COMPLETION_SOURCES.values())
def test_completion_sources_choose_one_kind(source: ToolConfig) -> None:
    assert not (source.package and (source.binary or source.args))


def test_load_config_is_strict_and_rejects_trailing_documents(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text("unknown: true\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(unknown)

    trailing = tmp_path / "trailing.yaml"
    trailing.write_text("ai:\n  binary: claude\n---\nai:\n  binary: codex\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one YAML document"):
        load_config(trailing)


def test_config_overlay_replaces_lists_and_merges_maps(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("doctor:\n  tools: [python]\ncompletions:\n  path: ~/fish\n", encoding="utf-8")

    config = load_config(path)

    assert config.doctor.tools == ["python"]
    assert config.doctor.secrets == Config().doctor.secrets
    assert config.completions.path == "~/fish"


@pytest.mark.parametrize("document", ["completions:\n  tools: [uv]\n", "completions:\n  custom_commands: {}\n"])
def test_removed_configuration_fields_are_rejected(tmp_path: Path, document: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(path)


def test_load_config_wraps_yaml_and_decode_failures_with_path_context(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("prune: [\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"failed to parse config file at .*malformed\.yaml"):
        load_config(malformed)

    undecodable = tmp_path / "undecodable.yaml"
    undecodable.write_bytes(b"\xff")
    with pytest.raises(ValueError, match=r"failed to read config file at .*undecodable\.yaml"):
        load_config(undecodable)

    directory = tmp_path / "directory.yaml"
    directory.mkdir()
    with pytest.raises(ValueError, match=r"failed to read config file at .*directory\.yaml"):
        load_config(directory)


@pytest.mark.skipif(os.geteuid() == 0, reason="Root bypasses owner directory permissions")
def test_unreadable_default_config_never_falls_back_to_default_policy(tmp_path: Path) -> None:
    path = tmp_path / ".config/dot.yaml"
    path.parent.mkdir()
    path.write_text("prune:\n  providers: [mise]\n")
    assert load_config().prune.providers == ["mise"]
    path.parent.chmod(0)
    try:
        with pytest.raises(ValueError, match="failed to read config file") as caught:
            load_config()
        assert isinstance(caught.value.__cause__, PermissionError)
    finally:
        path.parent.chmod(0o700)
    assert load_config().prune.providers == ["mise"]


def test_path_resolution_expands_only_current_home(tmp_path: Path) -> None:

    assert expand_path("~") == tmp_path
    assert expand_path("~/project") == tmp_path / "project"
    assert expand_path("~someone/project") == Path("~someone/project")
    assert config_file_path(None) == (tmp_path / ".config/dot.yaml", True)


@pytest.mark.parametrize("content", ["", "---\n"])
def test_empty_config_documents_use_defaults(tmp_path: Path, content: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(content, encoding="utf-8")

    assert load_config(path) == Config()


def test_config_document_requires_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("- invalid\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        load_config(path)


@pytest.mark.parametrize(
    "document",
    [
        "auth:\n  github:\n    scopes: [repo]\n    remove_scopes: [repo]\n",
        "auth:\n  github:\n    scopes: ['repo,delete_repo']\n",
        "auth:\n  github:\n    scopes: ['--help']\n",
        "auth:\n  github:\n    host: github.com\n",
        "auth:\n  workspace:\n    scopes: []\n",
        "auth:\n  workspace:\n    project: '--flags-file=oops'\n",
        "auth:\n  workspace:\n    apis: ['--all']\n",
        "cache:\n  providers: [unknown]\n",
        "prune:\n  providers: []\n",
    ],
)
def test_workstation_policy_rejects_invalid_settings(tmp_path: Path, document: str) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text(document)
    with pytest.raises(ValidationError):
        load_config(path)


def test_scope_lists_replace_defaults_and_default_instances_are_independent(tmp_path: Path) -> None:
    path = tmp_path / "dot.yaml"
    path.write_text("auth:\n  workspace:\n    scopes: [openid]\ncache:\n  providers: [uv]\n")
    config = load_config(path)
    assert config.auth.workspace.scopes == ["openid"]
    assert config.auth.workspace.apis == Config().auth.workspace.apis
    assert config.cache.providers == ["uv"]
    first = Config()
    first.auth.github.scopes.append("custom")
    assert "custom" not in Config().auth.github.scopes
